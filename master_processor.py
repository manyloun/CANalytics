import os
import glob
import pandas as pd

# --- SYSTEM SETTINGS ---
BASE_DIR = r"D:\CAN"
BRONZE_DIR = os.path.join(BASE_DIR, "wican_bronze", "year_month=202606")
CHUNK_SIZE = 50000

# --- MINIO S3 LAKEHOUSE CONNECTION PROPERTIES ---
# Replace these strings with your exact MinIO Root / User Credentials
MINIO_ENDPOINT = "http://192.168.6.51:9000"
MINIO_ACCESS_KEY = "admin"
MINIO_SECRET_KEY = "minio_secure_password"
MINIO_BUCKET = "silver-lakehouse"

s3_storage_options = {
    "key": MINIO_ACCESS_KEY,
    "secret": MINIO_SECRET_KEY,
    "client_kwargs": {"endpoint_url": MINIO_ENDPOINT}
}

# --- DATA QUALITY LOGICAL BOUNDARIES (U.S. IMPERIAL UNITS) ---
VALID_RPM_MIN = 500       
VALID_RPM_MAX = 6500      
VALID_SPEED_MIN = 0       
VALID_SPEED_MAX = 85      # Max safe operational speed bound for a transit van in MPH
VALID_TEMP_MIN = -20      
VALID_TEMP_MAX = 120      

def decode_and_audit_stream(df):
    """
    Decodes raw CAN stream hex payloads into true physical units
    while checking physical data boundaries using aligned array indexes.
    """
    df['engine_rpm'] = pd.Series(dtype='Int32')
    df['vehicle_speed_mph'] = pd.Series(dtype='Int16')  
    df['coolant_temp_c'] = pd.Series(dtype='Float32')
    
    df['dq_status'] = 'PASSED'
    df['dq_notes'] = ''

    malformed_mask = df['id'].isna() | df['data'].isna() | (df['data'].str.len() < 2)
    if malformed_mask.any():
        df.loc[malformed_mask, 'dq_status'] = 'FAILED'
        df.loc[malformed_mask, 'dq_notes'] += '[Structural Error: Missing/Empty payload bytes] '

    mask_engine = (df['id'] == "0x0C4") & (~malformed_mask) & (df['data'].str.len() >= 6)
    mask_thermal = (df['id'] == "0x7E8") & (~malformed_mask) & (df['data'].str.len() >= 8)
    
    # --- DECODE ENGINE PACKETS (0x0C4) ---
    if mask_engine.any():
        raw_rpm = df.loc[mask_engine, 'data'].str.slice(0, 4).apply(int, base=16)
        decoded_rpm = (raw_rpm // 4).astype('Int32')
        
        raw_speed_kph = df.loc[mask_engine, 'data'].str.slice(4, 6).apply(int, base=16)
        decoded_speed_mph = (raw_speed_kph * 0.621371).round().astype('Int16')

        rpm_anomaly = (decoded_rpm < VALID_RPM_MIN) | (decoded_rpm > VALID_RPM_MAX)
        speed_anomaly = (decoded_speed_mph < VALID_SPEED_MIN) | (decoded_speed_mph > VALID_SPEED_MAX)
        
        full_rpm_error_mask = pd.Series(False, index=df.index)
        full_rpm_error_mask.loc[mask_engine] = rpm_anomaly.values
        
        full_speed_error_mask = pd.Series(False, index=df.index)
        full_speed_error_mask.loc[mask_engine] = speed_anomaly.values

        if full_rpm_error_mask.any():
            df.loc[full_rpm_error_mask, 'dq_status'] = 'FAILED'
            df.loc[full_rpm_error_mask, 'dq_notes'] += '[Boundary Error: RPM Out of Physical Range] '
            decoded_rpm[rpm_anomaly] = pd.NA
            
        if full_speed_error_mask.any():
            df.loc[full_speed_error_mask, 'dq_status'] = 'FAILED'
            df.loc[full_speed_error_mask, 'dq_notes'] += '[Boundary Error: Speed Out of Physical Range] '
            decoded_speed_mph[speed_anomaly] = pd.NA

        df.loc[mask_engine, 'engine_rpm'] = decoded_rpm
        df.loc[mask_engine, 'vehicle_speed_mph'] = decoded_speed_mph
        
    # --- DECODE THERMAL PACKETS (0x7E8) ---
    if mask_thermal.any():
        raw_temp = df.loc[mask_thermal, 'data'].str.slice(6, 8).apply(int, base=16)
        decoded_temp = (raw_temp - 40).astype('Float32')

        temp_anomaly = (decoded_temp < VALID_TEMP_MIN) | (decoded_temp > VALID_TEMP_MAX)
        
        full_temp_error_mask = pd.Series(False, index=df.index)
        full_temp_error_mask.loc[mask_thermal] = temp_anomaly.values

        if full_temp_error_mask.any():
            df.loc[full_temp_error_mask, 'dq_status'] = 'FAILED'
            df.loc[full_temp_error_mask, 'dq_notes'] += '[Boundary Error: Temperature Out of Physical Range] '
            decoded_temp[temp_anomaly] = pd.NA

        df.loc[mask_thermal, 'coolant_temp_c'] = decoded_temp
        
    df.loc[df['dq_notes'] == '', 'dq_notes'] = 'Clean: Verified OBD Line Signal'
    return df

if __name__ == "__main__":
    print("================================================================")
    print("Medallion Lakehouse Pipeline: Ingesting to MinIO S3 Object Store")
    print("================================================================\n")
    
    bronze_files = glob.glob(os.path.join(BRONZE_DIR, "*.json"))
    
    if not bronze_files:
        print(f"Error: No raw Bronze data files detected in {BRONZE_DIR}")
        exit()
        
    for file_path in bronze_files:
        file_name = os.path.basename(file_path)
        print(f"Processing: {file_name}")
        
        # Identify vehicle ID from filename layout
        parts = file_name.split("_")
        vehicle_id = f"{parts[0]}_{parts[1]}"
        
        # Define cloud-native S3 file paths
        s3_target_url = f"s3://{MINIO_BUCKET}/year_month=202606/vehicle_id={vehicle_id}/data.parquet"
        
        master_dataframe_list = []
        total_rows, total_failed_rows = 0, 0
        
        # Stream raw inputs and decode chunks
        for chunk in pd.read_json(file_path, lines=True, chunksize=CHUNK_SIZE):
            chunk['timestamp'] = pd.to_datetime(chunk['ts'], unit='ms', utc=True)
            processed_chunk = decode_and_audit_stream(chunk)
            
            total_rows += len(processed_chunk)
            total_failed_rows += (processed_chunk['dq_status'] == 'FAILED').sum()
            
            final_columns = [
                'timestamp', 'id', 'engine_rpm', 'vehicle_speed_mph', 
                'coolant_temp_c', 'dq_status', 'dq_notes'
            ]
            master_dataframe_list.append(processed_chunk[final_columns])
            
        # Combine chunks into a single clean dataframe
        full_trip_df = pd.concat(master_dataframe_list, ignore_index=True)
        
        # Enforce column data typing patterns
        full_trip_df = full_trip_df.astype({
            'id': 'category',
            'engine_rpm': 'Int32',
            'vehicle_speed_mph': 'Int16',
            'coolant_temp_c': 'Float32',
            'dq_status': 'category',
            'dq_notes': 'string'
        })
        
        # Upload directly to your MinIO silver-lakehouse bucket
        full_trip_df.to_parquet(
            s3_target_url,
            index=False,
            compression="SNAPPY",
            storage_options=s3_storage_options
        )
            
        failure_rate = (total_failed_rows / total_rows) * 100 if total_rows > 0 else 0
        print(f" └── MinIO S3 Profile Status:")
        print(f"     ├── Packets Uploaded: {total_rows}")
        print(f"     ├── Failed Signatures: {total_failed_rows} ({failure_rate:.2f}%)")
        print(f"     └── Lakehouse Destination:  {s3_target_url}\n")
        
    print("Silver Lakehouse Stage processing completed successfully!")
