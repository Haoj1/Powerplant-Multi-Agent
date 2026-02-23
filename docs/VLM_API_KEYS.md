# VLM API Keys Configuration

## Required API Key

Multimodal features need a Vision Language Model (VLM) API. **Choose one**:

### Option 1: Claude Vision (recommended)

**Why recommended:**
- ✅ Good quality, reasonable price
- ✅ Simple API
- ✅ Good understanding of industrial scenarios

**Required Key:**
- `ANTHROPIC_API_KEY` - Anthropic Claude API key

**How to get:**
1. Visit https://console.anthropic.com/
2. Register or log in
3. Create new key in Settings → API Keys
4. Copy key to `.env`

**Config:**
```bash
# In .env
VLM_PROVIDER=claude
ANTHROPIC_API_KEY=sk-ant-xxxxx  # your real key
```

---

### Option 2: OpenAI GPT-4V

**Required Key:**
- `OPENAI_API_KEY` - OpenAI API key

**How to get:**
1. Visit https://platform.openai.com/api-keys
2. Register or log in
3. Create new API key
4. Copy key to `.env`

**Config:**
```bash
# In .env
VLM_PROVIDER=openai
OPENAI_API_KEY=sk-proj-xxxxx  # your real key
```

---

## Install Dependencies

```bash
# Claude Vision
pip install anthropic

# Or OpenAI GPT-4V
pip install openai

# 3D visualization (required)
pip install pyvista
```

Or install all at once (already in requirements.txt):
```bash
pip install -r requirements.txt
```

---

## Usage

1. **Configure `.env`**:
   - Choose provider (claude or openai)
   - Add corresponding API key
   - Set `VISION_FREQUENCY_SEC=5` (vision every 5 seconds)

2. **Start Simulator**:
   - If API key is set, Simulator will:
     - Render 3D model every 5 seconds
     - Call VLM API to analyze image
     - Publish vision description to MQTT `vision/pump01`

3. **View Vision output**:
   ```bash
   mosquitto_sub -h localhost -p 1883 -t "vision/#" -v
   tail -f logs/vision.jsonl
   ```

---

## Cost Estimate

- **Claude Vision**: ~$0.003-0.015 per image (model dependent)
- **OpenAI GPT-4V**: ~$0.01-0.03 per image

At 5 seconds, ~720 images/hour, ~$2-20/hour depending on usage and model.

**Tip**: For testing, set `VISION_FREQUENCY_SEC=30` to reduce cost.

---

## Troubleshooting

**"VLM client not initialized (no API key provided)":**
- Check `.env` for `ANTHROPIC_API_KEY` or `OPENAI_API_KEY`
- Confirm `VLM_PROVIDER` is correct (claude or openai)

**"Could not initialize VLM client":**
- Check API key is valid
- Check network (API access required)
- Check library is installed (`anthropic` or `openai`)
