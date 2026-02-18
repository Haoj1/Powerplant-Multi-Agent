# Agent C (Review Queue)

Subscribes to diagnosis reports from Agent B and creates `review_requests` for Agent D.

## Role

- **Input**: MQTT topic `diagnosis/#` (DiagnosisReport with diagnosis_id)
- **Output**: SQLite `review_requests` table (status=pending)
- **No LLM** - rule-based relay only

## Run

From project root:

```bash
python agent-ticket/main.py
```

Or:

```bash
uvicorn agent-ticket.main:app --host 0.0.0.0 --port 8004
```

## Prerequisites

- MQTT broker running
- Agent B running and publishing diagnosis (with diagnosis_id in payload)
- DB initialized: `python scripts/init_db.py` (includes review_requests table)

## Config

- `TICKET_COOLDOWN_SEC=30` - max one review_request per asset per N seconds
