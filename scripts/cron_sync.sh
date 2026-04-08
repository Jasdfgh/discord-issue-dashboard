#!/bin/bash
# Hourly Google Sheets sync (cron job)
#
# Install (one-liner):
#   crontab -l 2>/dev/null | grep -v "cron_sync" | { cat; echo "0 * * * * /home/yaywang/discord-dashboard/output/discord-issue-dashboard/scripts/cron_sync.sh >> /home/yaywang/discord-dashboard/output/discord-issue-dashboard/logs/cron_sync.log 2>&1"; } | crontab -
#
# Verify: crontab -l
# Remove: crontab -l | grep -v "cron_sync" | crontab -

cd /home/yaywang/discord-dashboard/output/discord-issue-dashboard

/home/yaywang/anaconda3/bin/python scripts/sync_google_sheets.py
