from __future__ import annotations

from datetime import date as _date
from html import escape
from pathlib import Path

from report_engine import templates as _templates
from report_engine.formatting import format_metric_value
from report_engine.insights import (
    build_insights,
    build_readiness_assessment,
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


# ── Readiness PDF — polished one-page landscape executive brief ────────────────

_READINESS_PDF_STYLE = (
    "@page{size:A4 landscape;margin:10mm 12mm 8mm 12mm}"
    "body{font-family:Helvetica,Arial,sans-serif;font-size:8.5pt;color:#1a202c;margin:0;padding:0}"
    ".hdr-tbl{width:100%;margin-bottom:8pt}"
    ".hdr-left{background-color:#1a202c;padding:7pt 10pt 7pt 14pt;vertical-align:top}"
    ".hdr-right{background-color:#1a202c;padding:7pt 14pt 7pt 6pt;"
    "text-align:right;vertical-align:middle;width:80pt}"
    ".hdr-title{font-size:12pt;font-weight:bold;color:#f7fafc;margin:0;line-height:1.2}"
    ".hdr-asof{font-size:7pt;color:#718096;margin:0}"
    ".sec-title{font-size:6.5pt;font-weight:bold;color:#2d3748;"
    "border-bottom:1pt solid #e2e8f0;padding-bottom:1.5pt;margin:6pt 0 3pt 0}"
    ".kpi-tbl{width:100%;margin-bottom:8pt}"
    ".kpi-cell{border:0.75pt solid #e2e8f0;border-top:2.5pt solid #cbd5e0;"
    "background-color:#ffffff;padding:5pt 8pt 4pt;vertical-align:top;width:25%}"
    ".kpi-pri{border-top-color:#3182ce;background-color:#ebf8ff}"
    ".kpi-val{font-size:16pt;font-weight:bold;color:#1a202c;line-height:1.1}"
    ".kpi-val-pri{color:#2b6cb0}"
    ".kpi-lbl{font-size:6pt;font-weight:bold;color:#718096;margin-top:2pt}"
    ".body-tbl{width:100%}"
    ".body-l{vertical-align:top;padding-right:10pt;width:40%}"
    ".body-r{vertical-align:top;padding-left:10pt;width:60%}"
    ".steps{margin:1pt 0 3pt 12pt;padding:0}"
    ".steps li{font-size:8pt;color:#1a202c;margin-bottom:2pt;line-height:1.25}"
    ".s-crit{color:#c53030;font-weight:bold}"
    ".s-high{color:#2b6cb0}"
    ".bk-tbl{width:100%;border-collapse:collapse;margin-bottom:3pt}"
    ".bk-th{background-color:#f7fafc;border-bottom:1pt solid #e2e8f0;"
    "font-size:6pt;font-weight:bold;color:#a0aec0;padding:2pt 5pt;text-align:left}"
    ".bk-td{border-bottom:0.5pt solid #f0f4f8;padding:1.5pt 5pt;"
    "font-size:8pt;vertical-align:middle}"
    ".col-tbl{width:100%}"
    ".col-l{vertical-align:top;padding-right:6pt;width:50%}"
    ".col-r{vertical-align:top;padding-left:6pt;width:50%}"
    ".footer{margin-top:4pt;border-top:0.5pt solid #e2e8f0;padding-top:2pt}"
    ".footer p{font-size:6pt;color:#a0aec0;margin:1pt 0}"
    ".assess{background-color:#ebf8ff;border:0.75pt solid #bee3f8;"
    "border-top:3pt solid #3182ce;padding:6pt 8pt 6pt;margin:0 0 6pt 0;"
    "font-size:8pt;color:#1a202c;line-height:1.4}"
)


def _fmt_seg(s: str) -> str:
    if "_" not in s and s.isupper():
        return s
    return s.replace("_", " ").title()


def _pdf_completion_color(pct: float) -> str:
    if pct >= 70:
        return "#27ae60"
    if pct >= 50:
        return "#f39c12"
    return "#e74c3c"


def _readiness_pdf_as_of_date(data: ReportData) -> str:
    rows = readiness_snapshot_rows(data)
    if rows:
        return max(r["date"] for r in rows)
    return ""


def _readiness_pdf_header_html(title: str, as_of: str) -> str:
    full_title = escape(f"{title} — RFP Readiness Summary")
    asof_cell = ""
    if as_of:
        asof_cell = (
            f'<td class="hdr-right">'
            f'<p class="hdr-asof">As of {escape(as_of)}</p>'
            f"</td>"
        )
    return (
        '<table class="hdr-tbl" cellspacing="0" cellpadding="0">'
        "<tr>"
        f'<td class="hdr-left"><p class="hdr-title">{full_title}</p></td>'
        f"{asof_cell}"
        "</tr>"
        "</table>"
    )


def _readiness_pdf_kpi_cards_html(data: ReportData) -> str:
    _ORDER = [
        "readiness_completion_pct",
        "open_gap_count",
        "critical_item_count",
        "total_requirement_count",
    ]
    _LABELS = {
        "readiness_completion_pct": "Readiness Completion",
        "open_gap_count": "Open Gaps",
        "critical_item_count": "Critical Items",
        "total_requirement_count": "Requirements",
    }
    rows = readiness_snapshot_rows(data)
    by_id = {r["metric_id"]: r for r in rows}
    cards = ""
    for mid in _ORDER:
        if mid not in by_id:
            continue
        row = by_id[mid]
        formatted = format_metric_value(row["value"], row["unit"])
        label = _LABELS.get(mid, row["label"])
        is_primary = mid == "readiness_completion_pct"
        cell_cls = "kpi-cell kpi-pri" if is_primary else "kpi-cell"
        val_cls = "kpi-val kpi-val-pri" if is_primary else "kpi-val"
        cards += (
            f'<td class="{cell_cls}">'
            f'<div class="{val_cls}">{escape(formatted)}</div>'
            f'<div class="kpi-lbl">{escape(label.upper())}</div>'
            f"</td>"
        )
    if not cards:
        return ""
    return (
        '<p class="sec-title">KEY METRICS</p>'
        '<table class="kpi-tbl" cellspacing="3" cellpadding="0">'
        f"<tr>{cards}</tr>"
        "</table>"
    )


def _readiness_pdf_next_steps_html(data: ReportData) -> str:
    recs = build_readiness_recommendations(data)
    if not recs:
        return ""
    items = ""
    for r in recs:
        sev = r.get("severity", "")
        cls = ' class="s-crit"' if sev == "critical" else (' class="s-high"' if sev == "high" else "")
        items += f"<li{cls}>{escape(r['recommendation'])}</li>"
    return (
        '<p class="sec-title">RECOMMENDED NEXT STEPS</p>'
        f'<ol class="steps">{items}</ol>'
    )


def _readiness_pdf_assessment_html(data: ReportData) -> str:
    a = build_readiness_assessment(data)
    if not a["summary"]:
        return ""
    posture = a["posture"]
    posture_color = "#c53030" if posture in ("Not RFP-Ready", "At Risk") else "#2b6cb0"
    body_parts = [a["summary"]]
    if a.get("weakness_note"):
        body_parts.append(a["weakness_note"])
    body_text = " ".join(body_parts)
    return (
        '<p class="sec-title">EXECUTIVE ASSESSMENT</p>'
        '<p class="assess">'
        f'<strong style="font-size:10pt;color:{posture_color};">'
        f"Current Posture: {escape(posture)}</strong><br/>"
        f"{escape(body_text)}<br/>"
        f'<span style="font-size:8pt;color:#4a5568;">'
        f"Transaction posture: {escape(a['transaction_posture'])}</span>"
        "</p>"
    )


def _readiness_pdf_gaps_section_html(data: ReportData) -> str:
    all_snap = {r["metric_id"]: r for r in snapshot_rows(data)}
    gap_row = all_snap.get("open_gap_count")
    if gap_row is None:
        return ""
    try:
        count_str = str(int(float(gap_row["value"])))
    except (ValueError, TypeError):
        count_str = str(gap_row["value"])
    seg_data = readiness_segment_data(data, "date_category", "category")
    rows_html = ""
    if seg_data and any(r.get("open_gap_count") is not None for r in seg_data):
        for r in seg_data:
            val = r.get("open_gap_count")
            if val is None:
                continue
            try:
                count = int(float(val))
            except (ValueError, TypeError):
                continue
            if count == 0:
                continue
            rows_html += (
                f"<tr>"
                f'<td class="bk-td">{escape(_fmt_seg(r["segment"]))}</td>'
                f'<td class="bk-td" style="text-align:center;">{escape(str(count))}</td>'
                f"</tr>"
            )
    table = ""
    if rows_html:
        table = (
            '<table class="bk-tbl"><thead><tr>'
            '<th class="bk-th">Category</th>'
            '<th class="bk-th" style="text-align:center;">Gaps</th>'
            f"</tr></thead><tbody>{rows_html}</tbody></table>"
        )
    return (
        '<p class="sec-title">OPEN GAPS</p>'
        f'<p style="font-size:9pt;font-weight:bold;color:#1a202c;margin:2pt 0 4pt 0;">'
        f"Total: {escape(count_str)}</p>"
        f"{table}"
    )


def _readiness_pdf_critical_section_html(data: ReportData) -> str:
    all_snap = {r["metric_id"]: r for r in snapshot_rows(data)}
    crit_row = all_snap.get("critical_item_count")
    if crit_row is None:
        return ""
    try:
        count_int = int(float(crit_row["value"]))
        count_str = str(count_int)
    except (ValueError, TypeError):
        count_int = None
        count_str = str(crit_row["value"])
    count_color = "#c53030" if (count_int is not None and count_int > 0) else "#1a202c"
    seg_data = readiness_segment_data(data, "date_category", "category")
    rows_html = ""
    if seg_data and any(r.get("critical_item_count") is not None for r in seg_data):
        for r in seg_data:
            val = r.get("critical_item_count")
            if val is None:
                continue
            try:
                count = int(float(val))
            except (ValueError, TypeError):
                continue
            if count == 0:
                continue
            rows_html += (
                f"<tr>"
                f'<td class="bk-td">{escape(_fmt_seg(r["segment"]))}</td>'
                f'<td class="bk-td" style="text-align:center;">{escape(str(count))}</td>'
                f"</tr>"
            )
    table = ""
    if rows_html:
        table = (
            '<table class="bk-tbl"><thead><tr>'
            '<th class="bk-th">Category</th>'
            '<th class="bk-th" style="text-align:center;">Critical</th>'
            f"</tr></thead><tbody>{rows_html}</tbody></table>"
        )
    return (
        '<p class="sec-title">CRITICAL ITEMS</p>'
        f'<p style="font-size:9pt;font-weight:bold;color:{count_color};margin:2pt 0 4pt 0;">'
        f"Total: {escape(count_str)}</p>"
        f"{table}"
    )


def _readiness_pdf_segment_tables_html(data: ReportData) -> str:
    _SEG_MIDS = [
        "readiness_completion_pct",
        "open_gap_count",
        "critical_item_count",
        "total_requirement_count",
    ]
    _SEG_HDR = {
        "readiness_completion_pct": "Completion",
        "open_gap_count": "Gaps",
        "critical_item_count": "Critical",
        "total_requirement_count": "Reqs",
    }

    def _seg_table(seg_data: list[dict], first_col: str) -> str:
        if not seg_data:
            return ""
        present = [m for m in _SEG_MIDS if any(r.get(m) is not None for r in seg_data)]
        if not present:
            return ""
        col_hdrs = f'<th class="bk-th">{escape(first_col)}</th>'
        col_hdrs += "".join(
            f'<th class="bk-th" style="text-align:center;">{escape(_SEG_HDR[m])}</th>'
            for m in present
        )
        rows = ""
        for r in seg_data:
            cells = f'<td class="bk-td" style="font-weight:500;">{escape(_fmt_seg(r["segment"]))}</td>'
            for m in present:
                val = r.get(m)
                if val is None:
                    cell_html = f'<td class="bk-td" style="text-align:center;">—</td>'
                elif m == "readiness_completion_pct":
                    pct = float(val)
                    color = _pdf_completion_color(pct)
                    cell_html = (
                        f'<td class="bk-td">'
                        f'<span style="font-weight:bold;color:{color};">'
                        f'{escape(format_metric_value(val, "%"))}'
                        f"</span></td>"
                    )
                else:
                    try:
                        txt = str(int(float(val)))
                    except (ValueError, TypeError):
                        txt = str(val)
                    cell_html = f'<td class="bk-td" style="text-align:center;">{escape(txt)}</td>'
                cells += cell_html
            rows += f"<tr>{cells}</tr>"
        return (
            '<table class="bk-tbl">'
            f"<thead><tr>{col_hdrs}</tr></thead>"
            f"<tbody>{rows}</tbody>"
            "</table>"
        )

    cat_data = readiness_segment_data(data, "date_category", "category")
    mkt_data = readiness_segment_data(data, "date_market", "market")
    parts = []
    if cat_data:
        parts.append('<p class="sec-title">READINESS BY CATEGORY</p>')
        parts.append(_seg_table(cat_data, "Category"))
    if mkt_data:
        parts.append('<p class="sec-title">READINESS BY MARKET</p>')
        parts.append(_seg_table(mkt_data, "Market"))
    return "\n".join(parts)


def render_readiness_pdf_html(
    data: ReportData,
    title: str | None = None,
    report_date: _date | None = None,
) -> str:
    """Render a polished one-page landscape client-facing readiness brief as PDF-ready HTML.

    Layout (A4 landscape, single page):
        full-width dark header → KPI row
        left column (40%): executive assessment, recommended next steps
        right column (60%): open gaps / critical items, readiness by category, by market
        full-width footer
    """
    if title is None:
        title = Path(data.input_dir).name.replace("_", " ").title()
    if report_date is None:
        report_date = _date.today()

    as_of = _readiness_pdf_as_of_date(data)
    header = _readiness_pdf_header_html(title, as_of)
    kpi_cards = _readiness_pdf_kpi_cards_html(data)
    assessment = _readiness_pdf_assessment_html(data)
    next_steps = _readiness_pdf_next_steps_html(data)

    gaps = _readiness_pdf_gaps_section_html(data)
    critical = _readiness_pdf_critical_section_html(data)
    seg_tables = _readiness_pdf_segment_tables_html(data)

    if gaps and critical:
        gaps_critical = (
            '<table class="col-tbl" cellspacing="0" cellpadding="0"><tr>'
            f'<td class="col-l">{gaps}</td>'
            f'<td class="col-r">{critical}</td>'
            "</tr></table>"
        )
    else:
        gaps_critical = gaps or critical or ""

    footer_html = (
        '<div class="footer">'
        f"<p>Generated from Metrics Engine outputs and rendered by Report Engine."
        f" | Generated {escape(report_date.isoformat())}</p>"
        "</div>"
    )

    body_cols = (
        '<table class="body-tbl" cellspacing="0" cellpadding="0"><tr>'
        f'<td class="body-l">{assessment}\n{next_steps}</td>'
        f'<td class="body-r">{gaps_critical}\n{seg_tables}</td>'
        "</tr></table>"
    )

    full_title = escape(f"{title} — RFP Readiness Summary")
    body = f"{header}\n{kpi_cards}\n{body_cols}\n{footer_html}"

    return (
        "<!DOCTYPE html>\n"
        '<html lang="en">\n'
        "<head>\n"
        '<meta charset="UTF-8">\n'
        f"<title>{full_title}</title>\n"
        f"<style>{_READINESS_PDF_STYLE}</style>\n"
        "</head>\n"
        "<body>\n"
        f"{body}\n"
        "</body>\n"
        "</html>"
    )
