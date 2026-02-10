"""
公共定义模块 - 单一数据源
所有 Progress 归一化、日期解析、颜色常量集中在此
dashboard.py 和 pages/1_Analytics.py 统一 import
"""

import pandas as pd
from datetime import datetime


# ============== Progress Normalization ==============
# 2026-02 更新: Pending 作为独立状态（可能表示 Blocked/受阻）
# Google Sheets 当前值: Done / In Progress / Pending

PROGRESS_MAPPING = {
    "done": "Done",
    "Done": "Done",
    "DONE": "Done",
    "in progress": "In Progress",
    "In Progress": "In Progress",
    "In progress": "In Progress",
    "IN PROGRESS": "In Progress",
    "pending": "Pending",
    "Pending": "Pending",
    "PENDING": "Pending",
    "block": "Blocked",
    "Block": "Blocked",
    "blocked": "Blocked",
    "Blocked": "Blocked",
    "BLOCKED": "Blocked",
}

# 标准化后的有效值
PROGRESS_VALUES = ["Done", "In Progress", "Pending", "Blocked"]


def normalize_progress(value):
    """
    Normalize progress value to standard form.
    
    Returns: "Done" | "In Progress" | "Pending" | "Blocked" | "Unknown"
    """
    if pd.isna(value) or value is None:
        return "Unknown"
    val = str(value).strip()
    return PROGRESS_MAPPING.get(val, "Unknown")


# ============== Date Parsing ==============

# 支持的日期格式，按优先级排序
DATE_FORMATS = ["%m/%d/%Y", "%Y-%m-%d", "%m/%d/%y", "%d/%m/%Y"]


def parse_date(date_str):
    """
    Parse date string to datetime object.
    
    Supports: "01/23/2026", "2026-01-23", "01/23/26", "23/01/2026"
    Returns: datetime or None
    """
    if pd.isna(date_str) or not date_str:
        return None
    try:
        cleaned = str(date_str).strip()
        for fmt in DATE_FORMATS:
            try:
                return datetime.strptime(cleaned, fmt)
            except ValueError:
                continue
        return None
    except Exception:
        return None


# ============== Color Constants ==============

PROGRESS_COLORS = {
    "Done": "#22c55e",        # green
    "In Progress": "#f59e0b",  # amber
    "Pending": "#f97316",      # orange
    "Blocked": "#ef4444",      # red
    "Unknown": "#9ca3af",      # gray
}

PROBLEM_CATEGORY_COLORS = {
    "Setup/Drivers": "#3b82f6",       # blue
    "Library/Build": "#8b5cf6",        # purple
    "App Integration": "#ec4899",      # pink
    "Developer Program": "#14b8a6",    # teal
    "Internal Process": "#f59e0b",     # amber
    "Other": "#6b7280",                # gray
}

# Progress 表格样式 (用于 Styler.applymap)
PROGRESS_STYLES = {
    "Done": "background-color: #dcfce7; color: #166534; font-weight: 600;",
    "In Progress": "background-color: #fef3c7; color: #92400e; font-weight: 600;",
    "Pending": "background-color: #fed7aa; color: #c2410c; font-weight: 600;",
    "Blocked": "background-color: #fecaca; color: #991b1b; font-weight: 600;",
}


def style_progress(val):
    """Style for Progress column in st.dataframe"""
    if pd.isna(val):
        return ""
    norm_val = normalize_progress(val)
    return PROGRESS_STYLES.get(norm_val, "")
