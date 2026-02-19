#!/bin/bash

# Start all Agents and Simulator
# Usage: ./scripts/start_all_agents.sh

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
echo "Starting All Agents and Simulator"
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

# Check all ports
check_port 8001 "Simulator"
check_port 8002 "Agent A (Monitor)"
check_port 8003 "Agent B (Diagnosis)"
check_port 8004 "Agent C (Ticket)"
check_port 8005 "Agent D (Review)"

# Start service function
start_service() {
    local name=$1
    local script=$2
    local port=$3
    local log_file=$4
    local pid_file=$5
    
    echo "[Starting] $name (port $port)..."
    nohup python "$script" > "$log_file" 2>&1 &
    local pid=$!
    echo "$pid" > "$pid_file"
    echo "  ✓ $name started (PID: $pid)"
    echo "  Log: $log_file"
    sleep 1
}

# Start all services
start_service "Simulator" "simulator-service/main.py" 8001 \
    "$LOGS_DIR/simulator.log" "$PIDS_DIR/simulator.pid"

start_service "Agent A (Monitor)" "agent-monitor/main.py" 8002 \
    "$LOGS_DIR/agent_a.log" "$PIDS_DIR/agent_a.pid"

start_service "Agent B (Diagnosis)" "agent-diagnosis/main.py" 8003 \
    "$LOGS_DIR/agent_b.log" "$PIDS_DIR/agent_b.pid"

start_service "Agent C (Ticket)" "agent-ticket/main.py" 8004 \
    "$LOGS_DIR/agent_c.log" "$PIDS_DIR/agent_c.pid"

start_service "Agent D (Review)" "agent-review/main.py" 8005 \
    "$LOGS_DIR/agent_d.log" "$PIDS_DIR/agent_d.pid"

# Wait for services to start
echo ""
echo "Waiting for services to start..."
sleep 5

# Check service status
check_service() {
    local port=$1
    local service=$2
    local health_endpoint=$3
    
    if curl -s "http://localhost:$port/$health_endpoint" > /dev/null 2>&1; then
        echo "  ✓ $service is running"
        return 0
    else
        echo "  ⚠ $service may not have started properly, please check logs"
        return 1
    fi
}

echo ""
echo "Checking service status..."
check_service 8001 "Simulator" "status" || true
check_service 8002 "Agent A" "health" || true
check_service 8003 "Agent B" "health" || true
check_service 8004 "Agent C" "health" || true
check_service 8005 "Agent D" "health" || true

echo ""
echo "=========================================="
echo "Startup Complete!"
echo "=========================================="
echo ""
echo "Service Information:"
echo "  - Simulator:         http://localhost:8001"
echo "  - Agent A (Monitor): http://localhost:8002"
echo "  - Agent B (Diagnosis): http://localhost:8003"
echo "  - Agent C (Ticket):  http://localhost:8004"
echo "  - Agent D (Review):  http://localhost:8005"
echo ""
echo "Log Files:"
echo "  - Simulator: $LOGS_DIR/simulator.log"
echo "  - Agent A:   $LOGS_DIR/agent_a.log"
echo "  - Agent B:   $LOGS_DIR/agent_b.log"
echo "  - Agent C:   $LOGS_DIR/agent_c.log"
echo "  - Agent D:   $LOGS_DIR/agent_d.log"
echo ""
echo "To stop all services:"
echo "  ./scripts/stop_all_agents.sh"
echo ""
echo "PID files saved in: $PIDS_DIR/"
echo ""
