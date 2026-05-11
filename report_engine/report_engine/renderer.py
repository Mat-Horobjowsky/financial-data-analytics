from __future__ import annotations

from datetime import date as _date
from pathlib import Path

from report_engine import templates as _templates
from report_engine.formatting import format_metric_value
from report_engine.insights import (
    build_insights,
    has_period_data,
    readiness_segment_data,
    readiness_snapshot_rows,
    snapshot_rows,
)
from report_engine.loader import ReportData

_DISPLAY_COLS = ["date", "metric_id", "label", "value", "unit"]
_TIME_COLS = ["prior_period_value", "period_change", "period_change_pct"]
_COL_LABELS = {
    "date": "Date",
    "metric_id": "Metric ID",
    "label": "Metric",
    "value": "Value",
    "unit": "Unit",
    "prior_period_value": "Prior Period",
    "period_change": "Change",
    "period_change_pct": "Change %",
}
_DICT_COLS = ["id", "label", "type", "unit", "description"]
_DICT_COL_LABELS = {
    "id": "Metric ID",
    "label": "Metric",
    "type": "Type",
    "unit": "Unit",
    "description": "Description",
}


def render_markdown(
    data: ReportData,
    report_date: _date | None = None,
    sections: list[str] | None = None,
) -> str:
    if report_date is None:
        report_date = _date.today()
    if sections is None:
        sections = _templates.get_sections(_templates.DEFAULT_TEMPLATE)
    _dispatch = {
        "header":              lambda d: _header(d, report_date),
        "validation":          _validation,
        "kpi_snapshot":        _kpi_snapshot,
        "key_insights":        _key_insights,
        "metrics_summary":     _metrics_summary,
        "metric_dictionary":   _metric_dictionary,
        "readiness_snapshot":  _readiness_snapshot,
        "open_gaps":           _open_gaps,
        "critical_items":      _critical_items,
        "readiness_by_segment": _readiness_by_segment,
        "readiness_next_steps": _readiness_next_steps,
    }
    return "\n\n".join(s for s in (_dispatch[sid](data) for sid in sections) if s)


def _header(data: ReportData, report_date: _date) -> str:
    return (
        f"# Metrics Report\n\n"
        f"**Input:** `{Path(data.input_dir).name}`  \n"
        f"**Generated:** {report_date.isoformat()}"
    )


def _validation(data: ReportData) -> str:
    lines = ["## Validation", "", f"**Status:** {data.validation_status}"]
    if data.validation_errors:
        lines += ["", "**Errors:**"]
        lines += [f"- {e}" for e in data.validation_errors]
    if data.validation_warnings:
        lines += ["", "**Warnings:**"]
        lines += [f"- {w}" for w in data.validation_warnings]
    return "\n".join(lines)


def _metrics_summary(data: ReportData) -> str:
    if data.long_metrics.empty:
        return "## Metrics Summary\n\n_No metrics data available._"
    df = data.long_metrics
    if "rollup_level" in df.columns:
        df = df[df["rollup_level"] == "date_only"]
    if df.empty:
        return "## Metrics Summary\n\n_No metrics data available._"
    time_cols = [c for c in _TIME_COLS if c in df.columns]
    cols = [c for c in _DISPLAY_COLS if c in df.columns] + time_cols
    df = df[cols].sort_values(["date", "metric_id"]).reset_index(drop=True)
    if "unit" in df.columns:
        df = df.copy()
        for col in ["value", "prior_period_value", "period_change"]:
            if col in df.columns:
                df[col] = [format_metric_value(v, u) for v, u in zip(df[col], df["unit"])]
        if "period_change_pct" in df.columns:
            df["period_change_pct"] = [format_metric_value(v, "%") for v in df["period_change_pct"]]
    df = df.fillna("").reset_index(drop=True)
    display_cols = [_COL_LABELS.get(c, c) for c in cols]
    header = "| " + " | ".join(display_cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    rows = [
        "| " + " | ".join(str(row[c]).replace("|", "\\|") for c in cols) + " |"
        for _, row in df.iterrows()
    ]
    return "\n".join(["## Metrics Summary", "", header, sep] + rows)


def _metric_dictionary(data: ReportData) -> str:
    if data.metric_dictionary.empty:
        return "## Metric Dictionary\n\n_No metric dictionary available._"
    df = data.metric_dictionary
    cols = [c for c in _DICT_COLS if c in df.columns]
    df = df[cols].fillna("").reset_index(drop=True)
    display_cols = [_DICT_COL_LABELS.get(c, c) for c in cols]
    header = "| " + " | ".join(display_cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    rows = [
        "| " + " | ".join(str(row[c]).replace("|", "\\|") for c in cols) + " |"
        for _, row in df.iterrows()
    ]
    return "\n".join(["## Metric Dictionary", "", header, sep] + rows)


def _kpi_snapshot(data: ReportData) -> str:
    rows = snapshot_rows(data)
    if not rows:
        return ""
    _SNAP_COLS = ["label", "date", "value", "unit"]
    _SNAP_LABELS = {"label": "Metric", "date": "Latest Period", "value": "Value", "unit": "Unit"}
    header = "| " + " | ".join(_SNAP_LABELS[c] for c in _SNAP_COLS) + " |"
    sep = "| " + " | ".join("---" for _ in _SNAP_COLS) + " |"
    table_rows = []
    for row in rows:
        formatted_value = format_metric_value(row["value"], row["unit"])
        cells = [
            str(row["label"]).replace("|", "\\|"),
            str(row["date"]).replace("|", "\\|"),
            formatted_value.replace("|", "\\|"),
            str(row["unit"]).replace("|", "\\|"),
        ]
        table_rows.append("| " + " | ".join(cells) + " |")
    return "\n".join(["## KPI Snapshot", "", header, sep] + table_rows)


def _key_insights(data: ReportData) -> str:
    if not has_period_data(data):
        return ""
    insights = build_insights(data)
    if not insights:
        return ""
    lines = ["## Key Insights", ""]
    for insight in insights:
        lines.append(f"- {insight['text']}")
    return "\n".join(lines)


# ── Readiness sections ─────────────────────────────────────────────────────────

_SEG_METRIC_IDS = ["readiness_completion_pct", "open_gap_count", "critical_item_count", "total_requirement_count"]
_SEG_METRIC_LABELS = {
    "readiness_completion_pct": "Completion %",
    "open_gap_count": "Open Gaps",
    "critical_item_count": "Critical Items",
    "total_requirement_count": "Requirements",
}


def _readiness_snapshot(data: ReportData) -> str:
    rows = readiness_snapshot_rows(data)
    if not rows:
        return "## Readiness Snapshot\n\n_No readiness data available._"
    header = "| Metric | Period | Value | Unit |"
    sep = "| --- | --- | --- | --- |"
    table_rows = []
    for row in rows:
        formatted = format_metric_value(row["value"], row["unit"])
        cells = [
            str(row["label"]).replace("|", "\\|"),
            str(row["date"]).replace("|", "\\|"),
            formatted.replace("|", "\\|"),
            str(row["unit"]).replace("|", "\\|"),
        ]
        table_rows.append("| " + " | ".join(cells) + " |")
    return "\n".join(["## Readiness Snapshot", "", header, sep] + table_rows)


def _open_gaps(data: ReportData) -> str:
    all_rows = {r["metric_id"]: r for r in snapshot_rows(data)}
    gap_row = all_rows.get("open_gap_count")
    if gap_row is None:
        return "## Open Gaps\n\n_No gap data available._"
    try:
        count_str = str(int(float(gap_row["value"])))
    except (ValueError, TypeError):
        count_str = str(gap_row["value"])
    lines = ["## Open Gaps", "", f"**Open Gaps:** {count_str}"]
    seg_data = readiness_segment_data(data, "date_category", "category")
    if seg_data and any(r.get("open_gap_count") is not None for r in seg_data):
        lines += ["", "**By Category:**", "", "| Category | Open Gaps |", "| --- | --- |"]
        for r in seg_data:
            val = r.get("open_gap_count")
            cell = str(int(float(val))) if val is not None else "—"
            lines.append(f"| {r['segment']} | {cell} |")
    return "\n".join(lines)


def _critical_items(data: ReportData) -> str:
    all_rows = {r["metric_id"]: r for r in snapshot_rows(data)}
    crit_row = all_rows.get("critical_item_count")
    if crit_row is None:
        return "## Critical Items\n\n_No critical item data available._"
    try:
        count_int = int(float(crit_row["value"]))
        count_str = str(count_int)
    except (ValueError, TypeError):
        count_int = None
        count_str = str(crit_row["value"])
    alert = " — requires immediate attention" if count_int and count_int > 0 else ""
    lines = ["## Critical Items", "", f"**Critical Items:** {count_str}{alert}"]
    seg_data = readiness_segment_data(data, "date_category", "category")
    if seg_data and any(r.get("critical_item_count") is not None for r in seg_data):
        lines += ["", "**By Category:**", "", "| Category | Critical Items |", "| --- | --- |"]
        for r in seg_data:
            val = r.get("critical_item_count")
            cell = str(int(float(val))) if val is not None else "—"
            lines.append(f"| {r['segment']} | {cell} |")
    return "\n".join(lines)


def _readiness_by_segment(data: ReportData) -> str:
    def _table(seg_data: list[dict], seg_label: str) -> list[str]:
        if not seg_data:
            return []
        present = [m for m in _SEG_METRIC_IDS if any(r.get(m) is not None for r in seg_data)]
        if not present:
            return []
        col_labels = [_SEG_METRIC_LABELS[m] for m in present]
        header = "| " + " | ".join([seg_label] + col_labels) + " |"
        sep = "| " + " | ".join(["---"] * (1 + len(present))) + " |"
        rows = []
        for r in seg_data:
            cells = [r["segment"]]
            for m in present:
                val = r.get(m)
                if val is None:
                    cells.append("—")
                elif m == "readiness_completion_pct":
                    cells.append(format_metric_value(val, "%"))
                else:
                    try:
                        cells.append(str(int(float(val))))
                    except (ValueError, TypeError):
                        cells.append(str(val))
            rows.append("| " + " | ".join(cells) + " |")
        return [header, sep] + rows

    cat_data = readiness_segment_data(data, "date_category", "category")
    mkt_data = readiness_segment_data(data, "date_market", "market")
    if not cat_data and not mkt_data:
        return ""
    lines = ["## Readiness by Segment"]
    if cat_data:
        lines += ["", "**By Category:**", ""]
        lines += _table(cat_data, "Category")
    if mkt_data:
        lines += ["", "**By Market:**", ""]
        lines += _table(mkt_data, "Market")
    return "\n".join(lines)


def _readiness_next_steps(data: ReportData) -> str:
    rows = {r["metric_id"]: r for r in snapshot_rows(data)}
    steps = []
    crit = rows.get("critical_item_count")
    if crit is not None:
        try:
            n = int(float(crit["value"]))
            if n > 0:
                steps.append(f"Resolve {n} critical item{'s' if n != 1 else ''} before project gate review.")
        except (ValueError, TypeError):
            pass
    gaps = rows.get("open_gap_count")
    if gaps is not None:
        try:
            n = int(float(gaps["value"]))
            if n > 0:
                steps.append(f"Address {n} open gap{'s' if n != 1 else ''} to advance readiness.")
        except (ValueError, TypeError):
            pass
    completion = rows.get("readiness_completion_pct")
    if completion is not None:
        try:
            pct = float(completion["value"])
            if pct >= 100:
                steps.append("Readiness is at 100% — maintain posture and schedule periodic reviews.")
            else:
                steps.append(
                    f"Current readiness is {format_metric_value(pct, '%')} — close remaining items "
                    "to reach 100% before milestone review."
                )
        except (ValueError, TypeError):
            pass
    if not steps:
        steps.append("Review readiness metrics to identify gaps and priorities.")
    steps.append("Schedule periodic readiness reviews to monitor progress against plan.")
    lines = ["## Recommended Next Steps", ""]
    lines += [f"- {s}" for s in steps]
    return "\n".join(lines)
