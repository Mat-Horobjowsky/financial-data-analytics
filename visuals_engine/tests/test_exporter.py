import csv
from pathlib import Path

import duckdb
import pytest

from visuals_engine.exporter import CATEGORY_LABELS, export_powerbi


def _read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _headers(path: Path) -> set[str]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return set(reader.fieldnames or [])


def _open(store_path: str) -> duckdb.DuckDBPyConnection:
    return duckdb.connect(store_path, read_only=True)


# --- all five files created ---


def test_export_powerbi_creates_all_files(sample_store, tmp_path):
    con = _open(sample_store)
    try:
        export_powerbi(con, tmp_path / "powerbi")
    finally:
        con.close()
    out = tmp_path / "powerbi"
    for fname in [
        "readiness_kpis.csv",
        "readiness_by_category.csv",
        "readiness_by_market.csv",
        "validation_summary.csv",
        "metric_dictionary.csv",
    ]:
        assert (out / fname).exists(), f"Missing: {fname}"


def test_export_powerbi_returns_five_paths(sample_store, tmp_path):
    con = _open(sample_store)
    try:
        paths = export_powerbi(con, tmp_path / "powerbi")
    finally:
        con.close()
    assert len(paths) == 5
    assert all(p.endswith(".csv") for p in paths)


# --- readiness_kpis.csv ---


def test_kpi_csv_columns(sample_store, tmp_path):
    con = _open(sample_store)
    try:
        export_powerbi(con, tmp_path / "powerbi")
    finally:
        con.close()
    assert _headers(tmp_path / "powerbi" / "readiness_kpis.csv") == {
        "metric_id", "label", "value", "unit", "description"
    }


def test_kpi_csv_contains_all_four_metrics(sample_store, tmp_path):
    con = _open(sample_store)
    try:
        export_powerbi(con, tmp_path / "powerbi")
    finally:
        con.close()
    rows = _read_csv(tmp_path / "powerbi" / "readiness_kpis.csv")
    ids = {r["metric_id"] for r in rows}
    assert ids == {
        "readiness_completion_pct",
        "total_requirement_count",
        "open_gap_count",
        "critical_item_count",
    }


def test_kpi_csv_readiness_value(sample_store, tmp_path):
    con = _open(sample_store)
    try:
        export_powerbi(con, tmp_path / "powerbi")
    finally:
        con.close()
    rows = _read_csv(tmp_path / "powerbi" / "readiness_kpis.csv")
    row = next(r for r in rows if r["metric_id"] == "readiness_completion_pct")
    assert float(row["value"]) == pytest.approx(50.0)


def test_kpi_csv_description_populated(sample_store, tmp_path):
    con = _open(sample_store)
    try:
        export_powerbi(con, tmp_path / "powerbi")
    finally:
        con.close()
    rows = _read_csv(tmp_path / "powerbi" / "readiness_kpis.csv")
    row = next(r for r in rows if r["metric_id"] == "readiness_completion_pct")
    assert row["description"] != ""


# --- readiness_by_category.csv ---


def test_category_csv_columns(sample_store, tmp_path):
    con = _open(sample_store)
    try:
        export_powerbi(con, tmp_path / "powerbi")
    finally:
        con.close()
    assert _headers(tmp_path / "powerbi" / "readiness_by_category.csv") == {
        "category", "readiness_completion_pct", "open_gap_count"
    }


def test_category_csv_applies_friendly_labels(sample_store, tmp_path):
    con = _open(sample_store)
    try:
        export_powerbi(con, tmp_path / "powerbi")
    finally:
        con.close()
    rows = _read_csv(tmp_path / "powerbi" / "readiness_by_category.csv")
    labels = {r["category"] for r in rows}
    assert "Capital Readiness" in labels
    assert "Commercial Model" in labels
    assert "capital" not in labels
    assert "commercial" not in labels


def test_category_csv_pivot_values(sample_store, tmp_path):
    con = _open(sample_store)
    try:
        export_powerbi(con, tmp_path / "powerbi")
    finally:
        con.close()
    rows = _read_csv(tmp_path / "powerbi" / "readiness_by_category.csv")
    capital = next(r for r in rows if r["category"] == "Capital Readiness")
    assert float(capital["readiness_completion_pct"]) == pytest.approx(33.3)
    assert float(capital["open_gap_count"]) == pytest.approx(2.0)


def test_category_csv_empty_when_no_category_rows(sample_store_no_breakdowns, tmp_path):
    con = _open(sample_store_no_breakdowns)
    try:
        export_powerbi(con, tmp_path / "powerbi")
    finally:
        con.close()
    rows = _read_csv(tmp_path / "powerbi" / "readiness_by_category.csv")
    assert rows == []


# --- readiness_by_market.csv ---


def test_market_csv_columns(sample_store, tmp_path):
    con = _open(sample_store)
    try:
        export_powerbi(con, tmp_path / "powerbi")
    finally:
        con.close()
    assert _headers(tmp_path / "powerbi" / "readiness_by_market.csv") == {
        "market", "readiness_completion_pct", "open_gap_count"
    }


def test_market_csv_empty_when_no_market_rows(sample_store, tmp_path):
    # sample_store fixture has no date_market rows
    con = _open(sample_store)
    try:
        export_powerbi(con, tmp_path / "powerbi")
    finally:
        con.close()
    rows = _read_csv(tmp_path / "powerbi" / "readiness_by_market.csv")
    assert rows == []


def test_market_csv_empty_when_no_breakdowns(sample_store_no_breakdowns, tmp_path):
    con = _open(sample_store_no_breakdowns)
    try:
        export_powerbi(con, tmp_path / "powerbi")
    finally:
        con.close()
    rows = _read_csv(tmp_path / "powerbi" / "readiness_by_market.csv")
    assert rows == []


# --- validation_summary.csv ---


def test_validation_summary_csv_columns(sample_store, tmp_path):
    con = _open(sample_store)
    try:
        export_powerbi(con, tmp_path / "powerbi")
    finally:
        con.close()
    assert _headers(tmp_path / "powerbi" / "validation_summary.csv") == {
        "status", "error_count", "warning_count"
    }


def test_validation_summary_csv_values(sample_store, tmp_path):
    con = _open(sample_store)
    try:
        export_powerbi(con, tmp_path / "powerbi")
    finally:
        con.close()
    rows = _read_csv(tmp_path / "powerbi" / "validation_summary.csv")
    assert len(rows) == 1
    assert rows[0]["status"] == "passed_with_warnings"
    assert rows[0]["error_count"] == "0"
    assert rows[0]["warning_count"] == "5"


def test_validation_summary_csv_empty_when_no_rows(sample_store_no_breakdowns, tmp_path):
    con = _open(sample_store_no_breakdowns)
    try:
        export_powerbi(con, tmp_path / "powerbi")
    finally:
        con.close()
    rows = _read_csv(tmp_path / "powerbi" / "validation_summary.csv")
    assert rows == []


# --- metric_dictionary.csv ---


def test_metric_dictionary_csv_columns(sample_store, tmp_path):
    con = _open(sample_store)
    try:
        export_powerbi(con, tmp_path / "powerbi")
    finally:
        con.close()
    assert _headers(tmp_path / "powerbi" / "metric_dictionary.csv") == {
        "id", "label", "type", "unit", "decimals", "description"
    }


def test_metric_dictionary_csv_row_count(sample_store, tmp_path):
    con = _open(sample_store)
    try:
        export_powerbi(con, tmp_path / "powerbi")
    finally:
        con.close()
    rows = _read_csv(tmp_path / "powerbi" / "metric_dictionary.csv")
    assert len(rows) == 4


def test_metric_dictionary_csv_contains_readiness_metric(sample_store, tmp_path):
    con = _open(sample_store)
    try:
        export_powerbi(con, tmp_path / "powerbi")
    finally:
        con.close()
    rows = _read_csv(tmp_path / "powerbi" / "metric_dictionary.csv")
    assert any(r["id"] == "readiness_completion_pct" for r in rows)


def test_metric_dictionary_csv_empty_when_no_rows(sample_store_no_breakdowns, tmp_path):
    con = _open(sample_store_no_breakdowns)
    try:
        export_powerbi(con, tmp_path / "powerbi")
    finally:
        con.close()
    rows = _read_csv(tmp_path / "powerbi" / "metric_dictionary.csv")
    assert rows == []


# --- CATEGORY_LABELS constant ---


def test_category_labels_has_eight_entries():
    assert len(CATEGORY_LABELS) == 8


def test_category_labels_covers_known_categories():
    for slug in ("capacity", "timeline", "technical", "market", "power", "commercial", "capital", "decision"):
        assert slug in CATEGORY_LABELS
