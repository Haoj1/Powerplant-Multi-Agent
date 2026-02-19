## Multi-Agent Powerplant Project – Master TODO

High-level phases are ordered by priority. You can trim lower phases if time is tight but still keep a working demo.

---

### Phase 0 – Project Skeleton & Shared Library

- [ ] **Initialize project structure**
  - [ ] Create service folders: `simulator-service/`, `agent-monitor/`, `agent-diagnosis/`, `agent-ticket/`, `agent-review/`, `shared_lib/`
  - [ ] Add minimal `main.py` for each service
  - [ ] Add basic `FastAPI` app and `GET /health` endpoint for each service
- [ ] **Environment and configuration**
  - [ ] Create `.env.example` with placeholders (MQTT host/port, GitHub token, repo, etc.)
  - [ ] Add `settings` module in `shared_lib` to load configuration from env
  - [ ] Decide logging directory structure (e.g. `logs/telemetry.jsonl`, `logs/alerts.jsonl`, etc.)
- [ ] **Shared schemas and utilities**
  - [ ] Create `shared_lib/models.py` with pydantic models for:
    - [ ] `Telemetry`
    - [ ] `AlertEvent`
    - [ ] `DiagnosisReport`
    - [ ] `Ticket`
    - [ ] `Feedback`
  - [ ] Add common utility functions (timestamp helpers, ID generation, JSONL append helper)

---

### Phase 1 – MQTT Infrastructure & Minimal Simulator (Day 1–2)

- [ ] **MQTT setup**
  - [ ] Add `docker-compose.yml` entry for Mosquitto broker
  - [ ] Define base MQTT topics: `telemetry/*`, `alerts/*`, `diagnosis/*`, `tickets/*`, `feedback/*`
- [ ] **Simulator minimal implementation**
  - [ ] Implement simple internal state for pump (pressure, flow, temperature, vibration, rpm, current, valve position)
  - [ ] Implement random but stable "healthy" telemetry stream (1 Hz) for `plant01/pump01`
  - [ ] Publish telemetry messages as JSON to `telemetry/pump01`
  - [ ] Add CLI or config options for publish frequency and duration
- [ ] **Basic observability**
  - [ ] Log outgoing telemetry to `telemetry.jsonl`
  - [ ] Provide `GET /health` and `GET /status` in `simulator-service`

---

### Phase 2 – Agent A (Monitoring & Anomaly Detection) (Day 3–4)

- [ ] **MQTT client integration**
  - [ ] Implement MQTT client (e.g. `paho-mqtt` or `asyncio-mqtt`) for `agent-monitor`
  - [ ] Subscribe to `telemetry/#`
- [ ] **Simple threshold-based detection (MVP)**
  - [ ] Implement static threshold rules (e.g. `vibration_rms`, `bearing_temp_c`, `pressure_bar`)
  - [ ] On rule breach, create an `AlertEvent` and publish to `alerts/pump01`
  - [ ] Log alerts to `alerts.jsonl`
- [ ] **Sliding-window anomaly detection**
  - [ ] Maintain sliding window buffers (e.g. 60–120 seconds) per asset
  - [ ] Compute features: mean, standard deviation, simple slope
  - [ ] Implement z-score-based detection per signal using adaptive baseline
  - [ ] Enrich `AlertEvent.evidence` with window statistics
- [ ] **Service API**
  - [ ] Add `GET /health` and `GET /metrics` (basic counters for processed messages and alerts)

---

### Phase 3 – Simulator Fault Scenarios & Ground Truth (Day 4–5)

- [ ] **Internal state modeling**
  - [ ] Model key internal variables: resistance `R`, bearing wear `d`, pump efficiency `eta`
  - [ ] Link internal state to signals (flow, pressure, bearing temp, vibration, motor current, etc.)
- [ ] **Fault injection mechanics**
  - [ ] Implement `bearing_wear` evolution (increase `d` over time)
  - [ ] Implement `clogging` evolution (step or ramp increase in `R`)
  - [ ] Implement optional `sensor_drift` for selected signals
  - [ ] Update `truth.fault` and `truth.severity` according to active faults
- [ ] **Scenario definitions**
  - [ ] Define scenario JSON schema (timeline of fault events and parameters)
  - [ ] Implement scenario loading and execution in the simulator
  - [ ] Add minimal HTTP API:
    - [ ] `POST /scenario/load`
    - [ ] `POST /scenario/start`
    - [ ] `POST /scenario/stop`
    - [ ] `GET /scenario/status`
  - [ ] Create at least 1–2 example scenarios (healthy, simple bearing wear)

---

### Phase 4 – Agent B (Diagnosis Rules Engine) (Day 5–7)

- [ ] **Rule configuration**
  - [ ] Define a simple `rules.yaml` or `rules.json` format
  - [ ] Implement at least 4–6 core rules, for example:
    - [ ] Vibration + bearing temperature up → `bearing_wear`
    - [ ] Flow down + pressure up + current up → `clogging`
    - [ ] Valve position change but flow stuck → `valve_stuck`
    - [ ] Single-sensor offset but others normal → `sensor_drift`
- [ ] **Data access for diagnosis**
  - [ ] Subscribe to `alerts/*`
  - [ ] Maintain recent telemetry window per asset for context (e.g. last 5 minutes)
  - [ ] Build feature summaries used by rules (trends, deltas, averages)
- [ ] **Diagnosis engine**
  - [ ] Implement simple rule evaluation loop
  - [ ] Compute `root_cause`, `confidence`, `impact`, `recommended_actions`, `evidence`
  - [ ] Publish `DiagnosisReport` to `diagnosis/pump01`
  - [ ] Log diagnosis events to `diagnosis.jsonl`
- [ ] **Service API & tests**
  - [ ] Add `GET /health`
  - [ ] Add basic unit tests for at least 2–3 known scenarios to verify correct `root_cause`

---

### Phase 5 – Agent C (Ticket / Case Creation) (Day 7–9)

- [ ] **Ticket connector abstraction**
  - [ ] Define `TicketConnector` interface (e.g. `create_case(title, body, labels) -> Ticket`)
  - [ ] Implement `LocalFileTicketConnector` (JSONL-based) as a fallback
- [ ] **GitHub Issues integration**
  - [ ] Implement `GitHubIssueConnector` using GitHub REST API
  - [ ] Read GitHub token and repo from env/config
  - [ ] Map `DiagnosisReport` to issue title, body, and labels
  - [ ] Handle basic error cases (invalid token, rate limits)
- [ ] **Agent C logic**
  - [ ] Subscribe to `diagnosis/*`
  - [ ] On new diagnosis, create a ticket using configured connector
  - [ ] Publish `Ticket` events to `tickets/pump01`
  - [ ] Log tickets to `tickets.jsonl`
- [ ] **Service API**
  - [ ] Add `GET /health`
  - [ ] Add endpoint to inspect last created tickets (optional)

---

### Phase 6 – Agent D (Human Review & Feedback Loop) (Day 9–10)

- [ ] **Feedback data flow**
  - [ ] Define simple HTTP API for review:
    - [ ] `POST /review` with fields: `ticket_id`, `review_decision`, `final_root_cause`, `notes`
  - [ ] On review submission:
    - [ ] Publish `Feedback` to `feedback/pump01`
    - [ ] Append feedback to `feedback.jsonl`
- [ ] **Optional rule/threshold update**
  - [ ] Design a simple mapping from feedback to rule/threshold adjustments
  - [ ] Implement reload of `rules.yaml` when changed (optional)
- [ ] **Minimal UI**
  - [ ] Provide instructions / curl examples for reviewing tickets
  - [ ] (Optional) Add a very simple HTML or CLI interface for posting reviews

---

### Phase 7 – Evaluation & Metrics (Day 10–11)

- [ ] **Log and data alignment**
  - [ ] Ensure all services write JSONL logs with consistent timestamps and asset IDs
  - [ ] Confirm scenario ground-truth is stored and accessible
- [ ] **Evaluation script**
  - [ ] Implement loader for telemetry, alerts, diagnosis, tickets, and feedback logs
  - [ ] Compute metrics:
    - [ ] Detection latency (fault injection to first alert)
    - [ ] Precision and recall based on `truth.fault`
    - [ ] Ticket creation latency (diagnosis to ticket)
    - [ ] False positive rate (alerts when `truth.fault == none`)
  - [ ] Output a Markdown report summarizing metrics and key plots/tables

---

### Phase 8 – Demo Polish & Scenarios (Day 12–14)

- [ ] **Scenario library**
  - [ ] Finalize at least 3 reusable scenario JSONs:
    - [ ] Healthy baseline
    - [ ] Slow bearing wear
    - [ ] Sudden clogging + sensor drift
- [ ] **One-command demo**
  - [ ] Add `docker-compose.yml` entries for all services
  - [ ] Add a `make demo` or script to:
    - [ ] Start all services
    - [ ] Load and start a chosen scenario
    - [ ] Print instructions on where to watch logs and tickets
- [ ] **Optional dashboards**
  - [ ] Integrate with Grafana / InfluxDB (or similar) if time permits
  - [ ] Create basic dashboards for telemetry, alerts, and diagnosis

---

### Nice-to-Have Extensions (Optional)

- [ ] **Additional fault types and rules**
- [ ] **More advanced anomaly detection (e.g. IsolationForest)**
- [ ] **Salesforce or other external ticket system connector**
- [ ] **Richer web dashboard for real-time monitoring**

