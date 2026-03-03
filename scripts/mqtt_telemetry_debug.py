#!/usr/bin/env python3
"""
Subscribe to MQTT telemetry and print temp_c, rpm, valve, flow for debugging.
Run in a separate terminal while run_alert_eval_four runs.
Usage: python scripts/mqtt_telemetry_debug.py
"""
import json
import sys
from pathlib import Path

_project_root = Path(__file__).parent.parent
sys.path.insert(0, str(_project_root))

try:
    import paho.mqtt.client as mqtt
except ImportError:
    print("pip install paho-mqtt")
    sys.exit(1)

from dotenv import load_dotenv
load_dotenv(_project_root / ".env")

host = __import__("os").environ.get("MQTT_HOST", "localhost")
port = int(__import__("os").environ.get("MQTT_PORT", "1883"))
topic = "telemetry/#"

count = 0
max_print = 80  # Print first 80 messages

def on_message(client, userdata, msg):
    global count
    count += 1
    if count > max_print:
        return
    try:
        payload = json.loads(msg.payload.decode())
        s = payload.get("signals", {})
        truth = payload.get("truth", {})
        fault = truth.get("fault", "?")
        t = s.get("temp_c", 0)
        r = s.get("rpm", 0)
        v = s.get("valve_open_pct", 0)
        f = s.get("flow_m3h", 0)
        # Highlight when values would trigger our 3 alerts
        flags = []
        if t >= 55: flags.append("TEMP_OK")
        if r < 2650: flags.append("RPM_OK")
        if v >= 65 and f <= 68: flags.append("VALVE_FLOW_OK")
        flag_str = " " + " ".join(flags) if flags else ""
        print(f"  #{count}: temp={t:.1f} rpm={r:.0f} valve={v:.1f}% flow={f:.1f} fault={fault}{flag_str}")
    except Exception as e:
        print(f"  #{count}: parse error: {e}")

client = mqtt.Client(client_id="mqtt-debug")
client.on_message = on_message
client.connect(host, port, 60)
client.subscribe(topic)
print(f"Subscribed to {topic}. Printing first {max_print} messages...\n")
client.loop_forever()
