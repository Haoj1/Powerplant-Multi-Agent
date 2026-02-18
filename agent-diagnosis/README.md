# Agent B (Diagnosis)

Subscribes to alerts from Agent A, runs a LangChain ReAct agent to diagnose root causes, and publishes diagnosis reports to MQTT and SQLite.

## Overview

- **Input**: MQTT topic `alerts/#` (AlertEvent from Agent A)
- **Output**: MQTT topic `diagnosis/{asset_id}`, SQLite `diagnosis` table, `logs/diagnosis.jsonl`
- **Logic**: ReAct agent with tools `query_rules`, `query_telemetry`, `query_alerts`

## Run

From project root:

```bash
python agent-diagnosis/main.py
```

Or with uvicorn:

```bash
uvicorn agent-diagnosis.main:app --host 0.0.0.0 --port 8003
```

## Requirements

- MQTT broker (e.g. Mosquitto)
- Agent A running and publishing alerts
- SQLite DB initialized (`python scripts/init_db.py`)
- LLM API: Set `DEEPSEEK_API_KEY` and `DEEPSEEK_BASE_URL` in `.env`, or `OPENAI_API_KEY` for OpenAI

## Rules

Rules live in `agent-diagnosis/rules/` (or path from `DIAGNOSIS_RULES_PATH`). Each `.md` file describes one fault type: symptoms, root cause, recommended actions, related signals.

## Architecture

See `docs/AGENT_B_ARCHITECTURE.md`.
