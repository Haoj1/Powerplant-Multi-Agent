# Multi-Agent Powerplant Monitoring System

A multi-agent system for real-time monitoring, anomaly detection, root cause analysis, and automated ticket creation for powerplant assets.

## Architecture

- **Simulator Service**: Generates telemetry data and publishes to MQTT
- **Agent Monitor (Agent A)**: Subscribes to telemetry, detects anomalies, publishes alerts
- **Agent Diagnosis (Agent B)**: Subscribes to alerts, performs root cause analysis, publishes diagnoses
- **Agent Ticket (Agent C)**: Subscribes to diagnoses, creates tickets (GitHub Issues or local)
- **Agent Review (Agent D)**: Provides human review interface and feedback loop

## Project Structure

```
.
├── simulator-service/    # Telemetry generator
├── agent-monitor/        # Anomaly detection agent
├── agent-diagnosis/      # Root cause analysis agent
├── agent-ticket/         # Ticket creation agent
├── agent-review/         # Human review agent
├── shared_lib/           # Shared models, config, utilities
├── logs/                 # JSONL log files
├── mosquitto/            # MQTT broker config
├── docker-compose.yml    # Docker services
├── requirements.txt      # Python dependencies
└── .env.example          # Environment variables template
```

## Quick Start

### Prerequisites

- Python 3.11+
- Docker and Docker Compose
- (Optional) GitHub token for ticket creation

### Setup

1. **Clone and install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

2. **Configure environment:**
   ```bash
   cp .env.example .env
   # Edit .env with your settings
   ```

3. **Start MQTT broker:**
   ```bash
   docker-compose up -d mosquitto
   ```

4. **Start services** (in separate terminals):
   ```bash
   # Terminal 1: Simulator
   cd simulator-service && python main.py
   
   # Terminal 2: Agent Monitor
   cd agent-monitor && python main.py
   
   # Terminal 3: Agent Diagnosis
   cd agent-diagnosis && python main.py
   
   # Terminal 4: Agent Ticket
   cd agent-ticket && python main.py
   
   # Terminal 5: Agent Review
   cd agent-review && python main.py
   ```

## Development Status

- ✅ Phase 0: Project skeleton and shared library
- ⏳ Phase 1: MQTT infrastructure & minimal simulator
- ⏳ Phase 2: Agent A (monitoring & anomaly detection)
- ⏳ Phase 3: Simulator fault scenarios
- ⏳ Phase 4: Agent B (diagnosis rules engine)
- ⏳ Phase 5: Agent C (ticket creation)
- ⏳ Phase 6: Agent D (human review)
- ⏳ Phase 7: Evaluation & metrics
- ⏳ Phase 8: Demo polish

See `TODO.md` for detailed task breakdown.

## API Endpoints

Each service exposes a `/health` endpoint for health checks.

- Simulator: `http://localhost:8001`
- Agent Monitor: `http://localhost:8002`
- Agent Diagnosis: `http://localhost:8003`
- Agent Ticket: `http://localhost:8004`
- Agent Review: `http://localhost:8005`

## License

MIT
