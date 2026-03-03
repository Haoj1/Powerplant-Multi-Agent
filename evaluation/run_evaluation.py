#!/usr/bin/env python3
"""
Evaluation script: compute alert detection quality, diagnosis accuracy, and
reasoning efficiency from recorded scenario runs.

Reads:
  - evaluation/scenario_runs.jsonl  (ground truth per run: scenario_name, expected_root_cause, fault_types, start_ts)
  - data/monitoring*.db             (alerts, diagnosis with tokens + steps)

No sensor re-analysis needed. Alerts and diagnoses are already in the DB.
"""

import json
import os
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

DEBUG = os.environ.get("EVAL_DEBUG", "").lower() in ("1", "true", "yes")

# Actual run durations from scripts/run_alert_eval.py (scenario_runs.jsonl uses scenario duration_sec which is wrong)
# HEALTH_DURATION=20, RESET_DURATION=20; fault scenarios: 120 or 90
REAL_DURATION_BY_SCENARIO: dict[str, int] = {
    "healthy_baseline": 20,
    "bearing_wear_eval": 120,
    "clogging_eval": 120,
    "valve_flow_mismatch_eval": 120,
    "sensor_drift_eval": 120,
    "sensor_drift_eval_temp_override": 120,
    "rpm_eval": 90,
    "rpm_eval_override": 90,
    "noise_burst_eval": 90,
}
# Extend fault scenario window by this many seconds before/after (edge alerts)
WINDOW_BUFFER_SEC = 5

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
    # sensor_drift and sensor_override are equivalent (Agent B uses sensor_drift, eval scenarios use sensor_override)
    if {p, e} <= {"sensor_drift", "sensor_override"}:
        return True
    return False


def root_causes_for_signal(signal: str) -> set[str]:
    """Map alert signal to root causes it typically indicates. Used for relaxed accuracy: diagnosis correct if it matches any alert's signal."""
    s = (signal or "").lower()
    if not s:
        return set()
    m: dict[str, set[str]] = {
        "vibration_rms": {"bearing_wear", "noise_burst"},
        "bearing_temp_c": {"bearing_wear"},
        "flow_m3h": {"clogging"},
        "pressure_bar": {"clogging"},
        "motor_current_a": {"clogging"},
        "valve_flow_mismatch": {"valve_stuck"},
        "temp_c": {"sensor_drift", "sensor_override"},
        "rpm": {"sensor_drift", "sensor_override"},
    }
    return m.get(s, set())


def expected_signals_for_run(run: dict) -> set[str]:
    """
    Map scenario_name to the set of signals we expect alerts on.
    Uses substring matching so it works for both base and *_override scenarios.
    """
    name = str(run.get("scenario_name", "")).lower()
    signals: set[str] = set()
    if "bearing_wear" in name:
        signals.update({"vibration_rms", "bearing_temp_c"})
    if "clogging" in name and "valve_flow" not in name:
        signals.update({"flow_m3h", "pressure_bar", "motor_current_a"})
    if "valve_flow" in name:
        signals.add("valve_flow_mismatch")
    if "sensor_drift" in name:
        signals.add("temp_c")
    if "rpm" in name:
        signals.add("rpm")
    if "noise_burst" in name:
        signals.add("vibration_rms")
    return signals


def is_healthy_run(run: dict) -> bool:
    """Identify healthy_baseline runs for false-positive analysis."""
    name = str(run.get("scenario_name", "")).lower()
    expected = normalize_root_cause(run.get("expected_root_cause", ""))
    return "healthy" in name or expected in ("", "none", "healthy")


def _finalize_detection_stats(det_stats: dict) -> dict:
    """Convert internal detection stats to a JSON-friendly summary."""
    out = {}
    for signal, s in det_stats.items():
        runs = s["expected_runs"]
        hits = s["hits"]
        rate = hits / runs if runs else 0.0
        latencies = s["latencies"]
        avg_lat = sum(latencies) / len(latencies) if latencies else None
        out[signal] = {
            "expected_runs": runs,
            "hits": hits,
            "detection_rate": round(rate, 4),
            "avg_latency_sec": round(avg_lat, 2) if avg_lat is not None else None,
        }
    return out


def _finalize_diag_stats(diag_stats: dict) -> dict:
    """Convert internal diagnosis stats (per root_cause) to a JSON-friendly summary."""
    out = {}
    for rc, s in diag_stats.items():
        count = s["count"]
        correct = s["correct"]
        acc = correct / count if count else 0.0

        def _avg(sum_val, n):
            return round(sum_val / n, 2) if n else None

        out[rc] = {
            "count": count,
            "correct": correct,
            "accuracy": round(acc, 4) if count else None,
            "avg_confidence": _avg(s["conf_sum"], s["conf_n"]),
            "avg_confidence_correct": _avg(s["conf_correct_sum"], s["conf_correct_n"]),
            "avg_confidence_incorrect": _avg(s["conf_incorrect_sum"], s["conf_incorrect_n"]),
            "avg_steps": _avg(s["steps_sum"], s["steps_n"]),
            "avg_steps_correct": _avg(s["steps_correct_sum"], s["steps_correct_n"]),
            "avg_steps_incorrect": _avg(s["steps_incorrect_sum"], s["steps_incorrect_n"]),
            "min_steps": int(min(s["steps_vals"])) if s["steps_vals"] else None,
            "max_steps": int(max(s["steps_vals"])) if s["steps_vals"] else None,
            "avg_total_tokens": _avg(s["total_tokens_sum"], s["total_tokens_n"]),
            "avg_tokens_correct": _avg(s["total_tokens_correct_sum"], s["total_tokens_correct_n"]),
            "avg_tokens_incorrect": _avg(s["total_tokens_incorrect_sum"], s["total_tokens_incorrect_n"]),
            "min_tokens": int(min(s["tokens_vals"])) if s["tokens_vals"] else None,
            "max_tokens": int(max(s["tokens_vals"])) if s["tokens_vals"] else None,
            "avg_prompt_tokens": _avg(s["prompt_tokens_sum"], s["prompt_tokens_n"]),
            "avg_completion_tokens": _avg(s["completion_tokens_sum"], s["completion_tokens_n"]),
        }
        # Resource utilization: tokens per step (rough efficiency proxy)
        steps = s["steps_sum"]
        steps_n = s["steps_n"]
        toks = s["total_tokens_sum"]
        toks_n = s["total_tokens_n"]
        if steps_n and steps > 0 and toks_n:
            out[rc]["avg_tokens_per_step"] = round(toks / steps, 2)
        else:
            out[rc]["avg_tokens_per_step"] = None
    return out


def _finalize_scenario_stats(scen_stats: dict) -> dict:
    """Summarize per-scenario detection & diagnosis metrics."""
    out = {}
    for name, s in scen_stats.items():
        runs = s["runs"]
        runs_with_alerts = s["runs_with_alerts"]
        det_rate = runs_with_alerts / runs if runs else 0.0
        lat = s["latencies"]
        avg_lat = sum(lat) / len(lat) if lat else None
        diag_count = s["diagnosis_count"]
        diag_correct = s["diagnosis_correct"]
        diag_acc = diag_correct / diag_count if diag_count else None
        steps_n = s["steps_n"]
        tokens_n = s["total_tokens_n"]
        steps_vals = s.get("steps_vals", [])
        tokens_vals = s.get("tokens_vals", [])
        out[name] = {
            "expected_root_cause": s["expected_root_cause"],
            "runs": runs,
            "runs_with_alerts": runs_with_alerts,
            "detection_rate": round(det_rate, 4) if runs else None,
            "avg_latency_sec": round(avg_lat, 2) if avg_lat is not None else None,
            "diagnosis_count": diag_count,
            "diagnosis_correct": diag_correct,
            "diagnosis_accuracy": round(diag_acc, 4) if diag_acc is not None else None,
            "avg_steps": round(s["steps_sum"] / steps_n, 2) if steps_n else None,
            "min_steps": int(min(steps_vals)) if steps_vals else None,
            "max_steps": int(max(steps_vals)) if steps_vals else None,
            "avg_total_tokens": round(s["total_tokens_sum"] / tokens_n, 2) if tokens_n else None,
            "min_tokens": int(min(tokens_vals)) if tokens_vals else None,
            "max_tokens": int(max(tokens_vals)) if tokens_vals else None,
        }
    return out


def _finalize_latency_by_root_cause(lat_dict: dict) -> dict:
    """Summarize detection latency distribution per root cause."""
    out = {}
    for rc, vals in lat_dict.items():
        if not vals:
            continue
        avg_lat = sum(vals) / len(vals)
        out[rc] = {
            "count": len(vals),
            "avg_latency_sec": round(avg_lat, 2),
            "min_latency_sec": round(min(vals), 2),
            "max_latency_sec": round(max(vals), 2),
        }
    return out


def _finalize_confusion(confusion: dict) -> dict:
    """Convert nested defaultdict expected->predicted->count into plain dict."""
    return {exp: dict(preds) for exp, preds in confusion.items()}


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

    # Time window: use actual run duration from run_alert_eval.py (not scenario duration_sec)

    # Overall metrics
    detection_run_count = 0  # runs with at least one alert
    diagnosis_count = 0      # diagnoses linked to alerts
    diagnosis_correct = 0
    latencies_overall: list[float] = []

    # Per-signal detection stats
    detection_by_signal = defaultdict(lambda: {"expected_runs": 0, "hits": 0, "latencies": []})

    # Per-root-cause diagnosis & efficiency stats (plus "_all" aggregate)
    diag_stats = defaultdict(
        lambda: {
            "count": 0,
            "correct": 0,
            "conf_sum": 0.0,
            "conf_n": 0,
            "conf_correct_sum": 0.0,
            "conf_correct_n": 0,
            "conf_incorrect_sum": 0.0,
            "conf_incorrect_n": 0,
            "steps_sum": 0.0,
            "steps_n": 0,
            "steps_correct_sum": 0.0,
            "steps_correct_n": 0,
            "steps_incorrect_sum": 0.0,
            "steps_incorrect_n": 0,
            "total_tokens_sum": 0.0,
            "total_tokens_n": 0,
            "total_tokens_correct_sum": 0.0,
            "total_tokens_correct_n": 0,
            "total_tokens_incorrect_sum": 0.0,
            "total_tokens_incorrect_n": 0,
            "steps_vals": [],
            "tokens_vals": [],
            "prompt_tokens_sum": 0.0,
            "prompt_tokens_n": 0,
            "completion_tokens_sum": 0.0,
            "completion_tokens_n": 0,
        }
    )

    # Per-scenario matrix
    scenario_stats = defaultdict(
        lambda: {
            "runs": 0,
            "runs_with_alerts": 0,
            "expected_root_cause": None,
            "latencies": [],
            "diagnosis_count": 0,
            "diagnosis_correct": 0,
            "steps_sum": 0.0,
            "steps_n": 0,
            "total_tokens_sum": 0.0,
            "total_tokens_n": 0,
            "steps_vals": [],
            "tokens_vals": [],
        }
    )

    # Confusion matrix: expected_root_cause -> predicted_root_cause -> count
    confusion = defaultdict(lambda: defaultdict(int))

    # Latency distribution by root cause
    latency_by_root_cause = defaultdict(list)

    # Healthy false positives broken down by signal
    healthy_alerts_by_signal = defaultdict(int)

    healthy_runs = 0
    healthy_runs_with_alerts = 0

    total = len(runs)
    if DEBUG:
        print("  [eval] DEBUG: starting main loop", flush=True)
    for i, run in enumerate(runs):
        if (i + 1) % 20 == 0 or i == 0:
            print(f"  [eval] run {i + 1}/{total} ...", flush=True)
        if DEBUG and i == 0:
            st = run.get("start_ts") or ""
            print(f"  [eval] run1: scenario={run.get('scenario_name')} start_ts={st[:40]}...", flush=True)
        start_ts = run.get("start_ts")
        asset_id = run.get("asset_id", "pump01")
        expected_rc = run.get("expected_root_cause", "unknown")
        rc_key = normalize_root_cause(expected_rc) or "_unknown"
        scenario_name = run.get("scenario_name", "unknown")
        scen_key = str(scenario_name)
        scen_bucket = scenario_stats[scen_key]
        scen_bucket["runs"] += 1
        if scen_bucket["expected_root_cause"] is None:
            scen_bucket["expected_root_cause"] = rc_key
        # Use actual run duration from run_alert_eval.py; fallback to record's duration_sec (cap 300 for unknown)
        w = REAL_DURATION_BY_SCENARIO.get(scen_key)
        if w is None:
            w = min(int(run.get("duration_sec", 120)), 300)

        if not start_ts:
            continue

        # Parse start time
        try:
            dt_start = datetime.fromisoformat(start_ts.replace("Z", "+00:00"))
        except Exception:
            continue
        dt_end = dt_start + timedelta(seconds=w)
        dt_start_orig = dt_start  # For latency: always use original fault start
        # Fault scenarios: extend query window by WINDOW_BUFFER_SEC before/after for edge alerts
        is_healthy = is_healthy_run(run)
        if not is_healthy and WINDOW_BUFFER_SEC > 0:
            dt_start = dt_start - timedelta(seconds=WINDOW_BUFFER_SEC)
            dt_end = dt_end + timedelta(seconds=WINDOW_BUFFER_SEC)
        since = dt_start.strftime("%Y-%m-%dT%H:%M:%S")
        until = dt_end.strftime("%Y-%m-%dT%H:%M:%S")

        if DEBUG and i == 0:
            print(f"  [eval] run1: query_alerts since={since} until={until} ...", flush=True)
            t0 = time.perf_counter()
        # Query alerts in window
        alerts = shared_db.query_alerts(
            asset_id=asset_id,
            since_ts=since,
            until_ts=until,
            limit=200,
        )
        if DEBUG and i == 0:
            print(f"  [eval] run1: query_alerts done in {time.perf_counter()-t0:.2f}s, alerts={len(alerts)}", flush=True)

        # Sort alerts oldest->newest by ts (defensive)
        try:
            alerts = sorted(
                alerts,
                key=lambda a: datetime.fromisoformat(str(a.get("ts", "")).replace("Z", "+00:00")),
            )
        except Exception:
            pass

        if is_healthy:
            healthy_runs += 1
            if alerts:
                healthy_runs_with_alerts += 1
                for a in alerts:
                    sig = a.get("signal")
                    if sig:
                        healthy_alerts_by_signal[sig] += 1

        expected_signals = expected_signals_for_run(run)

        # Scenario-level detection: any alert at all (latency vs original fault start)
        if alerts:
            detection_run_count += 1
            scen_bucket["runs_with_alerts"] += 1
            first_alert_ts = alerts[0].get("ts")
            try:
                first_dt = datetime.fromisoformat(str(first_alert_ts).replace("Z", "+00:00"))
                lat = (first_dt - dt_start_orig).total_seconds()
                latencies_overall.append(lat)
                latency_by_root_cause[rc_key].append(lat)
                scen_bucket["latencies"].append(lat)
            except Exception:
                pass

        # Per-signal detection: did each expected signal fire?
        # Companion relaxation: if any expected signal fired, count hit for all (伴生alert - one fault can trigger multiple related signals)
        if expected_signals:
            # Pre-index alerts by signal for this run
            alerts_by_signal = defaultdict(list)
            for a in alerts:
                sig = a.get("signal")
                if sig:
                    alerts_by_signal[sig].append(a)

            any_companion_fired = any(alerts_by_signal.get(s) for s in expected_signals)
            first_companion_ts = None
            if any_companion_fired:
                for s in expected_signals:
                    if alerts_by_signal.get(s):
                        first_companion_ts = alerts_by_signal[s][0].get("ts")
                        break

            for sig in expected_signals:
                stats = detection_by_signal[sig]
                stats["expected_runs"] += 1
                sig_alerts = alerts_by_signal.get(sig, [])
                if sig_alerts:
                    stats["hits"] += 1
                    first_ts = sig_alerts[0].get("ts")
                    try:
                        first_dt = datetime.fromisoformat(str(first_ts).replace("Z", "+00:00"))
                        stats["latencies"].append((first_dt - dt_start_orig).total_seconds())
                    except Exception:
                        pass
                elif any_companion_fired and first_companion_ts:
                    # Companion alert fired: count as hit for this signal too
                    stats["hits"] += 1
                    try:
                        first_dt = datetime.fromisoformat(str(first_companion_ts).replace("Z", "+00:00"))
                        stats["latencies"].append((first_dt - dt_start_orig).total_seconds())
                    except Exception:
                        pass

        # Batch-fetch diagnoses for all alerts in this run (single DB round-trip)
        if DEBUG and i == 0 and alerts:
            print(f"  [eval] run1: get_diagnoses_for_alerts_batch({len(alerts)} alerts) ...", flush=True)
            t0 = time.perf_counter()
        diag_by_alert = shared_db.get_diagnoses_for_alerts_batch(alerts)
        if DEBUG and i == 0:
            print(f"  [eval] run1: batch done in {time.perf_counter()-t0:.2f}s", flush=True)
        # Deduplicate: multiple alerts may share one diagnosis; count each diagnosis once per run
        seen_diag_ids: set[int] = set()
        for alert in alerts:
            aid = alert.get("id")
            if not aid:
                continue
            diag = diag_by_alert.get(aid)
            if not diag:
                continue
            diag_id = diag.get("id")
            if diag_id is not None and diag_id in seen_diag_ids:
                continue
            if diag_id is not None:
                seen_diag_ids.add(diag_id)

            diagnosis_count += 1
            bucket_all = diag_stats["_all"]
            bucket_rc = diag_stats[rc_key]

            def _accumulate(bucket: dict, correct: bool, diag_row: dict):
                bucket["count"] += 1
                if correct:
                    bucket["correct"] += 1
                conf = diag_row.get("confidence")
                if conf is not None:
                    try:
                        c = float(conf)
                    except Exception:
                        c = None
                    if c is not None:
                        bucket["conf_sum"] += c
                        bucket["conf_n"] += 1
                        if correct:
                            bucket["conf_correct_sum"] += c
                            bucket["conf_correct_n"] += 1
                        else:
                            bucket["conf_incorrect_sum"] += c
                            bucket["conf_incorrect_n"] += 1
                steps = diag_row.get("actual_steps")
                if steps is not None:
                    try:
                        s_val = float(steps)
                    except Exception:
                        s_val = None
                    if s_val is not None:
                        bucket["steps_sum"] += s_val
                        bucket["steps_n"] += 1
                        if correct:
                            bucket["steps_correct_sum"] += s_val
                            bucket["steps_correct_n"] += 1
                        else:
                            bucket["steps_incorrect_sum"] += s_val
                            bucket["steps_incorrect_n"] += 1
                        bucket["steps_vals"].append(s_val)
                toks = diag_row.get("total_tokens")
                if toks is not None:
                    try:
                        t_val = float(toks)
                    except Exception:
                        t_val = None
                    if t_val is not None:
                        if correct:
                            bucket["total_tokens_correct_sum"] += t_val
                            bucket["total_tokens_correct_n"] += 1
                        else:
                            bucket["total_tokens_incorrect_sum"] += t_val
                            bucket["total_tokens_incorrect_n"] += 1
                        bucket["tokens_vals"].append(t_val)
                for key_sum, key_n, col in [
                    ("total_tokens_sum", "total_tokens_n", "total_tokens"),
                    ("prompt_tokens_sum", "prompt_tokens_n", "prompt_tokens"),
                    ("completion_tokens_sum", "completion_tokens_n", "completion_tokens"),
                ]:
                    val = diag_row.get(col)
                    if val is None:
                        continue
                    try:
                        v = float(val)
                    except Exception:
                        v = None
                    if v is not None:
                        bucket[key_sum] += v
                        bucket[key_n] += 1

            pred = diag.get("root_cause", "")
            pred_key = normalize_root_cause(pred) or "_none"
            # Correct if: (1) matches expected, or (2) matches any root_cause implied by alert signals in this event
            signals_for_diag = {
                a.get("signal") for a in alerts
                if diag_by_alert.get(a.get("id")) and diag_by_alert[a["id"]].get("id") == diag_id
            }
            allowed_rcs = set()
            for sig in signals_for_diag:
                if sig:
                    allowed_rcs.update(root_causes_for_signal(sig))
            is_correct = match_root_cause(pred, expected_rc) or any(
                match_root_cause(pred, rc) for rc in allowed_rcs
            )
            if is_correct:
                diagnosis_correct += 1
            # Scenario-level diagnosis stats (incl. steps/tokens)
            scen_bucket["diagnosis_count"] += 1
            if is_correct:
                scen_bucket["diagnosis_correct"] += 1
            s_val = diag.get("actual_steps")
            if s_val is not None:
                try:
                    sv = float(s_val)
                    scen_bucket["steps_sum"] += sv
                    scen_bucket["steps_n"] += 1
                    scen_bucket["steps_vals"].append(sv)
                except Exception:
                    pass
            t_val = diag.get("total_tokens")
            if t_val is not None:
                try:
                    tv = float(t_val)
                    scen_bucket["total_tokens_sum"] += tv
                    scen_bucket["total_tokens_n"] += 1
                    scen_bucket["tokens_vals"].append(tv)
                except Exception:
                    pass

            # Error distribution (confusion matrix)
            confusion[rc_key][pred_key] += 1

            _accumulate(bucket_all, is_correct, diag)
            _accumulate(bucket_rc, is_correct, diag)

    print("  [eval] computing summary...", flush=True)
    detection_rate = detection_run_count / len(runs) if runs else 0.0
    diagnosis_accuracy = diagnosis_correct / diagnosis_count if diagnosis_count else 0.0
    avg_latency = sum(latencies_overall) / len(latencies_overall) if latencies_overall else None

    detection_by_signal_summary = _finalize_detection_stats(detection_by_signal)
    diagnosis_by_root_cause_summary = _finalize_diag_stats(diag_stats)
    scenario_matrix = _finalize_scenario_stats(scenario_stats)
    latency_by_root_cause_summary = _finalize_latency_by_root_cause(latency_by_root_cause)
    confusion_summary = _finalize_confusion(confusion)

    healthy_fp_rate = (
        healthy_runs_with_alerts / healthy_runs if healthy_runs else 0.0
    )

    return {
        "scenario_runs": len(runs),
        # Detection (any alert)
        "detection_count": detection_run_count,
        "detection_rate": round(detection_rate, 4),
        "avg_latency_sec": round(avg_latency, 2) if avg_latency is not None else None,
        # Detection by signal (expected vs hit per scenario)
        "detection_by_signal": detection_by_signal_summary,
        # Scenario-level matrix
        "scenario_matrix": scenario_matrix,
        # Healthy-baseline false positives
        "healthy_runs": healthy_runs,
        "healthy_runs_with_alerts": healthy_runs_with_alerts,
        "healthy_false_positive_rate": round(healthy_fp_rate, 4) if healthy_runs else None,
        "healthy_alerts_by_signal": dict(healthy_alerts_by_signal),
        # Diagnosis quality
        "diagnosis_count": diagnosis_count,
        "diagnosis_correct": diagnosis_correct,
        "diagnosis_accuracy": round(diagnosis_accuracy, 4) if diagnosis_count else None,
        "diagnosis_by_root_cause": diagnosis_by_root_cause_summary,
        # Time correlation
        "latency_by_root_cause": latency_by_root_cause_summary,
        # Error distribution
        "confusion_matrix": confusion_summary,
    }


def main():
    if DEBUG:
        print("  [eval] DEBUG mode: EVAL_DEBUG=1", flush=True)
    result = run_evaluation()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
