import os
import duckdb
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import ChatOpenAI

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

print("Initializing Context-Fed AI Fleet Operations Agent Node...")
llm = ChatOpenAI(model="gpt-4o", temperature=0.1)

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
    print("🚀 AI Fleet Operations Agent Online and Connected to MinIO Data Lake!")
    print("---------------------------------------------------------------------")
    print("You can now ask the AI conversational questions regarding your vans.")
    print("Type 'exit' to shut down the session link.\n")
    
    while True:
        user_query = input("Ask the AI Agent 🤖 > ")
        if user_query.lower() == 'exit':
            break
            
        if not user_query.strip():
            continue
            
        print("\nThinking... Formulating Fleet Analytics Profile...")
        
        formatted_prompt = prompt_template.format_messages(user_input=user_query)
        ai_response = llm.invoke(formatted_prompt)
        
        print(f"🤖 [AI Fleet Agent Response]:\n{ai_response.content}\n")
