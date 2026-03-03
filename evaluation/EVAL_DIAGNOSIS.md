# Diagnosis (Evaluation)

This document explains how **diagnoses** are produced, stored, and evaluated.

---

## What Is a Diagnosis?

A **diagnosis** is a root cause analysis report produced by **Agent B (Diagnosis)**. When Agent B receives an alert from Agent A, it runs a ReAct agent that calls tools (query_rules, query_telemetry, query_alerts) and outputs a `DiagnosisReport` with root cause, confidence, evidence, and recommended actions.

---

## Diagnosis Schema

| Field | Type | Description |
|-------|------|-------------|
| `ts` | datetime | Timestamp |
| `plant_id` | str | Plant identifier |
| `asset_id` | str | Asset (e.g. `pump01`) |
| `root_cause` | enum | `bearing_wear`, `clogging`, `valve_stuck`, `sensor_drift`, `unknown` |
| `confidence` | float | 0.0–1.0 |
| `impact` | enum | `low`, `medium`, `high` |
| `recommended_actions` | list | Suggested maintenance steps |
| `evidence` | list | Rule matches and details |
| `alert_id` | int | Links to source alert |

---

## How Agent B Produces a Diagnosis

1. **Input:** Receives `AlertEvent` via MQTT (alerts/#).
2. **ReAct loop:** LLM reasons and calls tools:
   - `query_rules(symptom, signal)` — Retrieve rule documents from `agent-diagnosis/rules/*.md`
   - `query_telemetry(asset_id, since_ts)` — Historical telemetry from SQLite
   - `query_alerts(asset_id, limit)` — Recent alerts
3. **Output:** Parses LLM final answer into `DiagnosisReport` (root_cause, confidence, evidence).
4. **Publish:** MQTT `diagnosis/{asset_id}` + `insert_diagnosis()` to SQLite.

---

## Root Cause Types

| Root Cause | Typical Alert Signals | Rule File |
|------------|-----------------------|-----------|
| `bearing_wear` | vibration_rms, bearing_temp_c | bearing_wear.md |
| `clogging` | flow_m3h, pressure_bar, motor_current_a | clogging.md |
| `valve_stuck` | valve_flow_mismatch | valve_stuck.md |
| `sensor_drift` / `sensor_override` | temp_c, rpm, single-signal anomaly | sensor_drift.md |
| `none` | (healthy baseline) | unknown.md |

---

## Evaluation Metrics

| Metric | Definition |
|--------|------------|
| **Diagnosis accuracy** | % of diagnoses where `root_cause` matches `expected_root_cause` |
| **Per-scenario accuracy** | Accuracy for each scenario (e.g. bearing_wear_eval 100%) |
| **Per root cause accuracy** | Accuracy when grouping by predicted root cause |
| **Avg steps** | ReAct steps per diagnosis |
| **Avg tokens** | Total LLM tokens per diagnosis |

---

## Matching Rules

- **Exact:** `bearing_wear` == `bearing_wear`
- **Partial:** `bearing_wear` in `bearing_wear_chronic`
- **Alias:** `sensor_drift` ↔ `sensor_override` (eval scenarios use sensor_override)

---

## Typical Results (from eval_report)

| Root Cause | Accuracy | Notes |
|------------|----------|-------|
| bearing_wear | 100% | Strong rule + clear signals |
| valve_stuck | 100% | valve_flow_mismatch is distinctive |
| clogging | 63.6% | Can confuse with sensor_drift |
| sensor_override | 58.3% | temp_c/rpm overrides; LLM sometimes wrong |
| none | 85.7% | Healthy baseline; some misdiagnosis |

---

## Related Files

- `agent-diagnosis/agent/agent.py` — ReAct agent setup
- `agent-diagnosis/agent/tools.py` — query_rules, query_telemetry, query_alerts
- `agent-diagnosis/rules/*.md` — Rule documents
- `shared_lib/models.py` — `DiagnosisReport`, `DiagnosisEvidence`
- `docs/AGENT_B_ARCHITECTURE.md` — Full Agent B design
