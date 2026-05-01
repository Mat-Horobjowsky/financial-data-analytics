from __future__ import annotations

import math

from report_engine.formatting import format_metric_value
from report_engine.loader import ReportData

_PERIOD_COL = "period_change_pct"


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
