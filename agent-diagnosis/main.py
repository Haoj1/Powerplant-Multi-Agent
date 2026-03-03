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
from typing import Optional

from fastapi import FastAPI

from shared_lib.config import get_settings
from shared_lib.utils import append_jsonl

try:
    from shared_lib import db as shared_db
except ImportError:
    shared_db = None

try:
    from shared_lib.vector_indexing import index_diagnosis, index_rules
except ImportError:
    index_diagnosis = None
    index_rules = None

from mqtt import AlertsSubscriber, DiagnosisPublisher
from agent import run_diagnosis

try:
    from kafka_queue import DiagnosisQueue
except ImportError:
    DiagnosisQueue = None


app = FastAPI(
    title="Agent Diagnosis",
    description="Performs root cause analysis on alerts using ReAct",
    version="0.1.0",
)

settings = get_settings()
stats = {"alerts_received": 0, "diagnoses_published": 0, "diagnoses_failed": 0, "diagnoses_skipped_cooldown": 0}
_stats_lock = threading.Lock()

subscriber: Optional[AlertsSubscriber] = None
diagnosis_publisher: Optional[DiagnosisPublisher] = None
diagnosis_queue: Optional["DiagnosisQueue"] = None


def _run_and_publish_diagnosis(payload: dict):
    """Run diagnosis and publish to MQTT/DB. Shared by Kafka worker and sync path."""
    global diagnosis_publisher, stats
    asset_id = payload.get("asset_id", "")
    alert_id = payload.get("alert_id")

    print(f"[Agent B] Running diagnosis for {asset_id}...")
    try:
        report, eval_metadata = run_diagnosis(payload)
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
        print(f"[Agent B] eval: recursion_limit={eval_metadata.get('recursion_limit')}, actual_steps={eval_metadata.get('actual_steps')}, tokens={eval_metadata.get('total_tokens')} (prompt={eval_metadata.get('prompt_tokens')}, completion={eval_metadata.get('completion_tokens')})")
        return

    print(f"[Agent B] eval: recursion_limit={eval_metadata.get('recursion_limit')}, actual_steps={eval_metadata.get('actual_steps')}, tokens={eval_metadata.get('total_tokens')} (prompt={eval_metadata.get('prompt_tokens')}, completion={eval_metadata.get('completion_tokens')})")

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
                recursion_limit=eval_metadata.get("recursion_limit"),
                actual_steps=eval_metadata.get("actual_steps"),
                total_tokens=eval_metadata.get("total_tokens"),
                prompt_tokens=eval_metadata.get("prompt_tokens"),
                completion_tokens=eval_metadata.get("completion_tokens"),
            )
            if diagnosis_id and index_diagnosis:
                diagnosis_data = {
                    "asset_id": report.asset_id,
                    "plant_id": report.plant_id,
                    "root_cause": report.root_cause.value if hasattr(report.root_cause, "value") else str(report.root_cause),
                    "confidence": report.confidence,
                    "impact": report.impact.value if hasattr(report.impact, "value") else str(report.impact),
                    "recommended_actions": report.recommended_actions,
                    "evidence": [e.model_dump() if hasattr(e, "model_dump") else e for e in report.evidence],
                }
                index_diagnosis(diagnosis_id, diagnosis_data)
        except Exception as e:
            print(f"[Agent B] DB write error: {e}")

    if diagnosis_publisher:
        try:
            diagnosis_publisher.publish(report, append_jsonl, alert_id=alert_id, diagnosis_id=diagnosis_id, eval_metadata=eval_metadata)
            print(f"[Agent B] Published diagnosis: root_cause={report.root_cause.value}, confidence={report.confidence:.2f}")
        except Exception as e:
            print(f"[Agent B] Publish error: {e}")

    with _stats_lock:
        stats["diagnoses_published"] += 1


# Per-fault cooldown for sync mode (when Kafka disabled)
_sync_fault_cooldown: dict = {}
_sync_cooldown_lock = threading.Lock()


def _fault_key(payload: dict) -> tuple:
    """Per-fault key: (asset_id, tuple of signals). Same fault = same key."""
    asset_id = payload.get("asset_id", "")
    alerts = payload.get("alerts", [])
    signals = tuple(sorted(a.get("signal", "") for a in alerts if a.get("signal")))
    return (asset_id, signals)


def on_alert(topic: str, payload: dict):
    """Handle incoming alert: queue to Kafka (with per-fault cooldown) or run sync."""
    global diagnosis_queue, stats
    with _stats_lock:
        stats["alerts_received"] += 1

    asset_id = payload.get("asset_id", "")
    if not asset_id:
        print("[Agent B] Ignoring alert without asset_id")
        return

    cooldown = settings.diagnosis_cooldown_sec or 60

    if diagnosis_queue and diagnosis_queue.enabled:
        # Kafka mode: enqueue (per-fault cooldown inside enqueue)
        queued = diagnosis_queue.enqueue(payload)
        if not queued:
            with _stats_lock:
                stats["diagnoses_skipped_cooldown"] = stats.get("diagnoses_skipped_cooldown", 0) + 1
            print(f"[Agent B] Skipped (same fault cooldown {cooldown}s): asset={asset_id}")
        else:
            print(f"[Agent B] Queued alert for {asset_id}")
    else:
        # Sync mode: per-fault cooldown, then run directly
        import time
        key = _fault_key(payload)
        now = time.time()
        with _sync_cooldown_lock:
            last = _sync_fault_cooldown.get(key)
            if last is not None and (now - last) < cooldown:
                with _stats_lock:
                    stats["diagnoses_skipped_cooldown"] = stats.get("diagnoses_skipped_cooldown", 0) + 1
                print(f"[Agent B] Skipped (same fault cooldown {cooldown}s): asset={asset_id}")
                return
            _sync_fault_cooldown[key] = now
        _run_and_publish_diagnosis(payload)


@app.on_event("startup")
async def startup_event():
    global subscriber, diagnosis_publisher, diagnosis_queue
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
    # Kafka queue: when enabled, MQTT produces to queue, consumer runs diagnosis
    if DiagnosisQueue:
        cooldown = settings.diagnosis_cooldown_sec or 60
        diagnosis_queue = DiagnosisQueue(
            on_diagnosis=_run_and_publish_diagnosis,
            cooldown_sec=cooldown,
        )
        if diagnosis_queue.enabled:
            diagnosis_queue.start_consumer()
            print(f"[Agent B] Kafka queue enabled for diagnosis (topic={settings.kafka_diagnosis_topic})")
    # Index rules to vector DB on startup
    if index_rules:
        try:
            count = index_rules()
            if count > 0:
                print(f"[Agent B] Indexed {count} rules to vector DB")
        except Exception as e:
            print(f"[Agent B] Failed to index rules: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    global subscriber, diagnosis_queue
    if diagnosis_queue:
        diagnosis_queue.stop()
    if subscriber:
        subscriber.disconnect()


@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "service": "agent-diagnosis",
        "mqtt_connected": subscriber.connected if subscriber else False,
        "kafka_queue_enabled": bool(diagnosis_queue and diagnosis_queue.enabled),
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
