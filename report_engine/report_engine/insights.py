from __future__ import annotations

import math

from report_engine.formatting import format_metric_value
from report_engine.loader import ReportData

_PERIOD_COL = "period_change_pct"

_READINESS_METRIC_IDS: frozenset[str] = frozenset({
    "readiness_completion_pct",
    "total_requirement_count",
    "open_gap_count",
    "critical_item_count",
})


def has_period_data(data: ReportData) -> bool:
    return (
        not data.long_metrics.empty
        and _PERIOD_COL in data.long_metrics.columns
    )


def snapshot_rows(data: ReportData) -> list[dict]:
    if data.long_metrics.empty:
        return []
    df = data.long_metrics
    if "rollup_level" in df.columns:
        df = df[df["rollup_level"] == "date_only"]
    if df.empty:
        return []
    latest = (
        df.sort_values("date")
        .groupby("metric_id", sort=False)
        .last()
        .reset_index()
    )
    result = []
    for _, row in latest.iterrows():
        result.append({
            "metric_id": row["metric_id"],
            "label": row.get("label", row["metric_id"]),
            "date": str(row["date"]),
            "value": row["value"],
            "unit": row.get("unit", ""),
        })
    result.sort(key=lambda r: r["label"])
    return result


def build_insights(data: ReportData) -> list[dict]:
    if not has_period_data(data):
        return []
    df = data.long_metrics
    if "rollup_level" in df.columns:
        df = df[df["rollup_level"] == "date_only"]
    if df.empty:
        return []
    latest = (
        df.sort_values("date")
        .groupby("metric_id", sort=False)
        .last()
        .reset_index()
    )
    insights = []
    for _, row in latest.iterrows():
        raw_pct = row.get(_PERIOD_COL)
        if raw_pct is None:
            continue
        try:
            pct = float(raw_pct)
        except (ValueError, TypeError):
            continue
        if math.isnan(pct):
            continue
        label = str(row.get("label", row["metric_id"]))
        formatted_pct = format_metric_value(abs(pct), "%")
        if pct > 0:
            direction = "up"
            text = f"{label} increased {formatted_pct} vs prior period"
        elif pct < 0:
            direction = "down"
            text = f"{label} decreased {formatted_pct} vs prior period"
        else:
            direction = "flat"
            text = f"{label} remained flat vs prior period"
        insights.append({
            "metric_id": str(row["metric_id"]),
            "label": label,
            "date": str(row["date"]),
            "period_change_pct": round(pct, 4),
            "direction": direction,
            "text": text,
        })
    insights.sort(key=lambda x: x["metric_id"])
    return insights


def readiness_snapshot_rows(data: ReportData) -> list[dict]:
    """Latest date_only values for readiness metrics; falls back to all metrics if none found."""
    all_rows = snapshot_rows(data)
    readiness = [r for r in all_rows if r["metric_id"] in _READINESS_METRIC_IDS]
    return readiness if readiness else all_rows


def readiness_segment_data(data: ReportData, rollup: str, seg_col: str) -> list[dict]:
    """
    Latest segment-level readiness data for a given rollup level.

    Returns a list of dicts keyed by segment name, with metric values and units
    for the four core readiness metrics (None when absent for a segment).
    """
    if data.long_metrics.empty:
        return []
    df = data.long_metrics
    if "rollup_level" not in df.columns or seg_col not in df.columns:
        return []
    df = df[df["rollup_level"] == rollup].copy()
    if df.empty:
        return []
    latest_date = df["date"].max()
    df = df[df["date"] == latest_date]
    segments = sorted(df[seg_col].dropna().unique())
    if not segments:
        return []
    _SEG_METRICS = [
        "readiness_completion_pct",
        "open_gap_count",
        "critical_item_count",
        "total_requirement_count",
    ]
    result = []
    for seg in segments:
        seg_df = df[df[seg_col] == seg]
        row: dict = {"segment": str(seg)}
        for mid in _SEG_METRICS:
            m_rows = seg_df[seg_df["metric_id"] == mid]
            if not m_rows.empty:
                row[mid] = m_rows.iloc[0]["value"]
                row[f"{mid}_unit"] = str(m_rows.iloc[0].get("unit", ""))
            else:
                row[mid] = None
                row[f"{mid}_unit"] = ""
        result.append(row)
    return result
