import os
import duckdb
from datetime import datetime
from langchain_ollama import ChatOllama
from langchain_core.prompts import ChatPromptTemplate

# --- SYSTEM PROFILE TARGET NODE PROPERTIES ---
MINIO_ENDPOINT = "192.168.6.51:9000"
MINIO_ACCESS_KEY = "admin"
MINIO_SECRET_KEY = "minio_secure_password"
OUTPUT_DIR = r"D:\CAN\saved_compositions"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Mount local RTX 3080 execution core brain
llm = ChatOllama(model="llama3", temperature=0.1)

def run_sandbox_execution(sql_query: str):
    """The isolated local execution engine loop wrapper."""
    try:
        ctx = duckdb.connect()
        ctx.execute("SET home_directory='C:\\Windows\\Temp';")
        ctx.execute("INSTALL httpfs; LOAD httpfs;")
        ctx.execute(f"SET s3_endpoint='{MINIO_ENDPOINT}';")
        ctx.execute(f"SET s3_access_key_id='{MINIO_ACCESS_KEY}';")
        ctx.execute(f"SET s3_secret_access_key='{MINIO_SECRET_KEY}';")
        ctx.execute("SET s3_use_ssl=false; SET s3_url_style='path';")
        
        # Execute the query block
        df = ctx.execute(sql_query).df()
        ctx.close()
        return "SUCCESS", df.to_string(index=False)
    except Exception as e:
        ctx.close()
        return "CRASHED", str(e)

def compose_deterministic_report(user_intent: str):
    print("================================================================")
    print("🎼 AI Composition Core: Self-Healing SQL Script Writer")
    print("================================================================\n")
    
    # Initialize the history tracking string context
    current_attempt = 1
    max_healing_loops = 5
    
    system_directive = """You are an expert data engineer writing SQL code for DuckDB to query an S3 MinIO storage lakehouse.
    Target files layout schema:
    's3://silver-lakehouse/year_month=202606/vehicle_id=van_01/data.parquet' (Columns: timestamp, id, engine_rpm, vehicle_speed_mph, coolant_temp_c)
    
    You must output ONLY a valid SQL query block wrapped inside standard triple backticks. Do not write text explanations."""
    
    conversation_history = [
        ("system", system_directive),
        ("human", f"Write a query to achieve this intent: {user_intent}")
    ]
    
    prompt_template = ChatPromptTemplate.from_messages(conversation_history)

    while current_attempt <= max_healing_loops:
        print(f"🎵 Attempt #{current_attempt}: Local AI is writing code...")
        
        # Call local GPU to generate the code block
        formatted_prompt = prompt_template.format_messages()
        ai_response = llm.invoke(formatted_prompt)
        raw_content = ai_response.content
        
        # Extract the SQL code out from the markdown text markers cleanly
        if "```sql" in raw_content:
            generated_sql = raw_content.split("```sql")[1].split("```")[0].strip()
        elif "```" in raw_content:
            generated_sql = raw_content.split("```")[1].split("```")[0].strip()
        else:
            generated_sql = raw_content.strip()

        print(f"🔧 [Sandbox Execution] Testing Code Block:\n{generated_sql}\n")
        
        # Pass code straight into our local sandbox engine
        status, console_output = run_sandbox_execution(generated_sql)
        
        if status == "SUCCESS":
            print("🎉 SUCCESS! The composition is perfect and executed flawlessly.")
            print("--------------------------------------------------------------------------------")
            print(console_output)
            print("--------------------------------------------------------------------------------\n")
            
            # --- THE MOZART LOCKDOWN STEP ---
            # Save the sheet music out to a file so it is permanently deterministic
            filename = f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.sql"
            filepath = os.path.join(OUTPUT_DIR, filename)
            
            with open(filepath, "w") as f:
                f.write(f"-- USER INTENT: {user_intent}\n")
                f.write(f"-- COMPILED DETERMINISTICALLY ON: {datetime.now()}\n\n")
                f.write(generated_sql)
                
            print(f"💾 Sheet Music Captured! Permanent SQL logic saved to: {filepath}")
            print("This report can now be executed directly and repeatedly with 100% determinism.\n")
            return
            
        else:
            # SELF-HEALING REGRESSION: Feed the raw error logs straight back to the model brain
            print(f"❌ CRASHED! Sandbox engine caught compilation error:\n   {console_output}\n")
            print("🔄 Activating self-healing loop feedback parameters...")
            
            # Append the error context to the LangChain message log array
            prompt_template.append_placeholder = True
            conversation_history.extend([
                ("ai", raw_content),
                ("human", f"Your previous query crashed with this error: {console_output}. Please correct your syntax and rewrite the query completely.")
            ])
            prompt_template = ChatPromptTemplate.from_messages(conversation_history)
            current_attempt += 1

    print("❌ Failure: Self-healing loop exceeded max depth bounds without resolution.")

if __name__ == "__main__":
    # Test your self-healing composer loop with an open-ended fleet question
    prompt = "Get the average speed in MPH and max RPM for van_01 from our silver storage file."
    compose_deterministic_report(prompt)
