"""MQTT publisher for diagnosis reports."""

from pathlib import Path
from typing import Optional

import paho.mqtt.client as mqtt


class DiagnosisPublisher:
    """Publishes DiagnosisReport to MQTT and appends to diagnosis.jsonl."""

    def __init__(
        self,
        mqtt_client: mqtt.Client,
        diagnosis_topic_prefix: str = "diagnosis",
        log_dir: str = "logs",
    ):
        self.mqtt_client = mqtt_client
        self.diagnosis_topic_prefix = diagnosis_topic_prefix
        self.log_path = Path(log_dir) / "diagnosis.jsonl"
        self._ensure_log_dir()

    def _ensure_log_dir(self):
        self.log_path.parent.mkdir(parents=True, exist_ok=True)

    def publish(self, report, append_jsonl_fn, alert_id: Optional[int] = None):
        """
        Publish diagnosis to MQTT and append to log file.

        Args:
            report: DiagnosisReport model instance
            append_jsonl_fn: Function (path, dict) to append JSONL
            alert_id: Optional alert id for DB linkage
        """
        topic = f"{self.diagnosis_topic_prefix}/{report.asset_id}"
        payload = report.model_dump_json()
        self.mqtt_client.publish(topic, payload, qos=1)
        d = report.model_dump()
        if alert_id is not None:
            d["alert_id"] = alert_id
        append_jsonl_fn(self.log_path, d)
