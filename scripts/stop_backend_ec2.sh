#!/bin/bash
#
# Stop all backend services (EC2 or local)
# Usage: ./scripts/stop_backend_ec2.sh
#

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
PIDS_DIR="$PROJECT_ROOT/.pids"

echo "=========================================="
echo "Stopping Backend Services"
echo "=========================================="

stop_one() {
    local name=$1
    local pid_file=$2
    if [ -f "$pid_file" ]; then
        local pid=$(cat "$pid_file")
        if kill -0 "$pid" 2>/dev/null; then
            echo "Stopping $name (PID $pid)..."
            kill "$pid" 2>/dev/null || true
            sleep 2
            kill -9 "$pid" 2>/dev/null || true
            echo "  OK"
        fi
        rm -f "$pid_file"
    fi
}

stop_one "Simulator"    "$PIDS_DIR/simulator.pid"
stop_one "Agent A"      "$PIDS_DIR/agent_a.pid"
stop_one "Agent B"      "$PIDS_DIR/agent_b.pid"
stop_one "Agent C"      "$PIDS_DIR/agent_c.pid"
stop_one "Agent D"      "$PIDS_DIR/agent_d.pid"

# Fallback: kill by port
for port in 8005 8004 8003 8002 8001; do
    pid=$(lsof -ti :$port 2>/dev/null || true)
    if [ -n "$pid" ]; then
        echo "Killing process on port $port (PID $pid)"
        kill $pid 2>/dev/null || kill -9 $pid 2>/dev/null || true
    fi
done

echo ""
echo "Done. (MQTT/Docker not stopped - run 'docker compose down' if needed)"
