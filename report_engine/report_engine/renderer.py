from __future__ import annotations

from datetime import date as _date
from pathlib import Path

from report_engine import templates as _templates
from report_engine.formatting import format_metric_value
from report_engine.insights import build_insights, has_period_data, snapshot_rows
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
        "header":            lambda d: _header(d, report_date),
        "validation":        _validation,
        "kpi_snapshot":      _kpi_snapshot,
        "key_insights":      _key_insights,
        "metrics_summary":   _metrics_summary,
        "metric_dictionary": _metric_dictionary,
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
