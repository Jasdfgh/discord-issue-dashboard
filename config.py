"""
项目配置文件
支持三种运行方式：
  1. 本地开发: 环境变量 / fallback 默认路径
  2. Docker: 环境变量 + volume 挂载
  3. Streamlit Cloud: st.secrets (无文件系统)
"""
import os
from pathlib import Path

# Auto-load .env file if present (for local dev without Docker)
_env_file = Path(__file__).parent / ".env"
if _env_file.exists():
    with open(_env_file) as _f:
        for _line in _f:
            _line = _line.strip()
            if _line and "=" in _line and not _line.startswith("#"):
                _k, _v = _line.split("=", 1)
                os.environ.setdefault(_k.strip(), _v.strip())

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

# ============== LLM 配置 ==============
# 后端优先级: Cursor CLI > 内部 API 网关
# Cursor CLI: 用 Cursor 订阅配额，无需额外 key，内网/外网均可用
# API: 备用方案，需要内网 + key 配置

LLM_BACKEND = os.getenv("LLM_BACKEND", "cli")  # "cli" or "api"

# --- Cursor CLI ---
LLM_CLI_MODEL = os.getenv("LLM_CLI_MODEL", "claude-4.6-opus-max-thinking")
LLM_CLI_BINARY = os.getenv("LLM_CLI_BINARY", "agent")

# --- API (备用) ---
LLM_API_BASE_URL = os.getenv("LLM_API_BASE_URL", "")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_API_MODEL = os.getenv("LLM_API_MODEL", "claude-opus-4-6")

# --- 通用 ---
LLM_GRADE_BATCH_SIZE = int(os.getenv("LLM_GRADE_BATCH_SIZE", "20"))
LLM_GRADE_WORKERS = int(os.getenv("LLM_GRADE_WORKERS", "5"))

# ============== Team 映射 ==============

def get_team(owner: str) -> str:
    """从 Owner 字段提取团队归属。Owner 格式: 'Name (AMD)' 或 'Name (Data Monsters)'"""
    owner = str(owner)
    if "(AMD)" in owner:
        return "AMD"
    if "(Data Monsters)" in owner:
        return "DM"
    return "Unknown"

# ============== 字段映射 ==============
# Google Sheets 列名 -> 数据库字段名
COLUMN_MAPPING = {
    "id": "id",
    "Date": "date",
    "Channel / Chat": "channel",
    "Original Source": "original_source",
    "Category": "category",
    "Issue": "issue",
    "Owner": "owner",
    "Reply / Approach": "reply_approach",
    "Progress": "progress",
    "Last Update Date": "last_update_date",
    "Result": "result",
    "Problem_Category": "problem_category",
}

# Dashboard 核心字段（MVP）
CORE_FIELDS = ["date", "category", "progress", "problem_category"]

# 所有字段
ALL_FIELDS = list(COLUMN_MAPPING.values())

# 显示名称映射 (用于 Dashboard UI)
DISPLAY_NAMES = {
    "problem_category": "Problem Type",
    "category": "Issue Details",
    "progress": "Status",
    "owner": "Owner",
    "date": "Date",
    "channel": "Channel",
    "issue": "Issue",
    "result": "Result",
}
