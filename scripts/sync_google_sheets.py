#!/usr/bin/env python3
"""
Google Sheets 数据同步脚本
将 Google Sheets 数据同步到本地 SQLite 数据库

用法:
    python scripts/sync_google_sheets.py
"""

import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import time
import gspread
from google.oauth2.service_account import Credentials

from config import (
    CREDENTIALS_PATH, SPREADSHEET_ID, SHEET_NAME, 
    SCOPES, COLUMN_MAPPING, get_google_credentials
)
from utils.db import (
    init_database, safe_replace_issues,
    log_sync, get_issues_count, get_last_sync
)
from utils.logger import setup_logger

logger = setup_logger("sync")

# ============== Retry Mechanism ==============
MAX_RETRIES = 3
BASE_DELAY = 2  # seconds


def retry_on_error(func, description="operation"):
    """
    Retry with exponential backoff.
    Retries MAX_RETRIES times with delays: 2s, 4s, 8s
    """
    for attempt in range(MAX_RETRIES):
        try:
            return func()
        except Exception as e:
            if attempt == MAX_RETRIES - 1:
                logger.error(f"{description} failed after {MAX_RETRIES} attempts: {e}")
                raise
            delay = BASE_DELAY * (2 ** attempt)
            logger.warning(f"{description} attempt {attempt + 1} failed: {e}. Retrying in {delay}s...")
            time.sleep(delay)


def fetch_google_sheets_data():
    """从 Google Sheets 获取数据 (with retry)"""
    logger.info("[1/3] Connecting to Google Sheets...")
    
    def _connect_and_fetch():
        credentials = get_google_credentials()
        gc = gspread.authorize(credentials)
        
        spreadsheet = gc.open_by_key(SPREADSHEET_ID)
        logger.info(f"  Spreadsheet: {spreadsheet.title}")
        
        worksheet = spreadsheet.worksheet(SHEET_NAME)
        logger.info(f"  Worksheet: {worksheet.title}")
        
        logger.info("[2/3] Fetching data...")
        raw_data = worksheet.get_all_records()
        logger.info(f"  Raw rows: {len(raw_data)}")
        return raw_data
    
    return retry_on_error(_connect_and_fetch, "Google Sheets fetch")


def transform_data(raw_data):
    """转换数据格式（列名映射），跳过无效行"""
    transformed = []
    skipped = 0
    
    for row in raw_data:
        # 跳过 ID 为空的行（上游数据录入遗漏）
        raw_id = row.get("ID", "")
        if raw_id == "" or raw_id is None:
            skipped += 1
            continue
        
        item = {}
        for sheet_col, db_col in COLUMN_MAPPING.items():
            value = row.get(sheet_col, "")
            if isinstance(value, str):
                value = value.strip()
            item[db_col] = value
        transformed.append(item)
    
    if skipped > 0:
        logger.warning(f"  Skipped {skipped} rows with empty ID")
    
    return transformed


def sync():
    """执行同步"""
    logger.info("=" * 50)
    logger.info("Google Sheets -> SQLite sync")
    logger.info(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    logger.info("=" * 50)
    
    try:
        # 初始化数据库
        init_database()
        
        # 获取数据
        raw_data = fetch_google_sheets_data()
        
        # 转换格式
        data = transform_data(raw_data)
        
        # 全量同步：事务保护（清空 + 插入在同一事务内）
        logger.info("[3/3] Writing to database...")
        count = safe_replace_issues(data)
        logger.info(f"  Rows written: {count}")
        
        # 记录日志
        log_sync(count, "success", f"Full sync completed")
        
        logger.info("=" * 50)
        logger.info(f"Sync completed: {count} records")
        logger.info("=" * 50)
        
        return True
        
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Sync failed: {error_msg}", exc_info=True)
        log_sync(0, "failed", error_msg)
        return False


def show_status():
    """显示当前状态"""
    logger.info("--- Current status ---")
    logger.info(f"Issues count: {get_issues_count()}")
    
    last_sync = get_last_sync()
    if last_sync:
        logger.info(f"Last sync time: {last_sync['sync_time']}")
        logger.info(f"Last sync status: {last_sync['status']}")
        logger.info(f"Last sync rows: {last_sync['rows_synced']}")
    else:
        logger.info("No sync history")


if __name__ == "__main__":
    success = sync()
    show_status()
    sys.exit(0 if success else 1)
