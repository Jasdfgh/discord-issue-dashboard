#!/bin/bash
# Start Discord Dashboard (background, auto-restart on crash)
# Usage: ./scripts/start.sh
# Stop:  ./scripts/stop.sh

cd "$(dirname "$0")/.."
PROJECT_DIR=$(pwd)
PID_FILE="$PROJECT_DIR/data/dashboard.pid"
LOG_FILE="$PROJECT_DIR/logs/dashboard.log"

mkdir -p "$PROJECT_DIR/data" "$PROJECT_DIR/logs"

# Check if already running
if [ -f "$PID_FILE" ] && kill -0 "$(cat "$PID_FILE")" 2>/dev/null; then
    echo "Dashboard already running (PID $(cat "$PID_FILE"))"
    echo "Stop first: ./scripts/stop.sh"
    exit 1
fi

echo "Starting Discord Dashboard on port 8501..."

nohup bash -c '
while true; do
    /home/yaywang/anaconda3/bin/streamlit run dashboard.py \
        --server.port 8501 \
        --server.address 0.0.0.0 \
        --server.headless true \
        --browser.gatherUsageStats false \
        2>&1
    echo "[$(date)] Streamlit exited, restarting in 5s..."
    sleep 5
done
' > "$LOG_FILE" 2>&1 &

echo $! > "$PID_FILE"
echo "Started (PID $!, log: $LOG_FILE)"
echo "Health check: curl -f http://localhost:8501/_stcore/health"
