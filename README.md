# Discord Issue Dashboard

A Streamlit-based dashboard for tracking and analyzing Discord community support issues. Data is synced from Google Sheets and visualized with interactive charts and filters.

## Quick Start

### Docker (Recommended)

```bash
# 1. Create .env file from template
cp .env.example .env
# Edit .env: set GOOGLE_CREDENTIALS_PATH to your credentials file

# 2. Place your Google service account JSON file
#    (path must match GOOGLE_CREDENTIALS_PATH in .env)

# 3. Start
docker compose up -d

# Dashboard available at http://localhost:8501
```

### Local Development

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Set environment variable (or edit config.py defaults)
export GOOGLE_CREDENTIALS_PATH=/path/to/credentials.json

# 3. Initial data sync
python scripts/sync_google_sheets.py

# 4. Start dashboard
streamlit run dashboard.py --server.port 8501 --server.address 0.0.0.0 --server.headless true
```

## Configuration

All configuration is via environment variables (with sensible defaults for local dev).

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GOOGLE_CREDENTIALS_PATH` | Yes | `../../*.json` (local) | Path to Google service account JSON |
| `SPREADSHEET_ID` | No | *(built-in)* | Google Sheets spreadsheet ID |
| `SHEET_NAME` | No | `Merged Activity Log` | Worksheet name |
| `DATABASE_PATH` | No | `./data/issues.db` | SQLite database file path |
| `DATA_DIR` | No | `./data` | Data directory |
| `LOGS_DIR` | No | `./logs` | Log files directory |

## Architecture

```
Google Sheets (source of truth)
       │
       │  Sheets API (gspread) - hourly cron
       ▼
   sync_google_sheets.py → SQLite (data/issues.db)
       │
       │  utils/db.py
       ▼
   Streamlit Dashboard
   ├── dashboard.py    (Main: table + filters + sync button)
   └── 1_Analytics.py  (Charts: trends, distributions, comparisons)
```

**Tech Stack**: Streamlit, Pandas, Plotly, SQLite, gspread

## Features

- **Issue Table** — Filterable by date, status, problem type, keyword
- **Manual Sync** — One-click data refresh from Google Sheets
- **Analytics** — Time-range comparisons (Day/Week/Month/Custom)
- **Charts** — Progress distribution, channel breakdown, problem type analysis, trend over time

## Maintenance

### Data Sync
- **Auto**: Hourly via cron (Docker) or system crontab (local)
- **Manual**: Click "Sync Now" in sidebar, or run `python scripts/sync_google_sheets.py`

### Backup
```bash
bash scripts/backup.sh              # Default: 7-day retention
bash scripts/backup.sh /path 14     # Custom path, 14-day retention
```

### Logs
- Location: `./logs/app.log` (auto-rotates at 5MB, keeps 3 files)
- Cron sync log (Docker): `./logs/cron_sync.log`

### Health Check
- Streamlit built-in: `GET /_stcore/health` → 200 OK
- Docker: auto-configured healthcheck every 30s

## Project Structure

```
├── dashboard.py           # Main Streamlit page
├── config.py              # Configuration (env vars)
├── pages/
│   └── 1_Analytics.py     # Analytics page
├── scripts/
│   ├── sync_google_sheets.py  # Data sync script
│   └── backup.sh              # Database backup
├── utils/
│   ├── db.py              # Database operations
│   ├── common.py          # Shared constants & helpers
│   └── logger.py          # Logging configuration
├── data/                  # Runtime: SQLite + backups
├── logs/                  # Runtime: log files
├── Dockerfile
├── docker-compose.yml
├── .env.example
└── requirements.txt
```
