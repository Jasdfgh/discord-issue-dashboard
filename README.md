# Discord Issue Dashboard

Streamlit dashboard for tracking Discord community support issues. Includes AI-powered quality grading and automated weekly report generation.

**Live**: `http://10.161.176.9:8501` (internal) | Streamlit Cloud (external, password-protected)

## Features

- **Issue Table** — Filterable by date, status, problem type, keyword search
- **Analytics** — Time-range comparisons, trend charts, channel/problem distribution
- **Weekly Report** — Claude quality grading (H/M/L), team comparison donut chart, auto-generated report text (internal only)
- **Manual Sync** — One-click data refresh from Google Sheets

## Quick Start

```bash
# 1. Clone and configure
git clone git@github.com:Jasdfgh/discord-issue-dashboard.git
cd discord-issue-dashboard
cp .env.example .env
# Edit .env: set GOOGLE_CREDENTIALS_PATH and LLM settings

# 2. Install dependencies
pip install -r requirements.txt

# 3. Initial data sync
python scripts/sync_google_sheets.py

# 4. Start dashboard (background, auto-restart)
./scripts/start.sh
# Dashboard at http://localhost:8501
```

## Configuration

All configuration via `.env` (auto-loaded by `config.py`):

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_CREDENTIALS_PATH` | Yes | — | Path to Google service account JSON |
| `SPREADSHEET_ID` | No | *(built-in)* | Google Sheets spreadsheet ID |
| `SHEET_NAME` | No | `Merged Activity Log` | Worksheet name |
| `LLM_BACKEND` | No | `cli` | LLM backend: `cli` (Cursor) or `api` |
| `LLM_CLI_MODEL` | No | `claude-4.6-opus-max-thinking` | Cursor CLI model |
| `LLM_CLI_BINARY` | No | `agent` | Cursor CLI binary name |
| `LLM_API_BASE_URL` | No | — | API gateway URL (backup) |
| `LLM_API_KEY` | No | — | API gateway key (backup) |
| `LLM_GRADE_BATCH_SIZE` | No | `20` | Issues per grading batch |
| `LLM_GRADE_WORKERS` | No | `5` | Parallel grading workers |
| `DATABASE_PATH` | No | `./data/issues.db` | SQLite database |

## Architecture

```
Google Sheets ──sync──→ SQLite (issues + quality_grades + sync_log)
                           │
                    ┌──────┴──────┐
                    │ Cursor CLI  │  claude-4.6-opus-max-thinking
                    │ (blind      │  Owner excluded from prompt
                    │  grading)   │
                    └──────┬──────┘
                           │
              ┌────────────┼────────────┐
              ▼            ▼            ▼
         Dashboard    Analytics    Weekly Report
         (table +     (charts +   (donut chart +
          filters)     trends)     report text)
```

**Tech Stack**: Streamlit, Pandas, Plotly, SQLite, gspread, Cursor CLI (Agent)

## Maintenance

### Service Management

```bash
./scripts/start.sh              # Start (background, auto-restart on crash)
./scripts/stop.sh               # Stop
curl -f http://localhost:8501/_stcore/health   # Health check
tail -f logs/dashboard.log      # View logs
```

### Data Sync

```bash
# Manual sync:
python scripts/sync_google_sheets.py

# Install hourly auto-sync (cron):
crontab -l 2>/dev/null | grep -v "cron_sync" | { cat; echo "0 * * * * /home/yaywang/discord-dashboard/output/discord-issue-dashboard/scripts/cron_sync.sh >> /home/yaywang/discord-dashboard/output/discord-issue-dashboard/logs/cron_sync.log 2>&1"; } | crontab -

# Verify cron is installed:
crontab -l

# Remove cron:
crontab -l | grep -v "cron_sync" | crontab -
```

### Quality Grading

```bash
python scripts/grade_quality.py              # Grade new/changed issues
python scripts/grade_quality.py --status     # Show grading progress
python scripts/grade_quality.py --regrade    # Re-grade everything (~7 min)
```

Or use the Sync & Grade / Re-grade All buttons on the Weekly Report page.

### Update Code

```bash
git pull
./scripts/stop.sh
./scripts/start.sh
```

### Backup

```bash
bash scripts/backup.sh              # Default: 7-day retention
bash scripts/backup.sh /path 14     # Custom path, 14-day retention
```

### Recovery After Reboot

```bash
cd ~/discord-dashboard/output/discord-issue-dashboard

# 1. Start the dashboard
./scripts/start.sh

# 2. Verify it's running
curl -f http://localhost:8501/_stcore/health

# 3. Verify cron is still installed (crontab survives reboot, but check)
crontab -l | grep cron_sync
# If missing, re-install:
crontab -l 2>/dev/null | grep -v "cron_sync" | { cat; echo "0 * * * * /home/yaywang/discord-dashboard/output/discord-issue-dashboard/scripts/cron_sync.sh >> /home/yaywang/discord-dashboard/output/discord-issue-dashboard/logs/cron_sync.log 2>&1"; } | crontab -

# 4. Verify .env exists and has correct GOOGLE_CREDENTIALS_PATH
cat .env | grep GOOGLE_CREDENTIALS_PATH
```

## Deployment Modes

| Mode | URL | LLM | Weekly Report |
|------|-----|-----|---------------|
| **Host (primary)** | `http://10.161.176.9:8501` | Cursor CLI | Full |
| Streamlit Cloud | Public URL (password) | N/A | Hidden |
| Docker (backup) | `docker compose up -d` | N/A | N/A |

## Project Structure

```
├── dashboard.py               # Main page: table + filters + sync
├── config.py                  # Config center (auto-loads .env)
├── pages/
│   ├── 1_Analytics.py         # Analytics: charts + time comparison
│   └── 2_Weekly_Report.py     # Weekly Report (hidden on Cloud)
├── scripts/
│   ├── sync_google_sheets.py  # Sheet → SQLite sync
│   ├── grade_quality.py       # Quality grading CLI
│   ├── start.sh / stop.sh     # Service start/stop
│   ├── cron_sync.sh           # Cron entry point
│   └── backup.sh              # Database backup
├── utils/
│   ├── db.py                  # Database (issues + quality_grades)
│   ├── llm.py                 # LLM interface (CLI + API)
│   ├── grading.py             # Quality grading engine
│   ├── report.py              # Report generator (stats + chart + text)
│   ├── common.py              # Shared constants & helpers
│   ├── auth.py                # Password auth (Cloud)
│   └── logger.py              # Logging config
├── data/                      # Runtime (gitignored)
├── logs/                      # Runtime (gitignored)
├── .env.example               # Environment template
├── requirements.txt
├── Dockerfile                 # Docker (backup deployment)
└── docker-compose.yml
```
