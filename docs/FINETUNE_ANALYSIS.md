# Feasibility and Necessity of Fine-tuning OpenAI API for "Rules + Sensor Data" Analysis

## 1. How Rules and Sensor Data Are Used in This Project

- **Rules**: Five Markdown files in `agent-diagnosis/rules/` (bearing_wear, clogging, valve_stuck, sensor_drift, unknown) describing symptoms, root cause, recommended actions, and related signals. Agent B uses **query_rules** (keyword/vector retrieval) to fetch rule content.
- **Sensor data**: Agent A uses **ThresholdDetector** for threshold detection; Agent B uses **query_telemetry** to fetch recent time series (pressure_bar, flow_m3h, vibration_rms, bearing_temp_c, etc.) and passes it to the LLM for root cause analysis.
- **LLM role**: The diagnosis agent uses **ReAct + tools** (query_rules, query_telemetry, query_alerts) with a system prompt that defines root_cause enums and JSON output format; currently uses **gpt-4o-mini or DeepSeek** without fine-tuning.

In other words: **rules and sensor data are injected at inference time via prompt + tools; the model itself has not been trained specifically on "rules + sensors."**

---

## 2. What Fine-tuning Would Solve (Necessity)

Fine-tuning a model "specialized in rules and sensor data" would make it **more stable and better aligned with your domain's rules and signal semantics** for the same inputs.

| Dimension | High necessity | Your current situation |
|-----------|----------------|------------------------|
| **Output format** | Frequent JSON missing fields, wrong enums | `_parse_final_answer` provides fallback; fine-tuning helps if parsing often fails |
| **Root cause vs rules** | Many rules/signals, base model confuses them | Only 5 rule types, fixed signal names in prompt; base + prompt usually sufficient |
| **Sensor pattern understanding** | Need to detect trends, multi-signal patterns | Mainly "alert summary + rule snippet + telemetry text"; patterns relatively simple |
| **Domain terms** | Heavy use of plant-specific terms, fault codes | root_cause already constrained by enums in prompt |
| **Latency/cost** | Want shorter prompts, fewer tool calls | Fine-tuning can enable single-call diagnosis with fewer ReAct steps |
| **Labeled data** | Large labeled set of (alert + rules + sensors) → diagnosis | No ready dataset; can come from Agent D approve/reject or historical tickets |

**Conclusion (necessity):**

- **Short term**: With few rules, fixed signal set, and RAG + tools + clear prompt, **improve prompt + retrieval + evaluation first**; fine-tuning is often not needed yet.
- **Consider fine-tuning when**:
  - Production diagnosis often has wrong root_cause enums or evidence misaligned with rules; or
  - You want a lightweight "single call, few tools" diagnosis API; or
  - You have or can produce **high-quality (alert, rules_snippet, telemetry_snippet) → (root_cause, actions, evidence)** labels and want to bake that into the model.

---

## 3. Technical Feasibility

### 3.1 OpenAI Capabilities

- **Fine-tunable models**: Including `gpt-4o-mini`, via OpenAI Fine-tuning API.
- **Data format**: JSONL, each line a chat `messages` (system / user / assistant).
- **Data volume**: Official examples show effect with tens of samples; for "rules + sensors → structured diagnosis" you should aim for **hundreds** of high-quality samples.
- **Length**: Each sample has a token limit (e.g. 4k); keep rule snippet + sensor summary within a reasonable length.

Fit for your scenario:
- Input = alert summary + retrieved rule snippet + telemetry text;
- Output = fixed JSON (root_cause, confidence, impact, recommended_actions, evidence).

This "text input + structured output" pattern is well suited for **supervised fine-tuning**.

### 3.2 Where Training Data Comes From

| Source | Feasibility | Notes |
|--------|-------------|-------|
| **Agent D approvals** | High | Human approve = acceptance of diagnosis; extract (alert, diagnosis_id) from DB, use diagnosis as "correct output", reconstruct rules/telemetry for input. Filter out rejected or edited cases. |
| **Historical diagnosis + spot checks** | Medium | Use existing reports if spot-checked by ops; prefer high-confidence or human-corrected. |
| **Simulation + known root cause** | High | Simulator knows injected fault type; batch-generate (alert, rules, telemetry) → (root_cause, ...) as synthetic data; keep distribution close to real. |
| **Pure synthetic** | Medium | Generate with current model or rule templates, then validate; quality depends on validation. |

Your project has **simulator-service** and fault injection; best approach is **"simulation + known root_cause"** for automatic labeling, supplemented by Agent D approval data for real distribution.

### 3.3 Engineering Considerations

- **Rule/signal changes**: Fine-tuned model will be tied to the rules/signals at training time; either **periodically retrain** with new rules/samples or use a hybrid (new rules via RAG+prompt, old logic via fine-tuned model).
- **Relation to ReAct**:
  - Option A: Fine-tune a "final step only" model: input = (alert + rules + telemetry) already assembled by tools; output = final JSON. ReAct only calls tools and assembles context.
  - Option B: Fine-tune a "few-step ReAct" model that better chooses tools and interprets rules/sensors.
  Option A is easier to build data for and evaluate; recommend starting with A.
- **Cost**: Training billed by token; inference cost for fine-tuned model is similar to base. Start with a small dataset (hundreds of samples) for a POC.

---

## 4. Recommended Path (For This Project)

1. **Baseline evaluation (no fine-tuning)**  
   - Run existing ReAct + tools on **simulation scenarios** or **real alerts over a period**.  
   - Measure: root_cause accuracy, JSON parse success rate, agreement with approval decisions.  
   - If baseline is good, iterate on **prompt / retrieval / tools** before fine-tuning.

2. **If fine-tuning is needed**  
   - **Data**: Use simulation to generate "(alert + rules + telemetry) → standard JSON" JSONL; add samples from Agent D approvals where root_cause was not changed.  
   - **Task**: Start with "single turn: input = assembled context, output = diagnosis JSON" (Option A above), integrated with existing ReAct.  
   - **Evaluation**: Hold out some simulation cases and human-labeled cases; measure root_cause accuracy, evidence vs rules consistency, JSON parse success.

3. **Long term**  
   - If rules/sensors will expand often, treat the fine-tuned model as "high-performance version for a fixed rule/signal set"; new rules/signals stay on RAG + general model or require new training data.

---

## 5. Summary

| Question | Answer |
|----------|--------|
| **Necessary?** | With few rules and fixed signals, **not urgent**; consider if diagnosis quality is poor, or you want fewer tools/single-call output, or you have/can produce high-quality labels. |
| **Feasible?** | **Yes**. OpenAI supports fine-tuning gpt-4o-mini; data can come from simulation (known root_cause) + Agent D approvals; recommend "context → diagnosis JSON" single-step model first, then integrate with ReAct tools. |
| **Next steps** | Run baseline evaluation and data audit (simulation + approved sample count and quality); then decide on fine-tuning. If yes, build a small JSONL dataset from simulation + approvals for a POC. |
