#!/usr/bin/env python3
"""
Verify simulator output for the 4 missing-alert scenarios (no MQTT/Agent A).
Run: python scripts/verify_simulator_output.py

Prints motor_current_a, temp_c, rpm, valve, flow for first 10 steps of each scenario.
"""
import json
import sys
from pathlib import Path

_project_root = Path(__file__).parent.parent
_sim = _project_root / "simulator-service"
sys.path.insert(0, str(_project_root))
sys.path.insert(0, str(_sim))

_scenarios_dir = _sim / "scenarios"

def load_and_override(name, overrides):
    with open(_scenarios_dir / f"{name}.json") as f:
        data = json.load(f)
    for k, v in overrides.items():
        if k == "resistance_factor":
            for f in data.get("faults", []):
                if f.get("type") == "clogging" and "params" in f:
                    f["params"]["resistance_factor"] = v
        elif k == "valve_stuck_pct":
            for f in data.get("faults", []):
                if f.get("type") == "valve_stuck" and "params" in f:
                    f["params"]["stuck_value"] = v
        elif k == "valve_open_pct" and "initial_conditions" in data:
            data["initial_conditions"]["valve_open_pct"] = v
        elif k == "initial_rpm" and "initial_conditions" in data:
            data["initial_conditions"]["rpm"] = v
        elif k == "drift_rate":
            for f in data.get("faults", []):
                if f.get("type") == "sensor_drift" and "params" in f:
                    f["params"]["drift_rate"] = v
        elif k == "drift_rate_temp_c":
            for f in data.get("faults", []):
                if f.get("type") == "sensor_drift" and f.get("params", {}).get("signal") == "temp_c":
                    f["params"]["drift_rate"] = v
        elif k == "rpm_setpoint" and data.get("setpoints"):
            data["setpoints"][0]["rpm"] = v
        elif k == "add_faults":
            data.setdefault("faults", []).extend(v)
    data["sensor_noise_pct"] = 0
    return data

pump_config = {
    "pump": {"nominal_rpm": 2950, "nominal_flow_m3h": 100, "nominal_head_m": 50, "nominal_efficiency": 0.75},
    "pipe": {"pipe_length_m": 100, "pipe_diameter_m": 0.2, "fitting_loss_coefficient": 2.5, "static_head_m": 10},
    "bearing": {"base_vibration_mm_s": 2.0, "base_bearing_temp_c": 45.0},
    "motor": {"voltage_v": 400, "motor_efficiency": 0.92, "power_factor": 0.85, "no_load_current_a": 5.0},
}

from scenarios import ScenarioExecutor

scenarios = [
    ("clogging_eval", {"valve_open_pct": 35, "resistance_factor": 80, "add_faults": [
        {"type": "sensor_drift", "start_time_sec": 0, "params": {"signal": "motor_current_a", "drift_rate": 20.0}},
    ]}, "motor>=45"),
    ("valve_flow_mismatch_eval", {"resistance_factor": 300, "valve_stuck_pct": 70}, "valve>=70 & flow<=65"),
    ("sensor_drift_eval", {"drift_rate": 20, "drift_rate_temp_c": 40}, "temp_c>=55"),
    ("rpm_eval", {"rpm_setpoint": 1500, "initial_rpm": 1500}, "rpm<2650"),
]

for name, ov, cond in scenarios:
    data = load_and_override(name, ov)
    ex = ScenarioExecutor(data, pump_config)
    ex.start()
    print(f"\n=== {name} (expect {cond}) ===")
    for i in range(10):
        t = ex.step(1.0)
        if t is None:
            break
        s = t.signals
        m, temp, rpm, valve, flow = s.motor_current_a, s.temp_c, s.rpm, s.valve_open_pct, s.flow_m3h
        ok = ""
        if "motor" in cond and m >= 45: ok = " TRIGGER"
        elif "temp" in cond and temp >= 55: ok = " TRIGGER"
        elif "rpm" in cond and rpm < 2650: ok = " TRIGGER"
        elif "valve" in cond and valve >= 70 and flow <= 65: ok = " TRIGGER"
        print(f"  t={i}: motor={m:.1f} temp={temp:.1f} rpm={rpm:.0f} valve={valve:.0f}% flow={flow:.1f}{ok}")

print("\nDone. If TRIGGER appears, simulator output is correct; check Agent A / duration.")
