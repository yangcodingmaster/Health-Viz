"""
visualize.py
------------
Generates an interactive HTML dashboard from a parsed Apple Health export.
The output is a single self-contained file — open it in any browser.

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

import sys
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Ensure src/ is importable when running from the project root
sys.path.insert(0, str(Path(__file__).parent))
from parse_health import load_sleep, load_heart_rate, load_steps

# ---------------------------------------------------------------------------
# Color palette
# ---------------------------------------------------------------------------
COLOR_SLEEP      = "#5C85D6"
COLOR_SLEEP_AVG  = "#1A4FA8"
COLOR_HR         = "#E05C5C"
COLOR_HR_AVG     = "#A01010"
COLOR_STEPS_OK   = "#5CB85C"   # met 10,000-step goal
COLOR_STEPS_MISS = "#E05C5C"   # missed goal
COLOR_GOAL_LINE  = "#888888"

ROLLING_WINDOW   = 7           # days for rolling average
STEPS_GOAL       = 10_000
OUTPUT_PATH      = "dashboard.html"


# ---------------------------------------------------------------------------
# Helper: rolling average series
# ---------------------------------------------------------------------------

def _rolling(series: pd.Series, window: int = ROLLING_WINDOW) -> pd.Series:
    """Return a centered rolling mean with at least 3 data points."""
    return series.rolling(window, center=True, min_periods=3).mean()


# ---------------------------------------------------------------------------
# Per-chart trace builders
# (each returns a list of go.Trace objects — no Figure created here)
# ---------------------------------------------------------------------------

def _sleep_traces(sleep_df: pd.DataFrame) -> list[go.BaseTraceType]:
    """Raw nightly sleep bars + 7-day rolling average line."""
    if sleep_df.empty:
        return []

    rolled = _rolling(sleep_df["sleep_hours"])

    raw = go.Bar(
        x=sleep_df["date"],
        y=sleep_df["sleep_hours"].round(2),
        name="Sleep (nightly)",
        marker_color=COLOR_SLEEP,
        opacity=0.55,
        hovertemplate="%{x|%b %d, %Y}<br>%{y:.1f} h<extra></extra>",
    )
    avg = go.Scatter(
        x=sleep_df["date"],
        y=rolled.round(2),
        name=f"{ROLLING_WINDOW}-day avg",
        line=dict(color=COLOR_SLEEP_AVG, width=2),
        hovertemplate="%{x|%b %d, %Y}<br>avg %{y:.1f} h<extra></extra>",
    )
    return [raw, avg]


def _hr_traces(hr_df: pd.DataFrame) -> list[go.BaseTraceType]:
    """Raw daily min heart rate scatter + 7-day rolling average line."""
    if hr_df.empty:
        return []

    rolled = _rolling(hr_df["hr_min"])

    raw = go.Scatter(
        x=hr_df["date"],
        y=hr_df["hr_min"].round(1),
        name="Resting HR (daily min)",
        mode="markers",
        marker=dict(color=COLOR_HR, size=4, opacity=0.5),
        hovertemplate="%{x|%b %d, %Y}<br>%{y:.0f} bpm<extra></extra>",
    )
    avg = go.Scatter(
        x=hr_df["date"],
        y=rolled.round(1),
        name=f"{ROLLING_WINDOW}-day avg",
        line=dict(color=COLOR_HR_AVG, width=2),
        hovertemplate="%{x|%b %d, %Y}<br>avg %{y:.0f} bpm<extra></extra>",
    )
    return [raw, avg]


def _steps_traces(steps_df: pd.DataFrame) -> list[go.BaseTraceType]:
    """Color-coded daily step count bars (green = goal met, red = missed)."""
    if steps_df.empty:
        return []

    colors = [
        COLOR_STEPS_OK if s >= STEPS_GOAL else COLOR_STEPS_MISS
        for s in steps_df["steps"]
    ]

    bars = go.Bar(
        x=steps_df["date"],
        y=steps_df["steps"],
        name="Daily steps",
        marker_color=colors,
        opacity=0.8,
        hovertemplate="%{x|%b %d, %Y}<br>%{y:,} steps<extra></extra>",
    )
    return [bars]


def _stats_table(sleep_df: pd.DataFrame, hr_df: pd.DataFrame,
                 steps_df: pd.DataFrame) -> go.Table:
    """A Plotly Table showing key statistics for the last 30 days."""
    cutoff = pd.Timestamp.today() - pd.Timedelta(days=30)

    def recent(df: pd.DataFrame) -> pd.DataFrame:
        return df[df["date"] >= cutoff] if not df.empty else df

    r_sleep = recent(sleep_df)
    r_hr    = recent(hr_df)
    r_steps = recent(steps_df)

    # Build rows: [metric, value]
    rows = []

    # Sleep
    if not r_sleep.empty:
        avg_s  = r_sleep["sleep_hours"].mean()
        days_s = int((r_sleep["sleep_hours"] >= 7).sum())
        rows += [
            ["Avg nightly sleep",  f"{avg_s:.1f} h"],
            ["Days ≥ 7 h (sleep)", f"{days_s} / {len(r_sleep)}"],
        ]
    else:
        rows.append(["Sleep data", "—"])

    # Heart rate
    if not r_hr.empty:
        avg_hr = r_hr["hr_min"].mean()
        min_hr = int(r_hr["hr_min"].min())
        rows += [
            ["Avg resting HR",  f"{avg_hr:.0f} bpm"],
            ["Min resting HR",  f"{min_hr} bpm"],
        ]
    else:
        rows.append(["Heart rate data", "—"])

    # Steps
    if not r_steps.empty:
        avg_st  = r_steps["steps"].mean()
        days_st = int((r_steps["steps"] >= STEPS_GOAL).sum())
        rows += [
            ["Avg daily steps",       f"{avg_st:,.0f}"],
            [f"Days ≥ {STEPS_GOAL:,}", f"{days_st} / {len(r_steps)}"],
        ]
    else:
        rows.append(["Steps data", "—"])

    metrics, values = zip(*rows) if rows else ([], [])

    return go.Table(
        columnwidth=[60, 40],
        header=dict(
            values=["<b>Metric (last 30 days)</b>", "<b>Value</b>"],
            fill_color="#e8eef8",
            align="left",
            font=dict(size=12),
            line_color="#aabbdd",
        ),
        cells=dict(
            values=[list(metrics), list(values)],
            fill_color=["#f7f9ff", "white"],
            align=["left", "right"],
            font=dict(size=12),
            line_color="#dde5f0",
            height=28,
        ),
    )


# ---------------------------------------------------------------------------
# Main dashboard builder
# ---------------------------------------------------------------------------

def build_dashboard(sleep_df: pd.DataFrame, hr_df: pd.DataFrame,
                    steps_df: pd.DataFrame) -> go.Figure:
    """
    Assemble the four panels into a single interactive Plotly figure.

    Returns the Figure (not yet written to disk).
    """
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=(
            "Nightly Sleep Duration",
            "Resting Heart Rate",
            "Daily Step Count",
            "",            # stats table has its own header
        ),
        specs=[
            [{"type": "xy"},    {"type": "xy"}],
            [{"type": "xy"},    {"type": "table"}],
        ],
        vertical_spacing=0.14,
        horizontal_spacing=0.08,
    )

    # ── Sleep (row 1, col 1) ────────────────────────────────────────────────
    for trace in _sleep_traces(sleep_df):
        fig.add_trace(trace, row=1, col=1)
    # Reference lines: 7 h and 9 h guidelines
    if not sleep_df.empty:
        for y_val, label, dash in [(7, "7 h min", "dash"), (9, "9 h max", "dot")]:
            fig.add_hline(
                y=y_val, row=1, col=1,
                line=dict(color=COLOR_GOAL_LINE, dash=dash, width=1),
                annotation_text=label,
                annotation_position="top right",
                annotation_font_size=10,
            )

    # ── Heart Rate (row 1, col 2) ───────────────────────────────────────────
    for trace in _hr_traces(hr_df):
        fig.add_trace(trace, row=1, col=2)

    # ── Steps (row 2, col 1) ────────────────────────────────────────────────
    for trace in _steps_traces(steps_df):
        fig.add_trace(trace, row=2, col=1)
    if not steps_df.empty:
        fig.add_hline(
            y=STEPS_GOAL, row=2, col=1,
            line=dict(color=COLOR_GOAL_LINE, dash="dash", width=1),
            annotation_text=f"{STEPS_GOAL:,} goal",
            annotation_position="top right",
            annotation_font_size=10,
        )

    # ── Stats table (row 2, col 2) ──────────────────────────────────────────
    fig.add_trace(_stats_table(sleep_df, hr_df, steps_df), row=2, col=2)

    # ── Axis labels ─────────────────────────────────────────────────────────
    fig.update_yaxes(title_text="Hours", row=1, col=1)
    fig.update_yaxes(title_text="BPM",   row=1, col=2)
    fig.update_yaxes(title_text="Steps", row=2, col=1,
                     tickformat=",")

    # ── Range slider on both x-axes ─────────────────────────────────────────
    fig.update_xaxes(
        rangeslider=dict(visible=True, thickness=0.04),
        type="date",
        row=2, col=1,
    )

    # ── Global layout ────────────────────────────────────────────────────────
    fig.update_layout(
        title=dict(
            text="Apple Health — Personal Dashboard",
            font=dict(size=20),
            x=0.5,
            xanchor="center",
        ),
        height=820,
        template="plotly_white",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.01,
            xanchor="right",
            x=1,
            font=dict(size=11),
        ),
        hoverlabel=dict(bgcolor="white", font_size=12),
        margin=dict(t=100, b=40, l=60, r=40),
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

    # Write a single self-contained HTML file (Plotly JS bundled via CDN link)
    fig.write_html(
        OUTPUT_PATH,
        include_plotlyjs="cdn",    # ~3 kB stub; Plotly loaded from CDN
        full_html=True,
    )
    print(f"  Saved → {OUTPUT_PATH}")
    print("\nDone! Open dashboard.html in your browser.")


if __name__ == "__main__":
    main()
