#!/bin/bash
# Stop Discord Dashboard
cd "$(dirname "$0")/.."
PID_FILE="$(pwd)/data/dashboard.pid"

if [ ! -f "$PID_FILE" ]; then
    echo "No PID file found. Dashboard may not be running."
    exit 0
fi

PID=$(cat "$PID_FILE")
if kill -0 "$PID" 2>/dev/null; then
    echo "Stopping dashboard (PID $PID)..."
    kill "$PID" 2>/dev/null
    # Also kill child streamlit process
    pkill -P "$PID" 2>/dev/null
    rm -f "$PID_FILE"
    echo "Stopped."
else
    echo "Process $PID not running. Cleaning up PID file."
    rm -f "$PID_FILE"
fi
