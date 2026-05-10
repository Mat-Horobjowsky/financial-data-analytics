from __future__ import annotations

import csv
from pathlib import Path

import duckdb

KPI_METRICS = [
    "readiness_completion_pct",
    "total_requirement_count",
    "open_gap_count",
    "critical_item_count",
]

CATEGORY_LABELS = {
    "capacity": "Capacity Clarity",
    "timeline": "Timeline Clarity",
    "technical": "Technical Specs",
    "market": "Market Clarity",
    "power": "Power Strategy",
    "commercial": "Commercial Model",
    "capital": "Capital Readiness",
    "decision": "Decision Alignment",
}


def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _export_kpis(con: duckdb.DuckDBPyConnection, output_dir: Path) -> None:
    fieldnames = ["metric_id", "label", "value", "unit", "description"]
    placeholders = ", ".join(f"'{m}'" for m in KPI_METRICS)
    rows_raw = con.execute(f"""
        SELECT m.metric_id, m.label, m.value, m.unit,
               COALESCE(d.description, '') AS description
        FROM long_metrics m
        LEFT JOIN metric_dictionary d ON d.id = m.metric_id
        WHERE m.rollup_level = 'date_only'
          AND m.date = (SELECT max(date) FROM long_metrics WHERE rollup_level = 'date_only')
          AND m.metric_id IN ({placeholders})
    """).fetchall()

    order = {m: i for i, m in enumerate(KPI_METRICS)}
    rows = sorted(
        [dict(zip(fieldnames, r)) for r in rows_raw],
        key=lambda r: order.get(r["metric_id"], 999),
    )
    _write_csv(output_dir / "readiness_kpis.csv", rows, fieldnames)


def _export_by_category(con: duckdb.DuckDBPyConnection, output_dir: Path) -> None:
    fieldnames = ["category", "readiness_completion_pct", "open_gap_count"]
    rows_raw = con.execute("""
        SELECT category, metric_id, value
        FROM long_metrics
        WHERE rollup_level = 'date_category'
          AND date = (SELECT max(date) FROM long_metrics WHERE rollup_level = 'date_category')
          AND metric_id IN ('readiness_completion_pct', 'open_gap_count')
        ORDER BY category, metric_id
    """).fetchall()

    pivot: dict[str, dict] = {}
    for category, metric_id, value in rows_raw:
        if category not in pivot:
            label = CATEGORY_LABELS.get(category, category)
            pivot[category] = {"category": label, "readiness_completion_pct": "", "open_gap_count": ""}
        pivot[category][metric_id] = value

    rows = sorted(pivot.values(), key=lambda r: r["category"])
    _write_csv(output_dir / "readiness_by_category.csv", rows, fieldnames)


def _export_by_market(con: duckdb.DuckDBPyConnection, output_dir: Path) -> None:
    fieldnames = ["market", "readiness_completion_pct", "open_gap_count"]
    rows_raw = con.execute("""
        SELECT market, metric_id, value
        FROM long_metrics
        WHERE rollup_level = 'date_market'
          AND date = (SELECT max(date) FROM long_metrics WHERE rollup_level = 'date_market')
          AND metric_id IN ('readiness_completion_pct', 'open_gap_count')
        ORDER BY market, metric_id
    """).fetchall()

    pivot: dict[str, dict] = {}
    for market, metric_id, value in rows_raw:
        if market not in pivot:
            pivot[market] = {"market": market, "readiness_completion_pct": "", "open_gap_count": ""}
        pivot[market][metric_id] = value

    rows = sorted(pivot.values(), key=lambda r: r["market"])
    _write_csv(output_dir / "readiness_by_market.csv", rows, fieldnames)


def _export_validation_summary(con: duckdb.DuckDBPyConnection, output_dir: Path) -> None:
    fieldnames = ["status", "error_count", "warning_count"]
    rows_raw = con.execute("""
        SELECT status, error_count, warning_count
        FROM metrics_validation_summary
        LIMIT 1
    """).fetchall()

    rows = [{"status": r[0], "error_count": r[1], "warning_count": r[2]} for r in rows_raw]
    _write_csv(output_dir / "validation_summary.csv", rows, fieldnames)


def _export_metric_dictionary(con: duckdb.DuckDBPyConnection, output_dir: Path) -> None:
    fieldnames = ["id", "label", "type", "unit", "decimals", "description"]
    rows_raw = con.execute("""
        SELECT id, label, type, unit, decimals, description
        FROM metric_dictionary
        ORDER BY id
    """).fetchall()

    rows = [dict(zip(fieldnames, r)) for r in rows_raw]
    _write_csv(output_dir / "metric_dictionary.csv", rows, fieldnames)


def export_powerbi(
    con: duckdb.DuckDBPyConnection,
    output_dir: Path,
    client_context_path: Path | None = None,
) -> list[str]:
    """Export Power BI-ready CSVs from analytics.duckdb. Returns list of created file paths.

    If client_context_path is provided and exists, it is copied into output_dir as
    client_context.csv and included in the returned file list (six files total).
    When omitted, behavior is unchanged (five files).
    """
    import shutil as _shutil

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    _export_kpis(con, output_dir)
    _export_by_category(con, output_dir)
    _export_by_market(con, output_dir)
    _export_validation_summary(con, output_dir)
    _export_metric_dictionary(con, output_dir)

    files = [
        "readiness_kpis.csv",
        "readiness_by_category.csv",
        "readiness_by_market.csv",
        "validation_summary.csv",
        "metric_dictionary.csv",
    ]

    if client_context_path is not None:
        src = Path(client_context_path)
        if not src.exists():
            raise FileNotFoundError(f"client_context file not found: {src}")
        dest = output_dir / "client_context.csv"
        _shutil.copy2(str(src), str(dest))
        files.append("client_context.csv")

    return [str(output_dir / f) for f in files]
