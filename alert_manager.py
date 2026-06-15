import sqlite3
import asyncio
from datetime import datetime
import json
from simulation_engine import fleet_state

DB_FILE = r"D:\CAN\alerts.sqlite"

def init_db():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS alert_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            vehicle_id TEXT,
            metric TEXT,
            operator TEXT,
            threshold REAL,
            message TEXT,
            enabled INTEGER DEFAULT 1
        )
    ''')
    
    c.execute('''
        CREATE TABLE IF NOT EXISTS alert_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            rule_id INTEGER,
            vehicle_id TEXT,
            message TEXT,
            telemetry_json TEXT
        )
    ''')
    try:
        c.execute("ALTER TABLE alert_rules ADD COLUMN enabled INTEGER DEFAULT 1")
    except sqlite3.OperationalError:
        pass # Column already exists
        
    conn.commit()
    conn.close()

def add_alert_rule(vehicle_id, metric, operator, threshold, message):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO alert_rules (vehicle_id, metric, operator, threshold, message, enabled)
        VALUES (?, ?, ?, ?, ?, 1)
    ''', (vehicle_id, metric, operator, threshold, message))
    conn.commit()
    conn.close()

def get_all_rules():
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('SELECT id, vehicle_id, metric, operator, threshold, message, enabled FROM alert_rules')
    rules = c.fetchall()
    conn.close()
    return rules

def log_alert_history(timestamp, rule_id, vehicle_id, message, telemetry_json):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        INSERT INTO alert_history (timestamp, rule_id, vehicle_id, message, telemetry_json)
        VALUES (?, ?, ?, ?, ?)
    ''', (timestamp, rule_id, vehicle_id, message, telemetry_json))
    conn.commit()
    conn.close()

def get_recent_alert_history(limit=10):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        SELECT timestamp, rule_id, vehicle_id, message, telemetry_json 
        FROM alert_history 
        ORDER BY id DESC 
        LIMIT ?
    ''', (limit,))
    history = c.fetchall()
    conn.close()
    return history

def update_alert_rule(rule_id, threshold, message, enabled):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('''
        UPDATE alert_rules 
        SET threshold = ?, message = ?, enabled = ?
        WHERE id = ?
    ''', (threshold, message, int(enabled), rule_id))
    conn.commit()
    conn.close()

def delete_alert_rule(rule_id):
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    c.execute('DELETE FROM alert_rules WHERE id = ?', (rule_id,))
    conn.commit()
    conn.close()

def evaluate_condition(current_value, operator, threshold):
    try:
        current_value = float(current_value)
        threshold = float(threshold)
    except (ValueError, TypeError):
        return False

    if operator == '>': return current_value > threshold
    if operator == '<': return current_value < threshold
    if operator == '>=': return current_value >= threshold
    if operator == '<=': return current_value <= threshold
    if operator == '==': return current_value == threshold
    if operator == '!=': return current_value != threshold
    return False

# Queue to send triggered alerts to the FastAPI WebSocket
alert_queue = asyncio.Queue()

async def alert_monitor_loop():
    init_db()
    # To prevent spamming the same alert every second, keep track of triggered ones
    triggered_state = {}
    
    while True:
        rules = get_all_rules()
        for rule_id, vehicle_id, metric, operator, threshold, message, enabled in rules:
            if not enabled:
                continue
                
            vans_to_check = [vehicle_id] if vehicle_id in fleet_state else list(fleet_state.keys())
            
            for v_id in vans_to_check:
                if v_id not in fleet_state: continue
                current_val = fleet_state[v_id].get(metric)
                
                if current_val is not None:
                    is_triggered = evaluate_condition(current_val, operator, threshold)
                    state_key = f"{rule_id}_{v_id}"
                    
                    if is_triggered and not triggered_state.get(state_key):
                        # Trigger new alert
                        triggered_state[state_key] = True
                        timestamp = datetime.now().strftime("%H:%M:%S")
                        
                        # Log history
                        telemetry_json = json.dumps(fleet_state[v_id])
                        log_alert_history(timestamp, rule_id, v_id, message, telemetry_json)
                        
                        formatted_msg = f"[{timestamp}] 🚨 ALERT ({v_id}): {message}"
                        await alert_queue.put(formatted_msg)
                    elif not is_triggered and triggered_state.get(state_key):
                        # Reset if condition is no longer met
                        triggered_state[state_key] = False
                        
        await asyncio.sleep(2) # Evaluate every 2 seconds
