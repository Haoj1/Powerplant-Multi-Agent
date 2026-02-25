# Alerts and Rules Implementation Guide

This document lists alerts (Agent A detection) and diagnosis rules (Agent B) that can be implemented, with implementation priority.

---

## 1. Agent A – Alerts (Detection Logic)

### 1.1 Already Implemented

| Signal | Type | Threshold | Notes |
|--------|------|-----------|-------|
| vibration_rms | threshold | warning 7.1, critical 18.0 mm/s | ISO 20816 |
| bearing_temp_c | threshold | warning 70, critical 85 °C | |
| pressure_bar | threshold_high | warning 18, critical 25 bar | |
| motor_current_a | threshold_high | warning 38, critical 45 A | |
| temp_c | threshold_high | warning 80, critical 95 °C | |
| vibration_rms | slope | warning 0.03, critical 0.08 /s | Gradual increase |
| bearing_temp_c | slope | warning 0.1, critical 0.3 °C/s | Gradual increase |
| All above | duration | min 5 s sustained | Reduces false positives |

### 1.2 Recommended Additions (Priority Order)

#### P1 – High Value (Implement First)

| Alert | Signal(s) | Logic | Config |
|-------|-----------|-------|--------|
| **flow_low** | flow_m3h | value < warning_low (e.g. 80 m³/h) for ≥ 15 s | Add flow_m3h to DEFAULT_THRESHOLDS with low-side |
| **valve_flow_mismatch** | valve_open_pct, flow_m3h | valve open high but flow low (e.g. valve > 80%, flow < 50% nominal) for ≥ 20 s | New combination rule |
| **rpm_anomaly** | rpm | value outside [min, max] (e.g. 1400–1600 rpm) for ≥ 10 s | Add rpm to thresholds |

#### P2 – Medium Value

| Alert | Signal(s) | Logic | Config |
|-------|-----------|-------|--------|
| **flow_sudden_drop** | flow_m3h | slope < -X over 10 s (e.g. -5 m³/h per s) | Add to slope_thresholds (negative) |
| **pressure_sudden_spike** | pressure_bar | slope > X over 10 s | Add to slope_thresholds |
| **current_surge** | motor_current_a | slope > X over 5 s | Add to slope_thresholds |

#### P3 – Lower Priority

| Alert | Signal(s) | Logic | Config |
|-------|-----------|-------|--------|
| **single_signal_anomaly** | any | Only one signal anomalous for > 120 s → possible sensor_drift | Post-process / combination |
| **valve_stuck_detect** | valve_open_pct | No change in valve for > 60 s while flow/pressure change | Combination + duration |

---

## 2. Agent B – Diagnosis Rules

### 2.1 Existing Rules

- `bearing_wear.md` – vibration↑ + bearing_temp↑
- `clogging.md` – flow↓ + pressure↓
- `valve_stuck.md` – valve vs flow mismatch
- `sensor_drift.md` – single-signal anomaly
- `unknown.md` – fallback

### 2.2 Recommended Additions (Priority Order)

#### P1 – High Value

| Rule | File | Condition | Uses New Tools |
|------|------|-----------|----------------|
| **bearing_wear_chronic** | bearing_wear_1.md (extend) | vibration slope > 0 over 60 s AND sustained > 30 s | compute_slope, get_telemetry_window |
| **clogging_sudden** | clogging.md (extend) | flow drop in 10 s, sustained > 15 s | compute_slope, get_telemetry_window |
| **valve_stuck_duration** | valve_stuck.md (extend) | valve vs flow mismatch > 20 s | get_telemetry_window |

#### P2 – Medium Value

| Rule | File | Condition | Uses New Tools |
|------|------|-----------|----------------|
| **sensor_drift_long** | sensor_drift.md (extend) | Single-signal anomaly > 120 s, others normal | get_telemetry_window, query_telemetry |
| **bearing_wear_acute** | bearing_wear.md (extend) | vibration + bearing_temp both above threshold, slope positive | compute_slope |

#### P3 – Lower Priority

| Rule | File | Condition |
|------|------|-----------|
| **flow_pressure_correlation** | clogging.md | flow and pressure move together (clogging) vs diverge (sensor) |
| **valve_command_response** | valve_stuck.md | valve_open_pct unchanged when flow/pressure change |

---

## 3. Implementation Checklist

### Agent A (Monitor)

- [x] Sliding window buffer (TelemetryBuffer)
- [x] Duration above threshold (min_duration_sec)
- [x] Slope-based alerts (vibration_rms, bearing_temp_c)
- [x] Evidence: window_sec, mean, std, slope, duration_above_threshold
- [ ] **flow_m3h** low-side threshold
- [ ] **rpm** range threshold
- [ ] **valve_flow_mismatch** combination rule
- [ ] **flow_sudden_drop** slope (negative)
- [ ] **pressure_sudden_spike** slope

### Agent B (Diagnosis)

- [x] get_telemetry_window(asset_id, window_sec)
- [x] compute_slope(asset_id, signal, window_sec)
- [ ] Update bearing_wear rule with slope/duration hints
- [ ] Update clogging rule with sudden vs gradual hints
- [ ] Update valve_stuck rule with duration hints
- [ ] Update sensor_drift rule with long-duration hint

### Shared / Config

- [ ] Add flow_m3h, rpm to DEFAULT_THRESHOLDS
- [ ] Add negative slope support for flow_m3h
- [ ] Optional: check_duration_above_threshold tool for Agent B (if LLM needs explicit duration query)

---

## 4. Rule Content Hints for Agent B

When updating rules, add guidance so the LLM knows when to use the new tools:

**bearing_wear.md** – Add:
```
## Time/Trend Hints
- Use compute_slope(asset_id, "vibration_rms", 60) to check for gradual increase
- Use compute_slope(asset_id, "bearing_temp_c", 60) for temperature trend
- Chronic bearing wear: slope > 0 over 60s, sustained > 30s
```

**clogging.md** – Add:
```
## Time/Trend Hints
- Use compute_slope(asset_id, "flow_m3h", 10) for sudden drop (negative slope)
- Use get_telemetry_window(asset_id, 30) to see flow/pressure evolution
- Sudden clogging: flow drop in 10s, sustained > 15s
```

**valve_stuck.md** – Add:
```
## Time/Trend Hints
- Use get_telemetry_window(asset_id, 60) to compare valve_open_pct vs flow_m3h over time
- Valve stuck: valve position unchanged while flow/pressure change, sustained > 20s
```

**sensor_drift.md** – Add:
```
## Time/Trend Hints
- Use get_telemetry_window to check if only one signal is anomalous for > 120s
- Cross-check: other correlated signals (flow, pressure, current) should be consistent
```
