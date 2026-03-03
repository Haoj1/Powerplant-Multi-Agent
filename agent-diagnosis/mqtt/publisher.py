"""MQTT publisher for diagnosis reports."""

import json
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

    def publish(self, report, append_jsonl_fn, alert_id: Optional[int] = None, diagnosis_id: Optional[int] = None, eval_metadata: Optional[dict] = None):
        """
        Publish diagnosis to MQTT and append to log file.

        Args:
            report: DiagnosisReport model instance
            append_jsonl_fn: Function (path, dict) to append JSONL
            alert_id: Optional alert id for DB linkage
            diagnosis_id: Optional diagnosis id for Agent C linkage
            eval_metadata: Optional dict with recursion_limit, actual_steps, total_tokens, prompt_tokens, completion_tokens
        """
        topic = f"{self.diagnosis_topic_prefix}/{report.asset_id}"
        d = report.model_dump()
        if alert_id is not None:
            d["alert_id"] = alert_id
        if diagnosis_id is not None:
            d["diagnosis_id"] = diagnosis_id
        if eval_metadata:
            d["recursion_limit"] = eval_metadata.get("recursion_limit")
            d["actual_steps"] = eval_metadata.get("actual_steps")
            d["total_tokens"] = eval_metadata.get("total_tokens")
            d["prompt_tokens"] = eval_metadata.get("prompt_tokens")
            d["completion_tokens"] = eval_metadata.get("completion_tokens")
        payload = json.dumps(d, default=str)
        self.mqtt_client.publish(topic, payload, qos=1)
        append_jsonl_fn(self.log_path, d)
