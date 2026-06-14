You are thinking like a seasoned Data Architect. Relying on raw hardware telemetry without validation is a recipe for broken dashboards down the road. Automotive networks are notorious for transient voltage spikes, loose adapter pins, or bus-collision garbage frames that can inject impossible values into your system.
Adding a Data Quality (DQ) and Profiling Layer into the master_processor.py engine ensures that anomalies (like a van suddenly traveling at 400 km/h or an engine reporting -10,000 RPM) are caught, flagged, and safely handled before they corrupt your clean Silver layer.
------------------------------
## The Data Quality Rules Blueprint
We will enforce three specific layers of data validation inside the processor:

   1. Structural Checks: Ensure mandatory fields (ts, id, data) exist and are populated.
   2. Physical Boundary Audits: Validate that the decoded telemetry aligns with the physical limits of a standard passenger shuttle van.
   3. Quarantine Handling: Instead of crashing the script, rows failing quality tests are stripped of their bad telemetry values, flagged with a dq_status="FAILED", and logged to an isolated tracking column.

------------------------------
## Updated Master Processor with Integrated Data Quality & Profiling
Replace your master_processor.py script with this updated version. It introduces a comprehensive profiling stage and appends data quality telemetry metadata directly into your output Parquet tables.

import osimport globimport pandas as pdimport pyarrow as paimport pyarrow.parquet as pq
# --- SYSTEM CONFIGURATION ---BASE_DIR = r"D:\CAN"BRONZE_DIR = os.path.join(BASE_DIR, "wican_bronze", "year_month=202606")SILVER_BASE_DIR = os.path.join(BASE_DIR, "wican_silver", "year_month=202606")CHUNK_SIZE = 50000
# --- DATA QUALITY LOGICAL BOUNDARIES ---# Define physical real-world limits for a standard transit vanVALID_RPM_MIN = 500       # Lowest operational hot idleVALID_RPM_MAX = 6500      # Redline ceiling limitVALID_SPEED_MIN = 0       # StationaryVALID_SPEED_MAX = 140     # Max physical top speed safe bound (kph)VALID_TEMP_MIN = -20      # Extreme cold weather startVALID_TEMP_MAX = 120      # Serious boiling / overheating threshold
def decode_and_audit_stream(df):
    """
    Decodes the raw CAN stream while executing real-time data profiling
    and data quality boundary verification rules.
    """
    # Initialize target columns
    df['engine_rpm'] = pd.Series(dtype='Int32')
    df['vehicle_speed_kph'] = pd.Series(dtype='Int16')
    df['coolant_temp_c'] = pd.Series(dtype='Float32')
    
    # Initialize Data Quality Metadata Tracking Columns
    df['dq_status'] = 'PASSED'
    df['dq_notes'] = ''

    # 1. STRUCTURAL DQ AUDIT: Catch missing or blank data elements
    malformed_mask = df['id'].isna() | df['data'].isna() | (df['data'].str.len() < 2)
    if malformed_mask.any():
        df.loc[malformed_mask, 'dq_status'] = 'FAILED'
        df.loc[malformed_mask, 'dq_notes'] += '[Structural Error: Missing/Empty payload bytes] '

    # Define masks for structural processing
    mask_engine = (df['id'] == "0x0C4") & (~malformed_mask) & (df['data'].str.len() >= 6)
    mask_thermal = (df['id'] == "0x7E8") & (~malformed_mask) & (df['data'].str.len() >= 8)
    
    # --- DECODE & PROFILE ENGINE DATA (0x0C4) ---
    if mask_engine.any():
        raw_rpm = df.loc[mask_engine, 'data'].str.slice(0, 4).apply(int, base=16)
        decoded_rpm = (raw_rpm // 4).astype('Int32')
        
        raw_speed = df.loc[mask_engine, 'data'].str.slice(4, 6).apply(int, base=16)
        decoded_speed = raw_speed.astype('Int16')

        # Run boundary profiling checks across the engine slice
        rpm_anomaly = (decoded_rpm < VALID_RPM_MIN) | (decoded_rpm > VALID_RPM_MAX)
        speed_anomaly = (decoded_speed < VALID_SPEED_MIN) | (decoded_speed > VALID_SPEED_MAX)
        
        # Isolate anomalies within the engine mask context
        full_rpm_error_mask = mask_engine & rpm_anomaly
        full_speed_error_mask = mask_engine & speed_anomaly

        # Apply flags and clean up values so they don't break downstream metrics
        if full_rpm_error_mask.any():
            df.loc[full_rpm_error_mask, 'dq_status'] = 'FAILED'
            df.loc[full_rpm_error_mask, 'dq_notes'] += '[Boundary Error: RPM Out of Physical Range] '
            decoded_rpm[rpm_anomaly] = pd.NA
            
        if full_speed_error_mask.any():
            df.loc[full_speed_error_mask, 'dq_status'] = 'FAILED'
            df.loc[full_speed_error_mask, 'dq_notes'] += '[Boundary Error: Speed Out of Physical Range] '
            decoded_speed[speed_anomaly] = pd.NA

        df.loc[mask_engine, 'engine_rpm'] = decoded_rpm
        df.loc[mask_engine, 'vehicle_speed_kph'] = decoded_speed
        
    # --- DECODE & PROFILE THERMAL DATA (0x7E8) ---
    if mask_thermal.any():
        raw_temp = df.loc[mask_thermal, 'data'].str.slice(6, 8).apply(int, base=16)
        decoded_temp = (raw_temp - 40).astype('Float32')

        # Run boundary profiling check for engine temperature
        temp_anomaly = (decoded_temp < VALID_TEMP_MIN) | (decoded_temp > VALID_TEMP_MAX)
        full_temp_error_mask = mask_thermal & temp_anomaly

        if full_temp_error_mask.any():
            df.loc[full_temp_error_mask, 'dq_status'] = 'FAILED'
            df.loc[full_temp_error_mask, 'dq_notes'] += '[Boundary Error: Temperature Out of Physical Range] '
            decoded_temp[temp_anomaly] = pd.NA

        df.loc[mask_thermal, 'coolant_temp_c'] = decoded_temp
        
    # Clean up empty strings for files that fully passed validation checks
    df.loc[df['dq_notes'] == '', 'dq_notes'] = 'Clean: Verified OBD Line Signal'
    return df
if __name__ == "__main__":
    print("================================================================")
    print("Medallion Silver Pipeline Master Processing Engine with Integrated DQ")
    print("================================================================\n")
    
    bronze_files = glob.glob(os.path.join(BRONZE_DIR, "*.json"))
    
    if not bronze_files:
        print(f"Error: No raw Bronze data files detected in {BRONZE_DIR}")
        exit()
        
    for file_path in bronze_files:
        file_name = os.path.basename(file_path)
        print(f"Ingesting: {file_name}")
        
        # Simple split logic to handle file naming pattern cleanly
        parts = file_name.split("_")
        vehicle_id = f"{parts[0]}_{parts[1]}"
        
        vehicle_silver_dir = os.path.join(SILVER_BASE_DIR, f"vehicle_id={vehicle_id}")
        os.makedirs(vehicle_silver_dir, exist_ok=True)
        parquet_output_file = os.path.join(vehicle_silver_dir, "data.parquet")
        
        parquet_writer = None
        total_rows, total_failed_rows = 0, 0
        
        for chunk in pd.read_json(file_path, lines=True, chunksize=CHUNK_SIZE):
            chunk['timestamp'] = pd.to_datetime(chunk['ts'], unit='ms', utc=True)
            
            # Execute processing and data quality assessment simultaneously
            processed_chunk = decode_and_audit_stream(chunk)
            
            # Update diagnostic tracking metrics
            total_rows += len(processed_chunk)
            total_failed_rows += (processed_chunk['dq_status'] == 'FAILED').sum()
            
            # Keep structural auditing records alongside business metrics for lineage tracking
            final_columns = [
                'timestamp', 'id', 'engine_rpm', 'vehicle_speed_kph', 
                'coolant_temp_c', 'dq_status', 'dq_notes'
            ]
            output_df = processed_chunk[final_columns]
            
            output_df = output_df.astype({
                'id': 'category',
                'engine_rpm': 'Int32',
                'vehicle_speed_kph': 'Int16',
                'coolant_temp_c': 'Float32',
                'dq_status': 'category',
                'dq_notes': 'string'
            })
            
            arrow_table = pa.Table.from_pandas(output_df, preserve_index=False)
            
            if parquet_writer is None:
                parquet_writer = pq.ParquetWriter(parquet_output_file, arrow_table.schema, compression='SNAPPY')
                
            parquet_writer.write_table(arrow_table)
            
        if parquet_writer:
            parquet_writer.close()
            
        # Display an administrative summary profile for each file run
        failure_rate = (total_failed_rows / total_rows) * 100 if total_rows > 0 else 0
        print(f" └── Profiling Summary:")
        print(f"     ├── Total Packets Evaluated: {total_rows}")
        print(f"     ├── Failed DQ Signatures:    {total_failed_rows} ({failure_rate:.2f}%)")
        print(f"     └── Target Asset Node:       {vehicle_silver_dir}/data.parquet\n")
        
    print("Silver Stage Processing with DQ Guardrails completed successfully!")

------------------------------
## 3. The New Silver Parquet Schema Shape
With these data quality safeguards in place, your resulting Silver layer table includes robust internal tracking metrics:

| Column Name | Data Type | Sample Value | Purpose / Logic |
|---|---|---|---|
| timestamp | TIMESTAMP(US, TZ=UTC) | 2026-06-14 15:58:01 | Chronological tracking index |
| engine_rpm | INT32 (Nullable) | 2150 | Stripped down to null if boundary check fails |
| vehicle_speed_kph | INT16 (Nullable) | 64 | Stripped down to null if boundary check fails |
| dq_status | DICTIONARY (STRING) | "FAILED" | Administrative flag (PASSED or FAILED) |
| dq_notes | STRING | "[Boundary Error: RPM Out of Physical Range] " | Explains exactly what triggered the failure |

## Test the Guardrails
If you want to verify your data validation logic right now, open one of your raw wican_bronze trip logs (.json) using a text editor. Alter one line's payload data field to something completely impossible, like an astronomical hex code string FFFFFFFFFFFFFFFF.
When you execute python master_processor.py, you will see the console log update automatically, registering the failed signature check while cleanly finishing its data compaction run.
Should we progress to building out your final Gold Layer aggregation views using these validated Silver files? We can summarize trip statistics like total mileage, average speeds, and a breakdown of vehicle operational health flags.
------------------------------
Quick questions if you have time:

* Which data layer should we build next?
* How is the text-to-code balance so far?


