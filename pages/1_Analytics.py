"""
Analytics Page - Charts and Statistics with Time Range Comparison
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from pathlib import Path
from datetime import datetime, date, timedelta
import sys

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from utils.db import get_all_issues
from utils.common import (
    normalize_progress, parse_date,
    PROGRESS_COLORS, PROBLEM_CATEGORY_COLORS,
)
from utils.auth import check_auth

# ============== Page Config ==============
st.set_page_config(
    page_title="Analytics - Discord Issue Dashboard",
    page_icon="📈",
    layout="wide",
)


def get_period_range(mode, custom_start=None, custom_end=None):
    """
    Get current period and comparison period date ranges.
    
    Day/Week/Month: 最新周期 vs 上一个周期 (固定)
    Custom: 任意日期范围 vs 前一个同等长度的周期
    
    Returns: (current_start, current_end, prev_start, prev_end, period_label, compare_label)
    """
    today = date.today()
    
    if mode == "Day":
        current_start = today
        current_end = today
        prev_start = today - timedelta(days=1)
        prev_end = today - timedelta(days=1)
        period_label = f"{today.strftime('%b %d, %Y')}"
        compare_label = f"{prev_start.strftime('%b %d, %Y')}"
        
    elif mode == "Week":
        # This week (Monday to today)
        days_since_monday = today.weekday()
        current_start = today - timedelta(days=days_since_monday)
        current_end = today
        # Last week (Monday to Sunday)
        prev_start = current_start - timedelta(days=7)
        prev_end = current_start - timedelta(days=1)
        period_label = f"{current_start.strftime('%b %d')} - {current_end.strftime('%b %d, %Y')}"
        compare_label = f"{prev_start.strftime('%b %d')} - {prev_end.strftime('%b %d, %Y')}"
        
    elif mode == "Month":
        # This month
        current_start = today.replace(day=1)
        current_end = today
        # Last month
        last_month_end = current_start - timedelta(days=1)
        prev_start = last_month_end.replace(day=1)
        prev_end = last_month_end
        period_label = f"{current_start.strftime('%b %Y')}"
        compare_label = f"{prev_start.strftime('%b %Y')}"
        
    else:  # Custom - 任意日期范围，对比前一个同等长度周期
        current_start = custom_start or (today - timedelta(days=6))
        current_end = custom_end or today
        # 计算选定范围的天数，向前推同等长度
        span = (current_end - current_start).days + 1  # 包含首尾
        prev_end = current_start - timedelta(days=1)
        prev_start = prev_end - timedelta(days=span - 1)
        period_label = f"{current_start.strftime('%b %d')} - {current_end.strftime('%b %d, %Y')} ({span} days)"
        compare_label = f"{prev_start.strftime('%b %d')} - {prev_end.strftime('%b %d, %Y')} ({span} days)"
    
    return current_start, current_end, prev_start, prev_end, period_label, compare_label


def filter_by_date_range(df, start_date, end_date):
    """Filter DataFrame by date range"""
    def in_range(row_date):
        parsed = parse_date(row_date)
        if parsed is None:
            return False
        d = parsed.date()
        return start_date <= d <= end_date
    
    return df[df["date"].apply(in_range)]


def calculate_stats(df):
    """Calculate statistics for a DataFrame"""
    df = df.copy()
    df["normalized_progress"] = df["progress"].apply(normalize_progress)
    
    total = len(df)
    done = len(df[df["normalized_progress"] == "Done"])
    in_progress = len(df[df["normalized_progress"] == "In Progress"])
    pending = len(df[df["normalized_progress"] == "Pending"])
    blocked = len(df[df["normalized_progress"] == "Blocked"])
    rate = (done / total * 100) if total > 0 else 0
    
    return {
        "total": total,
        "done": done,
        "in_progress": in_progress,
        "pending": pending,
        "blocked": blocked,
        "rate": rate,
    }


def render_time_selector():
    """Render time range selector"""
    st.markdown("### 📅 Time Range")
    
    col1, col2 = st.columns([2, 3])
    
    with col1:
        mode = st.radio(
            "Select period",
            options=["Day", "Week", "Month", "Custom"],
            horizontal=True,
            label_visibility="collapsed",
        )
    
    custom_start = None
    custom_end = None
    with col2:
        if mode == "Custom":
            today = date.today()
            custom_dates = st.date_input(
                "Select date range",
                value=(today - timedelta(days=6), today),
                key="analytics_custom_dates",
            )
            if isinstance(custom_dates, tuple) and len(custom_dates) == 2:
                custom_start, custom_end = custom_dates
    
    return mode, custom_start, custom_end


def render_comparison_metrics(current_stats, prev_stats, period_label, compare_label):
    """Render metrics with period comparison"""
    
    def get_delta(current, prev):
        diff = current - prev
        if diff > 0:
            return f"+{diff}"
        elif diff < 0:
            return str(diff)
        return "0"
    
    def get_rate_delta(current, prev):
        diff = current - prev
        if diff > 0:
            return f"+{diff:.1f}%"
        elif diff < 0:
            return f"{diff:.1f}%"
        return "0%"
    
    # Period info
    st.markdown(f"**Current Period:** {period_label}")
    st.markdown(f"**Compare To:** {compare_label}")
    st.markdown("")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        delta = get_delta(current_stats["total"], prev_stats["total"])
        st.metric(
            label="📋 Total Issues",
            value=current_stats["total"],
            delta=f"{delta} vs prev",
        )
    
    with col2:
        delta = get_delta(current_stats["done"], prev_stats["done"])
        st.metric(
            label="✅ Done",
            value=current_stats["done"],
            delta=f"{delta} vs prev",
        )
    
    with col3:
        delta = get_delta(current_stats["in_progress"], prev_stats["in_progress"])
        st.metric(
            label="🔄 In Progress",
            value=current_stats["in_progress"],
            delta=f"{delta} vs prev",
            delta_color="off",
        )
    
    with col4:
        delta = get_delta(current_stats["pending"], prev_stats["pending"])
        st.metric(
            label="⏸️ Pending",
            value=current_stats["pending"],
            delta=f"{delta} vs prev",
            delta_color="inverse",
            help="May indicate blocked/waiting issues",
        )
    
    with col5:
        delta = get_rate_delta(current_stats["rate"], prev_stats["rate"])
        st.metric(
            label="📈 Completion Rate",
            value=f"{current_stats['rate']:.1f}%",
            delta=f"{delta} vs prev",
        )
    
    # Data source explanation
    with st.expander("ℹ️ How is this calculated?"):
        st.markdown(f"""
        **Calculation Method:**
        - **Total Issues**: Count of all issues in the selected period
        - **Done**: Count of issues with Progress = "Done"
        - **In Progress**: Count of issues with Progress = "In Progress" or "Pending"
        - **Completion Rate**: Done ÷ Total × 100%
        
        **Current Period:** {period_label}
        - Total: {current_stats['total']} issues
        - Done: {current_stats['done']} issues
        - Rate: {current_stats['done']} ÷ {current_stats['total']} = {current_stats['rate']:.1f}%
        
        **Comparison Period:** {compare_label}
        - Total: {prev_stats['total']} issues
        - Done: {prev_stats['done']} issues
        - Rate: {prev_stats['rate']:.1f}%
        
        **Note:** Issues are filtered by their `Date` field. Issues with unparseable dates are excluded from time-based analysis.
        """)


def render_progress_chart(df, period_label):
    """Render progress distribution (pie chart)"""
    st.subheader("📊 Progress Distribution")
    st.caption(f"Period: {period_label}")
    
    df = df.copy()
    df["normalized_progress"] = df["progress"].apply(normalize_progress)
    
    progress_counts = df["normalized_progress"].value_counts().reset_index()
    progress_counts.columns = ["Progress", "Count"]
    
    if progress_counts.empty:
        st.info("No data for this period")
        return
    
    colors = [PROGRESS_COLORS.get(p, "#9ca3af") for p in progress_counts["Progress"]]
    
    fig = go.Figure(data=[go.Pie(
        labels=progress_counts["Progress"],
        values=progress_counts["Count"],
        marker_colors=colors,
        hole=0.4,
        textinfo="label+percent",
        textposition="outside",
    )])
    
    fig.update_layout(
        height=350,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        margin=dict(t=20, b=20),
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_channel_chart(df, period_label):
    """Render channel distribution (bar chart)"""
    st.subheader("📊 Issues by Channel")
    st.caption(f"Period: {period_label} (Top 10)")
    
    channel_counts = df["channel"].value_counts().head(10).reset_index()
    channel_counts.columns = ["Channel", "Count"]
    
    if channel_counts.empty:
        st.info("No channel data for this period")
        return
    
    fig = px.bar(
        channel_counts,
        x="Count",
        y="Channel",
        orientation="h",
        color="Count",
        color_continuous_scale="Blues",
    )
    
    fig.update_layout(
        xaxis_title="Number of Issues",
        yaxis_title="",
        height=350,
        showlegend=False,
        yaxis=dict(autorange="reversed"),
        margin=dict(t=20, b=20),
    )
    
    fig.update_coloraxes(showscale=False)
    
    st.plotly_chart(fig, use_container_width=True)


def render_trend_chart(df_all):
    """Render issue trend over time (line chart) with independent time selector"""
    st.subheader("📈 Issue Trend Over Time")
    
    # Independent time range selector for trend chart
    # Options order: 7 days, 30 days (default), 90 days, All time, Custom
    col1, col2, col3 = st.columns([2, 1, 1])
    
    with col2:
        trend_range = st.selectbox(
            "Time range",
            options=["7 days", "30 days", "90 days", "All time", "Custom"],
            index=1,  # Default: 30 days (second option)
            key="trend_time_range",
        )
    
    # Custom date range picker
    custom_start = None
    custom_end = None
    if trend_range == "Custom":
        with col3:
            custom_dates = st.date_input(
                "Date range",
                value=(date.today() - timedelta(days=14), date.today()),
                key="trend_custom_dates",
            )
            if isinstance(custom_dates, tuple) and len(custom_dates) == 2:
                custom_start, custom_end = custom_dates
    
    df = df_all.copy()
    df["parsed_date"] = df["date"].apply(parse_date)
    df_valid = df[df["parsed_date"].notna()].copy()
    
    if df_valid.empty:
        st.info("No valid date data for trend chart")
        return
    
    df_valid["date_only"] = df_valid["parsed_date"].dt.date
    
    # Filter by selected time range
    today = date.today()
    if trend_range == "7 days":
        start_date = today - timedelta(days=7)
        df_valid = df_valid[df_valid["date_only"] >= start_date]
    elif trend_range == "30 days":
        start_date = today - timedelta(days=30)
        df_valid = df_valid[df_valid["date_only"] >= start_date]
    elif trend_range == "90 days":
        start_date = today - timedelta(days=90)
        df_valid = df_valid[df_valid["date_only"] >= start_date]
    elif trend_range == "Custom" and custom_start and custom_end:
        df_valid = df_valid[(df_valid["date_only"] >= custom_start) & (df_valid["date_only"] <= custom_end)]
    # "All time" - no filter
    
    if df_valid.empty:
        st.info(f"No data for the selected time range ({trend_range})")
        return
    
    daily_counts = df_valid.groupby("date_only").size().reset_index(name="count")
    daily_counts = daily_counts.sort_values("date_only")
    
    # Show date range info
    if not daily_counts.empty:
        date_min = daily_counts["date_only"].min()
        date_max = daily_counts["date_only"].max()
        st.caption(f"Showing: {date_min.strftime('%b %d, %Y')} - {date_max.strftime('%b %d, %Y')} ({len(daily_counts)} days with data)")
    
    fig = px.line(
        daily_counts,
        x="date_only",
        y="count",
        markers=True,
        labels={"date_only": "Date", "count": "Number of Issues"},
    )
    
    fig.update_layout(
        xaxis_title="Date",
        yaxis_title="Issues",
        hovermode="x unified",
        height=350,
        margin=dict(t=20, b=20),
    )
    
    fig.update_traces(
        line_color="#667eea",
        marker_color="#667eea",
        line_width=2,
        marker_size=8,
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_problem_category_chart(df, period_label):
    """Render problem category distribution (pie chart) - Problem Type"""
    st.subheader("🏷️ Problem Type Distribution")
    st.caption(f"Period: {period_label}")
    
    if "problem_category" not in df.columns:
        st.info("Problem Category data not available")
        return
    
    # Filter out empty values
    df_valid = df[df["problem_category"].notna() & (df["problem_category"] != "")].copy()
    
    if df_valid.empty:
        st.info("No Problem Category data for this period")
        return
    
    problem_counts = df_valid["problem_category"].value_counts().reset_index()
    problem_counts.columns = ["Problem Type", "Count"]
    
    # Get colors
    colors = [PROBLEM_CATEGORY_COLORS.get(p, "#6b7280") for p in problem_counts["Problem Type"]]
    
    fig = go.Figure(data=[go.Pie(
        labels=problem_counts["Problem Type"],
        values=problem_counts["Count"],
        marker_colors=colors,
        hole=0.4,
        textinfo="label+percent",
        textposition="outside",
    )])
    
    fig.update_layout(
        height=350,
        showlegend=True,
        legend=dict(orientation="h", yanchor="bottom", y=-0.2, xanchor="center", x=0.5),
        margin=dict(t=20, b=20),
    )
    
    st.plotly_chart(fig, use_container_width=True)


def render_problem_category_progress_chart(df, period_label):
    """Render problem category by progress (stacked bar chart)"""
    st.subheader("📊 Problem Type by Status")
    st.caption(f"Period: {period_label}")
    
    if "problem_category" not in df.columns:
        st.info("Problem Category data not available")
        return
    
    df_valid = df[df["problem_category"].notna() & (df["problem_category"] != "")].copy()
    
    if df_valid.empty:
        st.info("No Problem Category data for this period")
        return
    
    df_valid["normalized_progress"] = df_valid["progress"].apply(normalize_progress)
    
    # Group by problem_category and progress
    grouped = df_valid.groupby(["problem_category", "normalized_progress"]).size().reset_index(name="count")
    
    fig = px.bar(
        grouped,
        x="problem_category",
        y="count",
        color="normalized_progress",
        color_discrete_map=PROGRESS_COLORS,
        barmode="stack",
        labels={
            "problem_category": "Problem Type",
            "count": "Number of Issues",
            "normalized_progress": "Status"
        }
    )
    
    fig.update_layout(
        height=350,
        legend=dict(orientation="h", yanchor="bottom", y=-0.3, xanchor="center", x=0.5),
        margin=dict(t=20, b=20),
        xaxis_tickangle=-45,
    )
    
    st.plotly_chart(fig, use_container_width=True)


def main():
    """Main function"""
    # Auth check (blocks with login page if REQUIRE_AUTH is set)
    check_auth()
    
    st.title("📈 Analytics")
    st.markdown("Data analysis with time range comparison")
    st.markdown("---")
    
    # Load all data
    issues = get_all_issues()
    
    if not issues:
        st.warning("⚠️ No data available. Run sync script first.")
        return
    
    df_all = pd.DataFrame(issues)
    
    # Time range selector
    mode, custom_start, custom_end = render_time_selector()
    
    # Get period ranges
    current_start, current_end, prev_start, prev_end, period_label, compare_label = get_period_range(mode, custom_start, custom_end)
    
    # Filter data by periods
    df_current = filter_by_date_range(df_all, current_start, current_end)
    df_prev = filter_by_date_range(df_all, prev_start, prev_end)
    
    # Calculate stats
    current_stats = calculate_stats(df_current)
    prev_stats = calculate_stats(df_prev)
    
    st.markdown("---")
    
    # Comparison metrics
    render_comparison_metrics(current_stats, prev_stats, period_label, compare_label)
    
    st.markdown("---")
    
    # Charts - Row 1: Progress & Channel
    col1, col2 = st.columns(2)
    
    with col1:
        render_progress_chart(df_current, period_label)
    
    with col2:
        render_channel_chart(df_current, period_label)
    
    st.markdown("---")
    
    # Charts - Row 2: Problem Category (新增)
    col1, col2 = st.columns(2)
    
    with col1:
        render_problem_category_chart(df_current, period_label)
    
    with col2:
        render_problem_category_progress_chart(df_current, period_label)
    
    st.markdown("---")
    
    # Trend chart (independent time selector)
    render_trend_chart(df_all)


if __name__ == "__main__":
    main()
