# Multi-Agent Powerplant Monitoring System

A multi-agent system for real-time monitoring, anomaly detection, root cause analysis, and automated ticket creation for powerplant assets.

**Live Demo:** [https://app.powerplantagent.com/review](https://app.powerplantagent.com/review)

---

## Project Overview

This project implements an end-to-end pipeline for industrial IoT asset monitoring. It simulates a powerplant subsystem (pump, piping, bearing) with configurable fault injection, detects anomalies in real-time sensor streams, diagnoses root causes using rules and LLM (ReAct), creates tickets automatically, and provides a human-in-the-loop review interface. The system combines MQTT pub/sub, multi-agent coordination, RAG-based retrieval, and optional Salesforce integration.

### Problems Solved

- **Real-time anomaly detection** from streaming telemetry (pressure, flow, temperature, vibration, etc.)
- **Interpretable root cause analysis** (RCA) with evidence and rules, not black-box predictions
- **Automated ticket creation** with recommended actions and evidence
- **Human-in-the-loop review** for safety and accountability before ticket closure
- **Reproducible evaluation** via fault injection and scenario-driven testing

### Technology Stack

| Layer | Technologies |
|-------|--------------|
| **Backend** | Python 3.11, FastAPI, pydantic, pydantic-settings |
| **Message bus** | MQTT (paho-mqtt, Mosquitto), Kafka (kafka-python, optional Agent B queue) |
| **LLM / Agents** | LangChain, LangChain-Core, LangGraph, langchain-openai (OpenAI/DeepSeek compatible) |
| **Frontend** | React, Vite |
| **RAG / Vector** | sqlite-vec, sentence-transformers (all-MiniLM-L6-v2) |
| **Streaming** | sse-starlette (Agent D chat) |
| **Numerics** | NumPy (simulator physics) |
| **Multimodal (optional)** | pyvista (3D viz), anthropic (Claude Vision) |
| **Eval / Charts** | matplotlib |

---

## Architecture

| Component | Role |
|-----------|------|
| **Simulator** | Generates telemetry, injects faults (bearing_wear, clogging, valve_stuck, sensor_drift), publishes to MQTT |
| **Agent A (Monitor)** | Subscribes to telemetry, threshold + slope + duration anomaly detection, publishes alerts |
| **Agent B (Diagnosis)** | Subscribes to alerts, rule-based + LLM (ReAct) root cause analysis, publishes diagnoses |
| **Agent C (Ticket)** | Subscribes to diagnoses, creates tickets (GitHub Issues or local), queues for review |
| **Agent D (Review)** | Human review interface, approve/reject/edit, optional Salesforce Case, chat assistant with RAG |

All agents communicate via **MQTT** (pub/sub). Each agent is stateless and scalable.

### Fault Types (Simulator)

| Fault | Physical Effect | Typical Alerts |
|-------|-----------------|----------------|
| `bearing_wear` | Vibration ↑, bearing temp ↑ | vibration_rms, bearing_temp_c |
| `clogging` | Flow ↓, pressure ↑, motor current ↑ | flow_m3h, pressure_bar, motor_current_a |
| `valve_stuck` | Valve vs flow mismatch | valve_flow_mismatch |
| `sensor_drift` | Single-signal drift | temp_c, rpm, etc. |
| `sensor_override` | Force signal to fixed value (eval) | temp_c, rpm |
| `noise_burst` | Transient spike | vibration_rms |

---

## Data Flow

```
┌─────────────┐     telemetry/*      ┌─────────────┐     alerts/*      ┌─────────────┐
│  Simulator  │ ──────────────────► │  Agent A    │ ───────────────► │  Agent B    │
│  (8001)     │                      │  (Monitor)  │                  │ (Diagnosis) │
└─────────────┘                      └─────────────┘                  └──────┬──────┘
                                                                             │
                                                                      diagnosis/*
                                                                             │
                                                                             ▼
┌─────────────┐     tickets/*        ┌─────────────┐     feedback/*   ┌─────────────┐
│  Agent D    │ ◄────────────────── │  Agent C    │ ◄────────────────│  Human      │
│  (Review)   │                      │  (Ticket)   │                  │  Reviewer   │
└─────────────┘                      └─────────────┘                  └─────────────┘
       │
       │  API + Frontend (8005)
       ▼
  Web Dashboard (Review Queue, Alerts, Sensors, Chat, Scenarios)
```

**Flow summary:** Telemetry → Alerts → Diagnosis → Ticket → Human Review → Feedback. Each step adds structure and context. Feedback can update rules and thresholds.

## Project Structure

```
.
├── simulator-service/    # Telemetry generator, fault injection (bearing_wear, clogging, valve_stuck, sensor_drift, noise_burst)
├── agent-monitor/         # Anomaly detection (threshold, slope, valve-flow mismatch)
├── agent-diagnosis/       # ReAct agent + rules (query_rules, query_telemetry, query_alerts)
├── agent-ticket/          # Review request creation (no LLM)
├── agent-review/          # Human review API + React dashboard + RAG chat
├── shared_lib/            # Models, config, db, vector indexing, integrations
├── evaluation/            # Eval scripts, scenario_runs.jsonl, report charts
├── docs/                  # Architecture, alerts/rules, RAG, external APIs
├── scripts/               # run_alert_eval.py, start_all_agents.sh, use_eval_db.sh
├── mosquitto/             # MQTT broker config
├── docker-compose.yml     # Mosquitto
├── requirements.txt       # Python dependencies
└── .env.example           # LLM keys, SQLITE_PATH, Salesforce, etc.
```

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose (for MQTT)
- LLM API key (OpenAI or DeepSeek) for Agent B diagnosis and Agent D chat
- (Optional) GitHub token for ticket creation
- (Optional) Salesforce credentials for Case creation on approve

### Setup

1. **Clone and install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings (LLM keys, Salesforce, etc.)
   ```

3. **Start MQTT broker:**
   ```bash
   docker-compose up -d mosquitto
   ```

4. **Start services** (or use `scripts/start_all_agents.sh`):
   ```bash
   # Terminal 1: Simulator
   python simulator-service/main.py
   
   # Terminal 2: Agent Monitor
   python agent-monitor/main.py
   
   # Terminal 3: Agent Diagnosis
   python agent-diagnosis/main.py
   
   # Terminal 4: Agent Ticket
   python agent-ticket/main.py
   
   # Terminal 5: Agent Review (backend + API)
   python agent-review/main.py
   
   # Terminal 6: Agent Review frontend
   cd agent-review/frontend && npm install && npm run dev
   ```

## Features

### Agent D Dashboard

Live demo: [https://app.powerplantagent.com/review](https://app.powerplantagent.com/review) (local dev: port 3000)

- **Review Queue**: Approve/reject diagnoses; optionally create Salesforce Case with pre-filled form
- **Alerts**: View alerts, generate/regenerate diagnosis, save, add to Review Queue
- **Sensors**: Telemetry visualization
- **Chat**: ReAct assistant with diagnosis tools
- **Scenario Management**:
  - **Simulator Scenarios**: Load, start, stop, reset fault scenarios
  - **Troubleshooting Rules**: Create rules from natural language or flowchart upload; view/delete rules (stored in `agent-diagnosis/rules/*.md`)

### Salesforce Integration

When approving a review, you can create a Salesforce Case with Subject, Description, Priority, Status, Origin, Type, and Reason. Picklist values are fetched from your Salesforce org. See `docs/EXTERNAL_API_CONFIG.md` for setup.

---

## How to Use the App

The dashboard has five main sections. Here is a step-by-step guide.

### 1. Scenarios – Run a Fault Simulation

Before you see alerts and diagnoses, you need to run a scenario that injects faults into the simulator.

1. Go to **Scenarios** in the sidebar.
2. Click **Load Scenario**.
3. Choose a scenario JSON (e.g. `test_alert_quick.json` for a quick fault, or `bearing_wear_chronic.json` for gradual bearing wear).
4. Set **Asset ID** (e.g. `pump01`) and **Plant ID** (e.g. `plant01`).
5. Click **Load**, then **Start**.
6. The simulator will publish telemetry; Agent A will detect anomalies and Agent B will produce diagnoses. New items will appear in **Review Queue** and **Alerts**.

**Troubleshooting Rules:** In the same page, you can create rules from natural language or by uploading a flowchart image. Rules are used by Agent B for root cause analysis.

---

### 2. Review Queue – Approve or Reject Diagnoses

Pending diagnoses from Agent B appear here for human review.

1. Go to **Review Queue**.
2. Use filters (Status, Asset ID) to find items.
3. Click a row or **View** to open the diagnosis modal (root cause, confidence, evidence, recommended actions).
4. **Approve** – Optionally add notes and check "Create Salesforce Case" to push a Case to Salesforce. The diagnosis is marked approved.
5. **Reject** – Add notes and reject. The diagnosis is marked rejected.

---

### 3. Alerts – View and Trigger Diagnosis

Shows all alerts from Agent A (anomaly detection).

1. Go to **Alerts**.
2. Browse alerts by asset, severity, time.
3. Click an alert to see details.
4. Use **Generate Diagnosis** to have Agent B analyze the alert and produce a diagnosis.
5. Use **Add to Review Queue** to send the diagnosis to the Review Queue for approval.

---

### 4. Sensors – Real-Time Telemetry

View live sensor values for an asset.

1. Go to **Sensors**.
2. Select an **Asset** (e.g. `pump01`).
3. The dashboard shows pressure, flow, temperature, vibration, etc., with auto-refresh.
4. Use this to monitor asset state while a scenario is running.

---

### 5. Chat – ReAct Assistant with RAG

A chat assistant that can query diagnoses, alerts, rules, and feedback.

1. Go to **Chat**.
2. Type a question, e.g.:
   - "Find similar bearing wear cases"
   - "What rules apply to vibration?"
   - "Show pending diagnoses for pump01"
3. The assistant uses RAG tools (query_similar_diagnoses, query_similar_rules, etc.) and returns answers with references.
4. ReAct steps (thought, tool call, result) are shown for transparency.

---

### Typical Workflow

1. **Load and start a scenario** (Scenarios) → Simulator injects fault.
2. **Watch Sensors** (Sensors) → See telemetry change.
3. **Check Alerts** (Alerts) → Agent A detects anomalies.
4. **Review Queue** (Review Queue) → Agent B diagnoses; you approve or reject.
5. **Chat** (Chat) → Ask questions about similar cases or rules.

---

## Evaluation and Reproducibility

The system supports reproducible evaluation via fault-injected scenarios. Metrics include **alert detection rate**, **diagnosis accuracy**, and **healthy false positive rate**.

### Reproduce Full Eval

1. **Start services:** MQTT + Simulator + Agent A + Agent B + Agent C + Agent D
2. **Run scenario eval:** `python scripts/run_alert_eval.py` (~10–12 min)
3. **Compute metrics:** `python evaluation/run_evaluation.py`
4. **Build report:** `python evaluation/build_report.py` → `evaluation/report/`

See **[evaluation/README.md](evaluation/README.md)** for full instructions.

### Eval Concepts

| Document | Description |
|----------|-------------|
| [evaluation/EVAL_ALERTS.md](evaluation/EVAL_ALERTS.md) | Alert schema, detection methods (threshold/slope/valve-flow), metrics |
| [evaluation/EVAL_DIAGNOSIS.md](evaluation/EVAL_DIAGNOSIS.md) | Diagnosis schema, ReAct flow, root causes, accuracy metrics |

---

## Development Status

- ✅ Phase 0: Project skeleton and shared library
- ✅ Phase 1: MQTT infrastructure & simulator
- ✅ Phase 2: Agent A (monitoring & anomaly detection)
- ✅ Phase 3: Simulator fault scenarios
- ✅ Phase 4: Agent B (diagnosis rules engine)
- ✅ Phase 5: Agent C (ticket creation)
- ✅ Phase 6: Agent D (human review, Salesforce, rules management)
- ✅ Phase 7: Evaluation & metrics (run_alert_eval, run_evaluation, build_report)
- ⏳ Phase 8: Demo polish

See `TODO.md` for detailed task breakdown.

## API Endpoints

Each service exposes a `/health` endpoint for health checks.

| Service        | Port | Notes                                      |
|----------------|------|--------------------------------------------|
| Simulator      | 8001 | `/scenario/load`, `/scenario/start/{asset}` |
| Agent Monitor  | 8002 | `/metrics` (messages_processed, alerts_generated) |
| Agent Diagnosis| 8003 |                                            |
| Agent Ticket   | 8004 |                                            |
| Agent Review   | 8005 | REST API for dashboard; `/api/rules`, `/api/review`, etc. |

Agent Review also serves the frontend via Vite proxy when running `npm run dev`.

## MQTT Topics

| Topic | Publisher | Subscriber |
|-------|-----------|------------|
| `telemetry/{asset_id}` | Simulator | Agent A |
| `alerts/{asset_id}` | Agent A | Agent B |
| `diagnosis/{asset_id}` | Agent B | Agent C |
| `tickets/{asset_id}` | Agent C | Agent D |
| `feedback/{asset_id}` | Agent D (on approve/reject) | — |

## Further Documentation

- `docs/AGENT_B_ARCHITECTURE.md` — ReAct agent, tools, rules
- `docs/AGENT_D_ARCHITECTURE.md` — Review API, RAG chat
- `docs/ALERTS_AND_RULES.md` — Alert thresholds, rule priorities
- `docs/RAG_IMPLEMENTATION.md` — Vector indexing, query tools
- `docs/EXTERNAL_API_CONFIG.md` — Salesforce, GitHub

## License

MIT
