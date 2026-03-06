# MS Project Report: Multi-Agent Powerplant Monitoring System

## TGS Format Compliance

- **Page size:** 8.5" × 11" (US Letter)
- **Margins:** 1" all sides; page numbers/headers ≥ ¾" from edge
- **Font:** 12pt Times New Roman or 10pt Arial equivalent
- **Spacing:** Double-spaced (body, abstract, TOC); single-spaced for captions, tables, references
- **Page numbers:** Upper right, start at 2 (title page unnumbered)
- **References:** IEEE style, numbered [1], [2], etc., at end of text (not per-chapter)

---

## Document Structure (Target: ~52 pages)

### Front Matter

| Section | Pages | Notes |
|---------|-------|-------|
| Title Page | 1 | Mixed case title; no special characters |
| Abstract | 1 | Double-spaced; no figures/formulas |
| Table of Contents | 1–2 | Double-spaced |
| List of Figures | <1 | Single-spaced |
| List of Tables | <1 | Single-spaced |

---

### Chapter 1. Introduction (~4 pages)

**1.1 Motivation and Problem Statement**
- Industrial IoT asset monitoring: real-time telemetry, fault detection, root cause analysis
- Gaps: black-box ML vs. interpretable RCA; manual ticket creation; lack of human-in-the-loop review
- Research question: Can a multi-agent system combining rule-based detection, LLM-based diagnosis, and RAG achieve reliable fault diagnosis with interpretable evidence?

**1.2 Objectives**
- Design and implement a four-agent pipeline: Monitor → Diagnosis → Ticket → Review
- Integrate threshold-based anomaly detection, ReAct-based diagnosis, and RAG for context retrieval
- Evaluate detection rate, diagnosis accuracy, and healthy false positive rate on fault-injected scenarios

**1.3 Contributions**
- End-to-end multi-agent architecture for powerplant monitoring
- Rule + LLM hybrid diagnosis with evidence traceability
- Reproducible evaluation framework with fault injection and scenario-driven testing

**1.4 Report Organization**
- Brief roadmap of chapters

---

### Chapter 2. Background and Related Work (~5 pages)

**2.1 Industrial IoT and Asset Monitoring**
- Real-time sensor streams, SCADA systems, predictive maintenance [1]–[3]
- Fault types: bearing wear, clogging, valve malfunction, sensor drift

**2.2 Anomaly Detection**
- Statistical methods: Z-score, threshold-based, sliding window [4], [5]
- ML-based approaches and trade-offs with interpretability

**2.3 Root Cause Analysis**
- Rule-based systems vs. data-driven diagnosis [6], [7]
- LLM-based reasoning: ReAct, tool use, chain-of-thought [8]–[10]

**2.4 Multi-Agent Systems**
- Agent coordination, message passing, pub/sub architectures [11], [12]
- MQTT in industrial IoT [13]

**2.5 Retrieval-Augmented Generation (RAG)**
- Vector search, semantic retrieval for domain knowledge [14], [15]

---

### Chapter 3. System Design (~14 pages)

**3.1 Overview**
- High-level architecture diagram (Simulator → Agent A → Agent B → Agent C → Agent D)
- Data flow: telemetry → alerts → diagnosis → tickets → feedback

**3.2 Architectural Background**
- Why multi-agent: separation of concerns, scalability, fault isolation
- Pub/sub vs. request-response: MQTT for loose coupling, async event flow
- Stateless agents: each agent processes events independently; no shared mutable state

**3.3 LLM, Agent, and ReAct**
- **LLM role:** Reasoning over tool outputs; structured output (JSON) for diagnosis
- **Agent paradigm:** Autonomous entity that perceives (alerts), reasons (ReAct), acts (tools)
- **ReAct:** Thought → Action → Observation loop [8]; interleaves reasoning and tool use
- **Tool use:** query_rules, query_telemetry, query_alerts; LLM decides when to call
- **Why ReAct over pure prompt:** Handles multi-step reasoning; evidence traceability

**3.4 RAG Design**
- **Purpose:** Enrich agent context with retrieved domain knowledge (rules, past diagnoses)
- **Indexing:** Alerts, diagnoses, rules, feedback, chat messages → vector embeddings
- **Retrieval:** Semantic search via sqlite-vec; cosine similarity
- **Agent D RAG tools:** query_similar_diagnoses, query_similar_rules, query_similar_alerts, etc.
- **Embedding model:** all-MiniLM-L6-v2 (384 dim)

**3.5 Simulator**
- Physical models: pump, piping, bearing
- Fault injection: bearing_wear, clogging, valve_stuck, sensor_drift, noise_burst
- Scenario-driven execution (JSON scripts)

**3.6 Agent A (Monitor)**
- MQTT subscription to telemetry
- Threshold detector: per-signal thresholds, duration, slope checks
- Alert schema and publishing

**3.7 Agent B (Diagnosis)**
- ReAct agent with tools: query_rules, query_telemetry, query_alerts
- Rule storage (Markdown documents) and retrieval
- Diagnosis report schema

**3.8 Agent C (Ticket)**
- Review request creation from diagnosis
- No LLM; rule-based relay

**3.9 Agent D (Review)**
- Human-in-the-loop interface
- RAG tools: query_similar_diagnoses, query_similar_rules, etc.
- Approve/reject workflow; optional Salesforce integration

**3.10 Message Bus and Data Schemas**
- MQTT topic convention
- Telemetry, AlertEvent, DiagnosisReport, Ticket, Feedback schemas

---

### Chapter 4. Implementation (~10 pages)

**4.1 Technology Stack**
- Python 3.11, FastAPI, pydantic; MQTT (Mosquitto); LangChain/LangGraph; sqlite-vec, sentence-transformers

**4.2 Simulator Implementation**
- Motor, bearing, pipe models; fault injector; scenario executor
- **Code example:** FaultInjector.inject_fault; BearingWearFault.update

**4.3 Agent A Implementation**
- Telemetry buffer, threshold detector, MQTT publisher
- **Code example:** ThresholdDetector.detect (threshold + duration check); DEFAULT_THRESHOLDS

**4.4 Agent B Implementation**
- ReAct setup, tool implementations, rule indexing
- **Code example:** create_react_agent (LangGraph); query_rules tool; _parse_final_answer

**4.5 Agent D Implementation**
- RAG indexing (alerts, diagnoses, rules, feedback, chat); ReAct tools for review chat
- **Code example:** index_diagnosis; add_text_to_vector_db; query_similar_diagnoses

**4.6 Database and Vector Store**
- SQLite schema; sqlite-vec for embeddings
- **Code example:** vec_memory schema; embedding pipeline

---

### Chapter 5. Evaluation (~9 pages)

**5.1 Evaluation Setup**
- Scenario set: healthy_baseline, bearing_wear, clogging, valve_flow_mismatch, sensor_drift, rpm_override, noise_burst
- Metrics: detection rate, diagnosis accuracy, healthy false positive rate, token usage, latency

**5.2 Alert Detection Results**
- Overall detection rate
- Detection by signal (vibration_rms, bearing_temp_c, flow_m3h, etc.)
- Healthy false positive rate

**5.3 Diagnosis Accuracy**
- Per-scenario accuracy
- Per root cause: bearing_wear, valve_stuck (100%); clogging, sensor_override (lower)
- Analysis of failure modes

**5.4 Token Usage and Latency**
- Average steps and tokens per scenario
- Cost/latency trade-offs

**5.5 Discussion**
- Strengths and limitations
- Comparison with baseline or related work (if applicable)

**5.6 Improvement Opportunities**
- **Alert detection:** noise_burst 0% (transient spike; threshold/slope not tuned); vibration_rms 50%; consider shorter duration for spikes; tune FAST_DURATION_SIGNALS
- **Diagnosis:** clogging vs. sensor_drift confusion; add discriminative rules (flow-pressure correlation); expand rule coverage for sensor_override
- **RAG:** batch indexing; hybrid keyword + semantic search; tune similarity threshold
- **Evaluation:** more scenarios; cross-validation; real sensor data; ablation (rule-only vs. ReAct)

---

### Chapter 6. Conclusion (~2 pages)

**6.1 Summary**
- Recap of design, implementation, and evaluation

**6.2 Future Work**
- Vision integration (VLM), multi-asset scaling, improved detection for noise_burst

---

### Back Matter

| Section | Pages |
|---------|-------|
| References | 2–3 |
| Appendices | 4–5 |

---

### Appendices

- **Appendix A:** Scenario JSON examples (healthy_baseline, bearing_wear_eval)
- **Appendix B:** Rule document examples (bearing_wear.md)
- **Appendix C:** API endpoints or configuration
- **Appendix D:** Key code snippets (ReAct agent creation, RAG indexing)

---

## Figure and Table Placeholders

| ID | Title |
|----|-------|
| Fig. 1 | System architecture diagram |
| Fig. 2 | Data flow (telemetry → alerts → diagnosis → tickets) |
| Fig. 3 | ReAct agent loop (Agent B) |
| Fig. 4 | RAG indexing and retrieval flow |
| Fig. 5 | Detection rate by signal |
| Fig. 6 | Diagnosis accuracy by scenario |
| Fig. 7 | Confusion matrix (if applicable) |
| Table 1 | Fault types and physical effects |
| Table 2 | MQTT topic convention |
| Table 3 | Evaluation scenario summary |
| Table 4 | Per-scenario metrics (detection, diagnosis, tokens) |
| Table 5 | Improvement opportunities summary |

---

## Page Budget Summary

| Chapter | Pages |
|---------|-------|
| Front matter | 4–5 |
| Ch. 1 Introduction | 4 |
| Ch. 2 Background | 5 |
| Ch. 3 System Design | 14 |
| Ch. 4 Implementation | 10 |
| Ch. 5 Evaluation | 9 |
| Ch. 6 Conclusion | 2 |
| References | 2–3 |
| Appendices | 4–5 |
| **Total** | **52–54** |
