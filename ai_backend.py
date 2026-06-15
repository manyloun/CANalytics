import json
from langchain_ollama import ChatOllama
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.tools import tool
from alert_manager import add_alert_rule, get_recent_alert_history
from simulation_engine import fleet_state

@tool
def create_alert_rule(vehicle_id: str, metric: str, operator: str, threshold: float, message: str) -> str:
    """
    Creates a persistent alert rule that runs in the background.
    WARNING: DO NOT CALL THIS TOOL TO ANSWER QUESTIONS ABOUT DATA! 
    ONLY call this tool if the user explicitly commands you with "alert me", "monitor", "notify me", or "set an alert".
    
    Args:
        vehicle_id: The ID of the van ('van_01', 'van_02', 'van_03') or 'all' for all vans.
        metric: The telemetry metric to monitor ('speed', 'rpm', 'temp', 'fuel', 'idle_time_seconds').
        operator: The comparison operator ('>', '<', '>=', '<=', '==', '!=').
        threshold: The numeric threshold to trigger the alert.
        message: The message to send when the alert triggers.
    Returns:
        A confirmation message.
    """
    add_alert_rule(vehicle_id, metric, operator, threshold, message)
    return f"Successfully created alert for {vehicle_id} when {metric} {operator} {threshold}."

# Configure the LLM
# In a real setup, we could pass this via args or env, but let's default to Ollama locally.
llm = ChatOllama(base_url="http://192.168.5.65:11434/", model="llama3.1:8b", temperature=0.1)

# Bind the tools to the LLM
llm_with_tools = llm.bind_tools([create_alert_rule])

system_prompt = """You are an elite automated AI Operations Agent managing a DFW transit shuttle van fleet.
You are running inside a real-time web simulation (SimFleet).

Here is the exact live operational data matrix right now:
{live_data}

Here is the recent historical alert log containing exact telemetry snapshots at the time each alert triggered:
{alert_history_data}

CRITICAL RULES:
1. If the user asks a question about the fleet data (e.g., "Which van has the worst idle ratio?"), you MUST ONLY answer their question using the {live_data}. DO NOT create an alert.
2. If the user asks WHY an alert occurred (e.g. "Why did van1 idle?"), you MUST cross-reference the {alert_history_data} telemetry snapshots to deduce the reason (e.g., speed was 0 because fuel was 0).
3. If, and ONLY if, the user explicitly commands you to "alert me", "monitor", "notify me", or "set up an alert", you MUST use the `create_alert_rule` tool.
Metrics available: speed, rpm, temp, fuel, idle_time_seconds. Time is evaluated in seconds.

Provide clear corporate recommendations or confirm when you've successfully scheduled a background task."""

prompt_template = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{user_input}")
])

async def process_chat(user_query: str) -> str:
    try:
        live_data = json.dumps(fleet_state, indent=2)
        
        # Format history
        history_rows = get_recent_alert_history(limit=15)
        history_str = "No recent alerts."
        if history_rows:
            history_str = "\n".join([f"[{r[0]}] Rule {r[1]} for {r[2]} triggered '{r[3]}'. Snapshot: {r[4]}" for r in history_rows])
            
        formatted_prompt = prompt_template.format_messages(
            live_data=live_data, 
            alert_history_data=history_str,
            user_input=user_query
        )
        
        response = llm.invoke(formatted_prompt)
        
        # Determine if we should allow the model to use the tool based on strict keyword matching
        trigger_words = ["alert", "monitor", "notify", "track", "watch"]
        wants_alert = any(word in user_query.lower() for word in trigger_words)
        
        if wants_alert:
            llm_with_tools = llm.bind_tools([create_alert_rule])
            response = llm_with_tools.invoke(formatted_prompt)
        else:
            response = llm.invoke(formatted_prompt)
            
        # Check if the LLM decided to call a tool
        if response.tool_calls:
            tool_responses = []
            for tool_call in response.tool_calls:
                if tool_call['name'] == 'create_alert_rule':
                    res = create_alert_rule.invoke(tool_call['args'])
                    tool_responses.append(res)
            return "🔧 Action Taken:\n" + "\n".join(tool_responses) + f"\n\n🤖 [AI]: I have configured the persistent background alert(s) as requested."
        
        return response.content
    except Exception as e:
        return f"❌ [AI Error] Failed to generate response: {str(e)}"
