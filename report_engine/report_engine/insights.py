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


_CATEGORY_GAP_RECS: dict[str, str] = {
    "power": "Resolve power interconnection requirements to unblock the grid-connection milestone.",
    "fiber": "Advance fiber routing and backhaul agreements to close fiber gaps.",
    "permitting": "Expedite permit applications and agency approvals to address permitting gaps.",
    "site_control": "Finalize lease or purchase agreements to resolve site control gaps.",
    "commercial": "Complete commercial negotiations and off-take agreements to close commercial gaps.",
    "capital": "Confirm capital commitments and financial close requirements to address capital gaps.",
}

_CATEGORY_COMPLETION_RECS: dict[str, str] = {
    "power": "Focus on power-related requirements; this category has the lowest completion rate.",
    "fiber": "Prioritize fiber planning and procurement; this category has the lowest completion rate.",
    "permitting": "Accelerate permitting activities; this category has the lowest completion rate.",
    "site_control": "Drive site control negotiations to completion; this category has the lowest completion rate.",
    "commercial": "Advance commercial workstreams; this category has the lowest completion rate.",
    "capital": "Advance capital formation activities; this category has the lowest completion rate.",
}


def build_readiness_recommendations(data: ReportData) -> list[dict]:
    """Deterministic readiness recommendations derived from snapshot and segment data."""
    overall = {r["metric_id"]: r for r in snapshot_rows(data)}
    _readiness_keys = {"readiness_completion_pct", "open_gap_count", "critical_item_count", "total_requirement_count"}
    if not any(k in overall for k in _readiness_keys):
        return [{
            "priority": 1,
            "category": None,
            "severity": "low",
            "recommendation": "Review readiness metrics to identify gaps and priorities.",
            "rationale": "Readiness data is incomplete or unavailable.",
        }]

    recs = []
    priority = 1
    crit_count = None

    crit_row = overall.get("critical_item_count")
    if crit_row is not None:
        try:
            crit_count = int(float(crit_row["value"]))
        except (ValueError, TypeError):
            pass

    if crit_count is not None and crit_count > 0:
        n = crit_count
        recs.append({
            "priority": priority,
            "category": None,
            "severity": "critical",
            "recommendation": (
                f"Resolve {n} critical blocker{'s' if n != 1 else ''} "
                "before advancing to project gate review."
            ),
            "rationale": (
                f"{n} critical item{'s' if n != 1 else ''} must be closed "
                "before milestone progression."
            ),
        })
        priority += 1

    cat_data = readiness_segment_data(data, "date_category", "category")

    if cat_data:
        gap_segs = [
            (r["segment"], float(r["open_gap_count"]))
            for r in cat_data
            if r.get("open_gap_count") is not None
        ]
        if gap_segs:
            gap_segs.sort(key=lambda x: (-x[1], x[0]))
            top_cat, top_val = gap_segs[0]
            top_count = int(top_val)
            if top_count > 0:
                rec_text = _CATEGORY_GAP_RECS.get(
                    top_cat.lower(),
                    f"Address open gaps in the {top_cat} category to improve overall readiness.",
                )
                recs.append({
                    "priority": priority,
                    "category": top_cat,
                    "severity": "high",
                    "recommendation": rec_text,
                    "rationale": f"{top_cat} has the highest open gap count ({top_count}).",
                })
                priority += 1

    if cat_data:
        pct_segs = [
            (r["segment"], float(r["readiness_completion_pct"]))
            for r in cat_data
            if r.get("readiness_completion_pct") is not None
        ]
        if pct_segs:
            pct_segs.sort(key=lambda x: (x[1], x[0]))
            low_cat, low_pct = pct_segs[0]
            rec_text = _CATEGORY_COMPLETION_RECS.get(
                low_cat.lower(),
                f"Focus on the {low_cat} category, which has the lowest readiness completion rate.",
            )
            recs.append({
                "priority": priority,
                "category": low_cat,
                "severity": "high",
                "recommendation": rec_text,
                "rationale": f"{low_cat} has the lowest completion rate ({format_metric_value(low_pct, '%')}).",
            })
            priority += 1

    overall_pct = None
    comp_row = overall.get("readiness_completion_pct")
    if comp_row is not None:
        try:
            overall_pct = float(comp_row["value"])
        except (ValueError, TypeError):
            pass

    if overall_pct is not None and overall_pct < 60:
        recs.append({
            "priority": priority,
            "category": None,
            "severity": "medium",
            "recommendation": "Hold transaction and RFP outreach until overall readiness improves.",
            "rationale": (
                f"Overall readiness is {format_metric_value(overall_pct, '%')}, "
                "below the 60% threshold for external engagement."
            ),
        })
        priority += 1

    if overall_pct is not None and overall_pct >= 80 and crit_count == 0:
        recs.append({
            "priority": priority,
            "category": None,
            "severity": "low",
            "recommendation": "Prepare market-facing materials and investor outreach packages.",
            "rationale": (
                f"Overall readiness is {format_metric_value(overall_pct, '%')} "
                "with no critical blockers."
            ),
        })
        priority += 1

    if not recs:
        recs.append({
            "priority": 1,
            "category": None,
            "severity": "low",
            "recommendation": "Review readiness metrics to identify gaps and priorities.",
            "rationale": "No specific recommendations apply given the current readiness data.",
        })

    return recs


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
