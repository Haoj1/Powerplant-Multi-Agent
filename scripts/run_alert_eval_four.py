#!/usr/bin/env python3
"""
Run ONLY temp_c and rpm scenarios for quick testing (reduced from full 4-scenario eval).

Scenarios:
  - sensor_drift_eval -> temp_c (sensor_override temp=120)
  - rpm_eval -> rpm (sensor_override rpm=500)

Usage: python scripts/run_alert_eval_four.py [--debug]
  --debug: print last 5 DB telemetry rows after each scenario (temp, rpm, valve, flow)

Requires: MQTT, Simulator (8001), Agent A (8002)

To debug: run with --debug, or in another terminal: python scripts/mqtt_telemetry_debug.py
"""

import json
import sys
import time
from pathlib import Path

DEBUG = "--debug" in sys.argv

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)

_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
_simulator_dir = _project_root / "simulator-service"
_scenarios_dir = _simulator_dir / "scenarios"

SIMULATOR_URL = "http://localhost:8001"
AGENT_A_URL = "http://localhost:8002"
ASSET_ID = "pump01"

# Only temp_c and rpm (quick test)
SCENARIOS = [
    ("sensor_drift_eval", 30, "temp_c"),
    ("rpm_eval", 30, "rpm"),
]

HEALTH_DURATION = 10
RESET_DURATION = 10


def load_scenario(name: str, **overrides) -> dict:
    path = _scenarios_dir / f"{name}.json"
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    for k, v in overrides.items():
        if k == "resistance_factor" and "faults" in data:
            for f in data["faults"]:
                if f.get("type") == "clogging" and "params" in f:
                    f["params"]["resistance_factor"] = v
        elif k == "valve_stuck_pct" and "faults" in data:
            for f in data["faults"]:
                if f.get("type") == "valve_stuck" and "params" in f:
                    f["params"]["stuck_value"] = v
        elif k == "valve_open_pct" and "initial_conditions" in data:
            data["initial_conditions"]["valve_open_pct"] = v
        elif k == "initial_rpm" and "initial_conditions" in data:
            data["initial_conditions"]["rpm"] = v
        elif k == "drift_rate" and "faults" in data:
            for f in data["faults"]:
                if f.get("type") == "sensor_drift" and "params" in f:
                    f["params"]["drift_rate"] = v
        elif k == "drift_rate_temp_c" and "faults" in data:
            for f in data["faults"]:
                if f.get("type") == "sensor_drift" and f.get("params", {}).get("signal") == "temp_c":
                    f["params"]["drift_rate"] = v
        elif k == "rpm_setpoint":
            if data.get("setpoints"):
                data["setpoints"][0]["rpm"] = v
            else:
                data.setdefault("setpoints", []).append({"time_sec": 0, "rpm": v})
        elif k == "add_faults" and isinstance(v, list):
            data.setdefault("faults", []).extend(v)
        elif k == "replace_faults" and isinstance(v, list):
            data["faults"] = v  # Replace entirely to ensure sensor_override is used
    return data


def api_load(scenario: dict):
    return requests.post(f"{SIMULATOR_URL}/scenario/load", json={"scenario": scenario}, timeout=10).raise_for_status()


def api_start(asset_id: str):
    return requests.post(f"{SIMULATOR_URL}/scenario/start/{asset_id}", timeout=10).raise_for_status()


def api_stop(asset_id: str):
    return requests.post(f"{SIMULATOR_URL}/scenario/stop/{asset_id}", timeout=10).raise_for_status()


def fetch_alerts():
    try:
        from dotenv import load_dotenv
        load_dotenv(_project_root / ".env")
        from shared_lib import db as shared_db
        return shared_db.query_alerts(asset_id=ASSET_ID, limit=50)
    except Exception:
        return []


def main():
    print("=" * 60)
    print("Alert Eval: temp_c + rpm only (quick test)")
    print("  sensor_drift->temp_c | rpm")
    print("=" * 60)

    try:
        requests.get(f"{SIMULATOR_URL}/scenarios", timeout=5).raise_for_status()
    except requests.RequestException as e:
        print(f"Simulator not reachable: {e}")
        sys.exit(1)

    m0 = {}
    try:
        r = requests.get(f"{AGENT_A_URL}/metrics", timeout=3)
        h = requests.get(f"{AGENT_A_URL}/health", timeout=3)
        if r.ok and h.ok:
            m0 = {**r.json(), "mqtt_connected": h.json().get("mqtt_connected", False)}
    except Exception:
        pass
    if not m0 or not m0.get("mqtt_connected", True):
        print("Agent A not reachable or MQTT not connected. Start both first.")
        sys.exit(1)

    print(f"Agent A: messages={m0.get('messages_processed', 0)}, mqtt=OK\n")

    # Initial health
    print("[Health] healthy_baseline 15s...")
    api_load(load_scenario("healthy_baseline"))
    api_start(ASSET_ID)
    time.sleep(HEALTH_DURATION)
    api_stop(ASSET_ID)

    expected = {"temp_c", "rpm"}

    for i, (name, run_sec, target_signal) in enumerate(SCENARIOS):
        if i > 0:
            print("\n[Reset] healthy_baseline 15s...")
            api_load(load_scenario("healthy_baseline"))
            api_start(ASSET_ID)
            time.sleep(RESET_DURATION)
            api_stop(ASSET_ID)

        overrides = {}
        if "clogging" in name and "valve" not in name:
            overrides = {
                "valve_open_pct": 35,
                "resistance_factor": 80,
                "add_faults": [
                    {"type": "sensor_drift", "start_time_sec": 0, "params": {"signal": "pressure_bar", "drift_rate": 2.5}},
                    {"type": "sensor_drift", "start_time_sec": 0, "params": {"signal": "motor_current_a", "drift_rate": 20.0}},
                ],
            }
        elif "valve_flow" in name:
            overrides = {"resistance_factor": 800, "valve_stuck_pct": 80}

        if "sensor_drift" in name:
            scenario = json.loads((_scenarios_dir / "sensor_drift_eval_temp_override.json").read_text(encoding="utf-8"))
        elif "rpm" in name:
            scenario = json.loads((_scenarios_dir / "rpm_eval_override.json").read_text(encoding="utf-8"))
        else:
            scenario = load_scenario(name, **overrides)

        print(f"\n[{name}] {run_sec}s -> expect {target_signal}")
        api_load(scenario)
        api_start(ASSET_ID)
        time.sleep(run_sec)
        api_stop(ASSET_ID)
        time.sleep(5)

        if DEBUG:
            try:
                from dotenv import load_dotenv
                load_dotenv(_project_root / ".env")
                from shared_lib import db as shared_db
                rows = shared_db.query_telemetry(asset_id=ASSET_ID, limit=5)
                for r in rows[:3]:
                    print(f"    [DB] temp={r.get('temp_c',0):.1f} rpm={r.get('rpm',0):.0f} valve={r.get('valve_open_pct',0):.1f}% flow={r.get('flow_m3h',0):.1f} fault={r.get('fault','?')}")
            except Exception as e:
                print(f"    [DB] err: {e}")

        alerts = fetch_alerts()
        signals = {a.get("signal") for a in alerts}
        hit = target_signal in signals
        status = "OK" if hit else "MISS"
        print(f"  [{status}] DB signals: {', '.join(sorted(signals)) or 'none'}")

    print("\n" + "=" * 60)
    alerts = fetch_alerts()
    by_signal = {}
    for a in alerts:
        s = a.get("signal", "?")
        by_signal[s] = by_signal.get(s, 0) + 1
    print("Final alerts by signal:", by_signal)
    missing = expected - {a.get("signal") for a in alerts}
    if missing:
        print(f"MISSING: {missing}")
    else:
        print("All 2 expected alerts present.")
    print("=" * 60)


if __name__ == "__main__":
    main()
