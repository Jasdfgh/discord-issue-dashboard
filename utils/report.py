"""
Weekly Report Generator — statistics, donut chart, and report text.
"""

import io
import logging
from datetime import date, timedelta
from typing import Dict, Any, List, Optional, Tuple

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import get_team
from utils.common import normalize_progress, parse_date

logger = logging.getLogger("discord_dashboard.report")


# ============== Date Range ==============

def get_default_week_range() -> Tuple[date, date]:
    """Default report period: current week (most recent Saturday → today)."""
    today = date.today()
    days_since_saturday = (today.weekday() + 2) % 7
    saturday = today - timedelta(days=days_since_saturday)
    return saturday, today


def get_previous_week_range(week_start: date, week_end: date) -> Tuple[date, date]:
    """Previous period of equal length, ending the day before week_start."""
    span = (week_end - week_start).days + 1
    prev_end = week_start - timedelta(days=1)
    prev_start = prev_end - timedelta(days=span - 1)
    return prev_start, prev_end


# ============== Statistics ==============

def filter_issues_by_date(df: pd.DataFrame, start: date, end: date) -> pd.DataFrame:
    """Filter DataFrame rows whose 'date' falls within [start, end]."""
    def in_range(d):
        parsed = parse_date(d)
        if parsed is None:
            return False
        return start <= parsed.date() <= end
    return df[df["date"].apply(in_range)]


def compute_weekly_stats(df: pd.DataFrame) -> Dict[str, Any]:
    """Compute stats for a filtered period DataFrame (already filtered by date)."""
    df = df.copy()
    df["team"] = df["owner"].apply(get_team)
    df["norm_progress"] = df["progress"].apply(normalize_progress)
    df["grade"] = df.get("quality_grade", pd.Series(dtype=str))

    total = len(df)
    done = len(df[df["norm_progress"] == "Done"])
    in_progress = len(df[df["norm_progress"].isin(["In Progress", "Pending"])])

    def team_quality(team_name: str) -> Dict[str, Any]:
        t = df[df["team"] == team_name]
        t_total = len(t)
        high = len(t[t["grade"] == "High"])
        medium = len(t[t["grade"] == "Medium"])
        low = len(t[t["grade"] == "Low"])
        hm = high + medium
        hm_pct = round(hm / t_total * 100, 1) if t_total > 0 else 0
        low_pct = round(low / t_total * 100, 1) if t_total > 0 else 0
        return {
            "total": t_total, "high": high, "medium": medium, "low": low,
            "hm": hm, "hm_pct": hm_pct, "low_pct": low_pct,
        }

    return {
        "total": total,
        "done": done,
        "in_progress": in_progress,
        "completion_rate": round(done / total * 100, 1) if total > 0 else 0,
        "amd": team_quality("AMD"),
        "dm": team_quality("DM"),
    }


# ============== Donut Chart ==============

COLOR_HIGH = "#2ecc71"    # green
COLOR_MEDIUM = "#f39c12"  # amber
COLOR_LOW = "#e74c3c"     # red

def generate_donut_chart(
    amd_stats: Dict[str, Any],
    dm_stats: Dict[str, Any],
    period_label: str,
) -> go.Figure:
    """Create side-by-side donut charts: DM (left) vs AMD (right), H/M/L three segments."""
    fig = make_subplots(
        rows=1, cols=2,
        specs=[[{"type": "domain"}, {"type": "domain"}]],
        subplot_titles=[
            f"<b>Data Monsters Team</b><br>(Total: {dm_stats['total']} items)",
            f"<b>AMD Team</b><br>(Total: {amd_stats['total']} items)",
        ],
    )

    for col, stats in [(1, dm_stats), (2, amd_stats)]:
        if stats["total"] == 0:
            values, labels, colors = [1], ["No Data"], ["#cccccc"]
        else:
            values = [stats["high"], stats["medium"], stats["low"]]
            labels = ["High", "Medium", "Low"]
            colors = [COLOR_HIGH, COLOR_MEDIUM, COLOR_LOW]

        fig.add_trace(go.Pie(
            values=values,
            labels=labels,
            marker_colors=colors,
            hole=0.55,
            textinfo="label+percent",
            textfont_size=14,
            textposition="outside",
            showlegend=(col == 1),
            sort=False,
        ), row=1, col=col)

    fig.add_annotation(
        text=f"<b>{dm_stats['total']}</b><br><span style='font-size:12px'>total</span>",
        x=0.19, y=0.5, font_size=32, showarrow=False, xref="paper", yref="paper",
    )
    fig.add_annotation(
        text=f"<b>{amd_stats['total']}</b><br><span style='font-size:12px'>total</span>",
        x=0.81, y=0.5, font_size=32, showarrow=False, xref="paper", yref="paper",
    )

    fig.update_layout(
        title_text=f"<b>Q&A Quality Ratio Comparison: AMD vs Data Monster ({period_label})</b>",
        title_x=0.5,
        title_font_size=16,
        paper_bgcolor="white",
        plot_bgcolor="white",
        height=500,
        width=1000,
        margin=dict(t=80, b=60, l=40, r=40),
        legend=dict(
            orientation="h", yanchor="bottom", y=-0.10,
            xanchor="center", x=0.5, font_size=13,
        ),
    )

    for ann in fig.layout.annotations:
        if ann.text and ("<b>Data Monsters" in str(ann.text) or "<b>AMD" in str(ann.text)):
            ann.font = dict(size=14)

    return fig


def export_chart_png(fig: go.Figure) -> bytes:
    """Export Plotly figure to PNG bytes (white background, high-res)."""
    return fig.to_image(format="png", width=960, height=480, scale=2)


# ============== Report Text ==============

REPORT_WRITING_PROMPT = """\
You are the AMD community support team's weekly report writing assistant.

STRICT RULES:
- Write in English ONLY. No Chinese, no extra commentary, no "notes" section.
- Output ONLY the report in the exact template format below. Nothing else before or after.
- All numbers must come from the provided statistics. Do NOT fabricate data.
- Examples in section 2 MUST be from the AMD team only (provided below). Never use Data Monsters examples.
- If a field is unavailable, write "N/A" — do not guess.

Statistics (JSON):
{stats_json}

High quality examples from AMD team this week (pick the best 2):
{examples_text}

Difficulties (from Pending/Blocked items):
{difficulties_text}

OUTPUT THIS EXACT FORMAT:

0) Q&A Quality Comparison
**Our team's High+Medium quality ratio: {{amd_hm_pct}}%.** Data Monsters team: {{dm_hm_pct}}% High+Medium, {{dm_low_pct}}% Low quality.
[Donut chart attached]

1) Overall, the number of total issues we followed up are **{{total}}**, in which **{{done}}** are done, **{{in_progress}}** are in progress, completion rate is **{{completion_rate}}%** which {{increases/decreases}} by **{{rate_change}}** compared to last period, total issues changed by **{{total_change}}**.

2) Top issues mainly focus on **{{topic_1}}**, **{{topic_2}}**, and we are currently either addressing these critical issues or escalate them to internal teams, finally contributing to the AMD AI ecosystem.
**High quality Q&A examples (AMD team):**
- **{{example_1_title}}**: {{1-2 sentence summary}}
- **{{example_2_title}}**: {{1-2 sentence summary}}

3) *[To be filled: Guides released on Discord channels]*

4) *[To be filled: Blog posts written/released]*

5) {{difficulties_or_no_blockers}}

6) *[To be filled: Community feedback, if any]*

7) *[To be filled: Efficiency improvements, if any]*

8) Quality comparison chart attached. **AMD team: {{amd_total}} items, {{amd_hm_pct}}% High+Medium quality. Data Monsters: {{dm_total}} items, {{dm_hm_pct}}% High+Medium, {{dm_low_pct}}% Low quality.**"""


def _get_high_examples(df: pd.DataFrame, n: int = 4) -> str:
    """Get top High-quality AMD examples for Claude to pick from."""
    df = df.copy()
    df["team"] = df["owner"].apply(get_team)
    amd_high = df[(df["team"] == "AMD") & (df.get("quality_grade", pd.Series(dtype=str)) == "High")]
    if amd_high.empty:
        return "No High-quality AMD examples found this week."
    samples = amd_high.head(n)
    lines = []
    for _, row in samples.iterrows():
        lines.append(
            f"- [{row.get('category', 'N/A')}] Issue: {str(row.get('issue', ''))[:150]} | "
            f"Reply: {str(row.get('reply_approach', ''))[:200]}"
        )
    return "\n".join(lines)


def _get_difficulties(df: pd.DataFrame) -> str:
    """Extract difficulties from Pending/Blocked items."""
    df = df.copy()
    df["norm_progress"] = df["progress"].apply(normalize_progress)
    blocked = df[df["norm_progress"].isin(["Pending", "Blocked"])]
    if blocked.empty:
        return "No major blockers this week."
    lines = []
    for _, row in blocked.head(5).iterrows():
        lines.append(f"- {row.get('category', 'N/A')}: {str(row.get('issue', ''))[:100]}")
    return "\n".join(lines)


def generate_report_text(
    current_stats: Dict[str, Any],
    prev_stats: Dict[str, Any],
    df_current: pd.DataFrame,
    period_label: str,
) -> str:
    """Call Claude to generate the weekly report text."""
    import json
    from utils.llm import call_llm

    rate_diff = current_stats["completion_rate"] - prev_stats["completion_rate"]
    total_diff = current_stats["total"] - prev_stats["total"]

    stats_for_prompt = {
        "period": period_label,
        "total": current_stats["total"],
        "done": current_stats["done"],
        "in_progress": current_stats["in_progress"],
        "completion_rate": current_stats["completion_rate"],
        "rate_change": f"{rate_diff:+.1f}%",
        "total_change": f"{total_diff:+d}",
        "amd_total": current_stats["amd"]["total"],
        "amd_hm_pct": current_stats["amd"]["hm_pct"],
        "dm_total": current_stats["dm"]["total"],
        "dm_hm_pct": current_stats["dm"]["hm_pct"],
        "dm_low_pct": current_stats["dm"]["low_pct"],
    }

    examples_text = _get_high_examples(df_current)
    difficulties_text = _get_difficulties(df_current)

    prompt = REPORT_WRITING_PROMPT.format(
        stats_json=json.dumps(stats_for_prompt, indent=2),
        examples_text=examples_text,
        difficulties_text=difficulties_text,
    )

    return call_llm(prompt, timeout=180)
