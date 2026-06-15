import os
import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.requests import Request
from pydantic import BaseModel

from simulation_engine import start_simulation, fleet_state
from alert_manager import alert_monitor_loop, alert_queue, get_all_rules, update_alert_rule, delete_alert_rule
from ai_backend import process_chat

app = FastAPI()

# Mount static files and templates
os.makedirs(r"D:\CAN\static\css", exist_ok=True)
os.makedirs(r"D:\CAN\static\js", exist_ok=True)
os.makedirs(r"D:\CAN\templates", exist_ok=True)

app.mount("/static", StaticFiles(directory=r"D:\CAN\static"), name="static")
templates = Jinja2Templates(directory=r"D:\CAN\templates")

class ChatRequest(BaseModel):
    message: str

class RuleUpdateRequest(BaseModel):
    threshold: float
    message: str
    enabled: bool

@app.on_event("startup")
async def startup_event():
    # Start the simulation loop
    asyncio.create_task(start_simulation())
    # Start the persistent alert monitor
    asyncio.create_task(alert_monitor_loop())

@app.get("/", response_class=HTMLResponse)
async def get_dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="index.html")

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    # Pass user query to AI Agent
    reply = await process_chat(req.message)
    return {"reply": reply}

@app.get("/api/prompts")
async def get_prompts():
    try:
        with open(r"D:\CAN\prompts.txt", "r", encoding="utf-8") as f:
            prompts = [line.strip() for line in f.readlines() if line.strip()]
        return {"prompts": prompts}
    except FileNotFoundError:
        return {"prompts": []}

@app.get("/api/rules")
async def api_get_rules():
    rules = get_all_rules()
    formatted = []
    for r in rules:
        formatted.append({
            "id": r[0], "vehicle_id": r[1], "metric": r[2], 
            "operator": r[3], "threshold": r[4], "message": r[5],
            "enabled": bool(r[6])
        })
    return {"rules": formatted}

@app.put("/api/rules/{rule_id}")
async def api_update_rule(rule_id: int, req: RuleUpdateRequest):
    update_alert_rule(rule_id, req.threshold, req.message, req.enabled)
    return {"status": "success"}

@app.delete("/api/rules/{rule_id}")
async def api_delete_rule(rule_id: int):
    delete_alert_rule(rule_id)
    return {"status": "success"}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        while True:
            # Prepare payload
            payload = {"telemetry": fleet_state, "alerts": []}
            
            # Flush any pending alerts from the queue to send to UI
            while not alert_queue.empty():
                alert_msg = await alert_queue.get()
                payload["alerts"].append(alert_msg)
            
            await websocket.send_json(payload)
            await asyncio.sleep(1) # Broadcast at 1Hz
    except WebSocketDisconnect:
        print("Client disconnected from WebSocket.")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
