# Evaluation

This folder contains evaluation data, scripts, and reports for measuring **alert detection** and **diagnosis accuracy** of the multi-agent system.

---

## Quick Links

| Document | Description |
|----------|-------------|
| [EVAL_ALERTS.md](./EVAL_ALERTS.md) | Alert detection: schema, methods (threshold/slope/valve-flow), metrics |
| [EVAL_DIAGNOSIS.md](./EVAL_DIAGNOSIS.md) | Diagnosis: schema, ReAct flow, root causes, accuracy metrics |

---

## Reproducing Evaluation (Full Pipeline)

### Prerequisites

- Python 3.11+, MQTT broker (Mosquitto), LLM API key (OpenAI/DeepSeek)
- All services running: MQTT, Simulator, Agent A, Agent B, Agent C, Agent D

### Step 1: Start Services

```bash
# Start MQTT
docker compose up -d mosquitto

# Start all agents (Simulator, Agent A/B/C, Agent D)
./scripts/start_all_agents.sh

# Or manually:
# python simulator-service/main.py          # 8001
# python agent-monitor/main.py               # 8002
# python agent-diagnosis/main.py             # 8003
# python agent-ticket/main.py                # 8004
# python agent-review/main.py                # 8005
```

### Step 2: Run Scenario Eval (Generates Data)

This script runs health + fault scenarios in sequence, records runs to `scenario_runs.jsonl`, and populates the DB with alerts and diagnoses.

```bash
python scripts/run_alert_eval.py
```

- **Duration:** ~10–12 minutes (6 cycles × 7 scenarios)
- **Output:** `evaluation/scenario_runs.jsonl` (written by Simulator on each `/scenario/start`)
- **DB:** `data/monitoring.db` (or `SQLITE_PATH`) gets alerts + diagnoses

### Step 3: Compute Metrics

```bash
python evaluation/run_evaluation.py
```

- **Reads:** `evaluation/scenario_runs.jsonl`, `data/monitoring*.db`
- **Output:** `evaluation/eval_result.json` (metrics), stdout summary

### Step 4: Build Report (Charts)

```bash
python evaluation/build_report.py
```

- **Output:** `evaluation/report/` — PNG charts + `eval_report.html` + `eval_report.md`

### One-Liner (after services are running)

```bash
python scripts/run_alert_eval.py && python evaluation/run_evaluation.py && python evaluation/build_report.py
```

---

## Using a Fresh Eval Database

To keep production data separate and run evaluation on a clean DB:

```bash
# 1. Backup current DB, create fresh eval DB, clear evaluation JSONL
./scripts/use_eval_db.sh

# 2. Start services with eval DB
export SQLITE_PATH=data/monitoring_eval.db
./scripts/start_all_agents.sh

# 3. Run eval pipeline
python scripts/run_alert_eval.py
python evaluation/run_evaluation.py
python evaluation/build_report.py
```

---

## Data Files

### scenario_runs.jsonl

**Written when:** Simulator receives `/scenario/start/{asset_id}` (e.g. from `run_alert_eval.py` or dashboard).

Each line:

```json
{
  "start_ts": "2025-02-11T12:00:00.123456+00:00",
  "asset_id": "pump01",
  "plant_id": "plant01",
  "scenario_name": "bearing_wear_eval",
  "duration_sec": 120,
  "fault_types": ["bearing_wear"],
  "expected_root_cause": "bearing_wear"
}
```

### manual_triggers.jsonl

**Written when:** You click "Trigger Alert" (manual test) on the Scenarios page.

### eval_result.json

**Written by:** `run_evaluation.py`

Contains: `detection_rate`, `diagnosis_accuracy`, `healthy_false_positive`, `scenario_matrix`, `detection_by_signal`, `diagnosis_by_root_cause`, token/steps stats.

---

## Database Tables (No Re-analysis)

Evaluation reads from the existing database. No sensor re-analysis needed.

| Table | Use |
|-------|-----|
| `alerts` | Alerts from Agent A (signal, severity, ts, asset_id) |
| `diagnosis` | Diagnoses from Agent B (root_cause, confidence, alert_id, tokens, steps) |
| `telemetry` | Optional: fault/severity ground truth per row |

---

## Metrics Explained

| Metric | Definition |
|--------|-------------|
| **Detection rate** | % of scenario runs that produced at least one alert |
| **Diagnosis accuracy** | % of diagnoses where `root_cause` matches `expected_root_cause` |
| **Healthy false positive** | % of `healthy_baseline` runs that produced any alert |
| **Avg steps** | ReAct reasoning steps per diagnosis |
| **Avg tokens** | Total LLM tokens per diagnosis |

---

## Eval Scenarios

| Scenario | Expected Root Cause | Duration |
|----------|---------------------|----------|
| healthy_baseline | none | 20s |
| bearing_wear_eval | bearing_wear | 120s |
| clogging_eval | clogging | 120s |
| valve_flow_mismatch_eval | valve_stuck | 120s |
| sensor_drift_eval_temp_override | sensor_override | 120s |
| rpm_eval_override | sensor_override | 90s |
| noise_burst_eval | (noise) | 90s |

---

## RAG Data

The vector index (`vec0`) lives in the same SQLite file. The eval DB starts empty. As new alerts and diagnoses are created during eval runs, they are automatically indexed. No manual re-import needed.
