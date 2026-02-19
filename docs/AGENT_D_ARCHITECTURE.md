# Agent D (Review) Architecture & Feature Spec

## 1. Overview

Agent D is the **review agent** with Web UI and Chat. It lists pending diagnoses (from `review_requests`), lets humans review them, and on approval creates Salesforce Case/Work Order. It uses ReAct + tools for intelligent assistance and integrates with Salesforce.

---

## 2. Feature List

### 2.1 Review Queue & List

- Query `review_requests` with `status=pending` from DB
- Filter by asset_id, plant_id, time range
- Click a row to view full diagnosis details (root_cause, confidence, recommended_actions, evidence)
- Mark as read/unread or group by review status

### 2.2 Web UI

**2.2.1 Main Pages**

- **Review Queue**: List of pending diagnoses for approval/reject
- **Diagnosis Detail**: Full DiagnosisReport for a selected item
- **Alerts List**: List alerts with links to corresponding diagnosis (alert_id → diagnosis) and ticket when created (diagnosis_id → tickets)
- **Real-time Sensor Status**: Live query of telemetry for selected asset (pressure, flow, temp, vibration, etc.)

**2.2.2 Alerts + Diagnosis + Ticket View**

- Show alert list (from `alerts` table)
- Each alert row:
  - Link to **corresponding Diagnosis** (via `diagnosis.alert_id` = alert.id)
  - Link to **corresponding Ticket** if exists (via `tickets.diagnosis_id` → diagnosis.id)
- Click alert → show related diagnosis, review actions, and ticket (e.g. Salesforce Case/Work Order) when created

**2.2.3 Real-time Sensor Query**

- Select asset (e.g. pump01)
- Query latest telemetry from DB (or poll/WebSocket for near-real-time)
- Display: pressure_bar, flow_m3h, temp_c, bearing_temp_c, vibration_rms, rpm, motor_current_a, valve_open_pct
- Optional: auto-refresh interval (e.g. every 5 sec)

**2.2.4 Approval Actions**

- Approve / Reject / Edit-then-Approve buttons on each review item
- On Approve: create Salesforce Case or Work Order, update review_requests, insert tickets + feedback
- Reject: update status, insert feedback
- Edit: allow editing final_root_cause, notes, then approve

### 2.3 Chat Panel

**2.3.1 Chat UI (Reference: Email-Agent frontend)**

- Chat panel (resizable, minimize/expand)
- Session list: load previous conversations
- Messages: user + assistant, render markdown
- Input area + quick action buttons

**2.3.2 ReAct Step Visibility (Full Display, No Hiding)**

- **Streaming**: Use SSE to stream each reasoning step as it happens
- **Every step must be visible**:
  - Thought: LLM reasoning
  - Tool call: which tool (query_rules, query_telemetry, query_alerts, query_salesforce_history, etc.) and args
  - Tool result: full observation (e.g. rule content, telemetry rows, alert rows)
- No collapsing or hiding — show complete flow: how rules were queried, which sensors were checked, what data was returned
- Similar to streaming "thinking steps" but **permanent** in the message, not cleared after 2 seconds

**2.3.3 Persistence**

- **Conversation**: Save to DB (chat_sessions, chat_messages tables)
- **ReAct steps**: Save each step (thought, tool_call, tool_result) linked to the message
- Load session history from DB and render full steps when viewing past conversations

### 2.4 ReAct Tools

| Tool | Purpose |
|------|---------|
| `query_review_requests(status, asset_id, limit)` | Pending reviews |
| `query_diagnosis(diagnosis_id)` | Full diagnosis detail |
| `query_alerts(asset_id, limit)` | Recent alerts |
| `query_telemetry(asset_id, since_ts)` | Sensor data for context |
| `query_rules(keywords)` | Search diagnosis rules |
| `query_salesforce_history(asset_id, type, limit)` | Past Cases/Work Orders |
| `create_salesforce_case(diagnosis_id, ...)` | Create Case |
| `create_salesforce_workorder(diagnosis_id, ...)` | Create Work Order |
| `approve_review_request(review_id, decision, notes)` | Approve/reject |

### 2.5 Salesforce Integration

- Query history: Cases and Work Orders by asset, time range
- Create Case: Subject, Description, Priority, Asset
- Create Work Order: Asset, Description, Type
- Store ticket_id (Case/Work Order Id) and url in `tickets` table

### 2.6 Data Persistence

- `feedback`: ticket_id, review_decision, final_root_cause, notes
- `tickets`: ticket_id, url, diagnosis_id (on approve)
- `review_requests`: update status, resolved_at
- `chat_sessions`, `chat_messages`, `chat_steps`: conversation and ReAct steps

---

## 3. New DB Tables for Chat

```
chat_sessions
├── id (PK)
├── created_at
├── updated_at
└── preview (first user message or summary)

chat_messages
├── id (PK)
├── session_id (FK)
├── role ('user' | 'assistant')
├── content (text)
├── created_at
└── (optional) tool_calls, citations

chat_steps
├── id (PK)
├── message_id (FK → chat_messages.id)
├── step_type ('thought' | 'tool_call' | 'tool_result')
├── step_order (int)
├── tool_name (nullable)
├── tool_args (JSON, nullable)
├── content (text - for thought or result summary)
├── raw_result (text, nullable - full tool output for tool_result)
└── created_at
```

---

## 4. Chat UI Behavior (vs Reference)

| Aspect | Email-Agent AssistChatPanel | Agent D Chat |
|--------|-----------------------------|--------------|
| Thinking steps | Shown during loading, cleared after 2s | **Always visible**, persisted per message |
| Step content | planning, tool_call, tool_result (summary) | **Full detail**: tool args, full raw_result |
| Sessions | Loaded from API, persisted | Same + DB storage |
| Rules/sensor display | Not applicable | **Explicit**: show query_rules result, query_telemetry rows |
| Streaming | SSE for steps + result | Same, but steps appended to message and saved |

---

## 5. Frontend Reference

- **Project**: `/Users/bianhaoji/Documents/MERN Project/Mail Agent/Email-Agent/frontend`
- **Components**: `AssistChatPanel.js`, `ThreadChatPanel.js`, Dashboard layout
- **Patterns**: SSE streaming, session list, ReactMarkdown, thinking-step UI
- **Difference**: Do **not** clear or hide steps; render full tool_call args and tool_result (raw or truncated with expand)

---

## 6. Implementation Order

1. DB: Add chat_sessions, chat_messages, chat_steps tables; add query_diagnosis_by_id if missing
2. Agent D backend: FastAPI, ReAct agent with tools, SSE streaming endpoint for chat
3. Agent D backend: Save chat + steps to DB
4. Frontend: Review Queue page (alerts list, diagnosis list, tickets; link alert↔diagnosis↔ticket)
5. Frontend: Real-time sensor status component
6. Frontend: Chat panel with full step display (no hiding)
7. Salesforce: query + create Case/Work Order (when config present)
8. Approval flow: wire approve → SF create → tickets + feedback

---

## 7. API Endpoints (Proposed)

```
GET  /api/review-requests?status=pending&asset_id=&limit=
GET  /api/diagnosis/:id
GET  /api/alerts?asset_id=&limit=
GET  /api/telemetry?asset_id=&since_ts=&limit=
GET  /api/chat/sessions
GET  /api/chat/sessions/:id
POST /api/chat/ask (SSE stream: steps + result)
POST /api/review/:id/approve { decision, notes, create_salesforce_case? }
POST /api/review/:id/reject { notes }
```

---

## 8. Config (.env)

```
# Salesforce (for Agent D)
SALESFORCE_CLIENT_ID=
SALESFORCE_CLIENT_SECRET=
SALESFORCE_USERNAME=
SALESFORCE_PASSWORD=
SALESFORCE_DOMAIN=login  # or test for sandbox
```
