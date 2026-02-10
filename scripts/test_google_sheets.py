#!/usr/bin/env python3
"""
测试 Google Sheets API 连接
运行方式: python scripts/test_google_sheets.py
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import gspread
from google.oauth2.service_account import Credentials

# ============== 配置 ==============
# 认证文件路径（不在 git 仓库内）
CREDENTIALS_PATH = Path(__file__).parent.parent.parent.parent / "credentials.json"

# Google Sheets 信息
SPREADSHEET_ID = "1Q9vwB7PMYn3sHOSBpbE_qg0KH3RtOL19YHIoN2rXOqw"
SHEET_GID = 421671622  # 特定的 sheet tab

# API Scopes
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]


def test_connection():
    """测试 Google Sheets API 连接"""
    print("=" * 50)
    print("Google Sheets API 连接测试")
    print("=" * 50)
    
    # 1. 检查认证文件
    print(f"\n[1/4] 检查认证文件...")
    print(f"      路径: {CREDENTIALS_PATH}")
    if not CREDENTIALS_PATH.exists():
        print(f"      ❌ 认证文件不存在!")
        print(f"      请确认文件路径正确")
        return False
    print(f"      ✅ 认证文件存在")
    
    # 2. 加载认证
    print(f"\n[2/4] 加载认证...")
    try:
        credentials = Credentials.from_service_account_file(
            str(CREDENTIALS_PATH),
            scopes=SCOPES
        )
        print(f"      ✅ 认证加载成功")
        print(f"      Service Account: {credentials.service_account_email}")
    except Exception as e:
        print(f"      ❌ 认证加载失败: {e}")
        return False
    
    # 3. 连接 Google Sheets
    print(f"\n[3/4] 连接 Google Sheets...")
    try:
        gc = gspread.authorize(credentials)
        spreadsheet = gc.open_by_key(SPREADSHEET_ID)
        print(f"      ✅ 连接成功")
        print(f"      表格标题: {spreadsheet.title}")
    except gspread.exceptions.SpreadsheetNotFound:
        print(f"      ❌ 找不到表格!")
        print(f"      请确认 Service Account 邮箱已添加到表格共享列表")
        return False
    except Exception as e:
        print(f"      ❌ 连接失败: {e}")
        return False
    
    # 4. 读取数据
    print(f"\n[4/4] 读取数据...")
    try:
        # 获取所有 worksheets
        worksheets = spreadsheet.worksheets()
        print(f"      共有 {len(worksheets)} 个 sheet:")
        for ws in worksheets:
            print(f"        - {ws.title} (gid={ws.id})")
        
        # 尝试获取指定 gid 的 sheet
        target_sheet = None
        for ws in worksheets:
            if ws.id == SHEET_GID:
                target_sheet = ws
                break
        
        if target_sheet is None:
            print(f"\n      ⚠️ 未找到 gid={SHEET_GID} 的 sheet，使用第一个 sheet")
            target_sheet = worksheets[0]
        
        print(f"\n      目标 Sheet: {target_sheet.title}")
        
        # 获取所有数据
        all_data = target_sheet.get_all_records()
        print(f"      ✅ 数据读取成功")
        print(f"      总行数: {len(all_data)}")
        
        # 显示列名
        if all_data:
            columns = list(all_data[0].keys())
            print(f"      列名: {columns}")
            
            # 显示前 3 行数据预览
            print(f"\n      数据预览 (前 3 行):")
            for i, row in enumerate(all_data[:3]):
                print(f"        [{i+1}] {row}")
        
    except Exception as e:
        print(f"      ❌ 数据读取失败: {e}")
        return False
    
    print("\n" + "=" * 50)
    print("✅ 所有测试通过!")
    print("=" * 50)
    return True


if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1)
