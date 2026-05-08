from __future__ import annotations

import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


def _format_value(value: float, unit: str) -> str:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "—"
    if unit == "%":
        return f"{value:.1f}%"
    return str(int(round(value)))


def _completion_color(pct: float) -> str:
    if pct >= 70:
        return "#27ae60"
    elif pct >= 50:
        return "#f39c12"
    else:
        return "#e74c3c"


def _build_kpi_cards(kpi_rows: list[dict], metric_dict: dict) -> list[dict]:
    display_order = [
        "readiness_completion_pct",
        "total_requirement_count",
        "open_gap_count",
        "critical_item_count",
    ]
    by_id = {r["metric_id"]: r for r in kpi_rows}
    cards = []
    for metric_id in display_order:
        if metric_id not in by_id:
            continue
        row = by_id[metric_id]
        meta = metric_dict.get(metric_id, {})
        cards.append({
            "metric_id": metric_id,
            "label": row["label"],
            "value": row["value"],
            "unit": row["unit"],
            "formatted_value": _format_value(row["value"], row["unit"]),
            "description": meta.get("description", ""),
            "is_primary": metric_id == "readiness_completion_pct",
        })
    return cards


def _pivot_breakdown(rows: list[dict], segment_col: str) -> list[dict]:
    segments: dict[str, dict] = {}
    for row in rows:
        seg = row.get(segment_col, "")
        if seg not in segments:
            segments[seg] = {}
        segments[seg][row["metric_id"]] = row["value"]

    result = []
    for name, metrics in segments.items():
        completion = metrics.get("readiness_completion_pct", 0.0) or 0.0
        open_gaps = metrics.get("open_gap_count", 0.0) or 0.0
        result.append({
            "name": name,
            "completion_pct": completion,
            "completion_pct_formatted": _format_value(completion, "%"),
            "open_gap_count": open_gaps,
            "open_gap_count_formatted": _format_value(open_gaps, "count"),
            "bar_width": min(100, max(0, int(round(completion)))),
            "bar_color": _completion_color(completion),
        })

    result.sort(key=lambda x: x["completion_pct"], reverse=True)
    return result


def build_template_context(spec: dict, data: dict) -> dict:
    dashboard_conf = spec["dashboard"]
    metric_dict = data.get("metric_dictionary", {})

    kpi_cards = _build_kpi_cards(data.get("kpi_cards", []), metric_dict)

    cat_rows_raw = data.get("category_breakdown")
    category_rows = _pivot_breakdown(cat_rows_raw, "category") if cat_rows_raw else []

    mkt_rows_raw = data.get("market_breakdown")
    market_rows = _pivot_breakdown(mkt_rows_raw, "market") if mkt_rows_raw else []

    section_titles: dict[str, str] = {}
    for section in spec.get("sections", []):
        section_titles[section["type"]] = section.get("title", section["type"])

    validation = data.get("validation_summary")

    return {
        "title": dashboard_conf["title"],
        "description": dashboard_conf["description"],
        "as_of_date": data.get("as_of_date", ""),
        "kpi_cards": kpi_cards,
        "category_rows": category_rows,
        "market_rows": market_rows,
        "kpi_section_title": section_titles.get("kpi_cards", "Key Metrics"),
        "category_section_title": section_titles.get("category_breakdown", "By Category"),
        "market_section_title": section_titles.get("market_breakdown", "By Market"),
        "validation_status": validation["status"] if validation else None,
        "validation_errors": validation["error_count"] if validation else 0,
        "validation_warnings": validation["warning_count"] if validation else 0,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
    }


def render_html(template_path: Path, spec: dict, data: dict) -> str:
    from jinja2 import Environment, FileSystemLoader

    context = build_template_context(spec, data)
    env = Environment(
        loader=FileSystemLoader(str(template_path.parent)),
        autoescape=True,
    )
    template = env.get_template(template_path.name)
    return template.render(**context)


def render_summary(
    spec: dict,
    data: dict,
    store_path: str,
    spec_path: str,
) -> dict:
    sections_rendered = []
    sections_skipped = list(data.get("sections_skipped", []))

    if data.get("kpi_cards"):
        sections_rendered.append("kpi_cards")
    if data.get("category_breakdown"):
        sections_rendered.append("category_breakdown")
    elif "category_breakdown" not in sections_skipped:
        sections_skipped.append("category_breakdown")
    if data.get("market_breakdown"):
        sections_rendered.append("market_breakdown")
    elif "market_breakdown" not in sections_skipped:
        sections_skipped.append("market_breakdown")

    validation = data.get("validation_summary")

    return {
        "dashboard": spec["dashboard"]["title"],
        "store": store_path,
        "spec": spec_path,
        "as_of_date": data.get("as_of_date"),
        "metrics_rendered": [r["metric_id"] for r in data.get("kpi_cards", [])],
        "sections_rendered": sections_rendered,
        "sections_skipped": sections_skipped,
        "validation_status": validation["status"] if validation else "unavailable",
        "validation_errors": validation["error_count"] if validation else None,
        "validation_warnings": validation["warning_count"] if validation else None,
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
