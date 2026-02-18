"""MQTT subscriber for telemetry topics."""

import json
import time
from typing import Callable, Optional

import paho.mqtt.client as mqtt


class MQTTSubscriber:
    """Subscribes to telemetry topics and invokes callback on each message."""

    def __init__(
        self,
        host: str = "localhost",
        port: int = 1883,
        username: Optional[str] = None,
        password: Optional[str] = None,
        on_message: Optional[Callable[[str, dict], None]] = None,
        subscribe_topic: Optional[str] = None,
    ):
        """
        Args:
            host: MQTT broker host
            port: MQTT broker port
            username: Optional username
            password: Optional password
            on_message: Callback(topic, payload_dict) when a message is received
            subscribe_topic: Topic to subscribe to (will subscribe in on_connect)
        """
        self.host = host
        self.port = port
        self.on_message = on_message or (lambda t, p: None)
        self.subscribe_topic = subscribe_topic
        self.client = mqtt.Client(client_id="agent-monitor")
        if username and password:
            self.client.username_pw_set(username, password)
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message
        self.connected = False

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            print(f"[Agent A] Connected to MQTT broker at {self.host}:{self.port}")
            # Subscribe after connection is established
            if self.subscribe_topic:
                self.client.subscribe(self.subscribe_topic)
                print(f"[Agent A] Subscribed to {self.subscribe_topic}")
        else:
            print(f"[Agent A] Failed to connect to MQTT broker, rc={rc}")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode("utf-8"))
            self.on_message(msg.topic, payload)
        except Exception as e:
            print(f"[Agent A] Error processing message: {e}")

    def subscribe(self, topic: str = "telemetry/#"):
        """Subscribe to topic (default: all telemetry)."""
        self.subscribe_topic = topic
        if self.connected:
            self.client.subscribe(topic)
            print(f"[Agent A] Subscribed to {topic}")
        # If not connected yet, subscription will happen in on_connect

    def connect(self):
        """Connect to broker and start loop."""
        self.client.connect(self.host, self.port, keepalive=60)
        self.client.loop_start()
        # Brief wait for connection
        for _ in range(50):
            if self.connected:
                break
            time.sleep(0.1)

    def disconnect(self):
        """Disconnect from broker."""
        self.client.loop_stop()
        self.client.disconnect()
        self.connected = False
