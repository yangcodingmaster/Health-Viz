"""
visualize.py
------------
Generates an interactive HTML dashboard from a parsed Apple Health export.
The output is a single self-contained file — open it in any browser.

Visual style: Apple Health dark theme
  - Deep dark background (#1C1C1E) matching iOS dark mode
  - Per-metric accent colors taken directly from the Health app:
      Sleep      → purple  #BF5AF2
      Heart Rate → pink    #FF375F
      Steps      → green   #30D158  /  red #FF453A
  - Area fills with glow-like transparency simulate the Health app gradient look
  - Subtle grid lines, SF-style font stack

Layout (2 × 2 grid):
  [top-left]     Nightly sleep duration
  [top-right]    Resting heart rate trend
  [bottom-left]  Daily step count
  [bottom-right] Key statistics table (last 30 days)

Usage:
    python src/visualize.py

Place your Apple Health export.xml in the data/ folder first.
Output: dashboard.html
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Ensure src/ is importable when running from the project root
sys.path.insert(0, str(Path(__file__).parent))
from parse_health import load_sleep, load_heart_rate, load_steps


# ---------------------------------------------------------------------------
# Apple Health dark-mode color palette
# ---------------------------------------------------------------------------

# Backgrounds (iOS system colors, dark mode)
BG_COLOR   = "#1C1C1E"            # iOS systemBackground
CARD_COLOR = "#2C2C2E"            # iOS secondarySystemBackground
CARD2_COLOR = "#3A3A3C"           # iOS tertiarySystemBackground

# Typography
TEXT_PRIMARY   = "#FFFFFF"
TEXT_SECONDARY = "rgba(235,235,245,0.6)"   # iOS secondaryLabel

# Grid & axes
GRID_COLOR = "rgba(255,255,255,0.07)"
AXIS_COLOR = "rgba(255,255,255,0.18)"
ZERO_COLOR = "rgba(255,255,255,0.12)"

# Sleep — Apple purple
SLEEP_LINE = "#BF5AF2"
SLEEP_FILL = "rgba(191,90,242,0.20)"
SLEEP_GLOW = "rgba(191,90,242,0.07)"

# Heart Rate — Apple pink/red
HR_LINE    = "#FF375F"
HR_FILL    = "rgba(255,55,95,0.18)"
HR_GLOW    = "rgba(255,55,95,0.06)"

# Steps — Activity ring green / red
STEPS_HIT  = "#30D158"             # Apple system green
STEPS_MISS = "#FF453A"             # Apple system red
STEPS_FILL_HIT  = "rgba(48,209,88,0.75)"
STEPS_FILL_MISS = "rgba(255,69,58,0.75)"

# Reference / goal lines
GOAL_LINE  = "rgba(255,255,255,0.22)"
GOAL_ANNOT = "rgba(235,235,245,0.45)"

# Font stack (mimics SF Pro on Apple devices, falls back gracefully)
FONT_FAMILY = "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'Helvetica Neue', Arial, sans-serif"

ROLLING_WINDOW = 7
STEPS_GOAL     = 10_000
OUTPUT_PATH    = "dashboard.html"


# ---------------------------------------------------------------------------
# Helper: rolling average
# ---------------------------------------------------------------------------

def _rolling(series: pd.Series, window: int = ROLLING_WINDOW) -> pd.Series:
    """Centered rolling mean; requires at least 3 observations."""
    return series.rolling(window, center=True, min_periods=3).mean()


# ---------------------------------------------------------------------------
# Trace builders
# ---------------------------------------------------------------------------

def _sleep_traces(sleep_df: pd.DataFrame) -> list[go.BaseTraceType]:
    """
    Two traces:
      1. Translucent filled area for raw nightly sleep (background glow)
      2. Bright filled area + line for 7-day rolling average (foreground)
    """
    if sleep_df.empty:
        return []

    rolled = _rolling(sleep_df["sleep_hours"])

    # Raw nightly — very soft glow fill, no visible line
    raw_area = go.Scatter(
        x=sleep_df["date"],
        y=sleep_df["sleep_hours"].round(2),
        name="Nightly sleep",
        mode="none",                       # no markers or line, just fill
        fill="tozeroy",
        fillcolor=SLEEP_GLOW,
        hovertemplate="%{x|%b %d}<br><b>%{y:.1f} h</b><extra></extra>",
        hoverlabel=dict(bgcolor=CARD_COLOR, font_color=SLEEP_LINE),
    )

    # Rolling average — solid line + soft fill underneath
    avg_fill = go.Scatter(
        x=sleep_df["date"],
        y=rolled.round(2),
        name=f"{ROLLING_WINDOW}-day avg",
        mode="lines",
        fill="tozeroy",
        fillcolor=SLEEP_FILL,
        line=dict(color=SLEEP_LINE, width=2.5, shape="spline", smoothing=0.8),
        hovertemplate="%{x|%b %d}<br><b>avg %{y:.1f} h</b><extra></extra>",
        hoverlabel=dict(bgcolor=CARD_COLOR, font_color=SLEEP_LINE),
    )

    return [raw_area, avg_fill]


def _hr_traces(hr_df: pd.DataFrame) -> list[go.BaseTraceType]:
    """
    Two traces:
      1. Translucent filled area for raw daily-min HR (background glow)
      2. Bright filled area + line for 7-day rolling average (foreground)
    """
    if hr_df.empty:
        return []

    rolled = _rolling(hr_df["hr_min"])

    raw_area = go.Scatter(
        x=hr_df["date"],
        y=hr_df["hr_min"].round(1),
        name="Daily min HR",
        mode="none",
        fill="tozeroy",
        fillcolor=HR_GLOW,
        hovertemplate="%{x|%b %d}<br><b>%{y:.0f} bpm</b><extra></extra>",
        hoverlabel=dict(bgcolor=CARD_COLOR, font_color=HR_LINE),
    )

    avg_fill = go.Scatter(
        x=hr_df["date"],
        y=rolled.round(1),
        name=f"{ROLLING_WINDOW}-day avg",
        mode="lines",
        fill="tozeroy",
        fillcolor=HR_FILL,
        line=dict(color=HR_LINE, width=2.5, shape="spline", smoothing=0.8),
        hovertemplate="%{x|%b %d}<br><b>avg %{y:.0f} bpm</b><extra></extra>",
        hoverlabel=dict(bgcolor=CARD_COLOR, font_color=HR_LINE),
    )

    return [raw_area, avg_fill]


def _steps_traces(steps_df: pd.DataFrame) -> list[go.BaseTraceType]:
    """
    Color-coded bars — Apple green when goal is met, Apple red when missed.
    Uses two separate Bar traces (one per category) so the legend is clean.
    """
    if steps_df.empty:
        return []

    hit  = steps_df[steps_df["steps"] >= STEPS_GOAL]
    miss = steps_df[steps_df["steps"] <  STEPS_GOAL]

    traces = []
    if not hit.empty:
        traces.append(go.Bar(
            x=hit["date"], y=hit["steps"],
            name=f"≥ {STEPS_GOAL:,} steps",
            marker_color=STEPS_FILL_HIT,
            marker_line_width=0,
            hovertemplate="%{x|%b %d}<br><b>%{y:,} steps</b><extra></extra>",
            hoverlabel=dict(bgcolor=CARD_COLOR, font_color=STEPS_HIT),
        ))
    if not miss.empty:
        traces.append(go.Bar(
            x=miss["date"], y=miss["steps"],
            name=f"< {STEPS_GOAL:,} steps",
            marker_color=STEPS_FILL_MISS,
            marker_line_width=0,
            hovertemplate="%{x|%b %d}<br><b>%{y:,} steps</b><extra></extra>",
            hoverlabel=dict(bgcolor=CARD_COLOR, font_color=STEPS_MISS),
        ))

    return traces


def _stats_table(sleep_df: pd.DataFrame, hr_df: pd.DataFrame,
                 steps_df: pd.DataFrame) -> go.Table:
    """
    Dark-themed statistics table matching the dashboard palette.
    Values are colored with their metric accent color.
    """
    cutoff = pd.Timestamp.today() - pd.Timedelta(days=30)

    def recent(df):
        return df[df["date"] >= cutoff] if not df.empty else df

    r_sleep = recent(sleep_df)
    r_hr    = recent(hr_df)
    r_steps = recent(steps_df)

    metrics, values, value_colors = [], [], []

    # ── Sleep ──
    if not r_sleep.empty:
        avg_s  = r_sleep["sleep_hours"].mean()
        days_s = int((r_sleep["sleep_hours"] >= 7).sum())
        for m, v in [
            ("Avg nightly sleep",  f"{avg_s:.1f} h"),
            ("Days ≥ 7 h",         f"{days_s} / {len(r_sleep)}"),
        ]:
            metrics.append(m); values.append(v); value_colors.append(SLEEP_LINE)
    else:
        metrics.append("Sleep"); values.append("—"); value_colors.append(TEXT_SECONDARY)

    # ── Heart Rate ──
    if not r_hr.empty:
        avg_hr = r_hr["hr_min"].mean()
        min_hr = int(r_hr["hr_min"].min())
        for m, v in [
            ("Avg resting HR", f"{avg_hr:.0f} bpm"),
            ("Min resting HR", f"{min_hr} bpm"),
        ]:
            metrics.append(m); values.append(v); value_colors.append(HR_LINE)
    else:
        metrics.append("Heart rate"); values.append("—"); value_colors.append(TEXT_SECONDARY)

    # ── Steps ──
    if not r_steps.empty:
        avg_st  = r_steps["steps"].mean()
        days_st = int((r_steps["steps"] >= STEPS_GOAL).sum())
        for m, v in [
            ("Avg daily steps",        f"{avg_st:,.0f}"),
            (f"Days ≥ {STEPS_GOAL:,}", f"{days_st} / {len(r_steps)}"),
        ]:
            metrics.append(m); values.append(v); value_colors.append(STEPS_HIT)
    else:
        metrics.append("Steps"); values.append("—"); value_colors.append(TEXT_SECONDARY)

    return go.Table(
        columnwidth=[62, 38],
        header=dict(
            values=["<b>Last 30 days</b>", "<b>Value</b>"],
            fill_color=CARD2_COLOR,
            align="left",
            font=dict(color=TEXT_PRIMARY, size=12, family=FONT_FAMILY),
            line_color=AXIS_COLOR,
            height=32,
        ),
        cells=dict(
            values=[metrics, values],
            fill_color=[CARD_COLOR, CARD_COLOR],
            align=["left", "right"],
            font=dict(
                color=[TEXT_SECONDARY, value_colors],
                size=12,
                family=FONT_FAMILY,
            ),
            line_color=GRID_COLOR,
            height=30,
        ),
    )


# ---------------------------------------------------------------------------
# Dashboard assembler
# ---------------------------------------------------------------------------

def build_dashboard(sleep_df: pd.DataFrame, hr_df: pd.DataFrame,
                    steps_df: pd.DataFrame) -> go.Figure:
    """Assemble the four panels into a single interactive Plotly figure."""

    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "  Sleep",
            "  Heart Rate",
            "  Steps",
            "",
        ),
        specs=[
            [{"type": "xy"},    {"type": "xy"}],
            [{"type": "xy"},    {"type": "table"}],
        ],
        vertical_spacing=0.15,
        horizontal_spacing=0.08,
    )

    # ── Sleep ────────────────────────────────────────────────────────────────
    for trace in _sleep_traces(sleep_df):
        fig.add_trace(trace, row=1, col=1)
    if not sleep_df.empty:
        for y_ref, label, dash in [(7, "7 h", "dash"), (9, "9 h", "dot")]:
            fig.add_hline(
                y=y_ref, row=1, col=1,
                line=dict(color=GOAL_LINE, dash=dash, width=1),
                annotation_text=label,
                annotation_font=dict(color=GOAL_ANNOT, size=10),
                annotation_position="top right",
            )

    # ── Heart Rate ───────────────────────────────────────────────────────────
    for trace in _hr_traces(hr_df):
        fig.add_trace(trace, row=1, col=2)

    # ── Steps ────────────────────────────────────────────────────────────────
    for trace in _steps_traces(steps_df):
        fig.add_trace(trace, row=2, col=1)
    if not steps_df.empty:
        fig.add_hline(
            y=STEPS_GOAL, row=2, col=1,
            line=dict(color=GOAL_LINE, dash="dash", width=1),
            annotation_text=f"{STEPS_GOAL:,}",
            annotation_font=dict(color=GOAL_ANNOT, size=10),
            annotation_position="top right",
        )

    # ── Stats table ──────────────────────────────────────────────────────────
    fig.add_trace(_stats_table(sleep_df, hr_df, steps_df), row=2, col=2)

    # ── Axis styling ─────────────────────────────────────────────────────────
    axis_style = dict(
        gridcolor=GRID_COLOR,
        zerolinecolor=ZERO_COLOR,
        tickcolor=AXIS_COLOR,
        tickfont=dict(color=TEXT_SECONDARY, size=10, family=FONT_FAMILY),
        linecolor=AXIS_COLOR,
    )
    fig.update_xaxes(**axis_style)
    fig.update_yaxes(**axis_style)

    fig.update_yaxes(title_text="hours", title_font=dict(color=TEXT_SECONDARY, size=10),
                     row=1, col=1)
    fig.update_yaxes(title_text="bpm",   title_font=dict(color=TEXT_SECONDARY, size=10),
                     row=1, col=2)
    fig.update_yaxes(title_text="steps", title_font=dict(color=TEXT_SECONDARY, size=10),
                     tickformat=",", row=2, col=1)

    # Range slider on steps chart
    fig.update_xaxes(
        rangeslider=dict(visible=True, thickness=0.035,
                         bgcolor=CARD_COLOR, bordercolor=AXIS_COLOR),
        type="date",
        row=2, col=1,
    )

    # ── Subplot title colors (annotations) ───────────────────────────────────
    for ann in fig.layout.annotations:
        if ann.text in ("  Sleep", "  Heart Rate", "  Steps"):
            ann.font = dict(
                color={
                    "  Sleep":      SLEEP_LINE,
                    "  Heart Rate": HR_LINE,
                    "  Steps":      STEPS_HIT,
                }[ann.text],
                size=14,
                family=FONT_FAMILY,
            )

    # ── Global layout ────────────────────────────────────────────────────────
    fig.update_layout(
        title=dict(
            text="<b>Health</b>",
            font=dict(size=26, color=TEXT_PRIMARY, family=FONT_FAMILY),
            x=0.5,
            xanchor="center",
            y=0.98,
        ),
        height=860,
        paper_bgcolor=BG_COLOR,
        plot_bgcolor=BG_COLOR,
        font=dict(family=FONT_FAMILY, color=TEXT_PRIMARY),
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            font=dict(size=11, color=TEXT_SECONDARY),
            bgcolor="rgba(0,0,0,0)",
        ),
        hoverlabel=dict(font_size=12, font_family=FONT_FAMILY),
        margin=dict(t=90, b=30, l=55, r=30),
        barmode="overlay",
    )

    return fig


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    export_path = "data/export.xml"

    print("Parsing Apple Health data …")
    sleep_df = load_sleep(export_path)
    hr_df    = load_heart_rate(export_path)
    steps_df = load_steps(export_path)

    print(f"  Sleep records : {len(sleep_df)} days")
    print(f"  Heart rate    : {len(hr_df)} days")
    print(f"  Steps         : {len(steps_df)} days")

    print("\nBuilding interactive dashboard …")
    fig = build_dashboard(sleep_df, hr_df, steps_df)

    fig.write_html(
        OUTPUT_PATH,
        include_plotlyjs="cdn",
        full_html=True,
    )
    print(f"  Saved → {OUTPUT_PATH}")
    print("\nDone! Open dashboard.html in your browser.")


if __name__ == "__main__":
    main()
