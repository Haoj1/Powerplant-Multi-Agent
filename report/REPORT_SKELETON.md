# Multi-Agent Powerplant Monitoring System

**MS Project Report — Computer Engineering — Northwestern University**

---

## Title Page (TGS Template)

```
NORTHWESTERN UNIVERSITY

Multi-Agent Powerplant Monitoring System: Real-Time Anomaly Detection, Root Cause Analysis, and Human-in-the-Loop Review

A PROJECT REPORT

SUBMITTED TO THE GRADUATE SCHOOL
IN PARTIAL FULFILLMENT OF THE REQUIREMENTS
for the degree
MASTER OF SCIENCE
Computer Engineering

By
{Your Name}

EVANSTON, ILLINOIS
{Month and Year}
```

---

## Abstract

This report presents the design, implementation, and evaluation of a multi-agent system for powerplant asset monitoring. The system consists of four agents: a Monitor (Agent A) that detects anomalies in real-time telemetry using threshold-based methods, a Diagnosis agent (Agent B) that performs root cause analysis via LangChain ReAct with rule retrieval, a Ticket agent (Agent C) that creates review requests, and a Review agent (Agent D) that provides a human-in-the-loop interface with RAG-assisted chat. All agents communicate over MQTT. A physics-based simulator with fault injection (bearing wear, clogging, valve stuck, sensor drift) enables reproducible evaluation. On 234 scenario runs, the system achieves 44.9% alert detection rate, 82.9% diagnosis accuracy, and 11.9% healthy false positive rate. Bearing wear and valve stuck scenarios achieve 100% diagnosis accuracy; clogging and sensor override show lower accuracy. The report concludes with a discussion of limitations and future work.

---

## Table of Contents

1. Introduction  
   1.1 Motivation and Problem Statement  
   1.2 Objectives  
   1.3 Contributions  
   1.4 Report Organization  

2. Background and Related Work  
   2.1 Industrial IoT and Asset Monitoring  
   2.2 Anomaly Detection  
   2.3 Root Cause Analysis  
   2.4 Multi-Agent Systems  
   2.5 Retrieval-Augmented Generation  

3. System Design  
   3.1 Overview  
   3.2 Architectural Background  
   3.3 LLM, Agent, and ReAct  
   3.4 RAG Design  
   3.5 Simulator  
   3.6 Agent A (Monitor)  
   3.7 Agent B (Diagnosis)  
   3.8 Agent C (Ticket)  
   3.9 Agent D (Review)  
   3.10 Message Bus and Data Schemas  

4. Implementation  
   4.1 Technology Stack  
   4.2 Simulator Implementation  
   4.3 Agent A Implementation  
   4.4 Agent B Implementation  
   4.5 Agent D Implementation  
   4.6 Database and Vector Store  

5. Evaluation  
   5.1 Evaluation Setup  
   5.2 Alert Detection Results  
   5.3 Diagnosis Accuracy  
   5.4 Token Usage and Latency  
   5.5 Discussion  
   5.6 Improvement Opportunities  

6. Conclusion  
   6.1 Summary  
   6.2 Future Work  

References  

Appendices  

---

## Chapter 1. Introduction

### 1.1 Motivation and Problem Statement

[Write: Industrial IoT monitoring challenges; need for interpretable RCA; human-in-the-loop; research question.]

### 1.2 Objectives

[Write: Four-agent pipeline; threshold + ReAct + RAG; evaluation metrics.]

### 1.3 Contributions

[Write: End-to-end architecture; rule+LLM hybrid; reproducible evaluation.]

### 1.4 Report Organization

[Write: Brief roadmap of chapters.]

---

## Chapter 2. Background and Related Work

### 2.1 Industrial IoT and Asset Monitoring

[Cite: [1]–[3]. Describe SCADA, predictive maintenance, fault types.]

### 2.2 Anomaly Detection

[Cite: [4], [5]. Z-score, thresholds, sliding window; ML trade-offs.]

### 2.3 Root Cause Analysis

[Cite: [6], [7]. Rule-based vs. data-driven; interpretability.]

### 2.4 Multi-Agent Systems

[Cite: [11], [12]. Agent coordination; pub/sub.]

### 2.5 Retrieval-Augmented Generation

[Cite: [15], [16]. Vector search; semantic retrieval.]

---

## Chapter 3. System Design

### 3.1 Overview

[Insert Fig. 1: Architecture diagram. Describe data flow.]

### 3.2 Architectural Background

[Write: Why multi-agent—separation of concerns, scalability, fault isolation. Pub/sub vs. request-response; MQTT for loose coupling. Stateless agents: each processes events independently.]

### 3.3 LLM, Agent, and ReAct

[Write: Cite [8]. LLM role: reasoning over tool outputs, structured JSON output. Agent paradigm: perceive (alerts) → reason (ReAct) → act (tools). ReAct loop: Thought → Action → Observation. Tool use: query_rules, query_telemetry, query_alerts; LLM decides when. Why ReAct over pure prompt: multi-step reasoning, evidence traceability.]

### 3.4 RAG Design

[Write: Purpose—enrich context with rules, past diagnoses. Indexing: alerts, diagnoses, rules, feedback, chat → embeddings. Retrieval: sqlite-vec, cosine similarity. Agent D tools: query_similar_diagnoses, query_similar_rules, etc. Embedding: all-MiniLM-L6-v2. Insert Fig. 4: RAG flow.]

### 3.5 Simulator

[Describe: pump, piping, bearing models; fault types; scenario JSON.]

### 3.6 Agent A (Monitor)

[Describe: MQTT subscription; threshold detector; alert schema.]

### 3.7 Agent B (Diagnosis)

[Describe: ReAct; tools; rule storage; diagnosis schema.]

### 3.8 Agent C (Ticket)

[Describe: Review request creation; no LLM.]

### 3.9 Agent D (Review)

[Describe: RAG tools; approve/reject; optional Salesforce.]

### 3.10 Message Bus and Data Schemas

[Insert Table 1: MQTT topics. Describe schemas.]

---

## Chapter 4. Implementation

### 4.1 Technology Stack

[Python 3.11, FastAPI, pydantic; MQTT (paho-mqtt, Mosquitto); LangChain, LangGraph; sqlite-vec, sentence-transformers; matplotlib for eval charts.]

### 4.2 Simulator Implementation

[Describe: FaultInjector, fault_types (BearingWearFault, CloggingFault, etc.), scenario executor. **Code example:**]

```python
# FaultInjector.inject_fault (simulator-service/faults/fault_injector.py)
fault_map = {
    "bearing_wear": BearingWearFault,
    "clogging": CloggingFault,
    "valve_stuck": ValveStuckFault,
    ...
}
fault = fault_map[fault_type](start_time, params)
self.active_faults.append(fault)
```

### 4.3 Agent A Implementation

[Describe: TelemetryBuffer, ThresholdDetector, MQTT publisher. **Code example:**]

```python
# ThresholdDetector.detect (agent-monitor/detection/threshold_detector.py)
# Duration check: skip if sustained breach < min_dur
min_dur = 0.5 if signal_name in FAST_DURATION_SIGNALS else self.min_duration_sec
if buffer and min_dur > 0:
    dur = buffer.duration_above_threshold(asset_id, signal_name, thr_val, side, window_sec)
    if dur < min_dur:
        continue  # Not sustained long enough
```

### 4.4 Agent B Implementation

[Describe: LangGraph create_react_agent, tools, _parse_final_answer. **Code example:**]

```python
# agent-diagnosis/agent/agent.py
def create_diagnosis_agent():
    from langgraph.prebuilt import create_react_agent
    llm = ChatOpenAI(model="deepseek-chat", temperature=0)
    tools = get_diagnosis_tools()  # query_rules, query_telemetry, query_alerts
    return create_react_agent(llm, tools)
```

### 4.5 Agent D Implementation

[Describe: RAG indexing on approve/reject/chat; query_similar_* tools. **Code example:**]

```python
# shared_lib/vector_indexing.py
@_safe_index
def index_diagnosis(diagnosis_id: int, diagnosis_data: Dict[str, Any]):
    text = f"Root cause: {root_cause}\nConfidence: {confidence}\n..."
    return add_text_to_vector_db(text=text, doc_type="diagnosis", doc_id=diagnosis_id, ...)
```

### 4.6 Database and Vector Store

[Describe: SQLite (alerts, diagnosis, telemetry); sqlite-vec vec_memory table; embedding pipeline.]

---

## Chapter 5. Evaluation

### 5.1 Evaluation Setup

[Scenarios; metrics; eval_result.json; run_alert_eval.py flow.]

### 5.2 Alert Detection Results

[Detection rate 44.9%; by signal; healthy FP 11.9%. Insert Fig. 5.]

### 5.3 Diagnosis Accuracy

[Per-scenario; bearing_wear/valve_stuck 100%; clogging 63.6%; sensor_override 58.3%. Insert Fig. 6, Table 4.]

### 5.4 Token Usage and Latency

[Avg steps; avg tokens per scenario; cost trade-offs.]

### 5.5 Discussion

[Strengths; limitations; comparison with related work.]

### 5.6 Improvement Opportunities

| Area | Current Issue | Improvement |
|------|---------------|-------------|
| Alert detection | noise_burst 0%; vibration_rms 50% | Tune threshold/slope for spikes; shorter duration for transient signals |
| Diagnosis | clogging 63.6%; sensor_override 58.3% | Add flow-pressure correlation rules; expand sensor_drift discriminants |
| RAG | Single embedding model | Batch indexing; hybrid keyword + semantic; tune similarity threshold |
| Evaluation | Synthetic only | More scenarios; cross-validation; real sensor data; ablation (rule-only vs. ReAct) |

[Expand each row with 1–2 sentences. Insert as Table 5.]

---

## Chapter 6. Conclusion

### 6.1 Summary

[Recap design, implementation, evaluation.]

### 6.2 Future Work

[Vision/VLM; multi-asset; noise_burst detection.]

---

## References

[Copy from REFERENCES.md; IEEE format; single-spaced.]

---

## Appendix A. Scenario JSON Examples

[healthy_baseline.json; bearing_wear_eval.json structure.]

---

## Appendix B. Rule Document Example

[Full bearing_wear.md content.]

---

## Appendix C. API Endpoints / Configuration

[Key .env vars; /scenario/load, /scenario/start; /api/review.]

---

## Appendix D. Key Code Snippets

[ReAct agent creation (create_diagnosis_agent); query_rules tool; index_diagnosis; add_text_to_vector_db.]

---

## How to Use This Skeleton

1. Open `dissertation-formatting-word-template.docx`.
2. Replace placeholder content with sections from this skeleton.
3. Apply TGS formatting: 12pt Times New Roman, 1" margins, double-spaced body.
4. Insert figures from `evaluation/report/` (e.g., 01_detection_by_signal.png, 02_diagnosis_accuracy.png).
5. Copy references from REFERENCES.md into the References section.
6. Update page numbers and Table of Contents after final edits.
