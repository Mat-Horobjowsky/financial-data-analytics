"""
Power BI export contract tests.

These tests enforce the schema contract between the analytics pipeline Power BI
export stage and the reusable Power BI readiness dashboard template.
Contract is documented in: docs/powerbi_export_contract.md

Tests run against a minimal in-memory DuckDB store and do not require Power BI Desktop.
All tests are deterministic and use tmp_path outputs.
"""
from __future__ import annotations

import csv
from pathlib import Path

import duckdb
import pytest

from visuals_engine.exporter import export_powerbi

# ── Contract constants ──────────────────────────────────────────────────────────
# Changing these constants is a breaking change to the Power BI template.

_KPI_REQUIRED_COLUMNS = {"metric_id", "label", "value", "unit", "description"}
_KPI_REQUIRED_METRICS = {
    "readiness_completion_pct",
    "total_requirement_count",
    "open_gap_count",
    "critical_item_count",
}
_CATEGORY_REQUIRED_COLUMNS = {"category", "readiness_completion_pct", "open_gap_count"}
_MARKET_REQUIRED_COLUMNS = {"market", "readiness_completion_pct", "open_gap_count"}
_VALIDATION_REQUIRED_COLUMNS = {"status", "error_count", "warning_count"}
_DICT_REQUIRED_COLUMNS = {"id", "label", "type", "unit", "decimals", "description"}


# ── Helpers ─────────────────────────────────────────────────────────────────────

def _read_csv(path: Path) -> list[dict]:
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _headers(path: Path) -> set[str]:
    with open(path, newline="", encoding="utf-8") as f:
        return set(csv.DictReader(f).fieldnames or [])


def _build_store(tmp_path: Path, with_market: bool = True) -> str:
    """Build a minimal analytics.duckdb for contract tests."""
    db = tmp_path / "analytics.duckdb"
    con = duckdb.connect(str(db))
    con.execute("""
        CREATE TABLE long_metrics (
            rollup_level VARCHAR, date VARCHAR, category VARCHAR, market VARCHAR,
            metric_id VARCHAR, label VARCHAR, value DOUBLE, unit VARCHAR
        )
    """)
    con.execute("""
        INSERT INTO long_metrics VALUES
        ('date_only', '2025-01-15', NULL, NULL, 'readiness_completion_pct', 'Readiness Completion %', 50.0, '%'),
        ('date_only', '2025-01-15', NULL, NULL, 'total_requirement_count', 'Total Requirement Count', 20.0, 'requirements'),
        ('date_only', '2025-01-15', NULL, NULL, 'open_gap_count', 'Open Gap Count', 10.0, 'gaps'),
        ('date_only', '2025-01-15', NULL, NULL, 'critical_item_count', 'Critical Item Count', 4.0, 'items'),
        ('date_category', '2025-01-15', 'power', NULL, 'readiness_completion_pct', 'Readiness Completion %', 75.0, '%'),
        ('date_category', '2025-01-15', 'power', NULL, 'open_gap_count', 'Open Gap Count', 1.0, 'gaps'),
        ('date_category', '2025-01-15', 'commercial', NULL, 'readiness_completion_pct', 'Readiness Completion %', 25.0, '%'),
        ('date_category', '2025-01-15', 'commercial', NULL, 'open_gap_count', 'Open Gap Count', 3.0, 'gaps'),
        ('date_category', '2025-01-15', 'capital', NULL, 'readiness_completion_pct', 'Readiness Completion %', 33.3, '%'),
        ('date_category', '2025-01-15', 'capital', NULL, 'open_gap_count', 'Open Gap Count', 2.0, 'gaps')
    """)
    if with_market:
        con.execute("""
            INSERT INTO long_metrics VALUES
            ('date_market', '2025-01-15', NULL, 'NAM', 'readiness_completion_pct', 'Readiness Completion %', 46.7, '%'),
            ('date_market', '2025-01-15', NULL, 'NAM', 'open_gap_count', 'Open Gap Count', 5.0, 'gaps'),
            ('date_market', '2025-01-15', NULL, 'EMEA', 'readiness_completion_pct', 'Readiness Completion %', 60.0, '%'),
            ('date_market', '2025-01-15', NULL, 'EMEA', 'open_gap_count', 'Open Gap Count', 2.0, 'gaps')
        """)
    con.execute("""
        CREATE TABLE metric_dictionary (
            id VARCHAR, label VARCHAR, type VARCHAR, unit VARCHAR,
            decimals BIGINT, description VARCHAR
        )
    """)
    con.execute("""
        INSERT INTO metric_dictionary VALUES
        ('readiness_completion_pct', 'Readiness Completion %', 'completion_pct', '%', 1, 'Percentage of requirements marked complete'),
        ('total_requirement_count', 'Total Requirement Count', 'count', 'requirements', 0, 'Total number of requirements'),
        ('open_gap_count', 'Open Gap Count', 'conditional_count', 'gaps', 0, 'Requirements not yet complete'),
        ('critical_item_count', 'Critical Item Count', 'conditional_count', 'items', 0, 'Requirements marked critical')
    """)
    con.execute("""
        CREATE TABLE metrics_validation_summary (
            status VARCHAR, error_count BIGINT, warning_count BIGINT
        )
    """)
    con.execute("INSERT INTO metrics_validation_summary VALUES ('passed_with_warnings', 0, 3)")
    con.close()
    return str(db)


def _make_client_context_csv(path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["project_id", "client_name", "assessment_date"])
        writer.writeheader()
        writer.writerow({"project_id": "PRJ001", "client_name": "Acme Corp", "assessment_date": "2025-01-15"})
    return path


# ── Shared fixture ───────────────────────────────────────────────────────────────

@pytest.fixture(scope="module")
def powerbi_out(tmp_path_factory) -> Path:
    """Run export_powerbi once against a full store; return the output directory."""
    tmp = tmp_path_factory.mktemp("contract")
    store = _build_store(tmp, with_market=True)
    out = tmp / "powerbi"
    con = duckdb.connect(store, read_only=True)
    try:
        export_powerbi(con, out)
    finally:
        con.close()
    return out


# ── Required files present when --with-powerbi-export is used ──────────────────

@pytest.mark.parametrize("fname", [
    "readiness_kpis.csv",
    "readiness_by_category.csv",
    "readiness_by_market.csv",
    "validation_summary.csv",
    "metric_dictionary.csv",
])
def test_required_csv_exists(powerbi_out, fname):
    assert (powerbi_out / fname).exists(), (
        f"Contract violation: {fname} is required but was not found in Power BI export output"
    )


# ── Required columns ────────────────────────────────────────────────────────────

def test_readiness_kpis_required_columns(powerbi_out):
    missing = _KPI_REQUIRED_COLUMNS - _headers(powerbi_out / "readiness_kpis.csv")
    assert not missing, f"readiness_kpis.csv missing required columns: {missing}"


def test_by_category_required_columns(powerbi_out):
    missing = _CATEGORY_REQUIRED_COLUMNS - _headers(powerbi_out / "readiness_by_category.csv")
    assert not missing, f"readiness_by_category.csv missing required columns: {missing}"


def test_by_market_required_columns(powerbi_out):
    missing = _MARKET_REQUIRED_COLUMNS - _headers(powerbi_out / "readiness_by_market.csv")
    assert not missing, f"readiness_by_market.csv missing required columns: {missing}"


def test_validation_summary_required_columns(powerbi_out):
    missing = _VALIDATION_REQUIRED_COLUMNS - _headers(powerbi_out / "validation_summary.csv")
    assert not missing, f"validation_summary.csv missing required columns: {missing}"


def test_metric_dictionary_required_columns(powerbi_out):
    missing = _DICT_REQUIRED_COLUMNS - _headers(powerbi_out / "metric_dictionary.csv")
    assert not missing, f"metric_dictionary.csv missing required columns: {missing}"


# ── Required files not empty when data is present ──────────────────────────────

def test_readiness_kpis_not_empty(powerbi_out):
    assert _read_csv(powerbi_out / "readiness_kpis.csv"), (
        "readiness_kpis.csv must not be empty when KPI data is present"
    )


def test_by_category_not_empty(powerbi_out):
    assert _read_csv(powerbi_out / "readiness_by_category.csv"), (
        "readiness_by_category.csv must not be empty when category data is present"
    )


def test_by_market_not_empty(powerbi_out):
    assert _read_csv(powerbi_out / "readiness_by_market.csv"), (
        "readiness_by_market.csv must not be empty when market data is present"
    )


def test_validation_summary_not_empty(powerbi_out):
    assert _read_csv(powerbi_out / "validation_summary.csv"), (
        "validation_summary.csv must not be empty when validation data is present"
    )


def test_metric_dictionary_not_empty(powerbi_out):
    assert _read_csv(powerbi_out / "metric_dictionary.csv"), (
        "metric_dictionary.csv must not be empty when metrics are registered"
    )


# ── No duplicate grain keys (Power BI relies on one row per key) ───────────────

def test_by_category_no_duplicate_category_keys(powerbi_out):
    rows = _read_csv(powerbi_out / "readiness_by_category.csv")
    keys = [r["category"] for r in rows]
    dupes = [k for k in set(keys) if keys.count(k) > 1]
    assert not dupes, (
        f"readiness_by_category.csv has duplicate category keys: {dupes}. "
        "Power BI visuals require exactly one row per category."
    )


def test_by_market_no_duplicate_market_keys(powerbi_out):
    rows = _read_csv(powerbi_out / "readiness_by_market.csv")
    keys = [r["market"] for r in rows]
    dupes = [k for k in set(keys) if keys.count(k) > 1]
    assert not dupes, (
        f"readiness_by_market.csv has duplicate market keys: {dupes}. "
        "Power BI visuals require exactly one row per market."
    )


# ── KPI export contains all four required metric IDs ──────────────────────────

def test_kpi_export_contains_readiness_completion_pct(powerbi_out):
    rows = _read_csv(powerbi_out / "readiness_kpis.csv")
    assert any(r["metric_id"] == "readiness_completion_pct" for r in rows)


def test_kpi_export_contains_total_requirement_count(powerbi_out):
    rows = _read_csv(powerbi_out / "readiness_kpis.csv")
    assert any(r["metric_id"] == "total_requirement_count" for r in rows)


def test_kpi_export_contains_open_gap_count(powerbi_out):
    rows = _read_csv(powerbi_out / "readiness_kpis.csv")
    assert any(r["metric_id"] == "open_gap_count" for r in rows)


def test_kpi_export_contains_critical_item_count(powerbi_out):
    rows = _read_csv(powerbi_out / "readiness_kpis.csv")
    assert any(r["metric_id"] == "critical_item_count" for r in rows)


def test_kpi_export_contains_all_four_required_metrics(powerbi_out):
    rows = _read_csv(powerbi_out / "readiness_kpis.csv")
    exported = {r["metric_id"] for r in rows}
    missing = _KPI_REQUIRED_METRICS - exported
    assert not missing, f"readiness_kpis.csv is missing required metric IDs: {missing}"


# ── client_context.csv is copied when --client-context is provided ─────────────

def test_client_context_csv_present_when_provided(tmp_path):
    store = _build_store(tmp_path)
    ctx = _make_client_context_csv(tmp_path / "client_context.csv")
    out = tmp_path / "powerbi_with_ctx"
    con = duckdb.connect(store, read_only=True)
    try:
        export_powerbi(con, out, client_context_path=ctx)
    finally:
        con.close()
    assert (out / "client_context.csv").exists(), (
        "client_context.csv must be present in output when --client-context is provided"
    )


def test_client_context_csv_contents_preserved(tmp_path):
    store = _build_store(tmp_path)
    ctx = _make_client_context_csv(tmp_path / "client_context.csv")
    out = tmp_path / "powerbi_ctx_contents"
    con = duckdb.connect(store, read_only=True)
    try:
        export_powerbi(con, out, client_context_path=ctx)
    finally:
        con.close()
    rows = _read_csv(out / "client_context.csv")
    assert len(rows) == 1
    assert rows[0]["project_id"] == "PRJ001"
    assert rows[0]["client_name"] == "Acme Corp"


def test_client_context_csv_absent_when_not_provided(tmp_path):
    store = _build_store(tmp_path)
    out = tmp_path / "powerbi_no_ctx"
    con = duckdb.connect(store, read_only=True)
    try:
        export_powerbi(con, out)
    finally:
        con.close()
    assert not (out / "client_context.csv").exists(), (
        "client_context.csv must NOT be present when --client-context is not provided"
    )


# ── Return value contract ───────────────────────────────────────────────────────

def test_export_returns_five_file_paths_without_client_context(tmp_path):
    store = _build_store(tmp_path)
    out = tmp_path / "powerbi_rv5"
    con = duckdb.connect(store, read_only=True)
    try:
        paths = export_powerbi(con, out)
    finally:
        con.close()
    assert len(paths) == 5, f"Expected 5 file paths, got {len(paths)}"
    assert all(p.endswith(".csv") for p in paths)


def test_export_returns_six_file_paths_with_client_context(tmp_path):
    store = _build_store(tmp_path)
    ctx = _make_client_context_csv(tmp_path / "client_context.csv")
    out = tmp_path / "powerbi_rv6"
    con = duckdb.connect(store, read_only=True)
    try:
        paths = export_powerbi(con, out, client_context_path=ctx)
    finally:
        con.close()
    assert len(paths) == 6, f"Expected 6 file paths when client_context provided, got {len(paths)}"
    assert any("client_context.csv" in p for p in paths)
