from __future__ import annotations

from pathlib import Path
from typing import Optional

import duckdb

_VALID_SEGMENT_COLUMNS = {"category", "market", "provider", "region"}


def connect(store_path: str) -> duckdb.DuckDBPyConnection:
    path = Path(store_path)
    if not path.exists():
        raise FileNotFoundError(f"Analytics store not found: {store_path}")
    return duckdb.connect(str(path), read_only=True)


def load_kpi_cards(
    con: duckdb.DuckDBPyConnection,
    rollup_level: str,
    metric_ids: list[str],
) -> list[dict]:
    """Return one row per metric_id at the latest date for the given rollup_level."""
    if not metric_ids:
        return []
    placeholders = ", ".join(f"'{m}'" for m in metric_ids)
    df = con.execute(
        f"""
        SELECT metric_id, label, value, unit
        FROM long_metrics
        WHERE rollup_level = ?
          AND date = (SELECT MAX(date) FROM long_metrics WHERE rollup_level = ?)
          AND metric_id IN ({placeholders})
        ORDER BY metric_id
        """,
        [rollup_level, rollup_level],
    ).fetchdf()
    return df.to_dict(orient="records")


def load_breakdown(
    con: duckdb.DuckDBPyConnection,
    rollup_level: str,
    segment_column: str,
    metric_ids: list[str],
) -> list[dict]:
    """Return breakdown rows for the given rollup_level and segment column."""
    if segment_column not in _VALID_SEGMENT_COLUMNS:
        raise ValueError(f"Unknown segment_column: {segment_column!r}")
    if not metric_ids:
        return []
    placeholders = ", ".join(f"'{m}'" for m in metric_ids)
    df = con.execute(
        f"""
        SELECT {segment_column}, metric_id, label, value, unit
        FROM long_metrics
        WHERE rollup_level = ?
          AND date = (SELECT MAX(date) FROM long_metrics WHERE rollup_level = ?)
          AND metric_id IN ({placeholders})
        ORDER BY {segment_column}, metric_id
        """,
        [rollup_level, rollup_level],
    ).fetchdf()
    return df.to_dict(orient="records")


def load_metric_dictionary(con: duckdb.DuckDBPyConnection) -> dict[str, dict]:
    """Return {metric_id: row_dict} from metric_dictionary."""
    df = con.execute(
        "SELECT id, label, type, unit, decimals, description FROM metric_dictionary"
    ).fetchdf()
    return {row["id"]: row.to_dict() for _, row in df.iterrows()}


def load_validation_summary(con: duckdb.DuckDBPyConnection) -> Optional[dict]:
    """Return the first validation summary row, or None if the table is empty."""
    df = con.execute(
        "SELECT status, error_count, warning_count FROM metrics_validation_summary LIMIT 1"
    ).fetchdf()
    if df.empty:
        return None
    row = df.iloc[0]
    return {
        "status": row["status"],
        "error_count": int(row["error_count"]),
        "warning_count": int(row["warning_count"]),
    }


def load_all(con: duckdb.DuckDBPyConnection, spec: dict) -> dict:
    """Load all data required by the spec. Missing optional sections are recorded in sections_skipped."""
    data: dict = {
        "kpi_cards": [],
        "category_breakdown": None,
        "market_breakdown": None,
        "metric_dictionary": {},
        "validation_summary": None,
        "as_of_date": None,
        "sections_skipped": [],
    }

    data["metric_dictionary"] = load_metric_dictionary(con)
    data["validation_summary"] = load_validation_summary(con)

    for section in spec.get("sections", []):
        stype = section["type"]

        if stype == "kpi_cards":
            data["kpi_cards"] = load_kpi_cards(
                con,
                rollup_level=section["rollup_level"],
                metric_ids=section["metrics"],
            )

        elif stype in ("category_breakdown", "market_breakdown"):
            seg_col = section.get("segment_column", stype.replace("_breakdown", ""))
            rows = load_breakdown(
                con,
                rollup_level=section["rollup_level"],
                segment_column=seg_col,
                metric_ids=section["metrics"],
            )
            if rows:
                data[stype] = rows
            elif section.get("optional", False):
                data["sections_skipped"].append(stype)

    result = con.execute(
        "SELECT MAX(date) FROM long_metrics WHERE rollup_level = 'date_only'"
    ).fetchone()
    if result and result[0]:
        data["as_of_date"] = result[0]

    return data
