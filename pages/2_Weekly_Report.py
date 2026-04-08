"""
Weekly Report Page — Quality grading, donut chart comparison, report generation.
Requires Cursor CLI (local/Docker only). Hidden on Streamlit Cloud.
"""

import streamlit as st

# Block on Streamlit Cloud — this page needs local Cursor CLI
try:
    if "gcp_service_account" in st.secrets:
        st.set_page_config(page_title="Weekly Report", page_icon="📝")
        st.info("📝 Weekly Report is available on the internal deployment only.")
        st.stop()
except Exception:
    pass

import pandas as pd
from pathlib import Path
from datetime import date, timedelta
from typing import Dict
import sys

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.db import get_issues_with_grades, get_grading_stats, init_database
from utils.common import normalize_progress, parse_date
from utils.report import (
    get_default_week_range, get_previous_week_range,
    filter_issues_by_date, compute_weekly_stats,
    generate_donut_chart, export_chart_png, generate_report_text,
)
from utils.llm import is_llm_available
from config import get_team
from utils.auth import check_auth

st.set_page_config(
    page_title="Weekly Report - Discord Issue Dashboard",
    page_icon="📝",
    layout="wide",
)


def render_date_selector():
    """Date range selector: default Sat-Fri."""
    default_start, default_end = get_default_week_range()

    col1, col2, col3 = st.columns([2, 2, 1])
    with col1:
        week_start = st.date_input("Week Start (Sat)", value=default_start, key="wr_start")
    with col2:
        week_end = st.date_input("Week End (Fri)", value=default_end, key="wr_end")
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        period_label = f"{week_start.strftime('%b %d')} ~ {week_end.strftime('%b %d')}"
        st.markdown(f"**{period_label}**")

    return week_start, week_end, period_label


def render_grading_section():
    """Sync & Grade controls and progress."""
    st.markdown("### ⚙️ Quality Grading")

    stats = get_grading_stats()
    graded_pct = round(stats["graded"] / stats["total"] * 100) if stats["total"] > 0 else 0

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Issues", stats["total"])
    with col2:
        st.metric("Graded", stats["graded"])
    with col3:
        st.metric("Coverage", f"{graded_pct}%")
    with col4:
        if stats["ungraded"] > 0:
            st.warning(f"⚠️ {stats['ungraded']} ungraded")
        else:
            st.success("✅ All graded")

    if not is_llm_available():
        st.error("❌ LLM not available. Cursor CLI not found and API not configured.")
        return

    col1, col2 = st.columns(2)
    with col1:
        if st.button("🔄 Sync & Grade", use_container_width=True,
                      help="Pull latest data from Google Sheets, then grade only NEW or CHANGED issues with Claude. "
                           "Existing grades are kept. Fast for weekly incremental updates (~1 min for ~70 new items)."):
            _run_sync_and_grade()
    with col2:
        if st.button("🔁 Re-grade All", use_container_width=True,
                      help="Delete ALL existing grades and re-grade every issue from scratch. "
                           "Use when grading criteria changed or you want a fresh baseline. "
                           "Slow (~7 min for 500+ items)."):
            _run_regrade_all()


def _run_sync_and_grade():
    """Sync from Google Sheets, then grade ungraded issues."""
    with st.spinner("Syncing from Google Sheets..."):
        try:
            from scripts.sync_google_sheets import sync
            sync()
            st.cache_data.clear()
        except Exception as e:
            st.error(f"Sync failed: {e}")
            return

    with st.spinner("Grading with Claude..."):
        try:
            from utils.grading import run_grading
            progress_bar = st.progress(0)
            status_text = st.empty()

            def on_progress(done, total):
                progress_bar.progress(done / total if total > 0 else 1.0)
                status_text.text(f"Grading: {done}/{total}")

            result = run_grading(on_progress=on_progress)
            progress_bar.progress(1.0)
            status_text.empty()
            st.success(f"✅ {result['graded']} graded, {result['skipped']} skipped, {result['failed']} failed")
            st.rerun()
        except Exception as e:
            st.error(f"Grading failed: {e}")


def _run_regrade_all():
    """Clear all grades and re-grade everything."""
    from utils.db import get_connection
    with get_connection() as conn:
        conn.execute("DELETE FROM quality_grades")
        conn.commit()
    st.info("Grades cleared. Running full re-grade...")
    _run_sync_and_grade()


def render_donut_section(df: pd.DataFrame, week_start: date, week_end: date, period_label: str):
    """Render donut chart comparison."""
    st.markdown("---")
    st.markdown("### 🍩 Q&A Quality Comparison")

    df_week = filter_issues_by_date(df, week_start, week_end)
    stats = compute_weekly_stats(df_week)

    if stats["total"] == 0:
        st.info("No issues found for this period.")
        return stats, df_week

    fig = generate_donut_chart(stats["amd"], stats["dm"], period_label)
    st.plotly_chart(fig, use_container_width=False)

    try:
        png_bytes = export_chart_png(fig)
        st.download_button(
            label="📥 Download PNG",
            data=png_bytes,
            file_name=f"quality_comparison_{week_start}_{week_end}.png",
            mime="image/png",
        )
    except Exception as e:
        st.caption(f"PNG export unavailable: {e}")

    return stats, df_week


_REPORT_FILE = PROJECT_ROOT / "data" / "latest_report.txt"


def _load_saved_report() -> str:
    """Load report from disk (survives page refresh)."""
    try:
        if _REPORT_FILE.exists():
            return _REPORT_FILE.read_text(encoding="utf-8")
    except Exception:
        pass
    return ""


def _save_report(text: str):
    """Persist report to disk."""
    try:
        _REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
        _REPORT_FILE.write_text(text, encoding="utf-8")
    except Exception:
        pass


def render_report_section(
    current_stats: Dict, prev_stats: Dict,
    df_current: pd.DataFrame, period_label: str,
):
    """Generate and display the weekly report text."""
    st.markdown("---")
    st.markdown("### 📝 Weekly Report")

    if not is_llm_available():
        st.warning("LLM not available — cannot generate report text.")
        return

    if st.button("✨ Generate Report", use_container_width=True,
                  help="Call Claude to write the weekly report based on current stats. "
                       "Report is saved and persists across page refreshes until you regenerate."):
        with st.spinner("Claude is writing the report..."):
            try:
                report_text = generate_report_text(
                    current_stats, prev_stats, df_current, period_label,
                )
                st.session_state["report_text"] = report_text
                _save_report(report_text)
            except Exception as e:
                st.error(f"Report generation failed: {e}")
                return

    report = st.session_state.get("report_text") or _load_saved_report()
    if report:
        st.session_state["report_text"] = report
        st.text_area("Weekly Report (copy below)", value=report, height=500, key="report_output")


def render_detail_table(df: pd.DataFrame, week_start: date, week_end: date):
    """Filterable detail table with grades."""
    st.markdown("---")
    st.markdown("### 📋 Detail Table")

    df_week = filter_issues_by_date(df, week_start, week_end)

    if df_week.empty:
        st.info("No data for this period.")
        return

    col1, col2 = st.columns(2)
    with col1:
        team_filter = st.selectbox("Team", ["All", "AMD", "DM"], key="detail_team")
    with col2:
        grade_filter = st.selectbox("Grade", ["All", "High", "Medium", "Low", "Ungraded"], key="detail_grade")

    df_show = df_week.copy()
    df_show["team"] = df_show["owner"].apply(get_team)
    df_show["norm_progress"] = df_show["progress"].apply(normalize_progress)

    if team_filter != "All":
        df_show = df_show[df_show["team"] == team_filter]

    if grade_filter == "Ungraded":
        df_show = df_show[df_show["quality_grade"].isna() | (df_show["quality_grade"] == "")]
    elif grade_filter != "All":
        df_show = df_show[df_show["quality_grade"] == grade_filter]

    display_cols = ["id", "date", "team", "owner", "channel", "problem_category",
                    "category", "norm_progress", "quality_grade"]
    available_cols = [c for c in display_cols if c in df_show.columns]
    df_display = df_show[available_cols].copy()

    rename = {
        "norm_progress": "Status",
        "quality_grade": "Grade",
        "problem_category": "Problem Type",
        "category": "Issue Details",
    }
    df_display = df_display.rename(columns={k: v for k, v in rename.items() if k in df_display.columns})

    st.markdown(f"**{len(df_display)} records**")
    st.dataframe(df_display, use_container_width=True, height=400, hide_index=True)


def main():
    check_auth()

    st.title("📝 Weekly Report Generator")
    st.markdown("Quality grading, team comparison, and automated report generation.")
    st.markdown("---")

    init_database()

    # Date selector
    week_start, week_end, period_label = render_date_selector()

    # Grading controls
    render_grading_section()

    # Load all issues with grades
    issues = get_issues_with_grades()
    if not issues:
        st.warning("⚠️ No data. Run sync first.")
        return

    df = pd.DataFrame(issues)

    # Donut chart
    current_stats, df_current = render_donut_section(df, week_start, week_end, period_label)

    # Previous period stats for comparison
    prev_start, prev_end = get_previous_week_range(week_start, week_end)
    df_prev = filter_issues_by_date(df, prev_start, prev_end)
    prev_stats = compute_weekly_stats(df_prev)

    # Report text
    if isinstance(current_stats, dict) and current_stats.get("total", 0) > 0:
        render_report_section(current_stats, prev_stats, df_current, period_label)

    # Detail table
    render_detail_table(df, week_start, week_end)


if __name__ == "__main__":
    main()
