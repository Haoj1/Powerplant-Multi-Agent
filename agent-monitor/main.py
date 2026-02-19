"""Agent Monitor (Agent A) - subscribes to telemetry, detects anomalies, publishes alerts."""

import sys
from pathlib import Path

_project_root = Path(__file__).parent.parent
_agent_dir = Path(__file__).parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
if str(_agent_dir) not in sys.path:
    sys.path.insert(0, str(_agent_dir))

import threading
from typing import Set

from fastapi import FastAPI
from pydantic import ValidationError

from shared_lib.config import get_settings
from shared_lib.models import Telemetry
from shared_lib.utils import append_jsonl

try:
    from shared_lib import db as shared_db
except ImportError:
    shared_db = None

try:
    from shared_lib.vector_indexing import index_alert
except ImportError:
    index_alert = None

from mqtt import MQTTSubscriber, AlertPublisher
from detection import ThresholdDetector


app = FastAPI(
    title="Agent Monitor",
    description="Monitors telemetry and detects anomalies",
    version="0.1.0",
)

# Global state
settings = get_settings()
stats = {
    "messages_processed": 0,
    "alerts_generated": 0,
    "assets_monitored": set(),  # type: Set[str]
}
_stats_lock = threading.Lock()

# Components (initialized on startup)
subscriber: MQTTSubscriber = None
detector: ThresholdDetector = None
alert_publisher: AlertPublisher = None


def on_telemetry(topic: str, payload: dict):
    """Handle incoming telemetry: validate, detect, publish alert if needed."""
    global stats, detector, alert_publisher
    try:
        telemetry = Telemetry.model_validate(payload)
    except ValidationError as e:
        print(f"[Agent A] Invalid telemetry: {e}")
        return

    with _stats_lock:
        stats["messages_processed"] += 1
        stats["assets_monitored"].add(telemetry.asset_id)

    # Debug: print first few telemetry values to see what we're getting
    if stats["messages_processed"] <= 3:
        print(f"[Agent A] Received telemetry #{stats['messages_processed']}: "
              f"pressure={telemetry.signals.pressure_bar:.2f} bar, "
              f"current={telemetry.signals.motor_current_a:.2f} A, "
              f"vibration={telemetry.signals.vibration_rms:.2f} mm/s")
    
    alert = detector.detect(telemetry) if detector else None
    if alert:
        print(f"[Agent A] Alert generated: {alert.severity} - {len(alert.alerts)} signal(s)")
    
    if alert and alert_publisher:
        with _stats_lock:
            stats["alerts_generated"] += 1
        primary_alert_id = None
        if shared_db:
            try:
                primary_alert_id = shared_db.insert_alert(
                    ts=str(alert.ts), plant_id=alert.plant_id, asset_id=alert.asset_id,
                    severity=alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity),
                    alerts_list=[a.model_dump() for a in alert.alerts],
                )
                # Index alert to vector DB for RAG
                if primary_alert_id and index_alert:
                    alert_data = {
                        "asset_id": alert.asset_id,
                        "plant_id": alert.plant_id,
                        "severity": alert.severity.value if hasattr(alert.severity, "value") else str(alert.severity),
                        "signal": alert.alerts[0].signal if alert.alerts else "",
                        "score": alert.alerts[0].score if alert.alerts else 0.0,
                        "method": alert.alerts[0].method if alert.alerts else "",
                        "evidence": alert.alerts[0].evidence if alert.alerts else {},
                    }
                    index_alert(primary_alert_id, alert_data)
            except Exception as e:
                print(f"[Agent A] DB alert write error: {e}")
        alert_for_publish = alert.model_copy(update={"alert_id": primary_alert_id})
        try:
            alert_publisher.publish(alert_for_publish, append_jsonl)
        except Exception as e:
            print(f"[Agent A] Publish error: {e}")


@app.on_event("startup")
async def startup_event():
    global subscriber, detector, alert_publisher
    detector = ThresholdDetector()
    telemetry_topic = f"{settings.mqtt_topic_telemetry}/#"
    subscriber = MQTTSubscriber(
        host=settings.mqtt_host,
        port=settings.mqtt_port,
        username=settings.mqtt_username,
        password=settings.mqtt_password,
        on_message=on_telemetry,
        subscribe_topic=telemetry_topic,
    )
    subscriber.connect()
    # Subscribe if not already done in on_connect
    if subscriber.connected and not subscriber.subscribe_topic:
        subscriber.subscribe(telemetry_topic)
    alert_publisher = AlertPublisher(
        mqtt_client=subscriber.client,
        alerts_topic_prefix=settings.mqtt_topic_alerts,
        log_dir=settings.log_dir,
    )


@app.on_event("shutdown")
async def shutdown_event():
    global subscriber
    if subscriber:
        subscriber.disconnect()


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "agent-monitor",
        "mqtt_connected": subscriber.connected if subscriber else False,
    }


@app.get("/metrics")
async def metrics():
    """Get monitoring metrics."""
    with _stats_lock:
        return {
            "messages_processed": stats["messages_processed"],
            "alerts_generated": stats["alerts_generated"],
            "assets_monitored": list(stats["assets_monitored"]),
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)
