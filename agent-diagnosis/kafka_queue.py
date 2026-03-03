"""Kafka queue for diagnosis: produce alerts to queue, consume and run diagnosis."""

import json
import threading
import time
from typing import Callable, Optional

from shared_lib.config import get_settings


def _fault_key(payload: dict) -> tuple:
    """Per-fault key: (asset_id, tuple of signals). Same fault = same key."""
    asset_id = payload.get("asset_id", "")
    alerts = payload.get("alerts", [])
    signals = tuple(sorted(a.get("signal", "") for a in alerts if a.get("signal")))
    return (asset_id, signals)


def _create_producer():
    """Create Kafka producer. Returns None if Kafka not configured."""
    try:
        from kafka import KafkaProducer
    except ImportError:
        return None
    settings = get_settings()
    servers = (settings.kafka_bootstrap_servers or "").strip()
    if not servers:
        return None
    try:
        return KafkaProducer(
            bootstrap_servers=servers.split(","),
            value_serializer=lambda v: json.dumps(v, default=str).encode("utf-8"),
        )
    except Exception as e:
        print(f"[Agent B] Kafka producer init failed: {e}")
        return None


def _create_consumer(topic: str):
    """Create Kafka consumer. Returns None if Kafka not configured."""
    try:
        from kafka import KafkaConsumer
    except ImportError:
        return None
    settings = get_settings()
    servers = (settings.kafka_bootstrap_servers or "").strip()
    if not servers:
        return None
    try:
        return KafkaConsumer(
            topic,
            bootstrap_servers=servers.split(","),
            value_deserializer=lambda m: json.loads(m.decode("utf-8")) if m else None,
            auto_offset_reset="earliest",
            enable_auto_commit=True,
        )
    except Exception as e:
        print(f"[Agent B] Kafka consumer init failed: {e}")
        return None


class DiagnosisQueue:
    """
    Queue diagnosis requests via Kafka.
    - Per-fault cooldown: (asset_id, signals) won't be queued again within cooldown_sec
    - Producer: enqueue alerts from MQTT
    - Consumer: run diagnosis in worker thread
    """

    def __init__(
        self,
        on_diagnosis: Callable[[dict], None],
        cooldown_sec: float = 60.0,
    ):
        self.on_diagnosis = on_diagnosis
        self.cooldown_sec = cooldown_sec
        self._fault_cooldown: dict[tuple, float] = {}
        self._cooldown_lock = threading.Lock()
        self._producer = _create_producer()
        self._consumer = None
        self._worker_thread: Optional[threading.Thread] = None
        self._stop = threading.Event()

    @property
    def enabled(self) -> bool:
        return self._producer is not None

    def enqueue(self, payload: dict) -> bool:
        """
        Enqueue alert for diagnosis. Returns True if queued, False if skipped (cooldown).
        """
        if not self._producer:
            return False
        asset_id = payload.get("asset_id", "")
        if not asset_id:
            return False
        key = _fault_key(payload)
        now = time.time()
        with self._cooldown_lock:
            last = self._fault_cooldown.get(key)
            if last is not None and (now - last) < self.cooldown_sec:
                return False
            self._fault_cooldown[key] = now
        try:
            settings = get_settings()
            topic = settings.kafka_diagnosis_topic
            self._producer.send(topic, value=payload)
            self._producer.flush()
            return True
        except Exception as e:
            print(f"[Agent B] Kafka produce error: {e}")
            with self._cooldown_lock:
                self._fault_cooldown.pop(key, None)
            return False

    def _consume_loop(self):
        """Consumer loop: poll and run diagnosis."""
        if not self._consumer:
            return
        settings = get_settings()
        topic = settings.kafka_diagnosis_topic
        self._consumer.subscribe([topic])
        print(f"[Agent B] Kafka consumer started, topic={topic}")
        while not self._stop.is_set():
            try:
                msgs = self._consumer.poll(timeout_ms=1000)
                for msgs_list in msgs.values():
                    for msg in msgs_list:
                        if msg.value:
                            try:
                                self.on_diagnosis(msg.value)
                            except Exception as e:
                                print(f"[Agent B] Diagnosis error in worker: {e}")
                                import traceback
                                traceback.print_exc()
            except Exception as e:
                if not self._stop.is_set():
                    print(f"[Agent B] Kafka consumer error: {e}")
        print("[Agent B] Kafka consumer stopped")

    def start_consumer(self):
        """Start background consumer thread."""
        if not self.enabled:
            return
        settings = get_settings()
        topic = settings.kafka_diagnosis_topic
        self._consumer = _create_consumer(topic)
        if not self._consumer:
            return
        self._stop.clear()
        self._worker_thread = threading.Thread(target=self._consume_loop, daemon=True)
        self._worker_thread.start()

    def stop(self):
        """Stop consumer and close producer."""
        self._stop.set()
        if self._worker_thread:
            self._worker_thread.join(timeout=5)
        if self._consumer:
            try:
                self._consumer.close()
            except Exception:
                pass
        if self._producer:
            try:
                self._producer.close()
            except Exception:
                pass
