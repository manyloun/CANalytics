To create a realistic simulation for your fleet, we will distribute the vans across different major hotels surrounding DFW Airport. This creates realistic variations in trip durations, acceleration profiles, and highway cruising times.
## Fleet Deployment & Route Plan

* van1.py: Sheraton DFW Airport Hotel (Irving) $\rightarrow$ DFW Airport Terminals. (Mid-length highway run via SH-114 West).
* van2.py: Gaylord Texan Resort (Grapevine) $\rightarrow$ DFW Airport Terminals. (Longer run, entering from the north via Texan Trail and International Parkway).
* van3.py: Hyatt Regency DFW International Airport $\rightarrow$ DFW Airport Terminals. (Short, low-speed, high-idle terminal-to-terminal shuttle loop).

------------------------------
## Script 1: van1.py (Sheraton DFW Irving Route)

import osimport timeimport jsonimport randomfrom datetime import datetime
BASE_DIR = r"D:\CAN"BRONZE_DIR = os.path.join(BASE_DIR, "wican_bronze", "year_month=202606")
os.makedirs(BRONZE_DIR, exist_ok=True)
VEHICLE_ID = "van_01"TRIP_ID = f"{VEHICLE_ID}_{datetime.now().strftime('%Y%m%d')}_trip_1"OUTPUT_FILE = os.path.join(BRONZE_DIR, f"{TRIP_ID}.json")
# Route: Sheraton Irving via SH-114 West to DFW Terminalsroute_profile = [
    (30, 0, "Idling at Sheraton Irving Valet"),
    (45, 35, "Exiting hotel onto Esters Blvd frontage"),
    (60, 75, "Accelerating onto SH-114 Westbound On-Ramp"),
    (180, 105, "Cruising SH-114 toward North Airport Toll Plaza"),
    (45, 40, "Slowing down for Toll Plaza Lanes"),
    (120, 80, "Cruising South down International Parkway"),
    (60, 25, "Braking into Terminal D Arrival Loop"),
    (40, 0, "Fully Stopped at Terminal D for Baggage Drop")
]
def generate_can_payload(can_id, current_speed, current_rpm, coolant_temp):
    if can_id == "0x0C4":
        rpm_wire = int(current_rpm * 4)
        return f"{rpm_wire:04X}{int(current_speed):02X}0000000000"
    elif can_id == "0x7E8":
        return f"034105{int(coolant_temp + 40):02X}00000000"
    return "0000000000000000"

print(f"Starting pipeline for {VEHICLE_ID}...")current_speed, current_rpm, coolant_temp = 0.0, 800.0, 82.0system_clock_ms = int(time.time() * 1000)
with open(OUTPUT_FILE, "w") as f:
    for duration, target_speed, phase_name in route_profile:
        for _ in range(duration):
            speed_delta = target_speed - current_speed
            if speed_delta > 0:
                current_speed += random.uniform(1.5, 3.0)
                current_speed = min(current_speed, target_speed)
                current_rpm = 1200 + (current_speed * 22) + random.uniform(-100, 100)
            elif speed_delta < 0:
                current_speed -= random.uniform(2.5, 4.5)
                current_speed = max(current_speed, target_speed)
                current_rpm = 900 + (current_speed * 12) + random.uniform(-50, 50)
            else:
                current_rpm = random.uniform(750, 820) if current_speed == 0 else 1500 + (current_speed * 10) + random.uniform(-30, 30)
            
            coolant_temp = min(92.0, coolant_temp + 0.03)

            for packet_slice in range(4):
                system_clock_ms += 250
                target_id = "0x0C4" if packet_slice % 2 == 0 else "0x7E8"
                can_frame = {"ts": system_clock_ms, "bus": 0, "id": target_id, "dlc": 8, "data": generate_can_payload(target_id, current_speed, current_rpm, coolant_temp)}
                f.write(json.dumps(can_frame) + "\n")

print(f"Logged {VEHICLE_ID} data to Bronze.")

------------------------------
## Script 2: van2.py (Gaylord Texan Route)

import osimport timeimport jsonimport randomfrom datetime import datetime
BASE_DIR = r"D:\CAN"BRONZE_DIR = os.path.join(BASE_DIR, "wican_bronze", "year_month=202606")
os.makedirs(BRONZE_DIR, exist_ok=True)
VEHICLE_ID = "van_02"TRIP_ID = f"{VEHICLE_ID}_{datetime.now().strftime('%Y%m%d')}_trip_1"OUTPUT_FILE = os.path.join(BRONZE_DIR, f"{TRIP_ID}.json")
# Route: Gaylord Texan Resort down Texan Trail onto International Pkwy Southroute_profile = [
    (60, 0, "Idling at Gaylord Texan Convention Center Loop"),
    (50, 30, "Navigating Gaylord Trail Resort exits"),
    (75, 55, "Cruising down Texan Trail arterial road"),
    (90, 80, "Merging onto International Parkway Southbound entry"),
    (240, 110, "High-speed cruising on International Parkway spine"),
    (45, 30, "Slowing down for terminal bypass split"),
    (70, 20, "Crawling through heavy Terminal A traffic"),
    (50, 0, "Fully Stopped at Terminal A Gate 12 Arrivals")
]
def generate_can_payload(can_id, current_speed, current_rpm, coolant_temp):
    if can_id == "0x0C4":
        rpm_wire = int(current_rpm * 4)
        return f"{rpm_wire:04X}{int(current_speed):02X}0000000000"
    elif can_id == "0x7E8":
        return f"034105{int(coolant_temp + 40):02X}00000000"
    return "0000000000000000"

print(f"Starting pipeline for {VEHICLE_ID}...")current_speed, current_rpm, coolant_temp = 0.0, 750.0, 78.0 # Starts a bit colder from underground parkingsystem_clock_ms = int(time.time() * 1000)
with open(OUTPUT_FILE, "w") as f:
    for duration, target_speed, phase_name in route_profile:
        for _ in range(duration):
            speed_delta = target_speed - current_speed
            if speed_delta > 0:
                current_speed += random.uniform(1.2, 2.8)
                current_speed = min(current_speed, target_speed)
                current_rpm = 1300 + (current_speed * 20) + random.uniform(-120, 120)
            elif speed_delta < 0:
                current_speed -= random.uniform(2.0, 4.0)
                current_speed = max(current_speed, target_speed)
                current_rpm = 850 + (current_speed * 14) + random.uniform(-60, 60)
            else:
                current_rpm = random.uniform(720, 780) if current_speed == 0 else 1600 + (current_speed * 9) + random.uniform(-40, 40)
            
            coolant_temp = min(94.0, coolant_temp + 0.04) # Heats up more on long highway run

            for packet_slice in range(4):
                system_clock_ms += 250
                target_id = "0x0C4" if packet_slice % 2 == 0 else "0x7E8"
                can_frame = {"ts": system_clock_ms, "bus": 0, "id": target_id, "dlc": 8, "data": generate_can_payload(target_id, current_speed, current_rpm, coolant_temp)}
                f.write(json.dumps(can_frame) + "\n")

print(f"Logged {VEHICLE_ID} data to Bronze.")

------------------------------
## Script 3: van3.py (Hyatt Regency Inside Airport Loop)

import osimport timeimport jsonimport randomfrom datetime import datetime
BASE_DIR = r"D:\CAN"BRONZE_DIR = os.path.join(BASE_DIR, "wican_bronze", "year_month=202606")
os.makedirs(BRONZE_DIR, exist_ok=True)
VEHICLE_ID = "van_03"TRIP_ID = f"{VEHICLE_ID}_{datetime.now().strftime('%Y%m%d')}_trip_1"OUTPUT_FILE = os.path.join(BRONZE_DIR, f"{TRIP_ID}.json")
# Route: Hyatt Regency DFW (Inside Airport Grounds) loop directly between terminals# No high-speed highway segments. Lots of idling and low gear acceleration.route_profile = [
    (90, 0, "Extended Idle at Hyatt Regency Airport Hub entrance"),
    (40, 25, "Maneuvering out of hotel driveway"),
    (60, 45, "Merging onto Airport Service Rd road system"),
    (30, 15, "Slowing down for pedestrian crosswalk markers"),
    (80, 50, "Shuttling along terminal service connector lanes"),
    (50, 20, "Braking hard into Terminal C Inner Lane loop"),
    (120, 0, "Long Idle at Terminal C waiting for passenger group cargo")
]
def generate_can_payload(can_id, current_speed, current_rpm, coolant_temp):
    if can_id == "0x0C4":
        rpm_wire = int(current_rpm * 4)
        return f"{rpm_wire:04X}{int(current_speed):02X}0000000000"
    elif can_id == "0x7E8":
        return f"034105{int(coolant_temp + 40):02X}00000000"
    return "0000000000000000"

print(f"Starting pipeline for {VEHICLE_ID}...")current_speed, current_rpm, coolant_temp = 0.0, 780.0, 89.0 # Runs hot because it stays idling at terminalssystem_clock_ms = int(time.time() * 1000)
with open(OUTPUT_FILE, "w") as f:
    for duration, target_speed, phase_name in route_profile:
        for _ in range(duration):
            speed_delta = target_speed - current_speed
            if speed_delta > 0:
                current_speed += random.uniform(1.0, 2.2) # Heavy city van cargo acceleration
                current_speed = min(current_speed, target_speed)
                current_rpm = 1400 + (current_speed * 25) + random.uniform(-150, 150)
            elif speed_delta < 0:
                current_speed -= random.uniform(3.0, 5.0) # Frequent aggressive stop-and-go braking
                current_speed = max(current_speed, target_speed)
                current_rpm = 950 + (current_speed * 10) + random.uniform(-70, 70)
            else:
                current_rpm = random.uniform(760, 810) if current_speed == 0 else 1450 + (current_speed * 12) + random.uniform(-40, 40)
            
            coolant_temp = min(96.0, coolant_temp + 0.01) # Stays warm due to low air cooling flow

            for packet_slice in range(4):
                system_clock_ms += 250
                target_id = "0x0C4" if packet_slice % 2 == 0 else "0x7E8"
                can_frame = {"ts": system_clock_ms, "bus": 0, "id": target_id, "dlc": 8, "data": generate_can_payload(target_id, current_speed, current_rpm, coolant_temp)}
                f.write(json.dumps(can_frame) + "\n")

print(f"Logged {VEHICLE_ID} data to Bronze.")

------------------------------
## How to Run and Validate Your Data

   1. Run each script via command line or IDE (python van1.py, python van2.py, etc.).
   2. Open D:\CAN\wican_bronze\year_month=202606\ to check your inputs.
   3. You will see three independent JSON files containing valid time-stamped hex payloads tracking specific route behaviors.

Would you like to move directly to building a master processing engine that scans this incoming directory, extracts the metrics, and structures them into your Silver Parquet stage?

