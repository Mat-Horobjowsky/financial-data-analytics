from __future__ import annotations

from datetime import date as _date
from html import escape
from pathlib import Path

from report_engine.formatting import format_metric_value
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

_STYLE = (
    "body{font-family:sans-serif;max-width:960px;margin:40px auto;padding:0 20px;color:#222}"
    "h1,h2{border-bottom:1px solid #ddd;padding-bottom:4px}"
    "table{border-collapse:collapse;width:100%;margin:1em 0}"
    "th,td{border:1px solid #ccc;padding:6px 12px;text-align:left}"
    "th{background:#f5f5f5}"
    "code{background:#f0f0f0;padding:2px 4px;border-radius:3px;font-size:.9em}"
    "ul{margin:.5em 0;padding-left:1.5em}"
)


def render_html(data: ReportData, report_date: _date | None = None) -> str:
    if report_date is None:
        report_date = _date.today()
    body = "\n".join([
        _header_html(data, report_date),
        _validation_html(data),
        _metrics_summary_html(data),
        _metric_dictionary_html(data),
    ])
    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="UTF-8">\n'
        "<title>Metrics Report</title>\n"
        f"<style>{_STYLE}</style>\n"
        "</head>\n"
        "<body>\n"
        f"{body}\n"
        "</body>\n"
        "</html>"
    )


def _header_html(data: ReportData, report_date: _date) -> str:
    return (
        "<h1>Metrics Report</h1>\n"
        f"<p><strong>Input:</strong> <code>{escape(Path(data.input_dir).name)}</code><br>\n"
        f"<strong>Generated:</strong> {report_date.isoformat()}</p>"
    )


def _validation_html(data: ReportData) -> str:
    parts = [
        "<h2>Validation</h2>",
        f"<p><strong>Status:</strong> {escape(data.validation_status)}</p>",
    ]
    if data.validation_errors:
        items = "".join(f"<li>{escape(e)}</li>" for e in data.validation_errors)
        parts.append(f"<p><strong>Errors:</strong></p><ul>{items}</ul>")
    if data.validation_warnings:
        items = "".join(f"<li>{escape(w)}</li>" for w in data.validation_warnings)
        parts.append(f"<p><strong>Warnings:</strong></p><ul>{items}</ul>")
    return "\n".join(parts)


def _metrics_summary_html(data: ReportData) -> str:
    if data.long_metrics.empty:
        return "<h2>Metrics Summary</h2>\n<p><em>No metrics data available.</em></p>"
    df = data.long_metrics
    if "rollup_level" in df.columns:
        df = df[df["rollup_level"] == "date_only"]
    if df.empty:
        return "<h2>Metrics Summary</h2>\n<p><em>No metrics data available.</em></p>"
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
    header = "".join(f"<th>{escape(c)}</th>" for c in display_cols)
    rows = "".join(
        "<tr>" + "".join(f"<td>{escape(str(row[c]))}</td>" for c in cols) + "</tr>"
        for _, row in df.iterrows()
    )
    return (
        "<h2>Metrics Summary</h2>\n"
        f"<table><thead><tr>{header}</tr></thead><tbody>{rows}</tbody></table>"
    )


def _metric_dictionary_html(data: ReportData) -> str:
    if data.metric_dictionary.empty:
        return "<h2>Metric Dictionary</h2>\n<p><em>No metric dictionary available.</em></p>"
    df = data.metric_dictionary
    cols = [c for c in _DICT_COLS if c in df.columns]
    df = df[cols].fillna("").reset_index(drop=True)
    header = "".join(f"<th>{escape(c)}</th>" for c in cols)
    rows = "".join(
        "<tr>" + "".join(f"<td>{escape(str(row[c]))}</td>" for c in cols) + "</tr>"
        for _, row in df.iterrows()
    )
    return (
        "<h2>Metric Dictionary</h2>\n"
        f"<table><thead><tr>{header}</tr></thead><tbody>{rows}</tbody></table>"
    )
