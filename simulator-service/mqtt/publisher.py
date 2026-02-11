"""MQTT publisher for telemetry data."""

import json
import time
from typing import Optional
import paho.mqtt.client as mqtt

import sys
from pathlib import Path

# Add project root to path for shared-lib imports
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from shared_lib.models import Telemetry
from shared_lib.config import Settings, get_settings
from shared_lib.utils import format_mqtt_topic


class MQTTPublisher:
    """Publishes telemetry data to MQTT broker."""
    
    def __init__(self, settings: Optional[Settings] = None):
        """
        Initialize MQTT publisher.
        
        Args:
            settings: Application settings (defaults to get_settings())
        """
        self.settings = settings or get_settings()
        self.client: Optional[mqtt.Client] = None
        self.connected = False
        
    def connect(self):
        """Connect to MQTT broker."""
        self.client = mqtt.Client(client_id="simulator-service")
        
        # Set credentials if provided
        if self.settings.mqtt_username and self.settings.mqtt_password:
            self.client.username_pw_set(
                self.settings.mqtt_username,
                self.settings.mqtt_password
            )
        
        # Set callbacks
        self.client.on_connect = self._on_connect
        self.client.on_disconnect = self._on_disconnect
        
        try:
            self.client.connect(
                self.settings.mqtt_host,
                self.settings.mqtt_port,
                keepalive=60
            )
            self.client.loop_start()
            
            # Wait for connection
            timeout = 5.0
            start_time = time.time()
            while not self.connected and (time.time() - start_time) < timeout:
                time.sleep(0.1)
            
            if not self.connected:
                raise ConnectionError("Failed to connect to MQTT broker")
                
        except Exception as e:
            raise ConnectionError(f"MQTT connection error: {e}")
    
    def _on_connect(self, client, userdata, flags, rc):
        """Callback for MQTT connection."""
        if rc == 0:
            self.connected = True
            print(f"Connected to MQTT broker at {self.settings.mqtt_host}:{self.settings.mqtt_port}")
        else:
            print(f"Failed to connect to MQTT broker, return code {rc}")
    
    def _on_disconnect(self, client, userdata, rc):
        """Callback for MQTT disconnection."""
        self.connected = False
        print("Disconnected from MQTT broker")
    
    def publish_telemetry(self, telemetry: Telemetry):
        """
        Publish telemetry to MQTT.
        
        Args:
            telemetry: Telemetry object to publish
        """
        if not self.connected or not self.client:
            raise RuntimeError("MQTT client not connected")
        
        # Format topic: telemetry/{asset_id}
        topic = format_mqtt_topic(
            self.settings.mqtt_topic_telemetry,
            telemetry.asset_id
        )
        
        # Convert to JSON
        payload = telemetry.model_dump_json()
        
        # Publish
        result = self.client.publish(topic, payload, qos=1)
        
        if result.rc != mqtt.MQTT_ERR_SUCCESS:
            print(f"Warning: Failed to publish telemetry to {topic}")
    
    def disconnect(self):
        """Disconnect from MQTT broker."""
        if self.client:
            self.client.loop_stop()
            self.client.disconnect()
            self.connected = False
