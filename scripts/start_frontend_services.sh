#!/bin/bash

# Start frontend services: Agent D backend and Simulator
# Usage: ./scripts/start_frontend_services.sh

set -e

# Get project root directory (parent of script directory)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$PROJECT_ROOT"

# Check virtual environment
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment venv/ not found"
    echo "Please create virtual environment first: python3 -m venv venv"
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Create logs directory
LOGS_DIR="$PROJECT_ROOT/logs"
mkdir -p "$LOGS_DIR"

# PID file directory
PIDS_DIR="$PROJECT_ROOT/.pids"
mkdir -p "$PIDS_DIR"

echo "=========================================="
echo "Starting Frontend Services (Agent D + Simulator)"
echo "=========================================="
echo ""

# Check if port is already in use
check_port() {
    local port=$1
    local service=$2
    if lsof -Pi :$port -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "Warning: Port $port ($service) is already in use"
        read -p "Continue anyway? (y/n) " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi
    fi
}

check_port 8005 "Agent D"
check_port 8001 "Simulator"

# Start Agent D (port 8005)
echo "[1/2] Starting Agent D (Review) - port 8005..."
nohup python agent-review/main.py > "$LOGS_DIR/agent_d.log" 2>&1 &
AGENT_D_PID=$!
echo "$AGENT_D_PID" > "$PIDS_DIR/agent_d.pid"
echo "  ✓ Agent D started (PID: $AGENT_D_PID)"
echo "  Log: $LOGS_DIR/agent_d.log"

# Wait a bit to ensure startup
sleep 2

# Start Simulator (port 8001)
echo "[2/2] Starting Simulator - port 8001..."
nohup python simulator-service/main.py > "$LOGS_DIR/simulator.log" 2>&1 &
SIMULATOR_PID=$!
echo "$SIMULATOR_PID" > "$PIDS_DIR/simulator.pid"
echo "  ✓ Simulator started (PID: $SIMULATOR_PID)"
echo "  Log: $LOGS_DIR/simulator.log"

# Wait for services to start
echo ""
echo "Waiting for services to start..."
sleep 3

# Check if services are running properly
check_service() {
    local port=$1
    local service=$2
    if curl -s "http://localhost:$port/health" > /dev/null 2>&1 || \
       curl -s "http://localhost:$port/status" > /dev/null 2>&1; then
        echo "  ✓ $service is running"
        return 0
    else
        echo "  ✗ $service may not have started properly, please check logs"
        return 1
    fi
}

echo ""
echo "Checking service status..."
check_service 8005 "Agent D" || true
check_service 8001 "Simulator" || true

echo ""
echo "=========================================="
echo "Startup Complete!"
echo "=========================================="
echo ""
echo "Service Information:"
echo "  - Agent D (Review):  http://localhost:8005"
echo "  - Simulator:         http://localhost:8001"
echo ""
echo "Log Files:"
echo "  - Agent D:  $LOGS_DIR/agent_d.log"
echo "  - Simulator: $LOGS_DIR/simulator.log"
echo ""
echo "To stop services:"
echo "  ./scripts/stop_frontend_services.sh"
echo "  Or manually: kill $AGENT_D_PID $SIMULATOR_PID"
echo ""
echo "PID files saved in: $PIDS_DIR/"
echo ""
