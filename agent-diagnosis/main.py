"""Agent Diagnosis (Agent B) - subscribes to alerts, runs ReAct diagnosis, publishes reports."""

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
from shared_lib.utils import append_jsonl

try:
    from shared_lib import db as shared_db
except ImportError:
    shared_db = None

from mqtt import AlertsSubscriber, DiagnosisPublisher
from agent import run_diagnosis


app = FastAPI(
    title="Agent Diagnosis",
    description="Performs root cause analysis on alerts using ReAct",
    version="0.1.0",
)

settings = get_settings()
stats = {"alerts_received": 0, "diagnoses_published": 0, "diagnoses_failed": 0, "diagnoses_skipped_cooldown": 0}
_stats_lock = threading.Lock()
_last_diagnosis_time: float = 0.0

subscriber: Optional[AlertsSubscriber] = None
diagnosis_publisher: Optional[DiagnosisPublisher] = None


def on_alert(topic: str, payload: dict):
    """Handle incoming alert: run ReAct diagnosis, publish and write to DB (with cooldown)."""
    global diagnosis_publisher, stats, _last_diagnosis_time
    with _stats_lock:
        stats["alerts_received"] += 1

    asset_id = payload.get("asset_id", "")
    alert_id = payload.get("alert_id")
    if not asset_id:
        print("[Agent B] Ignoring alert without asset_id")
        return

    cooldown = getattr(settings, "diagnosis_cooldown_sec", 20.0) or 0.0
    if cooldown > 0:
        now = time.time()
        if now - _last_diagnosis_time < cooldown:
            with _stats_lock:
                stats["diagnoses_skipped_cooldown"] = stats.get("diagnoses_skipped_cooldown", 0) + 1
            print(f"[Agent B] Skipped (cooldown {cooldown}s), next in {cooldown - (now - _last_diagnosis_time):.0f}s")
            return

    print(f"[Agent B] Received alert for {asset_id}, running diagnosis...")
    try:
        report = run_diagnosis(payload)
    except Exception as e:
        print(f"[Agent B] Diagnosis error: {e}")
        import traceback
        traceback.print_exc()
        with _stats_lock:
            stats["diagnoses_failed"] += 1
        return

    if not report:
        print("[Agent B] Could not produce diagnosis (parse or LLM error)")
        with _stats_lock:
            stats["diagnoses_failed"] += 1
        return

    diagnosis_id = None
    if shared_db:
        try:
            diagnosis_id = shared_db.insert_diagnosis(
                ts=str(report.ts),
                plant_id=report.plant_id,
                asset_id=report.asset_id,
                root_cause=report.root_cause.value if hasattr(report.root_cause, "value") else str(report.root_cause),
                confidence=report.confidence,
                impact=report.impact.value if hasattr(report.impact, "value") else str(report.impact),
                recommended_actions=report.recommended_actions,
                evidence=[e.model_dump() if hasattr(e, "model_dump") else e for e in report.evidence],
                alert_id=alert_id,
            )
        except Exception as e:
            print(f"[Agent B] DB write error: {e}")

    if diagnosis_publisher:
        try:
            diagnosis_publisher.publish(report, append_jsonl, alert_id=alert_id, diagnosis_id=diagnosis_id)
            print(f"[Agent B] Published diagnosis: root_cause={report.root_cause.value}, confidence={report.confidence:.2f}")
        except Exception as e:
            print(f"[Agent B] Publish error: {e}")

    with _stats_lock:
        stats["diagnoses_published"] += 1
    _last_diagnosis_time = time.time()


@app.on_event("startup")
async def startup_event():
    global subscriber, diagnosis_publisher
    alerts_topic = f"{settings.mqtt_topic_alerts}/#"
    subscriber = AlertsSubscriber(
        host=settings.mqtt_host,
        port=settings.mqtt_port,
        username=settings.mqtt_username,
        password=settings.mqtt_password,
        on_message=on_alert,
        subscribe_topic=alerts_topic,
    )
    subscriber.connect()
    diagnosis_publisher = DiagnosisPublisher(
        mqtt_client=subscriber.client,
        diagnosis_topic_prefix=settings.mqtt_topic_diagnosis,
        log_dir=settings.log_dir,
    )


@app.on_event("shutdown")
async def shutdown_event():
    global subscriber
    if subscriber:
        subscriber.disconnect()


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "agent-diagnosis",
        "mqtt_connected": subscriber.connected if subscriber else False,
    }


@app.get("/metrics")
async def metrics():
    with _stats_lock:
        return {
            "alerts_received": stats["alerts_received"],
            "diagnoses_published": stats["diagnoses_published"],
            "diagnoses_failed": stats["diagnoses_failed"],
            "diagnoses_skipped_cooldown": stats.get("diagnoses_skipped_cooldown", 0),
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)
