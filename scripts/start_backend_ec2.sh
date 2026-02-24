#!/bin/bash
#
# Start all backend services for AWS EC2 deployment
# Usage: ./scripts/start_backend_ec2.sh
#
# Prerequisites on EC2:
#   - Docker (for MQTT)
#   - Python 3.11+ with venv
#   - pip install -r requirements.txt
#
# Access: http://<EC2_PUBLIC_IP>:8005 (Agent D API + frontend if built)
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Check virtual environment
if [ ! -d "venv" ]; then
    echo "Error: venv/ not found. Create with: python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

source venv/bin/activate

LOGS_DIR="${PROJECT_ROOT}/logs"
PIDS_DIR="${PROJECT_ROOT}/.pids"
mkdir -p "$LOGS_DIR" "$PIDS_DIR"

echo "=========================================="
echo "Starting Backend for EC2"
echo "=========================================="

# 1. Start MQTT (Docker)
echo ""
echo "[1/6] Starting MQTT broker (Mosquitto)..."
if docker compose ps 2>/dev/null | grep -q mosquitto; then
    echo "  MQTT already running"
else
    docker compose up -d mosquitto 2>/dev/null || docker-compose up -d mosquitto 2>/dev/null || {
        echo "  Warning: Could not start MQTT. Ensure Docker is running."
        echo "  Fallback: brew services start mosquitto (macOS) or install Mosquitto"
    }
fi
sleep 2

# 2. Simulator (8001)
echo ""
echo "[2/6] Starting Simulator (port 8001)..."
nohup python simulator-service/main.py >> "$LOGS_DIR/simulator.log" 2>&1 &
echo $! > "$PIDS_DIR/simulator.pid"
echo "  PID: $(cat $PIDS_DIR/simulator.pid)"
sleep 1

# 3. Agent A - Monitor (8002)
echo ""
echo "[3/6] Starting Agent A - Monitor (port 8002)..."
nohup python agent-monitor/main.py >> "$LOGS_DIR/agent_a.log" 2>&1 &
echo $! > "$PIDS_DIR/agent_a.pid"
echo "  PID: $(cat $PIDS_DIR/agent_a.pid)"
sleep 1

# 4. Agent B - Diagnosis (8003)
echo ""
echo "[4/6] Starting Agent B - Diagnosis (port 8003)..."
nohup python agent-diagnosis/main.py >> "$LOGS_DIR/agent_b.log" 2>&1 &
echo $! > "$PIDS_DIR/agent_b.pid"
echo "  PID: $(cat $PIDS_DIR/agent_b.pid)"
sleep 1

# 5. Agent C - Ticket (8004)
echo ""
echo "[5/6] Starting Agent C - Ticket (port 8004)..."
nohup python agent-ticket/main.py >> "$LOGS_DIR/agent_c.log" 2>&1 &
echo $! > "$PIDS_DIR/agent_c.pid"
echo "  PID: $(cat $PIDS_DIR/agent_c.pid)"
sleep 1

# 6. Agent D - Review (8005)
echo ""
echo "[6/6] Starting Agent D - Review (port 8005)..."
nohup python agent-review/main.py >> "$LOGS_DIR/agent_d.log" 2>&1 &
echo $! > "$PIDS_DIR/agent_d.pid"
echo "  PID: $(cat $PIDS_DIR/agent_d.pid)"

echo ""
echo "Waiting for services..."
sleep 5

# Health check
echo ""
echo "Health check:"
curl -s -o /dev/null -w "" http://127.0.0.1:8001/status 2>/dev/null && echo "  OK Simulator (8001)" || echo "  -- Simulator (8001)"
curl -s -o /dev/null -w "" http://127.0.0.1:8002/health 2>/dev/null && echo "  OK Agent A (8002)" || echo "  -- Agent A (8002)"
curl -s -o /dev/null -w "" http://127.0.0.1:8003/health 2>/dev/null && echo "  OK Agent B (8003)" || echo "  -- Agent B (8003)"
curl -s -o /dev/null -w "" http://127.0.0.1:8004/health 2>/dev/null && echo "  OK Agent C (8004)" || echo "  -- Agent C (8004)"
curl -s -o /dev/null -w "" http://127.0.0.1:8005/health 2>/dev/null && echo "  OK Agent D (8005)" || echo "  -- Agent D (8005)"

echo ""
echo "=========================================="
echo "Backend started!"
echo "=========================================="
echo ""
echo "Access from browser:"
echo "  http://<EC2_PUBLIC_IP>:8005"
echo ""
echo "To serve frontend: cd agent-review/frontend && npm run build"
echo ""
echo "API endpoints:"
echo "  - Agent D (API):  http://<EC2_PUBLIC_IP>:8005/api/..."
echo "  - Simulator:      http://<EC2_PUBLIC_IP>:8001"
echo ""
echo "EC2 Security Group: allow inbound TCP 8001, 8005 (and 1883 if MQTT from outside)"
echo ""
echo "To stop: ./scripts/stop_backend_ec2.sh"
echo ""
