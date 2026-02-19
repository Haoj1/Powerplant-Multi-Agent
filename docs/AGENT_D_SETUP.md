# Agent D Setup

## 1. Dependencies

### Python (Backend)

Add to `requirements.txt` (already added):

```
sse-starlette>=2.0.0
```

Install:

```bash
cd "/Users/bianhaoji/Documents/MERN Project/Multi-Agent Project"
source venv/bin/activate
pip install -r requirements.txt
```

### Frontend (React)

Agent D frontend is a separate React app. Create `agent-review/frontend/` with:

```bash
npx create-react-app frontend
cd frontend
npm install axios react-router-dom react-markdown
```

Or copy structure from `/Users/bianhaoji/Documents/MERN Project/Mail Agent/Email-Agent/frontend`.

---

## 2. Database Update

Run the init script to create new tables:

```bash
cd "/Users/bianhaoji/Documents/MERN Project/Multi-Agent Project"
python scripts/init_db.py
```

### New Tables

| Table | Purpose |
|-------|---------|
| `chat_sessions` | Chat conversation sessions |
| `chat_messages` | Messages (user + assistant) |
| `chat_steps` | ReAct steps (thought, tool_call, tool_result) per message |

### New DB Functions (in shared_lib/db.py)

| Function | Purpose |
|----------|---------|
| `get_diagnosis_by_id(id)` | Get diagnosis by id |
| `query_alerts_with_diagnosis_and_ticket(asset_id?, limit)` | Alerts with linked diagnosis_id and ticket_id/url |
| `insert_chat_session(preview)` | Create session |
| `update_chat_session(session_id, preview?)` | Update session |
| `insert_chat_message(session_id, role, content, tool_calls?)` | Add message |
| `insert_chat_step(message_id, step_type, step_order, ...)` | Add ReAct step |
| `list_chat_sessions(limit)` | List sessions |
| `get_chat_session_with_messages(session_id)` | Load session + messages + steps |
| `update_review_request_status(review_id, status)` | Approve/reject review |

---

## 3. Run Database Update (One-time)

```bash
python scripts/init_db.py
```

Expected output:

```
Schema created: .../data/monitoring.db
Tables: telemetry, alerts, diagnosis, vision_images, vision_analysis, tickets, review_requests, chat_sessions, chat_messages, chat_steps, feedback
```
