#!/bin/bash
# Hourly Google Sheets sync (cron job)
# Crontab entry: 0 * * * * /home/yaywang/discord-dashboard/output/discord-issue-dashboard/scripts/cron_sync.sh >> /home/yaywang/discord-dashboard/output/discord-issue-dashboard/logs/cron_sync.log 2>&1

cd /home/yaywang/discord-dashboard/output/discord-issue-dashboard

/home/yaywang/anaconda3/bin/python scripts/sync_google_sheets.py
