#!/usr/bin/env python3
"""
Evaluation script: compute detection rate and diagnosis accuracy from scenario runs.

Reads:
  - evaluation/scenario_runs.jsonl (ground truth: expected_root_cause, start_ts)
  - data/monitoring.db (alerts, diagnosis)

No sensor re-analysis needed. Alerts and diagnoses are already in the DB.
"""

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# Add project root for imports
_project_root = Path(__file__).parent.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

try:
    from shared_lib import db as shared_db
except ImportError:
    shared_db = None


def load_scenario_runs(eval_dir: Path) -> list:
    """Load scenario_runs.jsonl. Returns list of dicts."""
    path = eval_dir / "scenario_runs.jsonl"
    if not path.exists():
        return []
    runs = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                runs.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return runs


def normalize_root_cause(rc: str) -> str:
    """Normalize root cause for comparison (e.g. bearing_wear vs bearing wear)."""
    if not rc:
        return ""
    return str(rc).lower().replace(" ", "_").strip()


def match_root_cause(predicted: str, expected: str) -> bool:
    """Check if predicted matches expected (with normalization)."""
    p = normalize_root_cause(predicted)
    e = normalize_root_cause(expected)
    if p == e:
        return True
    # Allow partial match (e.g. "bearing_wear" in "bearing_wear_chronic")
    if e in p or p in e:
        return True
    return False


def run_evaluation() -> dict:
    """Run evaluation and return metrics dict."""
    eval_dir = _project_root / "evaluation"
    runs = load_scenario_runs(eval_dir)

    if not runs:
        return {
            "scenario_runs": 0,
            "message": "No scenario runs found. Load and start scenarios first.",
        }

    if not shared_db:
        return {
            "scenario_runs": len(runs),
            "message": "Database not available. Cannot query alerts/diagnosis.",
        }

    # Time window: from start_ts to start_ts + min(duration_sec, 300) seconds
    # (cap at 5 min to avoid overlapping with other runs)
    window_sec = 300
    detection_count = 0
    diagnosis_count = 0
    diagnosis_correct = 0
    latencies = []

    for run in runs:
        start_ts = run.get("start_ts")
        asset_id = run.get("asset_id", "pump01")
        expected = run.get("expected_root_cause", "unknown")
        duration = run.get("duration_sec", 3600)
        w = min(duration, window_sec)

        if not start_ts:
            continue

        # Parse start time
        try:
            dt_start = datetime.fromisoformat(start_ts.replace("Z", "+00:00"))
        except Exception:
            continue
        dt_end = dt_start + timedelta(seconds=w)
        since = dt_start.strftime("%Y-%m-%dT%H:%M:%S")
        until = dt_end.strftime("%Y-%m-%dT%H:%M:%S")

        # Query alerts in window
        alerts = shared_db.query_alerts(
            asset_id=asset_id,
            since_ts=since,
            until_ts=until,
            limit=50,
        )

        if alerts:
            detection_count += 1
            first_alert_ts = alerts[-1].get("ts")  # oldest first if ordered desc
            try:
                first_dt = datetime.fromisoformat(str(first_alert_ts).replace("Z", "+00:00"))
                lat = (first_dt - dt_start).total_seconds()
                latencies.append(lat)
            except Exception:
                pass

        # For each alert, get diagnosis and check accuracy
        for alert in alerts:
            aid = alert.get("id")
            if not aid:
                continue
            diag = shared_db.get_diagnosis_by_alert_id(aid)
            if not diag:
                continue
            diagnosis_count += 1
            pred = diag.get("root_cause", "")
            if match_root_cause(pred, expected):
                diagnosis_correct += 1

    detection_rate = detection_count / len(runs) if runs else 0
    diagnosis_accuracy = diagnosis_correct / diagnosis_count if diagnosis_count else 0
    avg_latency = sum(latencies) / len(latencies) if latencies else None

    return {
        "scenario_runs": len(runs),
        "detection_count": detection_count,
        "detection_rate": round(detection_rate, 4),
        "diagnosis_count": diagnosis_count,
        "diagnosis_correct": diagnosis_correct,
        "diagnosis_accuracy": round(diagnosis_accuracy, 4),
        "avg_latency_sec": round(avg_latency, 2) if avg_latency is not None else None,
    }


def main():
    result = run_evaluation()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
