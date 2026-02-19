#!/bin/bash

# Stop all Agents and Simulator
# Usage: ./scripts/stop_all_agents.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PIDS_DIR="$PROJECT_ROOT/.pids"

echo "=========================================="
echo "Stopping All Agents and Simulator"
echo "=========================================="
echo ""

stop_service() {
    local name=$1
    local pid_file="$PIDS_DIR/$2"
    
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if ps -p "$pid" > /dev/null 2>&1; then
            echo "Stopping $name (PID: $pid)..."
            kill "$pid" 2>/dev/null || true
            sleep 1
            # If still running, force kill
            if ps -p "$pid" > /dev/null 2>&1; then
                kill -9 "$pid" 2>/dev/null || true
            fi
            echo "  ✓ $name stopped"
        else
            echo "  ⚠ $name (PID: $pid) is not running"
        fi
        rm -f "$pid_file"
    else
        echo "  ⚠ PID file for $name does not exist"
    fi
}

# Stop all services
stop_service "Simulator" "simulator.pid"
stop_service "Agent A" "agent_a.pid"
stop_service "Agent B" "agent_b.pid"
stop_service "Agent C" "agent_c.pid"
stop_service "Agent D" "agent_d.pid"

# Also try to stop by port (fallback method)
for port in 8001 8002 8003 8004 8005; do
    pid=$(lsof -ti :$port 2>/dev/null || true)
    if [ -n "$pid" ]; then
        echo "Stopping process on port $port (PID: $pid)..."
        kill "$pid" 2>/dev/null || true
    fi
done

echo ""
echo "=========================================="
echo "Stop Complete"
echo "=========================================="
