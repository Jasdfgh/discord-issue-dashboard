"""
Discord Issue Dashboard - Main Entry
Run: streamlit run dashboard.py --server.port 8501 --server.address 0.0.0.0
"""

import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime, date
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.db import (
    get_all_issues, get_issues_count, get_last_sync,
    get_unique_values, get_statistics, search_issues, filter_issues
)
from utils.common import normalize_progress, parse_date, style_progress
from utils.auth import check_auth

# ============== Page Config ==============
st.set_page_config(
    page_title="Discord Issue Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============== Custom Styles ==============
st.markdown("""
<style>
    /* Main title */
    .main-title {
        font-size: 2.2rem;
        font-weight: 700;
        color: #1f2937;
        margin-bottom: 0.5rem;
    }
    
    /* Status labels */
    .status-done {
        background-color: #dcfce7;
        color: #166534;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .status-inprogress {
        background-color: #fef3c7;
        color: #92400e;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .status-pending {
        background-color: #fed7aa;
        color: #c2410c;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    .status-blocked {
        background-color: #fecaca;
        color: #991b1b;
        padding: 0.25rem 0.75rem;
        border-radius: 9999px;
        font-weight: 600;
        font-size: 0.85rem;
    }
    
    /* Table optimization */
    .dataframe {
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)


def render_metrics():
    """Render top metric cards"""
    stats = get_statistics()
    
    # Normalize progress counts
    normalized_progress = {}
    for key, count in stats.get("by_progress", {}).items():
        norm_key = normalize_progress(key)
        normalized_progress[norm_key] = normalized_progress.get(norm_key, 0) + count
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            label="📋 Total Issues",
            value=stats["total"],
        )
    
    with col2:
        done_count = normalized_progress.get("Done", 0)
        st.metric(
            label="✅ Done",
            value=done_count,
        )
    
    with col3:
        in_progress_count = normalized_progress.get("In Progress", 0)
        st.metric(
            label="🔄 In Progress",
            value=in_progress_count,
        )
    
    with col4:
        pending_count = normalized_progress.get("Pending", 0)
        st.metric(
            label="⏸️ Pending",
            value=pending_count,
            help="May indicate blocked/waiting issues",
        )
    
    with col5:
        # Completion rate
        if stats["total"] > 0:
            completion_rate = round(done_count / stats["total"] * 100, 1)
        else:
            completion_rate = 0
        st.metric(
            label="📈 Completion Rate",
            value=f"{completion_rate}%",
        )


def render_filters():
    """Render sidebar filters"""
    st.sidebar.header("🔍 Filters")
    
    # Keyword search
    search_keyword = st.sidebar.text_input(
        "Keyword Search",
        placeholder="Search in Issue, Category...",
    )
    
    # Date filter mode
    st.sidebar.markdown("**Date Filter**")
    date_mode = st.sidebar.selectbox(
        "Date Mode",
        options=["All dates", "Single day", "Date range", "Before date", "After date"],
        label_visibility="collapsed",
    )
    
    date_from = None
    date_to = None
    
    if date_mode == "Single day":
        selected_date = st.sidebar.date_input("Select date", value=date.today())
        date_from = selected_date.strftime("%m/%d/%Y")
        date_to = date_from
    elif date_mode == "Date range":
        col1, col2 = st.sidebar.columns(2)
        with col1:
            start_date = st.date_input("From", value=date.today())
        with col2:
            end_date = st.date_input("To", value=date.today())
        date_from = start_date.strftime("%m/%d/%Y")
        date_to = end_date.strftime("%m/%d/%Y")
    elif date_mode == "Before date":
        selected_date = st.sidebar.date_input("Before (≤)", value=date.today())
        date_to = selected_date.strftime("%m/%d/%Y")
    elif date_mode == "After date":
        selected_date = st.sidebar.date_input("After (≥)", value=date.today())
        date_from = selected_date.strftime("%m/%d/%Y")
    
    # Progress filter (with normalized values)
    st.sidebar.markdown("**Status Filter**")
    progress_options = ["All", "Done", "In Progress", "Pending"]
    selected_progress = st.sidebar.selectbox(
        "Progress",
        progress_options,
        label_visibility="collapsed",
    )
    
    # Problem Category filter (新增)
    st.sidebar.markdown("**Problem Type**")
    problem_categories = get_unique_values("problem_category")
    problem_cat_options = ["All"] + problem_categories
    selected_problem_cat = st.sidebar.selectbox(
        "Problem Category",
        problem_cat_options,
        label_visibility="collapsed",
    )
    
    return {
        "keyword": search_keyword,
        "date_from": date_from,
        "date_to": date_to,
        "progress": None if selected_progress == "All" else selected_progress,
        "problem_category": None if selected_problem_cat == "All" else selected_problem_cat,
    }



# style_progress and parse_date imported from utils.common


def filter_by_date(df, date_from, date_to):
    """Filter DataFrame by date range"""
    if date_from is None and date_to is None:
        return df
    
    # Parse filter dates
    from_dt = parse_date(date_from) if date_from else None
    to_dt = parse_date(date_to) if date_to else None
    
    def date_in_range(row_date):
        parsed = parse_date(row_date)
        if parsed is None:
            return True  # Keep rows with unparseable dates
        if from_dt and parsed < from_dt:
            return False
        if to_dt and parsed > to_dt:
            return False
        return True
    
    mask = df["date"].apply(date_in_range)
    return df[mask]


def filter_by_progress(df, progress):
    """Filter DataFrame by normalized progress value"""
    if progress is None:
        return df
    
    df["_normalized_progress"] = df["progress"].apply(normalize_progress)
    filtered = df[df["_normalized_progress"] == progress].copy()
    filtered = filtered.drop(columns=["_normalized_progress"])
    return filtered


def filter_by_problem_category(df, problem_category):
    """Filter DataFrame by problem_category"""
    if problem_category is None:
        return df
    return df[df["problem_category"] == problem_category]


def render_data_table(filters):
    """Render data table"""
    # Get data
    if filters["keyword"]:
        issues = search_issues(filters["keyword"])
    else:
        issues = get_all_issues()
    
    if not issues:
        st.info("No data found")
        return
    
    # Convert to DataFrame
    df = pd.DataFrame(issues)
    
    # Apply date filter
    df = filter_by_date(df, filters["date_from"], filters["date_to"])
    
    # Apply progress filter
    df = filter_by_progress(df, filters["progress"])
    
    # Apply problem category filter
    if "problem_category" in df.columns:
        df = filter_by_problem_category(df, filters.get("problem_category"))
    
    if df.empty:
        st.info("No matching records found")
        return
    
    # Select display columns - 增加 problem_category
    # problem_category = Problem Type (大类)
    # category = Issue Details (具体描述)
    if "problem_category" in df.columns:
        display_columns = ["date", "problem_category", "category", "progress"]
        df_display = df[display_columns].copy()
        df_display["progress"] = df_display["progress"].apply(normalize_progress)
        df_display.columns = ["Date", "Problem Type", "Issue Details", "Status"]
        # Truncate long text
        df_display["Issue Details"] = df_display["Issue Details"].apply(
            lambda x: (str(x)[:60] + "...") if len(str(x)) > 60 else x
        )
    else:
        display_columns = ["date", "category", "progress"]
        df_display = df[display_columns].copy()
        df_display["progress"] = df_display["progress"].apply(normalize_progress)
        df_display.columns = ["Date", "Category", "Status"]
        df_display["Category"] = df_display["Category"].apply(
            lambda x: (str(x)[:80] + "...") if len(str(x)) > 80 else x
        )
    
    # Show record count
    st.markdown(f"**{len(df_display)} records found**")
    
    # Apply styles and display
    styled_df = df_display.style.applymap(
        style_progress, 
        subset=["Status"]
    )
    
    st.dataframe(
        styled_df,
        use_container_width=True,
        height=500,
        hide_index=True,
    )


@st.cache_resource
def _auto_sync_on_startup():
    """
    Auto-sync on first load (runs once per app lifecycle).
    Critical for Streamlit Cloud where there's no cron and no persistent storage.
    """
    try:
        from scripts.sync_google_sheets import sync
        sync()
    except Exception as e:
        # Don't crash the app if sync fails - there might be cached data
        import logging
        logging.getLogger("discord_dashboard").warning(f"Auto-sync on startup failed: {e}")


def run_sync():
    """Run data sync from Google Sheets"""
    import subprocess
    try:
        result = subprocess.run(
            [sys.executable, "scripts/sync_google_sheets.py"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return result.returncode == 0, result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return False, "Sync timeout (>60s)"
    except Exception as e:
        return False, str(e)


@st.cache_data(ttl=300)  # 缓存 5 分钟
def get_sheets_last_update():
    """Get Google Sheets last update time via Sheets API"""
    try:
        import gspread
        from datetime import datetime
        
        from config import get_google_credentials, SPREADSHEET_ID
        
        credentials = get_google_credentials()
        gc = gspread.authorize(credentials)
        spreadsheet = gc.open_by_key(SPREADSHEET_ID)
        
        # 获取最后更新时间 (UTC)
        last_update_str = spreadsheet.lastUpdateTime  # ISO 格式: 2026-02-05T08:08:17.944Z
        
        # 解析并转换为本地时间显示
        if last_update_str:
            # 去掉毫秒和 Z
            dt_str = last_update_str.replace('Z', '+00:00')
            dt_utc = datetime.fromisoformat(dt_str.split('.')[0])
            # 返回格式化的字符串
            return dt_utc.strftime("%Y-%m-%d %H:%M:%S") + " UTC"
        return None
    except Exception as e:
        return f"Error: {str(e)[:50]}"


def render_sync_status():
    """Render sync status and manual sync button in sidebar"""
    st.sidebar.markdown("---")
    st.sidebar.markdown("### 📡 Data Sync")
    
    # Manual sync button
    if st.sidebar.button("🔄 Sync Now", use_container_width=True):
        with st.sidebar:
            with st.spinner("Syncing from Google Sheets..."):
                success, output = run_sync()
            
            if success:
                st.success("✅ Sync completed!")
                # Clear cache to refresh data
                st.cache_data.clear()
                st.rerun()
            else:
                st.error(f"❌ Sync failed")
                with st.expander("Error details"):
                    st.code(output)
    
    # Show Google Sheets last update time
    sheets_update = get_sheets_last_update()
    if sheets_update and not sheets_update.startswith("Error"):
        st.sidebar.markdown(f"**📄 Sheet updated:** {sheets_update}")
    
    # Show last sync info
    last_sync = get_last_sync()
    if last_sync:
        # Format time nicely
        sync_time = last_sync['sync_time']
        st.sidebar.markdown(f"**🔄 Last sync:** {sync_time}")
        
        # Status with color
        status = last_sync['status']
        if status == 'success':
            st.sidebar.markdown(f"**Status:** :green[{status}]")
        else:
            st.sidebar.markdown(f"**Status:** :red[{status}]")
        
        st.sidebar.markdown(f"**Records:** {last_sync['rows_synced']}")
    else:
        st.sidebar.info("No sync history yet")


def main():
    """Main function"""
    # Auth check (blocks with login page if REQUIRE_AUTH is set)
    check_auth()
    
    # Title
    st.markdown('<h1 class="main-title">📊 Discord Issue Dashboard</h1>', unsafe_allow_html=True)
    st.markdown("Discord Community Support Tracking")
    st.markdown("---")
    
    # Ensure database exists (critical for Streamlit Cloud where data/ doesn't persist)
    from utils.db import init_database
    init_database()
    
    # Auto-sync on startup if database is empty (important for Streamlit Cloud)
    if get_issues_count() == 0:
        with st.spinner("Syncing data from Google Sheets (first load)..."):
            _auto_sync_on_startup()
    
    if get_issues_count() == 0:
        st.warning("⚠️ Database is empty. Sync failed or not yet run.")
        return
    
    # Top metrics
    render_metrics()
    
    st.markdown("---")
    
    # Sidebar filters
    filters = render_filters()
    
    # Sync status
    render_sync_status()
    
    # Data table
    st.subheader("📋 Issue List")
    render_data_table(filters)


if __name__ == "__main__":
    main()
