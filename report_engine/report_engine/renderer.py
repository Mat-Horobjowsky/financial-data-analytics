from __future__ import annotations

from datetime import date

from report_engine.loader import ReportData

_DISPLAY_COLS = ["date", "metric_id", "label", "value", "unit"]
_DICT_COLS = ["id", "label", "type", "unit", "description"]


def render_markdown(data: ReportData) -> str:
    sections = [
        _header(data),
        _validation(data),
        _metrics_summary(data),
        _metric_dictionary(data),
    ]
    return "\n\n".join(s for s in sections if s)


def _header(data: ReportData) -> str:
    return (
        f"# Metrics Report\n\n"
        f"**Input:** `{data.input_dir}`  \n"
        f"**Generated:** {date.today().isoformat()}"
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
    cols = [c for c in _DISPLAY_COLS if c in df.columns]
    df = df[cols].fillna("").reset_index(drop=True)
    header = "| " + " | ".join(cols) + " |"
    sep = "| " + " | ".join("---" for _ in cols) + " |"
    rows = [
        "| " + " | ".join(str(row[c]) for c in cols) + " |"
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
        "| " + " | ".join(str(row[c]) for c in cols) + " |"
        for _, row in df.iterrows()
    ]
    return "\n".join(["## Metric Dictionary", "", header, sep] + rows)
