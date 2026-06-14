import os
import time
import json
import random
from datetime import datetime

BASE_DIR = r"D:\CAN"
BRONZE_DIR = os.path.join(BASE_DIR, "wican_bronze", "year_month=202606")
os.makedirs(BRONZE_DIR, exist_ok=True)

VEHICLE_ID = "van_01"
TRIP_ID = f"{VEHICLE_ID}_{datetime.now().strftime('%Y%m%d')}_trip_1"
OUTPUT_FILE = os.path.join(BRONZE_DIR, f"{TRIP_ID}.json")

# Route: Sheraton Irving via SH-114 West to DFW Terminals
route_profile = [
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

print(f"Starting pipeline for {VEHICLE_ID}...")
current_speed, current_rpm, coolant_temp = 0.0, 800.0, 82.0
system_clock_ms = int(time.time() * 1000)

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
