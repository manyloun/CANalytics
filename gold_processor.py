import os
import pandas as pd

# --- SYSTEM CONFIGURATION ---
GOLD_DIR = r"D:\CAN\wican_gold"
os.makedirs(GOLD_DIR, exist_ok=True)

# MinIO S3 configurations for reading our clean Silver data tables
s3_storage_options = {
    "key": "admin",
    "secret": "minio_secure_password",
    "client_kwargs": {"endpoint_url": "http://192.168.6.51:9000"}
}

def generate_gold_fleet_analytics():
    print("================================================================")
    print("Generating Medallion Gold Layer: Fleet Executive Summary Metrics (S3-Native)")
    print("================================================================\n")
    
    # Explicitly target our three clean fleet assets
    active_fleet_vans = ["van_01", "van_02", "van_03"]
    summary_records = []

    for vehicle_id in active_fleet_vans:
        # Define target direct remote endpoint URL paths
        s3_parquet_url = f"s3://silver-lakehouse/year_month=202606/vehicle_id={vehicle_id}/data.parquet"
        print(f"Streaming and aggregating Silver Data from MinIO for: {vehicle_id}")
        
        try:
            # Query the target dataset over the network
            df = pd.read_parquet(s3_parquet_url, storage_options=s3_storage_options)
            
            start_time = df['timestamp'].min()
            end_time = df['timestamp'].max()
            trip_duration_mins = (end_time - start_time).total_seconds() / 60.0
            
            max_speed = df['vehicle_speed_mph'].max()
            avg_speed = df['vehicle_speed_mph'].mean()
            max_rpm = df['engine_rpm'].max()
            avg_coolant_temp = df['coolant_temp_c'].mean()
            
            idle_mask = (df['vehicle_speed_mph'] == 0) & (df['engine_rpm'] > 500)
            idle_rows = idle_mask.sum()
            idle_seconds = idle_rows * 0.5
            idle_mins = idle_seconds / 60.0
            
            overspeed_instances = (df['vehicle_speed_mph'] > 70).sum() * 0.5

            summary_records.append({
                'vehicle_id': vehicle_id,
                'trip_start': start_time,
                'trip_end': end_time,
                'duration_minutes': round(trip_duration_mins, 2),
                'idle_minutes': round(idle_mins, 2),
                'idle_ratio_pct': round((idle_mins / trip_duration_mins) * 100, 2) if trip_duration_mins > 0 else 0,
                'max_speed_mph': int(max_speed) if pd.notna(max_speed) else 0,
                'avg_speed_mph': round(avg_speed, 1) if pd.notna(avg_speed) else 0,
                'max_rpm': int(max_rpm) if pd.notna(max_rpm) else 0,
                'avg_temp_c': round(avg_coolant_temp, 1) if pd.notna(avg_coolant_temp) else 0,
                'overspeed_seconds': int(overspeed_instances)
            })
        except Exception as e:
            print(f"Skipping {vehicle_id}: URL not found or bucket permissions error. {e}")

    if not summary_records:
        return
        
    gold_df = pd.DataFrame(summary_records)
    gold_parquet = os.path.join(GOLD_DIR, "fleet_trip_summaries.parquet")
    gold_csv = os.path.join(GOLD_DIR, "fleet_trip_summaries.csv")
    
    gold_df.to_parquet(gold_parquet, index=False)
    gold_df.to_csv(gold_csv, index=False)
    
    print("\n🚀 GOLD BUSINESS INTELLIGENCE METRICS PROFILED (MPH):")
    print("--------------------------------------------------------------------------------")
    print(gold_df.to_string(index=False, columns=[
        'vehicle_id', 'duration_minutes', 'idle_minutes', 'idle_ratio_pct', 'max_speed_mph', 'overspeed_seconds'
    ]))
    print("--------------------------------------------------------------------------------")

if __name__ == "__main__":
    generate_gold_fleet_analytics()
