#!/usr/bin/env python3
"""
Run health + all alert-triggering scenarios in sequence for testing and evaluation.

Triggers ALL Agent A alerts (slope + threshold):
  - bearing_wear_eval: vibration_rms, bearing_temp_c (slope + threshold)
  - clogging_eval: flow_m3h, pressure_bar, motor_current_a (threshold + slope)
  - valve_flow_mismatch_eval: valve_flow_mismatch
  - sensor_drift_eval: pressure_bar, temp_c (threshold)
  - rpm_eval: rpm (range)
  - noise_burst_eval: vibration_rms (spike)

Flow: health -> scenario1 -> health -> scenario2 -> ... -> health (reset between each)
Total time: ~10-12 min.

Required (all must be running):
  1. MQTT broker (e.g. docker compose up -d mosquitto)
  2. Simulator (localhost:8001)
  3. Agent A (subscribes to telemetry, detects alerts, writes to DB)
"""

import json
import os
import random
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

try:
    import requests
except ImportError:
    print("Install requests: pip install requests")
    sys.exit(1)

# Project root (add for shared_lib import)
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))
_simulator_dir = _project_root / "simulator-service"
_scenarios_dir = _simulator_dir / "scenarios"

SIMULATOR_URL = "http://localhost:8001"
AGENT_A_URL = "http://localhost:8002"
ASSET_ID = "pump01"

# (scenario_name, run_sec, description)
SCENARIOS = [
    ("bearing_wear_eval", 120, "vibration_rms, bearing_temp_c (slope+threshold)"),
    ("clogging_eval", 120, "flow_m3h, pressure_bar, motor_current_a"),
    ("valve_flow_mismatch_eval", 120, "valve_flow_mismatch"),
    ("sensor_drift_eval", 120, "temp_c (sensor_override=120)"),
    ("rpm_eval", 90, "rpm (sensor_override=500)"),
    ("noise_burst_eval", 90, "vibration_rms (noise spike)"),
]

HEALTH_DURATION = 20
RESET_DURATION = 20  # Health/reset interval between fault scenarios
CYCLES = 6  # Run full sequence 6 times (fixed) for data samples


def load_scenario(name: str, **overrides) -> dict:
    """Load scenario JSON, optionally override fields. Supports fault param overrides."""
    path = _scenarios_dir / f"{name}.json"
    if not path.exists():
        raise FileNotFoundError(f"Scenario not found: {path}")
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    for k, v in overrides.items():
        if k == "rate_per_sec" and "faults" in data:
            for f in data["faults"]:
                if f.get("type") == "bearing_wear" and "params" in f:
                    f["params"]["rate_per_sec"] = v
        elif k == "resistance_factor" and "faults" in data:
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
        elif k == "noise_amplitude" and "faults" in data:
            for f in data["faults"]:
                if f.get("type") == "noise_burst" and "params" in f:
                    f["params"]["noise_amplitude"] = v
        elif k == "rpm_setpoint":
            if data.get("setpoints"):
                data["setpoints"][0]["rpm"] = v
                if "time_sec" not in data["setpoints"][0]:
                    data["setpoints"][0]["time_sec"] = 0
            else:
                data["setpoints"] = [{"time_sec": 0, "rpm": v}]
        elif k == "add_faults" and isinstance(v, list):
            data.setdefault("faults", []).extend(v)
        elif k == "replace_faults" and isinstance(v, list):
            data["faults"] = v
        else:
            data[k] = v
    return data


def api_load(scenario: dict) -> dict:
    r = requests.post(f"{SIMULATOR_URL}/scenario/load", json={"scenario": scenario}, timeout=10)
    r.raise_for_status()
    return r.json()


def api_start(asset_id: str) -> dict:
    r = requests.post(f"{SIMULATOR_URL}/scenario/start/{asset_id}", timeout=10)
    r.raise_for_status()
    return r.json()


def api_stop(asset_id: str) -> dict:
    r = requests.post(f"{SIMULATOR_URL}/scenario/stop/{asset_id}", timeout=10)
    r.raise_for_status()
    return r.json()


def fetch_alerts_from_db(asset_id: str = "pump01", limit: int = 50) -> list:
    """Query alerts from SQLite. Returns list of dicts."""
    try:
        from dotenv import load_dotenv
        load_dotenv(_project_root / ".env")
    except Exception:
        pass
    try:
        from shared_lib import db as shared_db
    except ImportError:
        return []
    if not shared_db:
        return []
    try:
        return shared_db.query_alerts(asset_id=asset_id, limit=limit)
    except Exception as e:
        print(f"  [DB] Query error: {e}")
        return []


def print_alerts_summary(asset_id: str = "pump01"):
    """Print recent alerts from DB."""
    alerts = fetch_alerts_from_db(asset_id=asset_id, limit=30)
    if not alerts:
        print("  [DB] No alerts found.")
        return
    print(f"  [DB] Alerts ({len(alerts)}):")
    for a in alerts[:15]:
        ts = a.get("ts", "?")[:19] if a.get("ts") else "?"
        sig = a.get("signal", "?")
        sev = a.get("severity", "?")
        score = a.get("score", 0)
        print(f"    - {ts} | {sig} | {sev} | score={score}")


def get_agent_a_metrics() -> dict:
    """Fetch Agent A metrics (messages_processed, alerts_generated, mqtt_connected)."""
    try:
        m = requests.get(f"{AGENT_A_URL}/metrics", timeout=3)
        h = requests.get(f"{AGENT_A_URL}/health", timeout=3)
        if m.ok and h.ok:
            return {**m.json(), "mqtt_connected": h.json().get("mqtt_connected", False)}
    except Exception:
        pass
    return {}


def main():
    cycles = CYCLES
    print("=" * 70)
    print("Alert Eval: ALL alert types (health -> fault -> health -> ...)")
    print(f"Cycles: {cycles} | Health: {HEALTH_DURATION}s | Reset: {RESET_DURATION}s")
    print("=" * 70)

    try:
        r = requests.get(f"{SIMULATOR_URL}/scenarios", timeout=5)
        r.raise_for_status()
    except requests.RequestException as e:
        print(f"Simulator not reachable at {SIMULATOR_URL}. Start it first.")
        print(f"  Error: {e}")
        sys.exit(1)

    # Check MQTT - required for Simulator to publish telemetry and Agent A to receive
    try:
        h = requests.get(f"{SIMULATOR_URL}/health", timeout=5)
        if h.ok:
            data = h.json()
            if not data.get("mqtt_connected", True):
                print("\n" + "!" * 70)
                print("MQTT broker NOT connected! Simulator cannot publish telemetry.")
                print("Start MQTT first:")
                print("  docker compose up -d mosquitto   # or: docker-compose up -d mosquitto")
                print("  brew services start mosquitto    # macOS (if installed via brew)")
                print("!" * 70 + "\n")
                sys.exit(1)
    except Exception:
        pass

    # Check Agent A - REQUIRED to receive telemetry and generate alerts
    m0 = get_agent_a_metrics()
    if not m0:
        print("\n" + "!" * 70)
        print("Agent A (Monitor) not reachable at", AGENT_A_URL)
        print("Agent A must be running to receive telemetry and generate alerts.")
        print("Start with: ./scripts/start_all_agents.sh")
        print("Or: python agent-monitor/main.py")
        print("!" * 70 + "\n")
        sys.exit(1)
    if not m0.get("mqtt_connected", True):
        print("\n" + "!" * 70)
        print("Agent A: MQTT NOT connected! Agent A cannot receive telemetry.")
        print("Start MQTT: docker compose up -d mosquitto")
        print("!" * 70 + "\n")
        sys.exit(1)
    print(f"Agent A: messages={m0.get('messages_processed', 0)}, alerts={m0.get('alerts_generated', 0)}, mqtt=OK\n")

    total_start = time.time()

    for cycle in range(1, cycles + 1):
        print(f"\n--- Cycle {cycle}/{cycles} ---")

        # Initial health in cycle
        print(f"\n  [Health] healthy_baseline {HEALTH_DURATION}s...")
        api_load(load_scenario("healthy_baseline"))
        api_start(ASSET_ID)
        time.sleep(HEALTH_DURATION)
        api_stop(ASSET_ID)

        for i, (name, run_sec, desc) in enumerate(SCENARIOS):
            # Reset between faults
            if i > 0:
                print(f"\n  [Reset] healthy_baseline {RESET_DURATION}s...")
                api_load(load_scenario("healthy_baseline"))
                api_start(ASSET_ID)
                time.sleep(RESET_DURATION)
                api_stop(ASSET_ID)

            # Fault phase: apply EXTREME eval overrides to guarantee alert triggers
            # (no threshold changes; simulator params only)
            overrides = {}
            if "bearing_wear" in name:
                overrides["rate_per_sec"] = 0.35 * random.uniform(0.95, 1.05)
            elif "clogging" in name and "valve" not in name:
                # Physics: valve caps flow; pump model max ~6bar/32A. Override to force triggers:
                # 1) valve 35% -> flow ~35 (< 45)
                # 2) sensor_drift on pressure_bar + motor_current_a (physics can't reach 25bar/45A)
                overrides["valve_open_pct"] = 35
                overrides["resistance_factor"] = 80
                overrides["add_faults"] = [
                    {"type": "sensor_drift", "start_time_sec": 0, "params": {"signal": "pressure_bar", "drift_rate": 2.5}},
                    {"type": "sensor_drift", "start_time_sec": 0, "params": {"signal": "motor_current_a", "drift_rate": 20.0}},
                ]
            elif "valve_flow" in name:
                # valve>=65% + flow<=68 (valve_flow_mismatch). Proven: resist 800, valve stuck 80%
                overrides["resistance_factor"] = 800
                overrides["valve_stuck_pct"] = 80
            elif "sensor_drift" in name:
                # Use proven override: temp_c=120 via sensor_override (sensor_drift_eval_temp_override.json)
                scenario = json.loads((_scenarios_dir / "sensor_drift_eval_temp_override.json").read_text(encoding="utf-8"))
                print(f"\n  [{name}] {run_sec}s -> {desc}")
                api_load(scenario)
                api_start(ASSET_ID)
                time.sleep(run_sec)
                api_stop(ASSET_ID)
                time.sleep(6)
                m1 = get_agent_a_metrics()
                msgs = m1.get("messages_processed", 0)
                alrts = m1.get("alerts_generated", 0)
                print(f"  [Agent A] messages_processed={msgs}, alerts_generated={alrts}")
                if msgs == 0:
                    print("  [!] Agent A received NO telemetry. Check MQTT + Simulator publishing.")
                elif alrts == 0:
                    print("  [!] Agent A received telemetry but generated NO alerts (threshold/duration?).")
                print_alerts_summary(ASSET_ID)
                continue
            elif "rpm" in name:
                # Use proven override: rpm=500 via sensor_override (rpm_eval_override.json)
                scenario = json.loads((_scenarios_dir / "rpm_eval_override.json").read_text(encoding="utf-8"))
                print(f"\n  [{name}] {run_sec}s -> {desc}")
                api_load(scenario)
                api_start(ASSET_ID)
                time.sleep(run_sec)
                api_stop(ASSET_ID)
                time.sleep(6)
                m1 = get_agent_a_metrics()
                msgs = m1.get("messages_processed", 0)
                alrts = m1.get("alerts_generated", 0)
                print(f"  [Agent A] messages_processed={msgs}, alerts_generated={alrts}")
                if msgs == 0:
                    print("  [!] Agent A received NO telemetry. Check MQTT + Simulator publishing.")
                elif alrts == 0:
                    print("  [!] Agent A received telemetry but generated NO alerts (threshold/duration?).")
                print_alerts_summary(ASSET_ID)
                continue
            elif "noise_burst" in name:
                overrides["noise_amplitude"] = 60  # vibration spike >> 18
            scenario = load_scenario(name, **overrides)
            print(f"\n  [{name}] {run_sec}s -> {desc}")
            api_load(scenario)
            api_start(ASSET_ID)
            time.sleep(run_sec)
            api_stop(ASSET_ID)
            time.sleep(6)  # Wait for Agent A to process (sparse telemetry ~1/6s)
            m1 = get_agent_a_metrics()
            msgs = m1.get("messages_processed", 0)
            alrts = m1.get("alerts_generated", 0)
            print(f"  [Agent A] messages_processed={msgs}, alerts_generated={alrts}")
            if msgs == 0:
                print("  [!] Agent A received NO telemetry. Check MQTT + Simulator publishing.")
            elif alrts == 0:
                print("  [!] Agent A received telemetry but generated NO alerts (threshold/duration?).")
            print_alerts_summary(ASSET_ID)

        # Health at end of cycle
        print(f"\n  [Reset] healthy_baseline {RESET_DURATION}s...")
        api_load(load_scenario("healthy_baseline"))
        api_start(ASSET_ID)
        time.sleep(RESET_DURATION)
        api_stop(ASSET_ID)

    elapsed = time.time() - total_start
    print("\n" + "=" * 70)
    print("Final alert count from DB:")
    print_alerts_summary(ASSET_ID)
    print(f"\nDone in {elapsed:.1f}s. Check Agent D dashboard and run: python evaluation/run_evaluation.py")
    print("=" * 70)


if __name__ == "__main__":
    main()
