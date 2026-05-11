from __future__ import annotations

from datetime import date as _date
from html import escape
from pathlib import Path

from report_engine import templates as _templates
from report_engine.formatting import format_metric_value
from report_engine.insights import (
    build_insights,
    build_readiness_recommendations,
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

_STYLE = (
    "body{font-family:sans-serif;max-width:960px;margin:40px auto;padding:0 20px;color:#222}"
    "h1,h2{border-bottom:1px solid #ddd;padding-bottom:4px}"
    "table{border-collapse:collapse;width:100%;margin:1em 0}"
    "th,td{border:1px solid #ccc;padding:6px 12px;text-align:left}"
    "th{background:#f5f5f5}"
    "code{background:#f0f0f0;padding:2px 4px;border-radius:3px;font-size:.9em}"
    "ul{margin:.5em 0;padding-left:1.5em}"
)


def render_html(
    data: ReportData,
    report_date: _date | None = None,
    sections: list[str] | None = None,
) -> str:
    if report_date is None:
        report_date = _date.today()
    if sections is None:
        sections = _templates.get_sections(_templates.DEFAULT_TEMPLATE)
    _dispatch = {
        "header":               lambda d: _header_html(d, report_date),
        "validation":           _validation_html,
        "kpi_snapshot":         _kpi_snapshot_html,
        "key_insights":         _key_insights_html,
        "metrics_summary":      _metrics_summary_html,
        "metric_dictionary":    _metric_dictionary_html,
        "readiness_snapshot":   _readiness_snapshot_html,
        "open_gaps":            _open_gaps_html,
        "critical_items":       _critical_items_html,
        "readiness_by_segment": _readiness_by_segment_html,
        "readiness_next_steps": _readiness_next_steps_html,
    }
    body = "\n".join(s for s in (_dispatch[sid](data) for sid in sections) if s)
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
    header = "".join(f"<th>{escape(_DICT_COL_LABELS.get(c, c))}</th>" for c in cols)
    rows = "".join(
        "<tr>" + "".join(f"<td>{escape(str(row[c]))}</td>" for c in cols) + "</tr>"
        for _, row in df.iterrows()
    )
    return (
        "<h2>Metric Dictionary</h2>\n"
        f"<table><thead><tr>{header}</tr></thead><tbody>{rows}</tbody></table>"
    )


def _kpi_snapshot_html(data: ReportData) -> str:
    rows = snapshot_rows(data)
    if not rows:
        return ""
    _SNAP_LABELS = ["Metric", "Latest Period", "Value", "Unit"]
    header = "".join(f"<th>{escape(c)}</th>" for c in _SNAP_LABELS)
    table_rows = ""
    for row in rows:
        formatted_value = format_metric_value(row["value"], row["unit"])
        cells = [row["label"], row["date"], formatted_value, row["unit"]]
        table_rows += "<tr>" + "".join(f"<td>{escape(str(c))}</td>" for c in cells) + "</tr>"
    return (
        "<h2>KPI Snapshot</h2>\n"
        f"<table><thead><tr>{header}</tr></thead><tbody>{table_rows}</tbody></table>"
    )


def _key_insights_html(data: ReportData) -> str:
    if not has_period_data(data):
        return ""
    insights = build_insights(data)
    if not insights:
        return ""
    items = "".join(f"<li>{escape(i['text'])}</li>" for i in insights)
    return f"<h2>Key Insights</h2>\n<ul>{items}</ul>"


# ── Readiness sections (HTML) ──────────────────────────────────────────────────

_SEG_METRIC_IDS_HTML = ["readiness_completion_pct", "open_gap_count", "critical_item_count", "total_requirement_count"]
_SEG_METRIC_LABELS_HTML = {
    "readiness_completion_pct": "Completion %",
    "open_gap_count": "Open Gaps",
    "critical_item_count": "Critical Items",
    "total_requirement_count": "Requirements",
}


def _readiness_snapshot_html(data: ReportData) -> str:
    rows = readiness_snapshot_rows(data)
    if not rows:
        return "<h2>Readiness Snapshot</h2>\n<p><em>No readiness data available.</em></p>"
    header = "".join(f"<th>{escape(c)}</th>" for c in ["Metric", "Period", "Value", "Unit"])
    table_rows = ""
    for row in rows:
        formatted = format_metric_value(row["value"], row["unit"])
        cells = [str(row["label"]), str(row["date"]), formatted, str(row["unit"])]
        table_rows += "<tr>" + "".join(f"<td>{escape(c)}</td>" for c in cells) + "</tr>"
    return (
        "<h2>Readiness Snapshot</h2>\n"
        f"<table><thead><tr>{header}</tr></thead><tbody>{table_rows}</tbody></table>"
    )


def _open_gaps_html(data: ReportData) -> str:
    all_rows = {r["metric_id"]: r for r in snapshot_rows(data)}
    gap_row = all_rows.get("open_gap_count")
    if gap_row is None:
        return "<h2>Open Gaps</h2>\n<p><em>No gap data available.</em></p>"
    try:
        count_str = str(int(float(gap_row["value"])))
    except (ValueError, TypeError):
        count_str = str(gap_row["value"])
    parts = [
        "<h2>Open Gaps</h2>",
        f"<p><strong>Open Gaps:</strong> {escape(count_str)}</p>",
    ]
    seg_data = readiness_segment_data(data, "date_category", "category")
    if seg_data and any(r.get("open_gap_count") is not None for r in seg_data):
        parts.append("<p><strong>By Category:</strong></p>")
        hdr = "<th>Category</th><th>Open Gaps</th>"
        rows = ""
        for r in seg_data:
            val = r.get("open_gap_count")
            cell = str(int(float(val))) if val is not None else "—"
            rows += f"<tr><td>{escape(r['segment'])}</td><td>{escape(cell)}</td></tr>"
        parts.append(f"<table><thead><tr>{hdr}</tr></thead><tbody>{rows}</tbody></table>")
    return "\n".join(parts)


def _critical_items_html(data: ReportData) -> str:
    all_rows = {r["metric_id"]: r for r in snapshot_rows(data)}
    crit_row = all_rows.get("critical_item_count")
    if crit_row is None:
        return "<h2>Critical Items</h2>\n<p><em>No critical item data available.</em></p>"
    try:
        count_int = int(float(crit_row["value"]))
        count_str = str(count_int)
    except (ValueError, TypeError):
        count_int = None
        count_str = str(crit_row["value"])
    alert = " — requires immediate attention" if count_int and count_int > 0 else ""
    parts = [
        "<h2>Critical Items</h2>",
        f"<p><strong>Critical Items:</strong> {escape(count_str)}{escape(alert)}</p>",
    ]
    seg_data = readiness_segment_data(data, "date_category", "category")
    if seg_data and any(r.get("critical_item_count") is not None for r in seg_data):
        parts.append("<p><strong>By Category:</strong></p>")
        hdr = "<th>Category</th><th>Critical Items</th>"
        rows = ""
        for r in seg_data:
            val = r.get("critical_item_count")
            cell = str(int(float(val))) if val is not None else "—"
            rows += f"<tr><td>{escape(r['segment'])}</td><td>{escape(cell)}</td></tr>"
        parts.append(f"<table><thead><tr>{hdr}</tr></thead><tbody>{rows}</tbody></table>")
    return "\n".join(parts)


def _readiness_by_segment_html(data: ReportData) -> str:
    def _table_html(seg_data: list[dict], seg_label: str) -> str:
        if not seg_data:
            return ""
        present = [m for m in _SEG_METRIC_IDS_HTML if any(r.get(m) is not None for r in seg_data)]
        if not present:
            return ""
        col_labels = [_SEG_METRIC_LABELS_HTML[m] for m in present]
        hdr = f"<th>{escape(seg_label)}</th>" + "".join(f"<th>{escape(c)}</th>" for c in col_labels)
        rows = ""
        for r in seg_data:
            cells = f"<td>{escape(r['segment'])}</td>"
            for m in present:
                val = r.get(m)
                if val is None:
                    cell = "—"
                elif m == "readiness_completion_pct":
                    cell = format_metric_value(val, "%")
                else:
                    try:
                        cell = str(int(float(val)))
                    except (ValueError, TypeError):
                        cell = str(val)
                cells += f"<td>{escape(cell)}</td>"
            rows += f"<tr>{cells}</tr>"
        return f"<table><thead><tr>{hdr}</tr></thead><tbody>{rows}</tbody></table>"

    cat_data = readiness_segment_data(data, "date_category", "category")
    mkt_data = readiness_segment_data(data, "date_market", "market")
    if not cat_data and not mkt_data:
        return ""
    parts = ["<h2>Readiness by Segment</h2>"]
    if cat_data:
        parts.append("<p><strong>By Category:</strong></p>")
        parts.append(_table_html(cat_data, "Category"))
    if mkt_data:
        parts.append("<p><strong>By Market:</strong></p>")
        parts.append(_table_html(mkt_data, "Market"))
    return "\n".join(parts)


def _readiness_next_steps_html(data: ReportData) -> str:
    recs = build_readiness_recommendations(data)
    items = "".join(f"<li>{escape(r['recommendation'])}</li>" for r in recs)
    return f"<h2>Recommended Next Steps</h2>\n<ul>{items}</ul>"
