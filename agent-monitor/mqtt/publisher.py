"""MQTT publisher for alert events."""

from pathlib import Path
from typing import Optional

import paho.mqtt.client as mqtt


class AlertPublisher:
    """Publishes AlertEvent to MQTT and appends to alerts.jsonl."""

    def __init__(
        self,
        mqtt_client: mqtt.Client,
        alerts_topic_prefix: str = "alerts",
        log_dir: str = "logs",
    ):
        self.mqtt_client = mqtt_client
        self.alerts_topic_prefix = alerts_topic_prefix
        self.log_path = Path(log_dir) / "alerts.jsonl"
        self._ensure_log_dir()

    def _ensure_log_dir(self):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def publish(self, alert_event, append_jsonl_fn):
        """
        Publish alert to MQTT and append to log file.

        Args:
            alert_event: AlertEvent model instance
            append_jsonl_fn: Function (path, dict) to append JSONL
        """
        topic = f"{self.alerts_topic_prefix}/{alert_event.asset_id}"
        payload = alert_event.model_dump_json()
        self.mqtt_client.publish(topic, payload, qos=1)
        append_jsonl_fn(self.log_path, alert_event.model_dump())
