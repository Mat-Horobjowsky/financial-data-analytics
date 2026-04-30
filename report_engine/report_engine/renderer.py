from __future__ import annotations

from datetime import date as _date
from pathlib import Path

from report_engine.formatting import format_metric_value
from report_engine.loader import ReportData

_DISPLAY_COLS = ["date", "metric_id", "label", "value", "unit"]
_TIME_COLS = ["prior_period_value", "period_change", "period_change_pct"]
_DICT_COLS = ["id", "label", "type", "unit", "description"]


def render_markdown(data: ReportData, report_date: _date | None = None) -> str:
    if report_date is None:
        report_date = _date.today()
    sections = [
        _header(data, report_date),
        _validation(data),
        _metrics_summary(data),
        _metric_dictionary(data),
    ]
    return "\n\n".join(s for s in sections if s)


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
    header = "| " + " | ".join(cols) + " |"
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
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    rows = [
        "| " + " | ".join(str(row[c]).replace("|", "\\|") for c in cols) + " |"
        for _, row in df.iterrows()
    ]
    return "\n".join(["## Metric Dictionary", "", header, sep] + rows)
