# Alert Detection (Evaluation)

This document explains how **alerts** are defined, detected, and used in evaluation.

---

## What Is an Alert?

An **alert** is an anomaly detection event produced by **Agent A (Monitor)**. When sensor telemetry exceeds configured thresholds (or slope/duration rules), Agent A publishes an `AlertEvent` to MQTT and writes it to the database.

---

## Alert Schema

| Field | Type | Description |
|-------|------|-------------|
| `ts` | datetime | Timestamp |
| `plant_id` | str | Plant identifier |
| `asset_id` | str | Asset (e.g. `pump01`) |
| `severity` | enum | `warning` or `critical` |
| `alerts` | list | One or more `AlertDetail` |
| `alert_id` | int | DB primary key (for Agent B linkage) |

Each `AlertDetail` contains:

| Field | Description |
|-------|-------------|
| `signal` | Signal that triggered (e.g. `vibration_rms`, `flow_m3h`) |
| `score` | Anomaly score |
| `method` | Detection method (`threshold`, `slope`, `valve_flow_mismatch`) |
| `window_sec` | Window size used |
| `evidence` | Extra context (mean, std, slope, duration_above_threshold) |

---

## Detection Methods

Agent A uses three detection mechanisms (see `agent-monitor/detection/threshold_detector.py`):

### 1. Threshold (Value)

Signal exceeds a configured level for a minimum duration:

| Signal | Type | Threshold (eval) | Notes |
|--------|------|------------------|-------|
| `vibration_rms` | high | warning 2.8, critical 18.0 mm/s | ISO 20816 |
| `bearing_temp_c` | high | warning 55, critical 85 °C | |
| `pressure_bar` | high | warning 7.5, critical 25 bar | |
| `motor_current_a` | high | warning 34, critical 45 A | |
| `temp_c` | high | warning 55, critical 95 °C | |
| `flow_m3h` | low | warning 48, critical 45 m³/h | |
| `rpm` | range | min 2650, max 3150 | |

### 2. Slope (Trend)

Signal rate of change exceeds a threshold over a window:

| Signal | Slope Threshold | Window |
|--------|------------------|--------|
| `vibration_rms` | warning 0.008, critical 0.08 /s | 60s |
| `bearing_temp_c` | warning 0.38, critical 0.6 °C/s | 60s |
| `flow_m3h` | warning -0.85, critical -5.0 /s (low) | 10s |
| `pressure_bar` | warning 0.25, critical 1.0 /s | 10s |
| `motor_current_a` | warning 0.95, critical 1.5 /s | 10s |

### 3. Valve-Flow Mismatch

Combination rule: valve open ≥ 65% but flow ≤ 68 m³/h (indicates valve stuck or clogging).

---

## Duration and Fast Signals

- Most signals require **sustained breach** for `min_duration_sec` (default 5s) to reduce false positives.
- **Fast signals** (`temp_c`, `rpm`, `valve_flow_mismatch`) use 0.5s duration for quicker eval response.

---

## Evaluation Metrics

| Metric | Definition |
|--------|------------|
| **Detection rate** | % of scenario runs that produced at least one alert |
| **Detection by signal** | Per-signal hit rate (e.g. `vibration_rms` 50%, `bearing_temp_c` 100%) |
| **Healthy false positive** | % of `healthy_baseline` runs that incorrectly produced alerts |
| **Latency** | Time from scenario start to first alert (optional) |

---

## Scenario → Expected Alerts

| Scenario | Expected Signals | Notes |
|----------|------------------|-------|
| `bearing_wear_eval` | vibration_rms, bearing_temp_c | Slope + threshold |
| `clogging_eval` | flow_m3h, pressure_bar, motor_current_a | Threshold + slope |
| `valve_flow_mismatch_eval` | valve_flow_mismatch | Combination rule |
| `sensor_drift_eval_temp_override` | temp_c | Sensor override to 120°C |
| `rpm_eval_override` | rpm | Sensor override to 500 rpm |
| `noise_burst_eval` | vibration_rms | Spike; currently 0% detection (threshold/slope not tuned) |
| `healthy_baseline` | none | False positive if any alert |

---

## Related Files

- `agent-monitor/detection/threshold_detector.py` — Detection logic
- `agent-monitor/detection/telemetry_buffer.py` — Sliding window, stats, duration
- `shared_lib/models.py` — `AlertEvent`, `AlertDetail` schemas
- `docs/ALERTS_AND_RULES.md` — Full alert and rule spec
