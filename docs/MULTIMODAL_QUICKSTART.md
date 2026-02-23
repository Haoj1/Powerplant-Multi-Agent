# Multimodal Feature Quick Start

## 1. Install Dependencies

```bash
pip install pyvista anthropic
# or
pip install -r requirements.txt
```

## 2. Configure API Key

Add to `.env` (**choose one**):

**Option A: Claude Vision (recommended)**
```bash
VLM_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-xxxxx  # your real key
```

**Option B: OpenAI GPT-4V**
```bash
VLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-xxxxx  # your real key
```

**Get API Keys:**
- Claude: https://console.anthropic.com/ → Settings → API Keys
- OpenAI: https://platform.openai.com/api-keys

## 3. Start Simulator

```bash
python simulator-service/main.py
```

If you see:
```
[Simulator] 3D renderer initialized
[Simulator] VLM client (Claude) initialized
```
Multimodal features are enabled.

## 4. View Vision Output

**Subscribe to vision messages:**
```bash
mosquitto_sub -h localhost -p 1883 -t "vision/#" -v
```

**Or check logs:**
```bash
tail -f logs/vision.jsonl
```

## 5. How It Works

1. Simulator renders 3D pump model every 5 seconds (configurable)
2. Colors update from sensor data (high vibration → red, high temp → orange, etc.)
3. Screenshot saved as PNG
4. VLM API analyzes image
5. VLM returns text description (e.g. "Pump body is red, indicating vibration anomaly")
6. Vision description published to MQTT `vision/pump01`

## Config Options

In `.env`:
- `VISION_FREQUENCY_SEC=5` - Generate vision every N seconds (default 5)
- `VLM_PROVIDER=claude` - VLM provider

## Cost

- Claude Vision: ~$0.003-0.015 per image
- OpenAI GPT-4V: ~$0.01-0.03 per image

At 5 seconds, ~720 images/hour. For testing, set to 30 seconds to reduce cost.
