import os
import time
import json
import random
from datetime import datetime

BASE_DIR = r"D:\CAN"
BRONZE_DIR = os.path.join(BASE_DIR, "wican_bronze", "year_month=202606")
os.makedirs(BRONZE_DIR, exist_ok=True)

VEHICLE_ID = "van_02"
TRIP_ID = f"{VEHICLE_ID}_{datetime.now().strftime('%Y%m%d')}_trip_1"
OUTPUT_FILE = os.path.join(BRONZE_DIR, f"{TRIP_ID}.json")

# Route: Gaylord Texan Resort down Texan Trail onto International Pkwy South
route_profile = [
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

print(f"Starting pipeline for {VEHICLE_ID}...")
current_speed, current_rpm, coolant_temp = 0.0, 750.0, 78.0 # Starts a bit colder from underground parking
system_clock_ms = int(time.time() * 1000)

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
