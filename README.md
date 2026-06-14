## 🚐 DFW Shuttle Fleet Transit Tracker: Medallion Data Lakehouse Platform
An enterprise-grade, cloud-native telemetry tracking platform built to ingest, validate, and analyze high-frequency CAN bus data streams. Designed for an active vehicle shuttle fleet servicing major transit hubs like the Sheraton DFW Airport Hotel (Irving), Gaylord Texan Resort (Grapevine), and the Hyatt Regency DFW International Airport.
This system runs on a three-tier Medallion Architecture using file-level edge data targets, an index-aligned automated Data Quality (DQ) profiling pipeline, a MinIO S3 cloud-native object store network lakehouse, and live interactive query monitoring engines driven by DuckDB and Grafana.
------------------------------
## 🏗️ Architectural Topology Blueprint

 [Fleet Vehicles] 
    ├── van_01 (Sheraton) ──> [Raw Batch Files] ──> [Bronze JSON Logs] 
    ├── van_02 (Gaylord)                          │
    └── van_03 (Hyatt)                            ▼
                                         [Master Ingestion Engine]
                                                  │
 [Grafana Visual Cockpit]                         ├── 1. Hex Payload Decoder
           ▲                                      ├── 2. Vectorized Math (MPH)
           │                                      └── 3. Data Quality Audit 
     (DuckDB Engine)                                      │
           ▲                                              ▼
           └────────────────── [MinIO S3 Store] <── [Silver Parquet Tables]
                                      │
                                      ▼
                               [Gold Aggregations] ──> Executive KPI Summaries

------------------------------
## 🗂️ Project Directory Infrastructure

D:\CAN\
├── ai_fleet_agent.py        # Autonomous Fleet AI Agent powered by LLMs
├── van1.py                  # Telemetry Stream Engine: Sheraton Route
├── van2.py                  # Telemetry Stream Engine: Gaylord Texan Route
├── van3.py                  # Telemetry Stream Engine: Hyatt Terminal Loop
├── master_processor.py      # Silver ETL Engine: Ingests, Audits, Streams to MinIO S3
├── gold_processor.py        # Gold Analytics Engine: Compiles Fleet KPI Summaries
├── wican_bronze\            # Append-Only File Vault (Automated Network Dump Target)
├── wican_silver\            # Local backup/testing store for Parquet files
├── wican_gold\              # Local backup/testing store for KPI summaries
└── docs\                    # Project Documentation

------------------------------
## 🎛️ The Medallion Tier Schema Engine## 1. Bronze Layer (Raw Append-Only Data Store)
Automated file dump capturing unfiltered vehicle network states. Emulates raw broadcast communication messages flying across the car's Controller Area Network (CAN Bus) interface using a high-velocity event-driven design reminiscent of an Apache Kafka event broker system.

* Format: Line-delimited time-series JSON blocks.
* Properties: ts (Hardware real-time millisecond epoch timestamp), id (Computer system component module address hash hex tag), data (8-byte packed sensor hexadecimal string string payload context).

## 2. Silver Layer (Decoded & Audited Parquet Data Store)
The pipeline engine maps raw hex arrays via vectorized Pandas calculations, enforces strict data typing structures, runs physical boundary checks, and scales natively over the network straight into a centralized MinIO object store bucket (silver-lakehouse).

* Format: Column-oriented Apache Parquet compressed via SNAPPY partitioning.
* Schema Map:
* timestamp (TIMESTAMP_TZ): Clock tracking parameter corrected to localized view regions.
   * id (CATEGORY): Component packet source identifier (e.g., 0x0C4 for Engine, 0x7E8 for Thermal).
   * engine_rpm (INT32): Clean vehicle running speed value.
   * vehicle_speed_mph (INT16): Raw metric converted to true U.S. Imperial standard units via a 0.621371 multiplier scaling coefficient.
   * coolant_temp_c (FLOAT32): Core thermal monitoring parameter.
   * dq_status (CATEGORY): Audit validation marker status string (PASSED / FAILED).
   * dq_notes (STRING): Administrative diagnostic logging path for automated data validation checks.

## Integrated Data Quality Guardrails
To prevent corrupted signals, anomalies, or transient hardware errors from breaking downstream metrics, data profiles are checked against real-world physical limits before they leave the edge:

* Engine RPM: 500 to 6500 RPM range boundary check bounds.
* Vehicle Speed: 0 to 85 MPH threshold boundary limit.
* Coolant Temperature: -20°C to 120°C thermal boundary guardrails.

Anomalous rows are automatically stripped of bad values to protect analytics aggregations, logged with a FAILED tag, and mapped with custom reason codes in the logging column.
## 3. Gold Layer (Fleet Business Intelligence aggregates)
Queries clean Silver storage objects using cloud-native S3 bindings to produce trip summary aggregates for the executive fleet tracking dashboard view:

* Core Fleet Metrics Profiled: Total transit duration minutes, active vehicle Idle Time Tracking (isolates stationary idling at baggage loops where speed is 0 but the engine runs), idle ratio percentiles, maximum velocity caps, and safety event tracking (detecting instances where speeds exceed 70 MPH).

------------------------------
## 🐋 Ubuntu Docker deployment environment
Deployed on a home network server running an Ubuntu-based container architecture over node address IP 192.168.6.51.
## Docker Compose Stack Configuration (/opt/grafana-stack/docker-compose.yml)
To support the low-level C++ binary bindings required by the analytics query engine, the platform runs an Ubuntu-based Grafana container core runtime. The system includes a persistent named volume to handle user plugin states safely:

services:
  grafana:
    image: grafana/grafana:latest-ubuntu
    container_name: fleet_grafana
    restart: unless-stopped
    ports:
      - "3005:3000"
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_PLUGINS_ALLOW_LOADING_UNSIGNED_PLUGINS=motherduck-duckdb-datasource
    volumes:
      - grafana_storage:/var/lib/grafana
      - ./plugins:/var/lib/grafana/plugins
volumes:
  grafana_storage:
    driver: local

------------------------------
## 🦆 Embedded Query Gateway: DuckDB Integration
DuckDB runs inside the Grafana presentation tier as an embedded analytics gateway. Because it uses an open-source, vectorized execution model and tracks files by column blocks, it can stream specific columns out of MinIO Parquet files on demand. This completely removes the need to maintain heavy, expensive background database services on your host server.
## MinIO Data Source Initialization SQL (Grafana GUI Configuration)
To securely map cloud objects into standard SQL relations inside Grafana, the data source uses this network configuration startup rule:

SET home_directory='/tmp';
INSTALL httpfs;LOAD httpfs;
SET s3_endpoint='192.168.6.51:9000';SET s3_access_key_id='YOUR_MINIO_ACCESS_KEY';SET s3_secret_access_key='YOUR_MINIO_SECRET_KEY';SET s3_use_ssl=false;SET s3_url_style='path';

------------------------------
## 📊 Analytics Query Framework (Grafana Dashboards)## Live Comparative Transit Speed Plot (Time-Series Chart)
Tracks and compares multiple active vans side-by-side on a line graph as they move along local highways:

SELECT timestamp AS time, vehicle_speed_mph AS "Van 1 (Sheraton)"FROM 's3://silver-lakehouse/year_month=202606/vehicle_id=van_01/data.parquet'WHERE $__timeFilter(timestamp) AND vehicle_speed_mph IS NOT NULLUNION ALLSELECT timestamp AS time, vehicle_speed_mph AS "Van 2 (Gaylord)"FROM 's3://silver-lakehouse/year_month=202606/vehicle_id=van_02/data.parquet'WHERE $__timeFilter(timestamp) AND vehicle_speed_mph IS NOT NULLORDER BY time ASC;

## Fleet Operational Efficiency & Idle Time Audit (Bar Chart)
Exposes how many minutes each asset spent sitting stationary wasting fuel at baggage pickup zones:

SELECT 'Van 1 (Sheraton)' AS Vehicle, (COUNT(CASE WHEN vehicle_speed_mph = 0 AND engine_rpm > 500 THEN 1 END) * 0.5) / 60.0 AS "Idle Minutes"FROM 's3://silver-lakehouse/year_month=202606/vehicle_id=van_01/data.parquet'UNION ALLSELECT 'Van 2 (Gaylord)' AS Vehicle, (COUNT(CASE WHEN vehicle_speed_mph = 0 AND engine_rpm > 500 THEN 1 END) * 0.5) / 60.0 AS "Idle Minutes"FROM 's3://silver-lakehouse/year_month=202606/vehicle_id=van_02/data.parquet'UNION ALLSELECT 'Van 3 (Hyatt Loop)' AS Vehicle, (COUNT(CASE WHEN vehicle_speed_mph = 0 AND engine_rpm > 500 THEN 1 END) * 0.5) / 60.0 AS "Idle Minutes"FROM 's3://silver-lakehouse/year_month=202606/vehicle_id=van_03/data.parquet';


---

## 🚀 Advanced Horizons: Unlocking the Full Power of Grafana

Because this platform handles high-fidelity time-series telemetry data, we can leverage Grafana’s cloud-native observability features to transform passive charts into an automated, proactive fleet operations center.

### 1. Unified Alerting Engine: Real-Time Mobile & SMS Pings
Grafana can act as a 24/7 digital dispatcher. By continuously scanning your DuckDB S3 Parquet tables, it can run evaluation loops every 30 seconds and instantly route warnings to your phone via **Discord Webhooks, Telegram Bots, Slack Channels, or PagerDuty SMS**.

#### The Over-Speeding Warning Blueprint (International Parkway)
*   **The Problem**: Shuttle drivers speeding over **70 MPH** on airport grounds risk heavy structural fines and compromise passenger safety.
*   **The Alert Rule Logic**:
    ```sql
    -- Evaluates the trailing 60 seconds of streaming telemetry
    SELECT MAX(vehicle_speed_mph) 
    FROM 's3://silver-lakehouse/year_month=202606/vehicle_id=van_02/data.parquet'
    WHERE timestamp >= NOW() - INTERVAL '1 minute';
    ```
*   **The Threshold**: If the returning value is `> 70`, Grafana switches the state from `OK` to `ALERTING`.
*   **The Payloads**: It drops a rich text notification straight to your phone: 
    *   *🚨 "CRITICAL: Asset `van_02` has breached safety thresholds! Speed recorded at 74 MPH along International Parkway transit corridors. Dispatching warning."*

#### Additional Operational Alerts You Can Build:
*   **Low Car Battery Voltage Warning**: Ping your phone if a parked van's battery line drops below **11.9V** while idling in the garage lot, catching a dead battery before the morning shift starts.
*   **Critical Thermal Overheating Flag**: Trigger an immediate alert flag if `coolant_temp_c` breaches **105°C**, signaling a radiator hose burst or cooling fan failure.

---

### 2. Geographic Spatial Tracking: Geomap Satellite Panels
Grafana features a native **Geomap Visualization Panel** that allows you to drop your vehicle assets directly onto live, interactive maps powered by OpenStreetMap or ArcGIS satellite layers.

*   **How it Works**: When the physical WiCAN Pro hardware arrives, we can expand our edge script schema to pull GPS data coordinates (`0x180` and `0x181` J1939 frames) alongside speed.
*   **The Lakehouse Schema Expansion**:
    ```text
    ├── latitude (FLOAT64)   --> e.g., 32.8998 (DFW Airport Coordinates)
    └── longitude (FLOAT64)  --> e.g., -97.0403
    ```
*   **Visual Enhancements Inside Grafana**:
    *   **Live Route Tracing**: See the exact route your vans take from the Sheraton Irving onto the SH-114 highway ramps.
    *   **Dynamic Speed Heatmapping**: Configure the map markers to automatically shift colors based on vehicle speed. The dot turns **Deep Blue** when the van is stuck idling at the hotel valet, shifts to **Bright Green** at a safe 60 MPH cruising pace, and flashes **Vibrant Red** if it breaches 70 MPH on the highway corridor.

---

### 3. Predictive Maintenance Analytics: Machine Learning Trends
Instead of reading past errors, Grafana can calculate and predict future mechanical failures using basic mathematical forecasting.

*   **Predicting Dead Batteries**: By monitoring the minor voltage drop slope while a vehicle sits parked over a weekend, a simple regression line can forecast exactly how many hours remain before the battery drops below starting voltage thresholds.
*   **Predictive Oil Life and Brake Wear Indexes**: Combine engine revolutions (`engine_rpm`), ambient temperatures, and mileage accumulation to plot exact, usage-based maintenance tracking lines, replacing outdated "every 3,000 miles" guesswork with hyper-accurate data insights.

---

### 4. Interactive Variable Dropdowns: The Multi-Tenant Fleet Selector
Instead of building three separate dashboards for Van 1, Van 2, and Van 3, Grafana allows you to build a single dashboard that controls everything using **Dynamic Dashboard Variables**.

*   **The Implementation**: You create a text variable named `$vehicle` at the top of your screen that queries your MinIO directory tree partitions.
*   **The Dynamic Dropdown SQL Query**:
    ```sql
    SELECT DISTINCT vehicle_id FROM 's3://silver-lakehouse/year_month=202606/**/*.parquet';
    ```
*   **The Result**: A clean dropdown selection box appears at the top of your dashboard screen. Selecting `van_03` will instantly rewrite all your dashboard charts, tables, gauges, and thermal maps to pull data exclusively for the Hyatt terminal shuttle loop, instantly filtering out the rest of the fleet!

---

## 📈 Enterprise Horizons: Maintenance, Safety, & Insurance Analytics

By capturing high-frequency time-series telemetry metrics at sub-second intervals, this data lakehouse platform can be expanded to run advanced modeling for machine health forecasting, driving habit audits, and commercial insurance risk profiling.

### 1. Predictive Maintenance & Vehicle Health Profiling
Instead of relying on reactive dashboard trouble codes (DTCs), the platform can implement continuous wear profiling by cross-referencing mechanical load parameters over time.

*   **Thermal Stress Tracking**: While a standard gauge shows a simple temperature reading, the Gold layer can track engine heat saturation velocity. If a van's coolant temperature climbs significantly faster under highway acceleration this week compared to its baseline month, Grafana flags a degradation alert—catching a failing thermostat or a clogged radiator long before the engine overheats.
*   **Battery Cold-Cranking Health (CCA) Analytics**: The WiCAN Pro logs car battery voltage lines live during engine ignition. By isolating the minimum voltage drop spike during a starter motor crank, the pipeline can plot cranking health. A cranking drop that dips closer to 9.5V over consecutive weeks signals an imminent battery cell failure, allowing shop mechanics to replace the battery before the van gets stranded at an airport terminal terminal.
*   **The Check Engine Light (DTC) Event Log Schema**:
    ```sql
    -- Tracks active engine trouble codes straight from OBD-II Mode 03 broadcasts
    SELECT 
      timestamp AS time,
      vehicle_id,
      active_dtc_code AS "Fault Code",
      dtc_description AS "Diagnostic Meaning"
    FROM 's3://silver-lakehouse/year_month=202606/vehicle_id=*/diagnostics.parquet'
    WHERE trigger_alert = TRUE;
    ```

---

### 2. Fleet Safety Monitoring & Driver Telematics
Fleet managers can monitor driving habits by evaluating sudden changes in speed and throttle input, allowing them to coach drivers and lower maintenance costs.

*   **Hard Braking & Rapid Acceleration Event Tracing**: The pipeline uses rolling window functions over the velocity arrays to detect sudden changes in speed. A drop in speed greater than **7 MPH within a rolling 1-second window** is flagged as a Hard Braking event. Conversely, a spike greater than **6 MPH within 1 second** registers as a Rapid Acceleration event.
*   **Aggressive Throttle Transitions**: By measuring throttle position percentages alongside engine speed (`engine_rpm`), the system detects instances where drivers stomp on the gas pedal while the engine is cold (coolant temp `< 70°C`), protecting the fleet from premature engine wear.

---

### 3. Insurance Risk Assessment (Driving Habits Scorecard)
Commercial auto insurance providers calculate premiums based on fleet operating risks. This lakehouse engine can compile custom risk scores to help negotiate lower insurance premiums.

*   **The Fleet Driver Safety Leaderboard**: A monthly Gold pipeline script aggregates events to rank vans from best to worst based on a normalized safety score (Events per 100 Miles Driven).
*   **The Commercial Risk Profile Query**:
    This SQL script aggregates driver metrics across the fleet, providing clean data to help you negotiate lower commercial insurance rates:
    ```sql
    SELECT
      vehicle_id AS "Van Asset ID",
      ROUND(SUM(duration_minutes) / 60.0, 1) AS "Total Operating Hours",
      -- Calculates the total count of high-risk speeding instances over 70 MPH
      SUM(overspeed_seconds) AS "High-Speed Exposure (Sec)",
      -- Aggregates hard braking instances detected by rolling window functions
      COUNT(CASE WHEN dq_notes LIKE '%[Safety: Hard Brake]%' THEN 1 END) AS "Hard Brake Events",
      -- Profiles the fuel efficiency penalty based on extended idle ratios
      ROUND(AVG(idle_ratio_pct), 1) AS "Average Fuel Waste Idle %"
    FROM 's3://gold-analytics/fleet_trip_summaries.parquet'
    GROUP BY vehicle_id
    ORDER BY "Hard Brake Events" ASC;
    ```
*   **Visualizing Risk Inside Grafana**: You can map these metrics into a **Grafana Gauge panel**. The panel turns **Green** for safe drivers (zero hard brakes, low idling), shifts to **Yellow** for moderate risks, and flashes **Red** for high-risk drivers, giving you a clear view of your fleet's safety profile at a glance.


---

## 🤖 AI Core: Autonomous Fleet Coordination & Agent Frameworks

By leveraging the underlying time-series telemetry data stored inside MinIO S3, the data lakehouse can host autonomous **AI Agent Workflows** to manage vehicle safety, maximize operational fuel efficiency, and optimize passenger satisfaction metrics.

### 1. The Autonomous Safety Agent (Driver Coaching Network)
Instead of a manager checking dashboards once a week, an automated **Safety AI Agent** sits directly over the Silver data layer to handle driver habits in real-time.

*   **The Ingestion Event Loop**: The agent monitors rolling telemetry streams from `s3://silver-lakehouse/`.
*   **Cognitive Action Triggers**: If a hard braking or aggressive acceleration event is registered, the agent evaluates environmental metadata (e.g., weather or traffic congestion using local public APIs).
*   **Autonomous Output Execution**: If the agent detects an ongoing pattern of aggressive weaving or tailgating on International Parkway, it invokes a messaging API (like Twilio SMS) to text the driver at their next safe stop:
    *   *💬 "Hi Marcus, our fleet safety systems noted three consecutive hard-braking events over the last 10 minutes near Terminal D. Traffic is heavy; please increase your trailing distance by two vehicle lengths."*

---

### 2. The Predictive Efficiency Agent (Smart Dispatch & Maintenance)
This AI agent acts as a proactive virtual shop foreman, translating physical mechanical metrics into automated logistics decisions to lower vehicle downtime.

*   **Autonomous Maintenance Workflows**: By tracking engine thermal profiles, voltage drops, and raw fault patterns over time, an agent detects early component degradation. 
*   **Autonomous Action**: The agent reads available maintenance windows from your shop schedule, automatically submits a parts order for a new radiator or battery via an online vendor API, and drops an calendar entry to your mechanic:
    *   *🔧 "AI Notice: Van 3 has been booked for an emergency cooling system inspection tonight at 8 PM. Parts order #9142 (OEM Radiator Assembly) has been processed and will arrive at the shop bay by 5 PM."*

---

### 3. The Passenger Experience (CSAT) Agent
This agent bridges your vehicle telemetry with passenger booking databases to maximize customer satisfaction by predicting and eliminating transit delays.

*   **The Relational Customer-to-Vehicle KPI Schema**:
    To track and analyze customer satisfaction metrics alongside fleet operations, we introduce a unified analytics database view:
    ```sql
    SELECT 
      b.customer_name AS "Passenger",
      b.flight_number AS "Flight",
      b.target_terminal AS "Terminal",
      -- Calculates the physical delay between passenger curb check-in and shuttle arrival
      EPOCH_MS(v.timestamp) - EPOCH_MS(b.curb_checkin_ms) AS "Customer Wait Time (Sec)",
      v.vehicle_id AS "Assigned Shuttle ID",
      v.vehicle_speed_mph AS "Transit Speed",
      c.csat_score AS "Post-Trip Customer Rating"
    FROM 's3://customer-lakehouse/bookings.parquet' b
    JOIN 's3://silver-lakehouse/**/*.parquet' v 
      ON v.timestamp BETWEEN b.pickup_window_start AND b.pickup_window_end
    LEFT JOIN 's3://customer-lakehouse/csat.parquet' c 
      ON c.booking_id = b.booking_id;
    ```

*   **Predictive Terminal Re-Routing**: If **Van 1** is cruising down International Parkway to pick up a passenger group at Terminal C, the **Customer Experience Agent** continuously cross-references terminal traffic via your vehicle telemetry. 
*   **The Action**: If the agent computes that Terminal C is gridlocked, but **Van 3** is currently idling empty right outside Terminal C, the AI agent automatically swaps the dispatch assignments, updates the drivers' tablets, and texts the waiting customer:
    *   *📱 "Hi Sarah, your shuttle assignment has been optimized to beat terminal traffic! Your new driver, Carlos (Van 3), is pulling up to Terminal C Baggage Claim Curb Zone 4 in exactly 90 seconds. Look for Van #3!"*

I just hired an AI to help me with this running this operation. For this example I decided to use OpenAI GPT instead of Claude.

### Prerequisites & Setup
To run the AI agent, you will need to install its dependencies and configure your environment variables:

```bash
# Install the required Python packages
pip install langchain-openai langchain-core duckdb

# Set your OpenAI API key in your environment
set OPENAI_API_KEY=your_api_key_here  # Windows
export OPENAI_API_KEY=your_api_key_here  # Linux/Mac
```

D:\CAN>p ai_fleet_agent.py
Saved clipboard to: ai_fleet_agent.py

D:\CAN>python ai_fleet_agent.py
Initializing Context-Fed AI Fleet Operations Agent Node...

⚡ [System Action] Actively pulling streaming data metrics from MinIO S3...

✅ [System Success] Lakehouse Data Matrix Successfully Streamed:
--------------------------------------------------------------------------------
vehicle_id  total_duration_minutes  idle_minutes  idle_ratio_pct
    van_01                    9.66          1.05           10.87
    van_02                   11.33          1.73           15.27
    van_03                    7.83          3.43           43.81
--------------------------------------------------------------------------------

🚀 AI Fleet Operations Agent Online and Connected to MinIO Data Lake!
---------------------------------------------------------------------
You can now ask the AI conversational questions regarding your vans.
Type 'exit' to shut down the session link.

Ask the AI Agent 🤖 > Which of our three fleet vans is wasting the highest percentage of its time idling, and how many minutes did it spend sitting parked?

Thinking... Formulating Fleet Analytics Profile...
🤖 [AI Fleet Agent Response]:


Van_03 is wasting the highest percentage of its time idling, with an idle ratio of 43.81%. It spent 3.43 minutes sitting parked.

Ask the AI Agent 🤖 >


------------------------------
## Production-Ready Operations Stack (The Big Picture)
   1. The Edge Layer: Your vehicle simulator files (van1.py, etc.) convert real physical driving variables into true-to-life CAN hex streams.
   2. The Ingestion & Guardrail Layer: Your master processor running on your PC translates hex payloads, switches units to MPH, verifies data quality limits, and handles structural schema errors.
   3. The Storage Lakehouse Tier: Verified rows are tightly compressed into Snappy-Parquet tables and uploaded over the wire straight to your home server's secure MinIO S3 Buckets.
   4. The Visual Dashboard Cockpit: An Ubuntu-based Grafana instance connected via a virtual DuckDB driver streams your S3 objects on demand to plot beautiful speed curves and mechanical performance charts.
   5. The Autonomous AI Intelligence Core: A custom LangChain agent framework connects an advanced language model directly to your remote database endpoint, giving you actionable business optimization insights using conversational English.
