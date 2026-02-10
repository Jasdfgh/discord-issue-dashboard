"""
项目配置文件
支持三种运行方式：
  1. 本地开发: 环境变量 / fallback 默认路径
  2. Docker: 环境变量 + volume 挂载
  3. Streamlit Cloud: st.secrets (无文件系统)
"""
import os
from pathlib import Path

# ============== 路径配置 ==============
PROJECT_ROOT = Path(__file__).parent
DATA_DIR = Path(os.getenv("DATA_DIR", str(PROJECT_ROOT / "data")))
LOGS_DIR = Path(os.getenv("LOGS_DIR", str(PROJECT_ROOT / "logs")))

# 数据库文件
DATABASE_PATH = Path(os.getenv("DATABASE_PATH", str(DATA_DIR / "issues.db")))

# ============== Google 凭证 ==============
# 优先级: st.secrets > 环境变量 > 默认文件路径

def _has_streamlit_secrets():
    """Check if running on Streamlit Cloud with secrets configured"""
    try:
        import streamlit as st
        return "gcp_service_account" in st.secrets
    except Exception:
        return False

def get_google_credentials():
    """
    Get Google credentials object.
    - Streamlit Cloud: from st.secrets["gcp_service_account"]
    - Docker / Local: from JSON file at CREDENTIALS_PATH
    """
    from google.oauth2.service_account import Credentials
    
    if _has_streamlit_secrets():
        import streamlit as st
        creds_dict = dict(st.secrets["gcp_service_account"])
        return Credentials.from_service_account_info(creds_dict, scopes=SCOPES)
    else:
        return Credentials.from_service_account_file(str(CREDENTIALS_PATH), scopes=SCOPES)

# 文件路径 (Docker / 本地 fallback)
_default_credentials = str(PROJECT_ROOT.parent.parent / "credentials.json")
CREDENTIALS_PATH = Path(os.getenv("GOOGLE_CREDENTIALS_PATH", _default_credentials))

# ============== Google Sheets 配置 ==============
SPREADSHEET_ID = os.getenv("SPREADSHEET_ID", "1Q9vwB7PMYn3sHOSBpbE_qg0KH3RtOL19YHIoN2rXOqw")
SHEET_NAME = os.getenv("SHEET_NAME", "Merged Activity Log")
SHEET_GID = 421671622

# API Scopes
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly",
]

# ============== 字段映射 ==============
# Google Sheets 列名 -> 数据库字段名
# 注意: 2026-02 表格结构已更新，Progress 列名不再有尾部空格
COLUMN_MAPPING = {
    "ID": "id",
    "Date": "date",
    "Channel / Chat": "channel",
    "Original Source": "original_source",
    "Category": "category",  # 具体问题描述 (Issue Details)
    "Issue": "issue",
    "Owner": "owner",
    "Reply / Approach": "reply_approach",
    "Progress": "progress",  # 2026-02: 列名已无尾部空格; 值: Done/In Progress/Pending
    "Result": "result",
    "Problem_Category": "problem_category",  # 2026-02 新增: 问题大类 (Problem Type)
}

# 注意: Progress 字段值变更
# - Done: 已完成
# - In Progress: 进行中  
# - Pending: 待处理 (可能表示 Blocked/受阻)

# Problem Category 标准化分类 (下拉框选项):
# - App Integration
# - Developer Program
# - Internal Process
# - Library/Build
# - Other
# - Setup/Drivers

# Dashboard 核心字段（MVP）
CORE_FIELDS = ["date", "category", "progress", "problem_category"]

# 所有字段
ALL_FIELDS = list(COLUMN_MAPPING.values())

# 显示名称映射 (用于 Dashboard UI)
DISPLAY_NAMES = {
    "problem_category": "Problem Type",  # 大类
    "category": "Issue Details",  # 具体描述
    "progress": "Status",
    "owner": "Owner",
    "date": "Date",
    "channel": "Channel",
    "issue": "Issue",
    "result": "Result",
}
