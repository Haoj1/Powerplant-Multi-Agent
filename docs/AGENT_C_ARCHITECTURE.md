# Agent C (Review Queue) Architecture

## 1. Overview

Agent C is the **review queue agent**: it subscribes to Agent B's diagnosis reports and creates **review requests** for Agent D. It does **not** create tickets or call Salesforce — that is done by Agent D **after** approval.

**No LLM or LangChain** — rule-based relay only.

---

## 2. Role in the Flow

```
Agent B (Diagnosis) ──diagnosis/#──▶ Agent C ──review_requests──▶ Agent D (Web UI + Chat + ReAct)
                                                                    │
                                                                    ├─ List pending reviews
                                                                    ├─ Query Salesforce history
                                                                    ├─ Human/LLM approve
                                                                    └─ On approve → create Salesforce Case/Work Order
```

- **Agent C**: Diagnosis in → create `review_request` record (pending)
- **Agent D**: List pending → review (UI + chat) → approve → create in Salesforce

---

## 3. Data Flow

```
┌─────────────────┐   diagnosis/#    ┌─────────────────────────────────────────────────┐
│  Agent B        │ ───────────────▶ │  Agent C                                        │
│  (Diagnosis)    │   (with         │  ┌─────────────────────────────────────────────┐ │
└─────────────────┘    diagnosis_id) │  │ 1. Receive DiagnosisReport                  │ │
                                     │  │ 2. insert_review_request(diagnosis_id,      │ │
                                     │  │    status=pending)                          │ │
                                     │  │ 3. Optional: publish review_requests/#     │ │
                                     │  └─────────────────────────────────────────────┘ │
                                     │                         │                        │
                                     │                         ▼                        │
                                     │              SQLite review_requests              │
                                     └─────────────────────────────────────────────────┘
```

---

## 4. New Table: review_requests

```
review_requests
├── id (PK)
├── diagnosis_id (FK → diagnosis.id)
├── plant_id
├── asset_id
├── ts
├── status ('pending' | 'approved' | 'rejected')
├── created_at
└── resolved_at (nullable, set when approved/rejected)
```

Agent D queries `review_requests WHERE status = 'pending'` and joins `diagnosis` for full details.

---

## 5. Component Structure

```
agent-ticket/
├── main.py              # FastAPI + MQTT subscriber
├── mqtt/
│   ├── __init__.py
│   └── subscriber.py    # Subscribes to diagnosis/#
└── README.md
```

No `formatter`, no `creator` — Agent C only creates review_request records.

---

## 6. Logic (Pseudocode)

```python
def on_diagnosis(topic, payload):
    diagnosis_id = payload.get("diagnosis_id")
    if not diagnosis_id:
        return
    # Optional cooldown per asset
    insert_review_request(
        diagnosis_id=diagnosis_id,
        plant_id=payload["plant_id"],
        asset_id=payload["asset_id"],
        ts=payload["ts"],
        status="pending"
    )
    # Optional: publish to review_requests/# for real-time Agent D
```

---

## 7. Prerequisite

Agent B must include `diagnosis_id` in the MQTT payload:

- Modify `insert_diagnosis` to return the inserted row id
- Agent B adds `diagnosis_id` to the published JSON

---

## 8. Config (.env)

```
# Agent C
TICKET_COOLDOWN_SEC=30   # Optional: max one review_request per asset per N sec
```

---

## 9. Relationship to Agent D

| Agent | Responsibility |
|-------|----------------|
| **C** | Enqueue each diagnosis as a review_request (status=pending) |
| **D** | Web UI lists pending → human/LLM reviews → on approve, create Salesforce Case/Work Order, update status, insert feedback |

---

## 10. Implementation Order

1. Add `review_requests` table in `init_db.py` (or migration)
2. Add `insert_review_request` in `shared_lib/db.py`
3. Modify Agent B: `insert_diagnosis` returns id; include `diagnosis_id` in MQTT payload
4. Implement Agent C: subscribe diagnosis/#, insert_review_request, optional cooldown
