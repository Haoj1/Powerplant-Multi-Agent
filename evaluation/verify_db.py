#!/usr/bin/env python3
"""Verify alerts/diagnosis in DB for run_evaluation time windows."""

import json
import sys
from pathlib import Path

_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from dotenv import load_dotenv
load_dotenv(_project_root / ".env")

from shared_lib import db as shared_db

# Match run_evaluation: actual durations from run_alert_eval.py
REAL_DURATION_BY_SCENARIO = {
    "healthy_baseline": 20,
    "bearing_wear_eval": 120,
    "clogging_eval": 120,
    "valve_flow_mismatch_eval": 120,
    "sensor_drift_eval_temp_override": 120,
    "rpm_eval_override": 90,
    "noise_burst_eval": 90,
}

def main():
    eval_dir = _project_root / "evaluation"
    runs_path = eval_dir / "scenario_runs.jsonl"
    if not runs_path.exists():
        print("No scenario_runs.jsonl")
        return

    runs = []
    with open(runs_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                runs.append(json.loads(line))
            except json.JSONDecodeError:
                pass

    # 1. Raw counts via broad query
    all_alerts = shared_db.query_alerts(
        asset_id="pump01",
        since_ts="2026-01-01T00:00:00",
        until_ts="2027-01-01T00:00:00",
        limit=10000,
    )
    alert_count = len(all_alerts)
    min_ts = all_alerts[-1].get("ts") if all_alerts else None
    max_ts = all_alerts[0].get("ts") if all_alerts else None
    diag_count = shared_db.count_diagnosis()

    print("=== DB raw counts ===")
    print(f"  alerts: {alert_count}")
    print(f"  diagnosis: {diag_count}")
    print(f"  alerts ts range: {min_ts} .. {max_ts}")
    print()

    # 2. Sample a few fault runs and query same window as run_evaluation
    fault_runs = [r for r in runs if not (r.get("scenario_name", "").lower().startswith("healthy"))][:5]
    print("=== Sample fault runs (query same window as run_evaluation) ===")
    for r in fault_runs:
        start = r.get("start_ts")
        asset = r.get("asset_id", "pump01")
        name = r.get("scenario_name", "")
        dur = REAL_DURATION_BY_SCENARIO.get(name) or min(r.get("duration_sec", 120), 300)
        if not start:
            continue
        from datetime import datetime, timedelta
        dt_start = datetime.fromisoformat(start.replace("Z", "+00:00"))
        dt_end = dt_start + timedelta(seconds=dur)
        since = dt_start.strftime("%Y-%m-%dT%H:%M:%S")
        until = dt_end.strftime("%Y-%m-%dT%H:%M:%S")
        alerts = shared_db.query_alerts(asset_id=asset, since_ts=since, until_ts=until, limit=50)
        print(f"  {r.get('scenario_name')} | {since}..{until} | alerts: {len(alerts)}")
    print()

    # 3. Check ts format in DB vs query format
    if all_alerts:
        sample_ts = all_alerts[0].get("ts")
        print("=== Alert ts format in DB ===")
        print(f"  sample: {sample_ts}")


if __name__ == "__main__":
    main()
