# Evaluation Data & Scripts

This folder stores evaluation data and scripts for measuring alert detection and diagnosis accuracy.

---

## Data Files (JSONL)

### scenario_runs.jsonl

**Written when:** You click "Start" on a loaded scenario (Scenarios page).

Each line records one scenario run:

```json
{
  "start_ts": "2025-02-11T12:00:00.123456+00:00",
  "asset_id": "pump01",
  "plant_id": "plant01",
  "scenario_name": "bearing_wear_chronic",
  "duration_sec": 3600,
  "fault_types": ["bearing_wear"],
  "expected_root_cause": "bearing_wear"
}
```

- `start_ts`: When the scenario started (UTC)
- `expected_root_cause`: Ground truth for diagnosis evaluation (first fault type)

### manual_triggers.jsonl

**Written when:** You click "Trigger Alert" (manual test) on the Scenarios page.

Each line records one manual alert:

```json
{
  "ts": "2025-02-11T12:00:00.123456+00:00",
  "plant_id": "plant01",
  "asset_id": "pump01",
  "signal": "vibration_rms",
  "severity": "critical",
  "score": 3.5,
  "method": "manual",
  "evidence": { "manual_trigger": true }
}
```

Use for: diagnosis accuracy when you know the expected root cause (you triggered a specific signal).

---

## Database (no re-analysis needed)

Evaluation reads from the existing database. **No need to re-analyze sensors.**

| Table | Use |
|-------|-----|
| `alerts` | Alerts from Agent A (signal, severity, ts, asset_id) |
| `diagnosis` | Diagnoses from Agent B (root_cause, confidence, alert_id) |
| `telemetry` | Optional: fault/severity ground truth per row |

---

## Running Evaluation

```bash
# From project root
python evaluation/run_evaluation.py
```

**What it does:**
1. Reads `scenario_runs.jsonl` for ground truth (expected_root_cause, start_ts, asset_id)
2. Queries DB for alerts in the time window after each scenario start
3. For each alert, gets the linked diagnosis (root_cause)
4. Computes:
   - **Detection rate**: % of scenario runs that produced at least one alert
   - **Diagnosis accuracy**: % of diagnoses where root_cause matches expected_root_cause
   - **Latency**: Time from scenario start to first alert (optional)

---

## Evaluation Workflow

1. **Start all services** (MQTT, Simulator, Agents A/B/C, Agent D, frontend)
2. **Load & Start scenarios** (e.g. bearing_wear_chronic, clogging_sudden)
3. **Wait** 30–60 seconds for alerts and diagnoses to appear
4. **Run evaluation**: `python evaluation/run_evaluation.py`
5. Optionally **clear** `data/monitoring.db` and `evaluation/*.jsonl` before a fresh run
