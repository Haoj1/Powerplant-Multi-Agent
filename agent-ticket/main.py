"""Agent Ticket (Agent C) - creates review requests from diagnoses for Agent D."""

import sys
from pathlib import Path

_project_root = Path(__file__).parent.parent
_agent_dir = Path(__file__).parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
if str(_agent_dir) not in sys.path:
    sys.path.insert(0, str(_agent_dir))

# Load .env from project root
try:
    from dotenv import load_dotenv
    if (_project_root / ".env").exists():
        load_dotenv(_project_root / ".env")
except Exception:
    pass

import threading
import time
from typing import Optional

from fastapi import FastAPI

from shared_lib.config import get_settings

try:
    from shared_lib import db as shared_db
except ImportError:
    shared_db = None

from mqtt import DiagnosisSubscriber


app = FastAPI(
    title="Agent Ticket",
    description="Creates review requests from diagnosis reports for Agent D",
    version="0.1.0",
)

settings = get_settings()
stats = {"diagnoses_received": 0, "review_requests_created": 0, "skipped_cooldown": 0}
_stats_lock = threading.Lock()
_last_review_request_time: dict = {}  # asset_id -> timestamp

subscriber: Optional[DiagnosisSubscriber] = None


def on_diagnosis(topic: str, payload: dict):
    """Handle incoming diagnosis: create review_request if not in cooldown."""
    global stats, _last_review_request_time
    with _stats_lock:
        stats["diagnoses_received"] += 1

    diagnosis_id = payload.get("diagnosis_id")
    asset_id = payload.get("asset_id", "")
    plant_id = payload.get("plant_id", "")
    ts = payload.get("ts", "")

    if not diagnosis_id:
        print("[Agent C] Ignoring diagnosis without diagnosis_id")
        return

    if not asset_id:
        print("[Agent C] Ignoring diagnosis without asset_id")
        return

    cooldown = getattr(settings, "ticket_cooldown_sec", 30.0) or 0.0
    if cooldown > 0:
        now = time.time()
        last = _last_review_request_time.get(asset_id, 0)
        if now - last < cooldown:
            with _stats_lock:
                stats["skipped_cooldown"] = stats.get("skipped_cooldown", 0) + 1
            print(f"[Agent C] Skipped {asset_id} (cooldown {cooldown}s)")
            return

    if shared_db:
        try:
            shared_db.insert_review_request(
                diagnosis_id=int(diagnosis_id),
                plant_id=str(plant_id),
                asset_id=str(asset_id),
                ts=str(ts),
                status="pending",
            )
            _last_review_request_time[asset_id] = time.time()
            print(f"[Agent C] Created review_request for diagnosis_id={diagnosis_id} asset={asset_id}")
        except Exception as e:
            print(f"[Agent C] DB write error: {e}")
            return

    with _stats_lock:
        stats["review_requests_created"] += 1


@app.on_event("startup")
async def startup_event():
    global subscriber
    diagnosis_topic = f"{settings.mqtt_topic_diagnosis}/#"
    subscriber = DiagnosisSubscriber(
        host=settings.mqtt_host,
        port=settings.mqtt_port,
        username=settings.mqtt_username,
        password=settings.mqtt_password,
        on_message=on_diagnosis,
        subscribe_topic=diagnosis_topic,
    )
    subscriber.connect()


@app.on_event("shutdown")
async def shutdown_event():
    global subscriber
    if subscriber:
        subscriber.disconnect()


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "agent-ticket",
        "mqtt_connected": subscriber.connected if subscriber else False,
    }


@app.get("/metrics")
async def metrics():
    with _stats_lock:
        return {
            "diagnoses_received": stats["diagnoses_received"],
            "review_requests_created": stats["review_requests_created"],
            "skipped_cooldown": stats.get("skipped_cooldown", 0),
        }


@app.get("/tickets")
async def list_tickets():
    """Placeholder - tickets are created by Agent D. Returns empty for now."""
    return {"tickets": []}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8004)
