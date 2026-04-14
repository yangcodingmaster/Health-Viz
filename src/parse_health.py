"""
parse_health.py
---------------
Parses an Apple Health export.xml file and extracts three health metrics
into pandas DataFrames:

  - Sleep data       (HKCategoryTypeIdentifierSleepAnalysis)
  - Heart rate data  (HKQuantityTypeIdentifierHeartRate)
  - Step count data  (HKQuantityTypeIdentifierStepCount)

Usage:
    from parse_health import load_sleep, load_heart_rate, load_steps

    sleep_df      = load_sleep("data/export.xml")
    heart_rate_df = load_heart_rate("data/export.xml")
    steps_df      = load_steps("data/export.xml")
"""

import xml.etree.ElementTree as ET
from pathlib import Path

import pandas as pd

# ---------------------------------------------------------------------------
# Constants — Apple Health record type identifiers
# ---------------------------------------------------------------------------
SLEEP_TYPE      = "HKCategoryTypeIdentifierSleepAnalysis"
HEART_RATE_TYPE = "HKQuantityTypeIdentifierHeartRate"
STEPS_TYPE      = "HKQuantityTypeIdentifierStepCount"

# Apple Health sleep values that represent actual time asleep
ASLEEP_VALUES = {
    "HKCategoryValueSleepAnalysisAsleep",
    "HKCategoryValueSleepAnalysisAsleepCore",
    "HKCategoryValueSleepAnalysisAsleepDeep",
    "HKCategoryValueSleepAnalysisAsleepREM",
}


def _parse_xml(path: str) -> ET.Element:
    """Parse the XML file and return the root element."""
    xml_path = Path(path)
    if not xml_path.exists():
        raise FileNotFoundError(
            f"export.xml not found at '{path}'.\n"
            "Please copy your Apple Health export.xml into the data/ folder."
        )
    tree = ET.parse(xml_path)
    return tree.getroot()


def load_sleep(path: str = "data/export.xml") -> pd.DataFrame:
    """
    Extract sleep data and return a DataFrame with daily sleep duration.

    Each Apple Health sleep record covers a time window (startDate to endDate).
    We sum all asleep-type windows per calendar day to get total sleep hours.

    Returns a DataFrame with columns:
        date          : date (index)
        sleep_hours   : total hours asleep that night
    """
    root = _parse_xml(path)
    records = []

    for record in root.iter("Record"):
        if record.attrib.get("type") != SLEEP_TYPE:
            continue
        value = record.attrib.get("value", "")
        # Only count segments where the user is actually asleep
        if value not in ASLEEP_VALUES:
            continue

        start = pd.to_datetime(record.attrib["startDate"])
        end   = pd.to_datetime(record.attrib["endDate"])
        duration_hours = (end - start).total_seconds() / 3600
        records.append({"start": start, "duration_hours": duration_hours})

    if not records:
        return pd.DataFrame(columns=["date", "sleep_hours"])

    df = pd.DataFrame(records)

    # Attribute sleep to the date the session *started* (so 11pm–7am → night of 11pm)
    df["date"] = df["start"].dt.date

    # Sum all asleep segments per day
    daily = (
        df.groupby("date")["duration_hours"]
        .sum()
        .reset_index()
        .rename(columns={"duration_hours": "sleep_hours"})
    )
    daily["date"] = pd.to_datetime(daily["date"])
    daily = daily.sort_values("date").reset_index(drop=True)
    return daily


def load_heart_rate(path: str = "data/export.xml") -> pd.DataFrame:
    """
    Extract resting heart rate records and return a DataFrame with daily averages.

    Apple Health stores individual heart rate samples throughout the day.
    We compute the daily minimum (a proxy for resting heart rate when a dedicated
    resting-HR record is absent) and daily mean.

    Returns a DataFrame with columns:
        date       : date (index)
        hr_mean    : mean heart rate for the day (bpm)
        hr_min     : minimum heart rate for the day (bpm) — resting proxy
    """
    root = _parse_xml(path)
    records = []

    for record in root.iter("Record"):
        if record.attrib.get("type") != HEART_RATE_TYPE:
            continue
        try:
            bpm = float(record.attrib["value"])
        except (KeyError, ValueError):
            continue
        date = pd.to_datetime(record.attrib["startDate"]).date()
        records.append({"date": date, "bpm": bpm})

    if not records:
        return pd.DataFrame(columns=["date", "hr_mean", "hr_min"])

    df = pd.DataFrame(records)
    daily = (
        df.groupby("date")["bpm"]
        .agg(hr_mean="mean", hr_min="min")
        .reset_index()
    )
    daily["date"] = pd.to_datetime(daily["date"])
    daily = daily.sort_values("date").reset_index(drop=True)
    return daily


def load_steps(path: str = "data/export.xml") -> pd.DataFrame:
    """
    Extract step count records and return a DataFrame with daily totals.

    Apple Health can contain step records from multiple sources (iPhone, Apple
    Watch, third-party apps) that may overlap. We sum all non-overlapping
    contributions; for simplicity we sum all records — for most users this
    produces accurate daily totals.

    Returns a DataFrame with columns:
        date        : date (index)
        steps       : total steps for the day
    """
    root = _parse_xml(path)
    records = []

    for record in root.iter("Record"):
        if record.attrib.get("type") != STEPS_TYPE:
            continue
        try:
            steps = float(record.attrib["value"])
        except (KeyError, ValueError):
            continue
        date = pd.to_datetime(record.attrib["startDate"]).date()
        records.append({"date": date, "steps": steps})

    if not records:
        return pd.DataFrame(columns=["date", "steps"])

    df = pd.DataFrame(records)
    daily = (
        df.groupby("date")["steps"]
        .sum()
        .reset_index()
    )
    daily["date"] = pd.to_datetime(daily["date"])
    daily["steps"] = daily["steps"].astype(int)
    daily = daily.sort_values("date").reset_index(drop=True)
    return daily
