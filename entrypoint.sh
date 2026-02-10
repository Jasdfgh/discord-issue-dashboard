#!/bin/bash
set -e

echo "=== Discord Issue Dashboard ==="
echo "Starting at $(date)"

# 1. Run initial sync (ensure data exists)
echo "[1/3] Running initial data sync..."
python scripts/sync_google_sheets.py || echo "WARNING: Initial sync failed, continuing with existing data..."

# 2. Setup cron for periodic sync (every hour)
echo "[2/3] Setting up hourly sync cron..."
echo "0 * * * * cd /app && /usr/local/bin/python scripts/sync_google_sheets.py >> /app/logs/cron_sync.log 2>&1" | crontab -
cron

# 3. Start Streamlit (foreground)
echo "[3/3] Starting Streamlit dashboard..."
exec streamlit run dashboard.py \
    --server.port 8501 \
    --server.address 0.0.0.0 \
    --server.headless true \
    --browser.gatherUsageStats false
