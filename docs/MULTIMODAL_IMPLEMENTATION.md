# Multimodal Implementation (Image + VLM)

## Option Comparison (simple to complex)

| Option | Complexity | Time | Effect | Recommendation |
|--------|------------|------|--------|----------------|
| **A: 2D dashboard screenshot** | ⭐ Very low | 1-2 hours | Simple but effective | ⭐⭐⭐⭐⭐ |
| **B: 3D simplified model (PyVista)** | ⭐⭐ Low | 2-3 hours | More realistic | ⭐⭐⭐⭐ |
| **C: Unity/Blender render** | ⭐⭐⭐⭐⭐ Very high | Days | Most realistic | ⭐⭐ |

---

## Option A: 2D Dashboard + VLM (recommended, fastest)

### Approach
- Use **matplotlib** or **plotly** for a **real-time dashboard** (pressure, flow, temp, vibration, etc.)
- Screenshot every second, save as PNG
- Send image to **VLM API** (OpenAI GPT-4V / Claude Vision / DeepSeek-VL)
- VLM describes the view (e.g. "Pressure gauge 12.5 bar, vibration in normal range, temp slightly high")
- Use VLM description as **extra input** for Agent B (diagnosis)

### Stack
- **Visualization**: `matplotlib` (already present) or `plotly`
- **Screenshot**: `matplotlib` `savefig()` or `PIL`
- **VLM API**: `openai`, `anthropic`, or DeepSeek-VL API

### Steps
1. Add **visualization module** in Simulator: subscribe telemetry, draw dashboard, screenshot
2. Create **VLM client**: read image, call VLM API, return text description
3. **Publish** VLM description to MQTT (e.g. `vision/pump01`)
4. Agent B subscribes `vision/*`, combines vision + alerts for diagnosis

### Code size
- Visualization: ~100-150 lines
- VLM client: ~50-80 lines
- Simulator integration: ~30 lines
- **Total: ~200-260 lines**

---

## Option B: 3D Simplified Model (PyVista)

### Approach
- Use **PyVista** for a **simplified 3D pump** (cylinder for body, tubes for pipes, spheres for bearings)
- Update color/size from sensor data (e.g. high vibration → red, high temp → orange)
- Render screenshot, send to VLM
- VLM describes 3D scene (e.g. "Pump body red, vibration anomaly; bearing temp normal")

### Stack
- **3D render**: `pyvista`
- **VLM API**: same as above

### Steps
1. Create 3D model (PyVista primitives)
2. Update model state from telemetry (color, position)
3. Render screenshot
4. Call VLM, publish description

### Code size
- 3D model: ~100 lines
- Render loop: ~80 lines
- VLM integration: ~50 lines
- **Total: ~230 lines**

---

## Option C: Unity/Blender (not recommended)

Requires learning Unity/Blender; high time cost, not suitable for quick implementation.

---

## Recommendation: Option A (2D dashboard)

**Reasons:**
- ✅ Fastest (1-2 hours)
- ✅ Few dependencies (matplotlib already present, only VLM lib needed)
- ✅ Good enough (VLM understands dashboards well)
- ✅ Easy to debug (visual)

---

## Implementation Architecture

```
simulator-service/
├── visualization/
│   ├── dashboard.py          # Draw dashboard, screenshot
│   └── renderer.py           # Render loop
├── vlm/
│   ├── client.py             # VLM API client
│   └── prompts.py            # VLM prompt templates
└── main.py                   # Integrate visualization + VLM

agent-diagnosis/
└── main.py                   # Subscribe alerts + vision, multimodal diagnosis
```

### Data flow

```
Simulator → Telemetry (MQTT)
         ↓
    Dashboard → Screenshot (PNG)
         ↓
    VLM API → Vision Description (MQTT vision/pump01)
         ↓
Agent B → Alerts + Vision → Multi-modal Diagnosis
```

---

## VLM API Choice

| API | Library | Cost | Quality | Recommendation |
|-----|---------|------|---------|-----------------|
| **OpenAI GPT-4V** | `openai` | Higher | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **Claude Vision** | `anthropic` | Medium | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **DeepSeek-VL** | API | Low | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

**Recommended: Claude Vision** (good quality, simple API, reasonable price)

---

## Quick Start (Option A)

Implementation includes:
1. **Visualization module**: matplotlib dashboard + auto screenshot
2. **VLM client**: Claude Vision API (or OpenAI/DeepSeek)
3. **Integration**: Simulator publishes vision to MQTT
4. **Agent B extension**: Subscribe vision, multimodal diagnosis

**Estimated time**: 1-2 hours for MVP
