# Agent B (Diagnosis) Architecture

## 1. Overview

Agent B is the **diagnosis agent**: it subscribes to Agent A's alerts, uses **LangChain ReAct** to autonomously call tools (query rules, telemetry, alerts), and produces a `DiagnosisReport` that is published to MQTT and written to SQLite.

Rules are decoupled from Agent B: **rules live in documents or DB**, and Agent B queries them dynamically via tools instead of hardcoding logic in code.

---

## 2. Data Flow

```
┌─────────────┐     alerts/#      ┌──────────────────────────────────────────────────────┐
│  Agent A    │ ───────────────▶  │  Agent B (ReAct)                                      │
│  (Monitor)  │                   │  ┌─────────────────────────────────────────────────┐ │
└─────────────┘                   │  │ 1. Receive AlertEvent                            │ │
                                  │  │ 2. Call tools: query_rules, query_telemetry, ... │ │
                                  │  │ 3. LLM reasoning → DiagnosisReport               │ │
                                  │  │ 4. Publish diagnosis/# + insert_diagnosis(alert_id)│ │
                                  │  └─────────────────────────────────────────────────┘ │
                                  │                          │                           │
                                  │     ┌─────────────────────┼─────────────────────┐    │
                                  │     ▼                     ▼                     ▼    │
                                  │  rules/               SQLite                 MQTT   │
                                  │  (docs or DB)      telemetry, alerts    diagnosis/#  │
                                  └──────────────────────────────────────────────────────┘
```

---

## 3. Rules Storage

### Option A: Documents (Markdown / YAML)

- **Path**: `agent-diagnosis/rules/` or `docs/rules/`
- **Format**: One file per fault type
- **Example** `rules/bearing_wear.md`:

```markdown
# Bearing Wear

## Symptoms
- Elevated vibration_rms
- Elevated bearing_temp_c
- May accompany minor rpm fluctuation

## Root Cause
bearing_wear

## Recommended Actions
- Check bearing lubrication
- Schedule shutdown for inspection

## Related Signals
vibration_rms, bearing_temp_c
```

- **Retrieval**: Simple glob + keyword match when rules are few; use embedding + vector store for semantic search when rules grow.

### Option B: Database

- **Table**: `diagnosis_rules` (create in init_db.py or separate migration)
- **Columns**: `id`, `symptom_keywords`, `root_cause`, `recommended_actions`, `conditions_json`, `created_at`
- **Retrieval**: Query by symptom/signal keywords or simple SQL conditions.

### Recommendation

- **Initial**: Use **Option A (documents)** for easy maintenance and version control.
- **Later**: Migrate to **Option B (DB)** or hybrid when rules grow and need fine-grained conditions.

---

## 4. Agent B Component Structure

```
agent-diagnosis/
├── main.py              # FastAPI + MQTT subscription + ReAct reasoning entry
├── mqtt/                # Subscribe alerts/#, publish diagnosis/#
│   ├── __init__.py
│   ├── subscriber.py    # Reuse or adapt from agent-monitor subscriber
│   └── publisher.py     # DiagnosisPublisher
├── agent/               # ReAct Agent
│   ├── __init__.py
│   ├── tools.py         # LangChain tools: query_rules, query_telemetry, query_alerts
│   ├── agent.py         # ReAct agent setup + inference
│   └── prompts.py       # System prompt (role, task, tool descriptions)
├── rules/               # Rule documents (Option A)
│   ├── bearing_wear.md
│   ├── clogging.md
│   ├── valve_stuck.md
│   └── ...
└── README.md
```

---

## 5. Tools Design

The ReAct agent has the following tools; the LLM decides when to call them:

| Tool | Purpose | Implementation |
|------|---------|----------------|
| `query_rules` | Query rules by symptom / signal / keywords | Read `rules/*.md` or query `diagnosis_rules` table |
| `query_telemetry` | Query telemetry for given asset and time range | `shared_lib.db.query_telemetry(asset_id, since_ts)` |
| `query_alerts` | Query recent alerts for given asset | `shared_lib.db.query_alerts(asset_id, limit)` |

### shared_lib.db Extensions

Add read-only query functions in `shared_lib/db.py`:

- `query_telemetry(asset_id: str, since_ts: str, limit: int = 100) -> List[dict]`
- `query_alerts(asset_id: str, limit: int = 20) -> List[dict]`
- `get_alert_by_id(alert_id: int) -> Optional[dict]` (if Agent A includes alert_id in payload)

---

## 6. ReAct Agent Flow

1. **Input**: Receive `AlertEvent` (ts, plant_id, asset_id, severity, alerts list)
2. **Context**: Add current alert summary to prompt as initial context
3. **Reasoning**: ReAct loop: Thought → Action (call tool) → Observation until Final Answer
4. **Output**: Parse LLM Final Answer into `DiagnosisReport` (root_cause, confidence, impact, recommended_actions, evidence)
5. **Publish**: MQTT `diagnosis/{asset_id}` + `shared_db.insert_diagnosis(..., alert_id=...)`

### alert_id Linking

- After inserting alerts, Agent A must include the **primary alert id** (e.g. first detail's id) in the MQTT payload.
- Agent B uses it to call `insert_diagnosis(..., alert_id=payload.alert_id)`.
- **Implementation**: Modify `insert_alert` to return `last_insert_rowid`; Agent A adds `alert_id` to the published payload.

---

## 7. Dependencies

- `langchain` / `langchain-core`: ReAct agent, tools
- `langchain-openai` or `langchain-anthropic`: LLM backend (DeepSeek works with OpenAI-compatible API)
- Existing: `paho-mqtt`, `fastapi`, `pydantic`, `shared_lib`

---

## 8. Configuration (.env)

```
# Agent B / LLM (reuse existing DeepSeek)
DEEPSEEK_API_KEY=...
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
# Or OpenAI/Claude
OPENAI_API_KEY=...
ANTHROPIC_API_KEY=...

# Optional: rules path (default agent-diagnosis/rules/)
DIAGNOSIS_RULES_PATH=agent-diagnosis/rules
```

---

## 9. Implementation Order

1. **Rule documents**: Create `agent-diagnosis/rules/`, add 3–5 fault rules (bearing_wear, clogging, valve_stuck, etc.)
2. **DB queries**: Add `query_telemetry`, `query_alerts` to `shared_lib/db.py`
3. **alert_id chain**: Modify Agent A `insert_alert` to return id; include it in MQTT payload
4. **Tools**: Implement `query_rules`, `query_telemetry`, `query_alerts`
5. **ReAct agent**: Set up agent + prompt with tools
6. **Agent B main**: MQTT subscribe to `alerts/#`, on alert → run agent → publish + write DB

---

## 10. Relationship to Existing System

| Component | Relation to Agent B |
|-----------|----------------------|
| **Simulator** | No direct interaction; Agent B reads telemetry from DB |
| **Agent A** | Producer: publishes `alerts/#`, includes `alert_id` in payload |
| **shared_lib** | Shared `config`, `models`, `db`, `utils` |
| **SQLite** | Read telemetry/alerts; write diagnosis |

---

## 11. Future Extensions

- **Vector retrieval**: Use embedding + Chroma/FAISS when rule documents grow
- **Vision**: Add `query_vision_image` tool to call VLM on 3D images
- **Multi-agent**: Pass `diagnosis_id` to Agent C (ticket) workflow
