# Simulator Service

Physical pump system simulator with fault injection capabilities.

## Features

- **Physical Models**: Based on academic literature
  - Pump model: Reeh et al. (2023) - Euler equation and affinity laws
  - Pipe system: Darcy-Weisbach equation for resistance
  - Bearing: IEEE PHM vibration and temperature models
  - Motor: Standard electrical power equations

- **Fault Injection**: Physical mechanisms for various fault types
  - Bearing wear (chronic degradation)
  - Clogging (step or ramp)
  - Valve stuck
  - Sensor drift/stuck
  - Noise burst

- **Reproducible Scenarios**: JSON-based scenario definitions with seed control

- **MQTT Integration**: Publishes telemetry to MQTT broker

## Installation

Install dependencies:

```bash
pip install -r ../requirements.txt
```

## Configuration

1. Copy `.env.example` to `.env` and configure MQTT settings
2. Modify `config/pump_config.yaml` for different pump parameters

## Usage

### Start the service

```bash
cd simulator-service
python main.py
```

The service will start on `http://localhost:8001`

### API Endpoints

- `GET /health` - Health check
- `GET /status` - Get simulation status
- `POST /scenario/load` - Load a scenario JSON
- `POST /scenario/start` - Start simulation
- `POST /scenario/stop` - Stop simulation
- `POST /scenario/reset` - Reset to beginning

### Example: Load and run a scenario

```python
import requests
import json

# Load scenario
with open("scenarios/healthy_baseline.json") as f:
    scenario = json.load(f)

# Load scenario
response = requests.post(
    "http://localhost:8001/scenario/load",
    json={"scenario": scenario}
)
print(response.json())

# Start simulation
response = requests.post("http://localhost:8001/scenario/start")
print(response.json())

# Check status
response = requests.get("http://localhost:8001/status")
print(response.json())
```

### Example Scenarios

- `healthy_baseline.json` - Normal operation, no faults
- `bearing_wear_chronic.json` - Gradual bearing degradation
- `clogging_sudden.json` - Sudden pipe clogging
- `clogging_ramp.json` - Gradual pipe clogging
- `multi_fault.json` - Multiple simultaneous faults

## Telemetry Output

Telemetry is published to MQTT topic: `telemetry/{asset_id}` (default: `telemetry/pump01`)

Telemetry format follows `shared-lib/models.py` Telemetry schema:
- `ts`: Timestamp
- `plant_id`: Plant identifier
- `asset_id`: Asset identifier
- `signals`: Sensor readings (pressure, flow, temperature, vibration, etc.)
- `truth`: Ground truth (fault type and severity)

Telemetry is also logged to `logs/telemetry.jsonl` for evaluation.

## References (English literature)

- Reeh, N., Manthei, G., & Klar, P. J. (2023). Physical Modelling of the Set of Performance Curves for Radial Centrifugal Pumps. *Applied System Innovation*, 6(6), 111.
- Darcy–Weisbach equation (standard fluid mechanics, e.g. White, F.M. *Fluid Mechanics*).
- IEEE PHM: Vibration-based bearing health indicators.
- ISO 20816: Mechanical vibration – evaluation of machine vibration.

The 3D visualization (`visualization/pump_renderer.py`) uses the same physical parameters (pipe diameter/length, nominal flow/head) to scale geometry so proportions are consistent with these models.
