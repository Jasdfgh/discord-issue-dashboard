"""
Deprecated: Top Issue Details Chart
废弃原因: Category 字段太碎片化（98个不同值），无法产生有意义的聚合统计
废弃时间: 2026-02-05
替代方案: Problem Type Distribution 图表已提供分类洞察
"""

import plotly.express as px
import streamlit as st


def render_category_chart(df, period_label):
    """
    Render top categories (bar chart) - Issue Details
    
    DEPRECATED: This chart shows the Category field which has ~98 unique values,
    resulting in no meaningful aggregation (most items have count of 1-2).
    Use Problem Type Distribution instead.
    """
    st.subheader("📊 Top Issue Details")
    st.caption(f"Period: {period_label} (Top 10)")
    
    category_counts = df["category"].value_counts().head(10).reset_index()
    category_counts.columns = ["Category", "Count"]
    
    if category_counts.empty:
        st.info("No category data for this period")
        return
    
    category_counts["Category_Short"] = category_counts["Category"].apply(
        lambda x: (str(x)[:40] + "...") if len(str(x)) > 40 else str(x)
    )
    
    fig = px.bar(
        category_counts,
        x="Count",
        y="Category_Short",
        orientation="h",
        color="Count",
        color_continuous_scale="Purples",
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
