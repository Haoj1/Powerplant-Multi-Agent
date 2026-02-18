"""MQTT publisher for vision: image-ready (path only) and optional VLM description."""

from pathlib import Path
from typing import Optional

import paho.mqtt.client as mqtt

from shared_lib.models import VisionImageReady, VisionDescription
from shared_lib.utils import append_jsonl


class VisionPublisher:
    """Publishes VisionImageReady (image path only) or VisionDescription (after VLM)."""

    def __init__(
        self,
        mqtt_client: mqtt.Client,
        vision_topic_prefix: str = "vision",
        log_dir: str = "logs",
    ):
        self.mqtt_client = mqtt_client
        self.vision_topic_prefix = vision_topic_prefix
        self.log_dir = Path(log_dir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.images_log_path = self.log_dir / "vision_images.jsonl"
        self.descriptions_log_path = self.log_dir / "vision.jsonl"

    def publish_image_ready(self, msg: VisionImageReady) -> None:
        """Publish that a new image was saved (no VLM). Agents subscribe to get image_path and call VLM when needed."""
        topic = f"{self.vision_topic_prefix}/{msg.asset_id}"
        payload = msg.model_dump_json()
        self.mqtt_client.publish(topic, payload, qos=1)
        append_jsonl(self.images_log_path, msg.model_dump())

    def publish(self, vision: VisionDescription) -> None:
        """Publish VLM analysis result (used by agents after they call VLM)."""
        topic = f"{self.vision_topic_prefix}/{vision.asset_id}"
        payload = vision.model_dump_json()
        self.mqtt_client.publish(topic, payload, qos=1)
        append_jsonl(self.descriptions_log_path, vision.model_dump())
