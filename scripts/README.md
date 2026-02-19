# Startup Scripts Usage Guide

## Script List

### 1. Frontend Service Scripts
- **`start_frontend_services.sh`** - Start Agent D backend and Simulator (minimum services needed for frontend)
- **`stop_frontend_services.sh`** - Stop frontend services

### 2. Full System Scripts
- **`start_all_agents.sh`** - Start all Agents (A, B, C, D) and Simulator
- **`stop_all_agents.sh`** - Stop all Agents and Simulator

## Usage

### Start Frontend Services (Recommended for Frontend Development)

```bash
# Run from project root directory
./scripts/start_frontend_services.sh
```

This will start:
- Agent D (Review) - port 8005
- Simulator - port 8001

### Start All Agents (Full System)

```bash
# Run from project root directory
./scripts/start_all_agents.sh
```

This will start:
- Simulator - port 8001
- Agent A (Monitor) - port 8002
- Agent B (Diagnosis) - port 8003
- Agent C (Ticket) - port 8004
- Agent D (Review) - port 8005

### Stop Services

```bash
# Stop frontend services
./scripts/stop_frontend_services.sh

# Stop all services
./scripts/stop_all_agents.sh
```

## Features

- ✅ Automatic virtual environment check
- ✅ Automatic port conflict detection
- ✅ Background service execution (nohup)
- ✅ Automatic log file saving to `logs/` directory
- ✅ PID file management in `.pids/` directory for easy management
- ✅ Automatic health check after startup
- ✅ Graceful shutdown (SIGTERM first, SIGKILL if needed)

## Log Files

All service logs are saved in the `logs/` directory:
- `logs/simulator.log`
- `logs/agent_a.log`
- `logs/agent_b.log`
- `logs/agent_c.log`
- `logs/agent_d.log`

## PID Files

PID files are saved in the `.pids/` directory for stop scripts to identify processes:
- `.pids/simulator.pid`
- `.pids/agent_a.pid`
- `.pids/agent_b.pid`
- `.pids/agent_c.pid`
- `.pids/agent_d.pid`

## Notes

1. **Before First Use**: Ensure virtual environment is created
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Port Conflicts**: If a port is already in use, the script will prompt. You can choose to continue (will fail) or stop the process using the port first.

3. **MQTT Broker**: If Agents A/B/C/D require MQTT, ensure MQTT broker is started:
   ```bash
   docker-compose up -d mosquitto
   # or
   brew services start mosquitto
   ```

4. **View Logs**: After services start, you can view logs in real-time:
   ```bash
   tail -f logs/agent_d.log
   tail -f logs/simulator.log
   ```

5. **Manual Stop**: If scripts cannot stop services, you can manually:
   ```bash
   # View PID
   cat .pids/agent_d.pid
   
   # Stop process
   kill <PID>
   ```

## Example Workflows

### Frontend Development Workflow

```bash
# 1. Start frontend services
./scripts/start_frontend_services.sh

# 2. Start frontend in another terminal
cd agent-review/frontend
npm run dev

# 3. Access http://localhost:3000

# 4. Stop services after development
./scripts/stop_frontend_services.sh
```

### Full System Testing Workflow

```bash
# 1. Start MQTT broker
docker-compose up -d mosquitto

# 2. Start all Agents
./scripts/start_all_agents.sh

# 3. Load and run scenario
curl -X POST http://localhost:8001/scenario/load \
  -H "Content-Type: application/json" \
  -d "{\"scenario\": $(cat simulator-service/scenarios/test_alert_quick.json)}"
curl -X POST http://localhost:8001/scenario/start/pump01

# 4. Stop all services after testing
./scripts/stop_all_agents.sh
```
