# Agent Monitor (Agent A)

Subscribes to telemetry from the Simulator, runs threshold-based anomaly detection, and publishes alerts to MQTT.

## Features

- **MQTT subscriber**: Subscribes to `telemetry/#`
- **Threshold detector**: Checks vibration_rms, bearing_temp_c, pressure_bar, motor_current_a, temp_c against configurable limits
- **Alert publisher**: Publishes `AlertEvent` to `alerts/{asset_id}` and appends to `logs/alerts.jsonl`
- **API**: `GET /health`, `GET /metrics`

## Run

From project root (with venv activated):

```bash
python agent-monitor/main.py
# or
./venv/bin/python3.13 agent-monitor/main.py
```

Service listens on `http://localhost:8002`.

## Test

1. Start MQTT broker (e.g. `docker-compose up -d mosquitto`)
2. Start Simulator: `python simulator-service/main.py`
3. Start Agent A: `python agent-monitor/main.py`
4. Load and start a scenario (e.g. bearing_wear or clogging) via Simulator API
5. Subscribe to alerts: `mosquitto_sub -h localhost -p 1883 -t "alerts/#" -v`
6. Check metrics: `curl http://localhost:8002/metrics`

## Thresholds

Default thresholds are in `detection/threshold_detector.py` (DEFAULT_THRESHOLDS). They can be overridden by passing a custom dict to `ThresholdDetector(thresholds=...)`.
