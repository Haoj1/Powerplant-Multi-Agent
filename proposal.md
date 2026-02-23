Below is a **two-week project plan + spec** that can be sent directly to a code agent (recommended: **lightweight Simulator + fault injection + MQTT event bus + 4-agent loop + tickets via GitHub Issues / custom Ticket API**). Copy the full text and the agent can start.

---

## Project Goals

Implement a demo-ready multi-agent system in 14 days:

1. **Simulator** models powerplant subsystem (recommended: pump/piping/bearing), outputs real-time sensor stream
2. **Multi-agent** monitors and detects anomalies, diagnoses root cause
3. **Case/WorkOrder** (Ticket) creation with human-in-the-loop review and feedback
4. **Visualization and metrics**: false positive/negative, detection latency, ticket creation latency

---

## Architecture

### Services

* `simulator-service`: Generates sensor data, publishes to MQTT `telemetry/*`
* `agent-monitor` (Agent A): Subscribes to telemetry, detects anomalies, publishes `alerts/*`
* `agent-diagnosis` (Agent B): Subscribes to alerts, fetches history, outputs RCA diagnosis, publishes `diagnosis/*`
* `agent-ticket` (Agent C): Subscribes to diagnosis, creates tickets (GitHub Issues or custom Ticket API), publishes `tickets/*`
* `agent-review` (Agent D): Subscribes to tickets, provides approve/edit/close API, publishes `feedback/*`
* `shared_lib`: Shared schema, serialization, feature extraction, utilities
* Optional: `dashboard` (simple frontend/CLI) + Grafana

### Message Bus (MQTT)

* Topic convention:
  * `telemetry/pump01`
  * `alerts/pump01`
  * `diagnosis/pump01`
  * `tickets/pump01`
  * `feedback/pump01`

---

## Data Schemas (JSON)

### Telemetry (simulator → MQTT)

See spec for Telemetry, AlertEvent, DiagnosisReport, Ticket, Feedback schemas.

---

## Simulator Design (Lightweight Dynamic Model + Fault Injection)

### Subsystem: Pump/Piping/Bearing

Internal state:

* `R` resistance (clogging increases it)
* `d` bearing wear (grows over time)
* `eta` pump efficiency (affected by wear/clogging)
* Output signals: flow, pressure, bearing_temp, vibration, motor_current, etc.

### Fault Scripts (JSON-driven, reproducible)

Supported: `bearing_wear`, `clogging`, `valve_stuck`, `sensor_drift`, `sensor_stuck`, `noise_burst`  
Output `truth.fault` and `truth.severity` as ground truth.

### Simulator API

* `POST /scenario/load` - upload scenario JSON
* `POST /scenario/start` / `stop`
* `GET /scenario/status`
* MQTT publish rate: 1Hz default (configurable)

---

## Multi-agent Logic (2-week implementation)

### Agent A: Monitor

* Subscribe to telemetry
* Sliding window (60s/120s) features: mean, std, slope, diff
* Detection: Z-score, ESD, or IsolationForest
* Output AlertEvent with evidence

### Agent B: Diagnosis

* YAML/JSON rules (8–12 rules)
* VIB up + BEARING_TEMP up → bearing_wear
* FLOW down + PRESSURE up + CURRENT up → clogging
* VALVE_OPEN changes but FLOW unchanged → valve_stuck
* Single sensor offset, others consistent → sensor_drift
* Output DiagnosisReport (root cause, confidence, actions, evidence)

### Agent C: Ticket Creation

* Preferred: GitHub Issues
* Fallback: Custom Ticket service (FastAPI + Postgres)
* Fields: title, body (diagnosis summary + evidence + metrics), labels

### Agent D: Review

* `POST /review/approve`, `edit`, `close`
* Publish Feedback for:
  * Rule threshold updates
  * False positive case log (JSONL)

---

## Visualization and Evaluation

### Metrics

* Detection latency
* Precision/recall (event-level, truth.fault != none)
* Ticket creation latency
* False positive rate

### Visualization

* Minimal: console log + CSV/JSONL
* Optional: Grafana (MQTT→Telegraf→InfluxDB)

---

## 14-day Task Split

### Day 1–2: Infrastructure + Simulator

* mosquitto docker + python skeleton
* simulator-service: telemetry publish, scenario scripts, reproducible seed
* At least 8 signals + truth

### Day 3–4: Agent A

* Subscribe telemetry
* Sliding window detection → alerts
* Log alerts

### Day 5–6: Agent B

* Rules (>= 8)
* Output diagnosis with evidence
* Unit test: known scenario → correct root cause

### Day 7–8: Agent C

* GitHub Issues connector (token config)
* Create ticket + write ticket_id to MQTT

### Day 9: Agent D

* approve/edit/close API
* Feedback publish + local memory

### Day 10–11: Evaluation

* Read truth/alerts/diagnosis, compute precision/recall/latency
* Generate metrics report (markdown)

### Day 12–14: Demo

* 3 demo scenarios: normal, chronic wear, sudden clog + sensor drift
* Demo script: data → alert → diagnosis → ticket → human review

---

## Deliverables

1. Runnable docker-compose (mosquitto + services)
2. Three scenario JSONs (reproducible)
3. Metrics report (markdown)
4. Demo script (one-step start, play scenario, view tickets)

---

## Engineering Constraints

* Python 3.11
* FastAPI + pydantic schema
* MQTT client: paho-mqtt (or asyncio-mqtt)
* Config via `.env` (MQTT broker, GitHub token, repo)
* Logging: JSONL
* Health check: `GET /health` per service

---

## Optional Extensions

* Abstract `TicketConnector` interface: `create_case()`, future Salesforce swap
* `SalesforceCaseConnector` for Case only (no WorkOrder dependency)

---

After sending this plan to the agent:

* First: repo structure + docker-compose + minimal runnable chain (simulator→monitor→alerts)
* Then: add diagnosis/ticket/review
