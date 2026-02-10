#!/bin/bash
# SQLite Database Backup Script
# Usage: ./scripts/backup.sh [backup_dir] [keep_days]
#
# Defaults:
#   backup_dir = ./data/backups
#   keep_days  = 7

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

DB_PATH="${DATABASE_PATH:-$PROJECT_DIR/data/issues.db}"
BACKUP_DIR="${1:-$PROJECT_DIR/data/backups}"
KEEP_DAYS="${2:-7}"

# Check database exists
if [ ! -f "$DB_PATH" ]; then
    echo "ERROR: Database not found: $DB_PATH"
    exit 1
fi

# Create backup directory
mkdir -p "$BACKUP_DIR"

# Create backup with timestamp
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/issues_${TIMESTAMP}.db"

cp "$DB_PATH" "$BACKUP_FILE"
echo "Backup created: $BACKUP_FILE ($(du -h "$BACKUP_FILE" | cut -f1))"

# Clean old backups
DELETED=$(find "$BACKUP_DIR" -name "issues_*.db" -mtime +"$KEEP_DAYS" -delete -print | wc -l)
if [ "$DELETED" -gt 0 ]; then
    echo "Cleaned $DELETED backups older than $KEEP_DAYS days"
fi

# Show current backups
TOTAL=$(find "$BACKUP_DIR" -name "issues_*.db" | wc -l)
echo "Total backups: $TOTAL"
