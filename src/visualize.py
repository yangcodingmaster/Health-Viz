"""
visualize.py
------------
Generates four health-data charts from a parsed Apple Health export:

  1. sleep_trend.png      — line chart of nightly sleep duration
  2. heart_rate_trend.png — line chart of daily resting heart rate
  3. steps_chart.png      — bar chart of daily step counts
  4. dashboard.png        — 2×2 summary dashboard combining all three charts

Usage:
    python src/visualize.py

Place your Apple Health export.xml in the data/ folder first.
"""

import sys
from pathlib import Path

import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns
import pandas as pd

# Ensure src/ is importable when running from the project root
sys.path.insert(0, str(Path(__file__).parent))
from parse_health import load_sleep, load_heart_rate, load_steps

# ---------------------------------------------------------------------------
# Visual style
# ---------------------------------------------------------------------------
sns.set_theme(style="whitegrid", palette="muted")
FIGURE_DPI   = 150
OUTPUT_DIR   = Path(".")          # charts saved to project root

# Color palette
COLOR_SLEEP = "#5C85D6"
COLOR_HR    = "#E05C5C"
COLOR_STEPS = "#5CB85C"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _format_date_axis(ax: plt.Axes, df: pd.DataFrame) -> None:
    """Auto-select a sensible date tick interval based on data span."""
    if df.empty:
        return
    span_days = (df["date"].max() - df["date"].min()).days
    if span_days <= 30:
        locator = mdates.WeekdayLocator(interval=1)
        formatter = mdates.DateFormatter("%b %d")
    elif span_days <= 180:
        locator = mdates.MonthLocator()
        formatter = mdates.DateFormatter("%b %Y")
    else:
        locator = mdates.MonthLocator(interval=2)
        formatter = mdates.DateFormatter("%b '%y")
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(formatter)
    plt.setp(ax.get_xticklabels(), rotation=30, ha="right")


def _rolling_overlay(ax: plt.Axes, df: pd.DataFrame, col: str,
                     color: str, window: int = 7) -> None:
    """Plot a semi-transparent raw series plus a 7-day rolling average."""
    ax.plot(df["date"], df[col], color=color, alpha=0.25, linewidth=1)
    rolled = df[col].rolling(window, center=True, min_periods=3).mean()
    ax.plot(df["date"], rolled, color=color, linewidth=2,
            label=f"{window}-day avg")
    ax.legend(fontsize=8)


# ---------------------------------------------------------------------------
# Individual chart functions
# ---------------------------------------------------------------------------

def plot_sleep(sleep_df: pd.DataFrame, ax: plt.Axes | None = None,
               save_path: str | None = "sleep_trend.png") -> plt.Axes:
    """
    Line chart of nightly sleep duration.

    Args:
        sleep_df  : DataFrame returned by load_sleep()
        ax        : optional existing Axes to draw on (for dashboard)
        save_path : file path to save the figure; None to skip saving
    """
    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(figsize=(10, 4))

    if sleep_df.empty:
        ax.text(0.5, 0.5, "No sleep data found", transform=ax.transAxes,
                ha="center", va="center", color="grey")
    else:
        _rolling_overlay(ax, sleep_df, "sleep_hours", COLOR_SLEEP)
        # Reference lines for sleep guidelines
        ax.axhline(7, color="grey", linestyle="--", linewidth=0.8, alpha=0.6,
                   label="7 h guideline")
        ax.axhline(9, color="grey", linestyle=":",  linewidth=0.8, alpha=0.6,
                   label="9 h upper")
        ax.legend(fontsize=8)
        _format_date_axis(ax, sleep_df)

    ax.set_title("Nightly Sleep Duration", fontsize=13, fontweight="bold")
    ax.set_ylabel("Hours Asleep")
    ax.set_ylim(bottom=0)

    if standalone:
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=FIGURE_DPI)
            print(f"  Saved → {save_path}")
        plt.close()

    return ax


def plot_heart_rate(hr_df: pd.DataFrame, ax: plt.Axes | None = None,
                    save_path: str | None = "heart_rate_trend.png") -> plt.Axes:
    """
    Line chart of daily resting heart rate.

    Uses the daily minimum BPM as a proxy for resting heart rate when a
    dedicated resting-HR record type is unavailable.

    Args:
        hr_df     : DataFrame returned by load_heart_rate()
        ax        : optional existing Axes to draw on (for dashboard)
        save_path : file path to save the figure; None to skip saving
    """
    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(figsize=(10, 4))

    if hr_df.empty:
        ax.text(0.5, 0.5, "No heart rate data found", transform=ax.transAxes,
                ha="center", va="center", color="grey")
    else:
        _rolling_overlay(ax, hr_df, "hr_min", COLOR_HR)
        _format_date_axis(ax, hr_df)

    ax.set_title("Resting Heart Rate (daily min)", fontsize=13, fontweight="bold")
    ax.set_ylabel("BPM")
    ax.set_ylim(bottom=0)

    if standalone:
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=FIGURE_DPI)
            print(f"  Saved → {save_path}")
        plt.close()

    return ax


def plot_steps(steps_df: pd.DataFrame, ax: plt.Axes | None = None,
               save_path: str | None = "steps_chart.png") -> plt.Axes:
    """
    Bar chart of daily step counts.

    Bars are colored green when the step count meets the 10,000-step goal
    and red when below it.

    Args:
        steps_df  : DataFrame returned by load_steps()
        ax        : optional existing Axes to draw on (for dashboard)
        save_path : file path to save the figure; None to skip saving
    """
    standalone = ax is None
    if standalone:
        fig, ax = plt.subplots(figsize=(12, 4))

    if steps_df.empty:
        ax.text(0.5, 0.5, "No step data found", transform=ax.transAxes,
                ha="center", va="center", color="grey")
    else:
        GOAL = 10_000
        colors = [COLOR_STEPS if s >= GOAL else COLOR_HR for s in steps_df["steps"]]
        ax.bar(steps_df["date"], steps_df["steps"], color=colors,
               width=0.8, edgecolor="none", alpha=0.85)
        ax.axhline(GOAL, color="grey", linestyle="--", linewidth=1,
                   label=f"{GOAL:,} step goal")
        ax.legend(fontsize=8)
        _format_date_axis(ax, steps_df)

    ax.set_title("Daily Step Count", fontsize=13, fontweight="bold")
    ax.set_ylabel("Steps")
    ax.yaxis.set_major_formatter(
        plt.FuncFormatter(lambda x, _: f"{int(x):,}")
    )
    ax.set_ylim(bottom=0)

    if standalone:
        plt.tight_layout()
        if save_path:
            plt.savefig(save_path, dpi=FIGURE_DPI)
            print(f"  Saved → {save_path}")
        plt.close()

    return ax


def plot_dashboard(sleep_df: pd.DataFrame, hr_df: pd.DataFrame,
                   steps_df: pd.DataFrame,
                   save_path: str = "dashboard.png") -> None:
    """
    2×2 summary dashboard combining all three charts plus a stats panel.

    Layout:
        [0,0] Sleep duration trend
        [0,1] Resting heart rate trend
        [1,0] Daily steps bar chart  (spans both columns)
        — or —
        [1,0] Steps bar chart
        [1,1] Key stats text panel

    Args:
        sleep_df  : DataFrame returned by load_sleep()
        hr_df     : DataFrame returned by load_heart_rate()
        steps_df  : DataFrame returned by load_steps()
        save_path : file path to save the dashboard figure
    """
    fig, axes = plt.subplots(2, 2, figsize=(16, 9))
    fig.suptitle("Apple Health — Personal Dashboard", fontsize=16,
                 fontweight="bold", y=0.98)

    # Top row: sleep + heart rate
    plot_sleep(sleep_df,      ax=axes[0, 0], save_path=None)
    plot_heart_rate(hr_df,    ax=axes[0, 1], save_path=None)

    # Bottom-left: steps
    plot_steps(steps_df, ax=axes[1, 0], save_path=None)

    # Bottom-right: summary statistics panel
    _plot_stats_panel(axes[1, 1], sleep_df, hr_df, steps_df)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(save_path, dpi=FIGURE_DPI)
    print(f"  Saved → {save_path}")
    plt.close()


def _plot_stats_panel(ax: plt.Axes, sleep_df: pd.DataFrame,
                      hr_df: pd.DataFrame, steps_df: pd.DataFrame) -> None:
    """Render a text-based key-statistics panel onto ax."""
    ax.axis("off")

    lines = ["Key Statistics (last 30 days)\n"]

    # Restrict to the most recent 30 days for summary stats
    cutoff = pd.Timestamp.today() - pd.Timedelta(days=30)

    # Sleep stats
    recent_sleep = sleep_df[sleep_df["date"] >= cutoff] if not sleep_df.empty else sleep_df
    if not recent_sleep.empty:
        avg_sleep  = recent_sleep["sleep_hours"].mean()
        days_goal  = (recent_sleep["sleep_hours"] >= 7).sum()
        lines += [
            f"Sleep",
            f"  Avg nightly:  {avg_sleep:.1f} h",
            f"  Days ≥ 7 h:   {days_goal} / {len(recent_sleep)}",
            "",
        ]
    else:
        lines += ["Sleep: no data\n"]

    # Heart rate stats
    recent_hr = hr_df[hr_df["date"] >= cutoff] if not hr_df.empty else hr_df
    if not recent_hr.empty:
        avg_rhr = recent_hr["hr_min"].mean()
        lines += [
            f"Resting Heart Rate",
            f"  Avg:  {avg_rhr:.0f} bpm",
            f"  Min:  {recent_hr['hr_min'].min():.0f} bpm",
            "",
        ]
    else:
        lines += ["Heart Rate: no data\n"]

    # Steps stats
    recent_steps = steps_df[steps_df["date"] >= cutoff] if not steps_df.empty else steps_df
    if not recent_steps.empty:
        avg_steps  = recent_steps["steps"].mean()
        days_10k   = (recent_steps["steps"] >= 10_000).sum()
        lines += [
            f"Steps",
            f"  Avg daily:    {avg_steps:,.0f}",
            f"  Days ≥ 10 k:  {days_10k} / {len(recent_steps)}",
        ]
    else:
        lines += ["Steps: no data"]

    text = "\n".join(lines)
    ax.text(0.05, 0.95, text, transform=ax.transAxes,
            fontsize=11, verticalalignment="top", fontfamily="monospace",
            bbox=dict(boxstyle="round,pad=0.6", facecolor="#f0f4ff",
                      edgecolor="#aabbdd", linewidth=1))


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

    print("\nGenerating charts …")
    plot_sleep(sleep_df)
    plot_heart_rate(hr_df)
    plot_steps(steps_df)
    plot_dashboard(sleep_df, hr_df, steps_df)

    print("\nDone! Open dashboard.png for a full overview.")


if __name__ == "__main__":
    main()
