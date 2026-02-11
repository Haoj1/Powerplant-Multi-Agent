# Quick Start Guide

## 1. Install Dependencies

```bash
pip install -r requirements.txt
```

Or install individually:
```bash
pip install fastapi uvicorn pydantic pydantic-settings paho-mqtt httpx python-dotenv numpy
```

## 2. Start MQTT Broker

```bash
docker-compose up -d mosquitto
```

## 3. Configure Environment

```bash
cp .env.example .env
# Edit .env if needed (defaults should work)
```

## 4. Run Simulator

From project root:

```bash
cd simulator-service
python3 main.py
```

Or use the run script:

```bash
python3 simulator-service/run.py
```

The service will start on `http://localhost:8001`

## 5. Test the Simulator

### Load a scenario:

```bash
curl -X POST http://localhost:8001/scenario/load \
  -H "Content-Type: application/json" \
  -d @simulator-service/scenarios/healthy_baseline.json
```

### Start simulation:

```bash
curl -X POST http://localhost:8001/scenario/start
```

### Check status:

```bash
curl http://localhost:8001/status
```

### Stop simulation:

```bash
curl -X POST http://localhost:8001/scenario/stop
```

## 6. Monitor Telemetry

Telemetry is published to MQTT topic: `telemetry/pump01`

Subscribe to see the data:

```bash
mosquitto_sub -h localhost -p 1883 -t "telemetry/#" -v
```

Telemetry is also logged to `logs/telemetry.jsonl`

## Example Scenarios

- `healthy_baseline.json` - Normal operation
- `bearing_wear_chronic.json` - Gradual bearing degradation
- `clogging_sudden.json` - Sudden pipe clogging
- `clogging_ramp.json` - Gradual pipe clogging
- `multi_fault.json` - Multiple faults

## Troubleshooting

### Import errors

Make sure you're running from the project root or use the run script:

```bash
# From project root
cd "/path/to/Multi-Agent Project"
python3 simulator-service/main.py
```

### MQTT connection errors

1. Check if Mosquitto is running: `docker ps | grep mosquitto`
2. Check `.env` file for MQTT settings
3. Test MQTT: `mosquitto_pub -h localhost -p 1883 -t test -m "hello"`
