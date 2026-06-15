import os
import time
import json
import random
import asyncio
import urllib.request
from datetime import datetime

BASE_DIR = r"D:\CAN"
BRONZE_DIR = os.path.join(BASE_DIR, "wican_bronze", "year_month=202606")
os.makedirs(BRONZE_DIR, exist_ok=True)

# Locations (Lat, Lng)
LOCATIONS = {
    "Sheraton": (32.8998, -97.0003),
    "Gaylord": (32.9555, -97.0620),
    "Hyatt": (32.8953, -97.0374),
    "Terminal_D": (32.8967, -97.0425),
    "Terminal_A": (32.9015, -97.0335),
    "Terminal_C": (32.8965, -97.0333),
    "South_Toll_Plaza": (32.8600, -97.0400) # Far south on International Pkwy
}

ROUTES = {
    "van_01": {
        "start": LOCATIONS["Sheraton"],
        "end": LOCATIONS["Terminal_D"],
        "profile": [
            (30, 0, "Idling at Sheraton Irving Valet"),
            (45, 35, "Exiting hotel onto Esters Blvd frontage"),
            (60, 75, "Accelerating onto SH-114 Westbound On-Ramp"),
            (180, 105, "Cruising SH-114 toward North Airport Toll Plaza"),
            (45, 40, "Slowing down for Toll Plaza Lanes"),
            (120, 80, "Cruising South down International Parkway"),
            (60, 25, "Braking into Terminal D Arrival Loop"),
            (40, 0, "Fully Stopped at Terminal D for Baggage Drop")
        ]
    },
    "van_02": {
        "start": LOCATIONS["Gaylord"],
        "end": LOCATIONS["Terminal_A"],
        "profile": [
            (60, 0, "Idling at Gaylord Texan Convention Center Loop"),
            (50, 30, "Navigating Gaylord Trail Resort exits"),
            (75, 55, "Cruising down Texan Trail arterial road"),
            (90, 80, "Merging onto International Parkway Southbound entry"),
            (240, 110, "High-speed cruising on International Parkway spine"),
            (45, 30, "Slowing down for terminal bypass split"),
            (70, 20, "Crawling through heavy Terminal A traffic"),
            (50, 0, "Fully Stopped at Terminal A Gate 12 Arrivals")
        ]
    },
    "van_03": {
        "start": LOCATIONS["Hyatt"],
        "end": LOCATIONS["South_Toll_Plaza"],
        "profile": [
            (90, 0, "Extended Idle at Hyatt Regency Airport Hub entrance"),
            (40, 25, "Maneuvering out of hotel driveway"),
            (60, 45, "Merging onto Airport Service Rd road system"),
            (30, 15, "Slowing down for pedestrian crosswalk markers"),
            (80, 50, "Shuttling along terminal service connector lanes"),
            (50, 20, "Braking hard into Terminal C Inner Lane loop"),
            (120, 0, "Long Idle at Terminal C waiting for passenger group cargo")
        ]
    }
}

# Live Global State for WebSockets
fleet_state = {
    "van_01": {"speed": 0, "rpm": 0, "temp": 82.0, "fuel": 100.0, "lat": LOCATIONS["Sheraton"][0], "lng": LOCATIONS["Sheraton"][1], "status": "Idle", "idle_time_seconds": 0},
    "van_02": {"speed": 0, "rpm": 0, "temp": 78.0, "fuel": 100.0, "lat": LOCATIONS["Gaylord"][0], "lng": LOCATIONS["Gaylord"][1], "status": "Idle", "idle_time_seconds": 0},
    "van_03": {"speed": 0, "rpm": 0, "temp": 89.0, "fuel": 100.0, "lat": LOCATIONS["Hyatt"][0], "lng": LOCATIONS["Hyatt"][1], "status": "Idle", "idle_time_seconds": 0}
}

def generate_can_payload(can_id, current_speed, current_rpm, coolant_temp):
    if can_id == "0x0C4":
        rpm_wire = int(max(0, current_rpm) * 4)
        return f"{rpm_wire:04X}{int(max(0, current_speed)):02X}0000000000"
    elif can_id == "0x7E8":
        return f"034105{int(coolant_temp + 40):02X}00000000"
    return "0000000000000000"

def fetch_route(start_coord, end_coord):
    """Fetches a road route from OSRM (Open Source Routing Machine)."""
    # OSRM expects lon,lat
    url = f"http://router.project-osrm.org/route/v1/driving/{start_coord[1]},{start_coord[0]};{end_coord[1]},{end_coord[0]}?overview=full&geometries=geojson"
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'SimFleet/1.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read())
            coords = data['routes'][0]['geometry']['coordinates']
            # Return as [lat, lon]
            return [[c[1], c[0]] for c in coords]
    except Exception as e:
        print(f"OSRM Fetch Error: {e}")
        # Fallback to straight line
        return [start_coord, end_coord]

import math

def haversine(lat1, lon1, lat2, lon2):
    R = 3958.8 # Earth radius in miles
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat/2) * math.sin(dLat/2) + \
        math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * \
        math.sin(dLon/2) * math.sin(dLon/2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c

def get_exact_profile_distance(route_data):
    current_speed = 0.0
    dist = 0.0
    for duration, target_speed, phase_name in route_data["profile"]:
        for _ in range(duration):
            speed_delta = target_speed - current_speed
            if speed_delta > 0:
                current_speed += 2.0
                current_speed = min(current_speed, target_speed)
            elif speed_delta < 0:
                current_speed -= 3.5
                current_speed = max(current_speed, target_speed)
            dist += current_speed / 3600.0
    return max(dist, 0.001)

async def simulate_van(vehicle_id, route_data):
    trip_id = f"{vehicle_id}_{datetime.now().strftime('%Y%m%d')}_trip_live"
    output_file = os.path.join(BRONZE_DIR, f"{trip_id}.json")
    
    current_speed = fleet_state[vehicle_id]["speed"]
    current_rpm = fleet_state[vehicle_id]["rpm"]
    coolant_temp = fleet_state[vehicle_id]["temp"]
    fuel = random.uniform(85.0, 100.0)
    
    start_lat, start_lng = route_data["start"]
    end_lat, end_lng = route_data["end"]
    
    # Fetch road geometry
    road_coords = fetch_route(route_data["start"], route_data["end"])
    
    # Calculate cumulative physical distances along the polyline
    cumulative_road_dist = [0.0]
    for i in range(1, len(road_coords)):
        lat1, lon1 = road_coords[i-1]
        lat2, lon2 = road_coords[i]
        d = haversine(lat1, lon1, lat2, lon2)
        cumulative_road_dist.append(cumulative_road_dist[-1] + d)
    
    total_road_dist = cumulative_road_dist[-1]
    if total_road_dist == 0: total_road_dist = 0.001
    
    total_profile_dist = get_exact_profile_distance(route_data)
    
    while True: # Loop the route forever
        virtual_dist_traveled = 0.0
        
        with open(output_file, "a") as f:
            for duration, target_speed, phase_name in route_data["profile"]:
                fleet_state[vehicle_id]["status"] = phase_name
                
                for _ in range(duration):
                    speed_delta = target_speed - current_speed
                    if speed_delta > 0:
                        current_speed += random.uniform(1.0, 3.0)
                        current_speed = min(current_speed, target_speed)
                        current_rpm = 1200 + (current_speed * 20) + random.uniform(-100, 100)
                    elif speed_delta < 0:
                        current_speed -= random.uniform(2.0, 4.5)
                        current_speed = max(current_speed, target_speed)
                        current_rpm = 900 + (current_speed * 12) + random.uniform(-50, 50)
                    else:
                        current_rpm = random.uniform(750, 820) if current_speed == 0 else 1500 + (current_speed * 10) + random.uniform(-30, 30)
                    
                    coolant_temp = min(96.0, coolant_temp + 0.02)
                    fuel = max(0.0, fuel - 0.001)
                    
                    idle_time = fleet_state[vehicle_id].get("idle_time_seconds", 0)
                    if current_speed == 0:
                        idle_time += 1
                    else:
                        idle_time = 0
                        
                    # Physics-based distance tracking (Exact 1:1 scale)
                    virtual_dist_traveled += current_speed / 3600.0
                    
                    # Ping-pong mapping to the real physical map (to/from destination)
                    cycles = int(virtual_dist_traveled / total_road_dist)
                    if cycles % 2 == 0:
                        # Moving Forward
                        target_road_dist = virtual_dist_traveled % total_road_dist
                    else:
                        # Moving Backward
                        target_road_dist = total_road_dist - (virtual_dist_traveled % total_road_dist)
                    
                    # Find which segment of the polyline we are on
                    current_lat, current_lng = road_coords[-1] # default to end
                    for i in range(1, len(cumulative_road_dist)):
                        if target_road_dist <= cumulative_road_dist[i]:
                            segment_len = cumulative_road_dist[i] - cumulative_road_dist[i-1]
                            if segment_len > 0:
                                fraction = (target_road_dist - cumulative_road_dist[i-1]) / segment_len
                                lat1, lon1 = road_coords[i-1]
                                lat2, lon2 = road_coords[i]
                                current_lat = lat1 + (lat2 - lat1) * fraction
                                current_lng = lon1 + (lon2 - lon1) * fraction
                            else:
                                current_lat, current_lng = road_coords[i]
                            break
                    
                    # Update global state
                    fleet_state[vehicle_id].update({
                        "speed": current_speed,
                        "rpm": current_rpm,
                        "temp": coolant_temp,
                        "fuel": fuel,
                        "lat": current_lat,
                        "lng": current_lng,
                        "idle_time_seconds": idle_time
                    })
                    
                    system_clock_ms = int(time.time() * 1000)
                    for packet_slice in range(4): # 4 packets per second
                        target_id = "0x0C4" if packet_slice % 2 == 0 else "0x7E8"
                        can_frame = {
                            "ts": system_clock_ms + (packet_slice * 250), 
                            "bus": 0, 
                            "id": target_id, 
                            "dlc": 8, 
                            "data": generate_can_payload(target_id, current_speed, current_rpm, coolant_temp)
                        }
                        f.write(json.dumps(can_frame) + "\n")
                    f.flush()
                    await asyncio.sleep(1) # Real-time 1 second tick
        
        # Route loop finished. No need to reset variables manually as the road_coords index will restart.
        pass

async def start_simulation():
    tasks = []
    for vehicle_id, route_data in ROUTES.items():
        tasks.append(simulate_van(vehicle_id, route_data))
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(start_simulation())
