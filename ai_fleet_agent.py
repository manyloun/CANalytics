import os
import argparse
import urllib.request
import json
import duckdb
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama
from prompt_toolkit import PromptSession
from prompt_toolkit.key_binding import KeyBindings

# Parse command line arguments
parser = argparse.ArgumentParser(description="AI Fleet Operations Agent")
parser.add_argument("--backend", type=str, choices=["ollama", "openai"], default="ollama", 
                    help="Choose the AI backend to use (default: ollama)")
parser.add_argument("--ollama-model", type=str, default=None, 
                    help="Ollama model to use. If not specified, available models will be listed.")
parser.add_argument("--ollama-url", type=str, default="http://192.168.5.65:11434", 
                    help="Ollama API endpoint URL")
args = parser.parse_args()

# --- SYSTEM & STORAGE ENVIRONMENT CONFIGURATIONS ---
MINIO_ENDPOINT = "192.168.6.51:9000"
MINIO_ACCESS_KEY = "admin"
MINIO_SECRET_KEY = "minio_secure_password"

def fetch_all_lakehouse_data():
    """
    Natively connects to MinIO over the network wire, aggregates the raw
    metrics via DuckDB, and returns a string data summary for the AI.
    """
    print("\n⚡ [System Action] Actively pulling streaming data metrics from MinIO S3...")
    try:
        ctx = duckdb.connect()
        ctx.execute("SET home_directory='C:\\Windows\\Temp';")
        ctx.execute("INSTALL httpfs; LOAD httpfs;")
        ctx.execute(f"SET s3_endpoint='{MINIO_ENDPOINT}';")
        ctx.execute(f"SET s3_access_key_id='{MINIO_ACCESS_KEY}';")
        ctx.execute(f"SET s3_secret_access_key='{MINIO_SECRET_KEY}';")
        ctx.execute("SET s3_use_ssl=false; SET s3_url_style='path';")
        
        # UNIVERSAL FIX: Switched to cross-platform epoch(time) parsing to support the local PC runtime
        master_sql = """
        SELECT
          'van_01' AS vehicle_id,
          ROUND((epoch(MAX(timestamp)) - epoch(MIN(timestamp))) / 60.0, 2) AS total_duration_minutes,
          ROUND((COUNT(CASE WHEN vehicle_speed_mph = 0 AND engine_rpm > 500 THEN 1 END) * 0.5) / 60.0, 2) AS idle_minutes,
          ROUND((idle_minutes / total_duration_minutes) * 100, 2) AS idle_ratio_pct
        FROM 's3://silver-lakehouse/year_month=202606/vehicle_id=van_01/data.parquet'
        
        UNION ALL
        
        SELECT
          'van_02' AS vehicle_id,
          ROUND((epoch(MAX(timestamp)) - epoch(MIN(timestamp))) / 60.0, 2) AS total_duration_minutes,
          ROUND((COUNT(CASE WHEN vehicle_speed_mph = 0 AND engine_rpm > 500 THEN 1 END) * 0.5) / 60.0, 2) AS idle_minutes,
          ROUND((idle_minutes / total_duration_minutes) * 100, 2) AS idle_ratio_pct
        FROM 's3://silver-lakehouse/year_month=202606/vehicle_id=van_02/data.parquet'
        
        UNION ALL
        
        SELECT
          'van_03' AS vehicle_id,
          ROUND((epoch(MAX(timestamp)) - epoch(MIN(timestamp))) / 60.0, 2) AS total_duration_minutes,
          ROUND((COUNT(CASE WHEN vehicle_speed_mph = 0 AND engine_rpm > 500 THEN 1 END) * 0.5) / 60.0, 2) AS idle_minutes,
          ROUND((idle_minutes / total_duration_minutes) * 100, 2) AS idle_ratio_pct
        FROM 's3://silver-lakehouse/year_month=202606/vehicle_id=van_03/data.parquet';
        """
        
        df = ctx.execute(master_sql).df()
        ctx.close()
        
        print("\n✅ [System Success] Lakehouse Data Matrix Successfully Streamed:")
        print("--------------------------------------------------------------------------------")
        print(df.to_string(index=False))
        print("--------------------------------------------------------------------------------\n")
        
        return df.to_string(index=False)
    except Exception as e:
        print(f"❌ [System Failure] Database error encountered: {str(e)}")
        return f"Database error encountered: {str(e)}"

def get_available_ollama_models(base_url):
    try:
        req = urllib.request.Request(f"{base_url}/api/tags")
        with urllib.request.urlopen(req, timeout=2.0) as response:
            data = json.loads(response.read().decode())
            return [model['name'] for model in data.get('models', [])]
    except Exception as e:
        print(f"❌ Failed to fetch models from Ollama: {e}")
        return []

print(f"Initializing Context-Fed AI Fleet Operations Agent Node (Backend: {args.backend.upper()})...")

if args.backend == "openai":
    llm = ChatOpenAI(model="gpt-4o", temperature=0.1)
    agent_label = "OpenAI"
else:
    model_to_use = args.ollama_model
    if not model_to_use:
        print(f"\n🔍 Scanning available Ollama models at {args.ollama_url}...")
        models = get_available_ollama_models(args.ollama_url)
        if not models:
            print("⚠️ No models found or Ollama is unreachable. Defaulting to 'llama3.1:8b'.")
            model_to_use = "llama3.1:8b"
        else:
            print("Available Ollama Models:")
            for i, m in enumerate(models):
                print(f"  [{i+1}] {m}")
            
            while True:
                try:
                    choice = input(f"Select a model number [1-{len(models)}] (default: 1): ")
                    if choice.strip() == "":
                        model_to_use = models[0]
                        break
                    idx = int(choice) - 1
                    if 0 <= idx < len(models):
                        model_to_use = models[idx]
                        break
                    else:
                        print("Invalid selection. Try again.")
                except ValueError:
                    print("Please enter a valid number.")
                    
    print(f"✅ Using Ollama model: {model_to_use}")
    llm = ChatOllama(base_url=args.ollama_url, model=model_to_use, temperature=0.1)
    agent_label = f"Ollama ({model_to_use})"

# Fetch the live dataset right now on startup
fleet_data_matrix = fetch_all_lakehouse_data()

system_prompt = f"""You are an elite automated AI Operations Agent managing a DFW transit shuttle van fleet.
You are running live inside a clean terminal session window with no database errors.

Here is the exact live operational data matrix pulled from the lakehouse objects right now:
{fleet_data_matrix}

Route behaviors profile context:
- van_01: Sheraton DFW Irving highway run.
- van_02: Gaylord Texan resort long cruise run.
- van_03: Hyatt Regency internal terminal loop run.

Read the provided matrix data directly, interpret the numbers logistically, and provide clear corporate recommendations to improve efficiency or lower fuel waste."""

prompt_template = ChatPromptTemplate.from_messages([
    ("system", system_prompt),
    ("human", "{user_input}")
])

if __name__ == "__main__":
    print(f"🚀 AI Fleet Operations Agent ({agent_label}) Online and Connected to MinIO Data Lake!")
    print("---------------------------------------------------------------------")
    print(f"You can now ask the {agent_label} AI conversational questions regarding your vans.")
    print("Press [Shift+Tab] to cycle through saved prompts from prompts.txt!")
    print("Type 'exit' to shut down the session link.\n")
    
    # Load preset prompts from file
    preset_prompts = []
    try:
        with open("prompts.txt", "r", encoding="utf-8") as f:
            preset_prompts = [line.strip() for line in f.readlines() if line.strip()]
    except FileNotFoundError:
        pass

    prompt_index = -1
    bindings = KeyBindings()

    @bindings.add('s-tab')
    def _(event):
        global prompt_index
        if not preset_prompts:
            return
        prompt_index = (prompt_index + 1) % len(preset_prompts)
        event.app.current_buffer.text = preset_prompts[prompt_index]
        event.app.current_buffer.cursor_position = len(preset_prompts[prompt_index])

    session = PromptSession(key_bindings=bindings)
    
    while True:
        try:
            user_query = session.prompt(f"Ask the AI Agent ({agent_label}) 🤖 > ")
        except (KeyboardInterrupt, EOFError):
            break
            
        if user_query.lower() == 'exit':
            break
            
        if not user_query.strip():
            continue
            
        print(f"\nThinking... Formulating Fleet Analytics Profile using {agent_label}...")
        
        try:
            formatted_prompt = prompt_template.format_messages(user_input=user_query)
            ai_response = llm.invoke(formatted_prompt)
            
            print(f"🤖 [{agent_label} Fleet Agent Response]:\n{ai_response.content}\n")
        except Exception as e:
            print(f"❌ [AI Error] Failed to generate response. Check if Ollama is running and model exists.")
            print(f"Error Details: {e}\n")
