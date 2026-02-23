# AI Agent (LangChain/LangGraph) and Multimodal Extension

## 1. Current Architecture vs AI Agent

### Current (no LLM)
- **Agent A**: Rule/threshold detection, no LangChain/LangGraph, no LLM.
- **Agent B/C/D** (planned): Design is rule/template-based.

### To Use "AI Agent" with LangChain/LangGraph

**When and where:**

| Component | LLM + LangChain/LangGraph use case | API Key needed |
|-----------|------------------------------------|----------------|
| **Agent B (diagnosis)** | Feed alerts + recent telemetry summary to LLM for root cause, confidence, recommended_actions; or LangGraph multi-step reasoning. | ✅ `OPENAI_API_KEY` or `DEEPSEEK_API_KEY` |
| **Agent C (ticket)** | LLM generates ticket title/body from diagnosis; or summarization. | ✅ API Key |
| **Agent D (review)** | LLM summarizes review; or natural language → structured feedback. | ✅ API Key |
| **Orchestration** | LangGraph defines workflow (Monitor → Diagnosis → Ticket → Review) with branches, retries. | ✅ API Key |

**Conclusion:**
- Code currently has **no** LLM calls; `.env` keys are **not used yet**.
- To use keys at "AI agent" level, integrate LangChain/LangGraph in **Agent B (or C/D/orchestration)** and call the configured API.

---

## 2. API Key Configuration and Security

- Putting **real keys in `.env.example`** and committing to Git is a **leak risk**.
- Recommendation:
  - **`.env.example`**: Placeholders only, e.g. `OPENAI_API_KEY=`, `DEEPSEEK_API_KEY=`, no real keys.
  - **`.env`**: Local real keys; ensure `.env` is in `.gitignore` (already ignored in this project).
- In code: use `os.getenv("OPENAI_API_KEY")` or `settings.openai_api_key` (pydantic-settings).

---

## 3. 3D Simulation + VLM + Multimodal

### Current Simulator
- Only **1D time-series sensor data** (pressure, flow, temp, vibration, etc.); no images, no 3D scene.

### Is 3D + VLM feasible?
- **Yes, as an extension**:
  - 3D: Needs separate simulation (Unity/Unreal, PyBullet/MuJoCo, or digital twin) to render 3D.
  - VLM: Input is **image/video**. Approach: 3D sim periodically renders an image (or virtual camera), send to VLM; VLM describes scene (e.g. "smoke near pump", "pipe leak"); use description as **extra input** for Agent.
- Agent then has two inputs: **sensor values + vision description**, enabling multimodal decisions (e.g. sensors say pressure anomaly + VLM says "visible leak" → higher confidence).

### Does sensor-only count as "multimodal"?
- Generally **no**.
- Multimodal usually means **multiple input modalities**, e.g. **numeric/time-series + image/video + text**.
- Sensor time-series alone is "single-modal (sensor/time-series)".
- For multimodal, add at least one more modality, e.g.:
  - **Image** (3D render or camera) + VLM, or
  - **Text** (reports, tickets, logs) + LLM.

### Summary
- **Now**: Simulator is sensor-only, no 3D, no VLM; Agents do not use LangChain/LangGraph or your API keys.
- **For AI Agent**: Integrate LangChain/LangGraph in Agent B (or C/D), read keys from `.env`, call LLM.
- **For 3D + VLM multimodal**: Add 3D sim and render/screenshot, feed images to VLM, combine VLM output with sensor data for Agent input.
