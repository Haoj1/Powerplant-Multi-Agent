"""MQTT subscriber for alerts topics."""

import json
import time
from typing import Callable, Optional

import paho.mqtt.client as mqtt


class AlertsSubscriber:
    """Subscribes to alerts topics and invokes callback on each message."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 1883,
        username: Optional[str] = None,
        password: Optional[str] = None,
        on_message: Optional[Callable[[str, dict], None]] = None,
        subscribe_topic: Optional[str] = None,
    ):
        self.host = host
        self.port = port
        self.on_message = on_message or (lambda t, p: None)
        self.subscribe_topic = subscribe_topic
        self.client = mqtt.Client(client_id="agent-diagnosis")
        if username and password:
            self.client.username_pw_set(username, password)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.connected = False

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            print(f"[Agent B] Connected to MQTT broker at {self.host}:{self.port}")
            if self.subscribe_topic:
                self.client.subscribe(self.subscribe_topic)
                print(f"[Agent B] Subscribed to {self.subscribe_topic}")
        else:
            print(f"[Agent B] Failed to connect to MQTT broker, rc={rc}")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            self.on_message(msg.topic, payload)
        except Exception as e:
            print(f"[Agent B] Error processing message: {e}")

    def connect(self):
        self.client.connect(self.host, self.port, keepalive=60)
        self.client.loop_start()
        for _ in range(50):
            if self.connected:
                break
            time.sleep(0.1)

    def disconnect(self):
        self.client.loop_stop()
        self.client.disconnect()
        self.connected = False
