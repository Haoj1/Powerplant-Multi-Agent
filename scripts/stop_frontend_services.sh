#!/bin/bash

# Stop frontend services (Agent D and Simulator)
# Usage: ./scripts/stop_frontend_services.sh

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

PIDS_DIR="$PROJECT_ROOT/.pids"

echo "=========================================="
echo "Stopping Frontend Services"
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

# Stop services
stop_service "Agent D" "agent_d.pid"
stop_service "Simulator" "simulator.pid"

# Also try to stop by port (fallback method)
for port in 8005 8001; do
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
