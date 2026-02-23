# RAG Implementation Summary

## ✅ Implemented Features

### 1. Vector Indexing Module (`shared_lib/vector_indexing.py`)

Provides indexing functions for 7 data types:
- `index_diagnosis()` - Diagnosis index
- `index_alert()` - Alert index
- `index_feedback()` - Feedback index
- `index_ticket()` - Ticket index
- `index_chat_message()` - Chat message index
- `index_vision_analysis()` - Vision analysis index
- `index_rules()` - Rules file index

All functions use the `@_safe_index` decorator to ensure indexing failures do not affect the main flow.

---

### 2. Agent A (Monitor) - Alert Indexing ✅

**Location:** `agent-monitor/main.py`

Automatically indexes alerts after creation:

```python
# After alert is written to DB
if primary_alert_id and index_alert:
    alert_data = {
        "asset_id": alert.asset_id,
        "plant_id": alert.plant_id,
        "severity": alert.severity,
        "signal": alert.alerts[0].signal,
        "score": alert.alerts[0].score,
        "method": alert.alerts[0].method,
        "evidence": alert.alerts[0].evidence,
    }
    index_alert(primary_alert_id, alert_data)
```

---

### 3. Agent B (Diagnosis) - Diagnosis Index + Rules Index ✅

**Location:** `agent-diagnosis/main.py`

#### 3.1 Diagnosis Index
Automatically indexes after diagnosis creation:

```python
# After diagnosis is written to DB
if diagnosis_id and index_diagnosis:
    diagnosis_data = {
        "asset_id": report.asset_id,
        "plant_id": report.plant_id,
        "root_cause": report.root_cause,
        "confidence": report.confidence,
        "impact": report.impact,
        "recommended_actions": report.recommended_actions,
        "evidence": report.evidence,
    }
    index_diagnosis(diagnosis_id, diagnosis_data)
```

#### 3.2 Rules Index
Automatically indexes all rule files when Agent B starts:

```python
# In startup_event()
if index_rules:
    count = index_rules()
    print(f"[Agent B] Indexed {count} rules to vector DB")
```

---

### 4. Agent D (Review) - Feedback Index + Chat Index ✅

**Location:** `agent-review/main.py`

#### 4.1 Feedback Index
Indexes on approve/reject:

```python
# Approve
if review_req and index_feedback:
    index_feedback(feedback_id, {
        "review_decision": "approved",
        "final_root_cause": diagnosis.get("root_cause"),
        "notes": b.notes,
        ...
    })

# Reject
if review_req and index_feedback:
    index_feedback(feedback_id, {
        "review_decision": "rejected",
        "notes": b.notes,
        ...
    })
```

#### 4.2 Chat Message Index
Indexes after chat completion (assistant messages only, content length > 100):

```python
# In chat_ask(), after answer completes
if index_chat_message:
    index_chat_message(msg_id, {
        "role": "assistant",
        "content": answer,
        "session_id": session_id_out,
        "tools_used": tools_used,
        "context": question,
    })
```

---

### 5. Agent D ReAct Tools - RAG Query Tools ✅

**Location:** `agent-review/agent/tools.py`

5 new RAG query tools:

#### 5.1 `query_similar_diagnoses(query, limit=5)`
Search for similar historical diagnosis cases

**Example:**
```
query_similar_diagnoses("bearing wear vibration high")
```

**Returns:**
```json
[
  {
    "diagnosis_id": 123,
    "similarity": "87.5%",
    "similarity_score": 0.875,
    "root_cause": "bearing_wear",
    "asset_id": "pump01",
    "confidence": 0.85,
    "text_preview": "Root cause: bearing wear..."
  }
]
```

#### 5.2 `query_similar_alerts(query, limit=5)`
Search for similar historical alerts

**Example:**
```
query_similar_alerts("vibration sensor anomaly")
```

#### 5.3 `query_similar_feedback(query, limit=5)`
Search for similar historical feedback/review decisions

**Example:**
```
query_similar_feedback("approved bearing replacement")
```

#### 5.4 `query_similar_rules(query, limit=5)`
Semantic search for related rules (smarter than keyword search)

**Example:**
```
query_similar_rules("bearing temperature vibration correlation")
```

#### 5.5 `query_similar_chat(query, limit=3)`
Search for similar historical conversations

**Example:**
```
query_similar_chat("how to diagnose bearing wear")
```

---

## 📋 Usage Flow

### Automatic Indexing Flow

1. **Agent A** detects alert → automatically indexes alert
2. **Agent B** creates diagnosis → automatically indexes diagnosis
3. **Agent B** on startup → indexes all rule files
4. **Agent D** approve/reject → indexes feedback
5. **Agent D** chat answer completes → indexes valuable conversations

### RAG Query Flow

In Agent D's chat, you can use RAG tools:

```
User: "Find similar bearing wear cases"

Agent D calls: query_similar_diagnoses("bearing wear")
Returns: List of similar diagnoses (diagnosis_id, similarity, root_cause, etc.)

Agent D: "Found 5 similar cases, diagnosis_id=123 has highest similarity (87.5%)..."
```

---

## 🔧 Configuration Requirements

### Required Dependencies

```bash
pip install sqlite-vec sentence-transformers
```

Already in `requirements.txt`:
- `sqlite-vec>=0.1.6`
- `sentence-transformers>=2.2.0`

### Optional Feature

If dependencies are not installed, RAG is automatically disabled without affecting main flow:
- Index functions fail silently
- RAG query tools return "RAG not available" message

---

## 📊 Data Flow Diagram

```
Agent A (alerts)
    ↓ index_alert()
vec_memory (vector store)

Agent B (diagnosis)
    ↓ index_diagnosis()
    ↓ index_rules() [on startup]
vec_memory (vector store)

Agent D (review)
    ↓ index_feedback() [approve/reject]
    ↓ index_chat_message() [chat complete]
vec_memory (vector store)

Agent D (query)
    ↓ query_similar_*() [ReAct tools]
    ← returns similar results
```

---

## 🎯 Next Steps

1. **Ticket index**: Add `index_ticket()` after `insert_ticket()` call
2. **Vision index**: Add `index_vision_analysis()` after vision analysis creation
3. **Frontend integration**: Show "similar cases" in UI
4. **Performance**: Batch indexing, async indexing

---

## 📝 Notes

1. **Auto-create table**: First index call auto-creates `vec_memory` virtual table
2. **Failure tolerance**: All index operations have exception handling; failures do not affect main flow
3. **Optional feature**: If RAG deps are not installed, feature is disabled
4. **Dimension match**: Default uses `all-MiniLM-L6-v2` (384 dim); if changing model, ensure dimension consistency
