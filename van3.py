import os
import time
import json
import random
from datetime import datetime

BASE_DIR = r"D:\CAN"
BRONZE_DIR = os.path.join(BASE_DIR, "wican_bronze", "year_month=202606")
os.makedirs(BRONZE_DIR, exist_ok=True)

VEHICLE_ID = "van_03"
TRIP_ID = f"{VEHICLE_ID}_{datetime.now().strftime('%Y%m%d')}_trip_1"
OUTPUT_FILE = os.path.join(BRONZE_DIR, f"{TRIP_ID}.json")

# Route: Hyatt Regency DFW (Inside Airport Grounds) loop directly between terminals
# No high-speed highway segments. Lots of idling and low gear acceleration.
route_profile = [
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

print(f"Starting pipeline for {VEHICLE_ID}...")
current_speed, current_rpm, coolant_temp = 0.0, 780.0, 89.0 # Runs hot because it stays idling at terminals
system_clock_ms = int(time.time() * 1000)

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
