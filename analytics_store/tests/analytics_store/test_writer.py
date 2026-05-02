from __future__ import annotations

from pathlib import Path

import duckdb
import pandas as pd
import pytest

from analytics_store.loader import MetricsData, ReportData
from analytics_store.writer import build_store


# --- Sample data helpers ---

def _long_metrics_df() -> pd.DataFrame:
    return pd.DataFrame({
        "rollup_level": ["date_only", "date_only", "date_only", "date_region"],
        "date": ["2024-01-01", "2024-02-01", "2024-03-01", "2024-01-01"],
        "provider": ["", "", "", ""],
        "region": ["", "", "", "EMEA"],
        "metric_id": ["total_revenue"] * 4,
        "label": ["Total Revenue"] * 4,
        "value": [1000.0, 1100.0, 1210.0, 500.0],
        "unit": ["USD"] * 4,
        "prior_period_value": [None, 1000.0, 1100.0, None],
        "period_change": [None, 100.0, 110.0, None],
        "period_change_pct": [None, 10.0, 10.0, None],
    })


def _wide_metrics_df() -> pd.DataFrame:
    return pd.DataFrame({
        "rollup_level": ["date_only"],
        "date": ["2024-03-01"],
        "total_revenue": [1210.0],
    })


def _metric_dict_df() -> pd.DataFrame:
    return pd.DataFrame({
        "id": ["total_revenue"],
        "label": ["Total Revenue"],
        "type": ["sum"],
        "unit": ["USD"],
        "decimals": [0],
        "description": ["Sum of all revenue"],
    })


def _sample_metrics(tmp_path: Path) -> MetricsData:
    return MetricsData(
        metrics_dir=tmp_path,
        validation_status="passed",
        validation_errors=[],
        validation_warnings=["minor warning"],
        long_metrics=_long_metrics_df(),
        wide_metrics=_wide_metrics_df(),
        metric_dictionary=_metric_dict_df(),
    )


def _empty_report() -> ReportData:
    return ReportData(report_dir=None, insights=[], summary={})


def _sample_report(tmp_path: Path) -> ReportData:
    insights = [
        {"metric_id": "total_revenue", "label": "Total Revenue", "date": "2024-03-01",
         "period_change_pct": 10.0, "direction": "up", "text": "Revenue up 10%"}
    ]
    summary = {
        "validation_status": "passed",
        "error_count": 0,
        "warning_count": 1,
        "template": "full_report",
        "metric_count": 1,
        "date_range": {"min": "2024-01-01", "max": "2024-03-01"},
    }
    return ReportData(report_dir=tmp_path, insights=insights, summary=summary)


# --- Query helpers ---

def _open(db_path: Path):
    return duckdb.connect(str(db_path), read_only=True)


def _query(db_path: Path, sql: str) -> list:
    con = _open(db_path)
    try:
        return con.execute(sql).fetchall()
    finally:
        con.close()


def _tables(db_path: Path) -> set[str]:
    rows = _query(
        db_path,
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'main' AND table_type = 'BASE TABLE'",
    )
    return {r[0] for r in rows}


def _views(db_path: Path) -> set[str]:
    rows = _query(
        db_path,
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'main' AND table_type = 'VIEW'",
    )
    return {r[0] for r in rows}


# --- build_store: file creation ---

def test_build_store_creates_db_file(tmp_path):
    db_path = tmp_path / "store.duckdb"
    build_store(_sample_metrics(tmp_path), _empty_report(), db_path)
    assert db_path.exists()


def test_build_store_creates_parent_dirs(tmp_path):
    db_path = tmp_path / "deep" / "nested" / "store.duckdb"
    build_store(_sample_metrics(tmp_path), _empty_report(), db_path)
    assert db_path.exists()


def test_build_store_accepts_string_path(tmp_path):
    db_path = str(tmp_path / "store.duckdb")
    build_store(_sample_metrics(tmp_path), _empty_report(), db_path)
    assert Path(db_path).exists()


# --- build_store: return value ---

def test_build_store_returns_list(tmp_path):
    db_path = tmp_path / "store.duckdb"
    result = build_store(_sample_metrics(tmp_path), _empty_report(), db_path)
    assert isinstance(result, list)


def test_build_store_return_includes_all_tables(tmp_path):
    db_path = tmp_path / "store.duckdb"
    result = build_store(_sample_metrics(tmp_path), _empty_report(), db_path)
    expected = {"long_metrics", "wide_metrics", "metric_dictionary",
                "metrics_validation_summary", "report_insights", "report_summary"}
    assert expected.issubset(set(result))


def test_build_store_return_includes_all_views(tmp_path):
    db_path = tmp_path / "store.duckdb"
    result = build_store(_sample_metrics(tmp_path), _empty_report(), db_path)
    expected = {"v_latest_kpis", "v_metric_trends", "v_report_insights"}
    assert expected.issubset(set(result))


# --- Tables: existence ---

def test_long_metrics_table_exists(tmp_path):
    db_path = tmp_path / "store.duckdb"
    build_store(_sample_metrics(tmp_path), _empty_report(), db_path)
    assert "long_metrics" in _tables(db_path)


def test_wide_metrics_table_exists(tmp_path):
    db_path = tmp_path / "store.duckdb"
    build_store(_sample_metrics(tmp_path), _empty_report(), db_path)
    assert "wide_metrics" in _tables(db_path)


def test_metric_dictionary_table_exists(tmp_path):
    db_path = tmp_path / "store.duckdb"
    build_store(_sample_metrics(tmp_path), _empty_report(), db_path)
    assert "metric_dictionary" in _tables(db_path)


def test_metrics_validation_summary_table_exists(tmp_path):
    db_path = tmp_path / "store.duckdb"
    build_store(_sample_metrics(tmp_path), _empty_report(), db_path)
    assert "metrics_validation_summary" in _tables(db_path)


def test_report_insights_table_exists(tmp_path):
    db_path = tmp_path / "store.duckdb"
    build_store(_sample_metrics(tmp_path), _empty_report(), db_path)
    assert "report_insights" in _tables(db_path)


def test_report_summary_table_exists(tmp_path):
    db_path = tmp_path / "store.duckdb"
    build_store(_sample_metrics(tmp_path), _empty_report(), db_path)
    assert "report_summary" in _tables(db_path)


# --- Tables: row counts ---

def test_long_metrics_row_count(tmp_path):
    db_path = tmp_path / "store.duckdb"
    build_store(_sample_metrics(tmp_path), _empty_report(), db_path)
    rows = _query(db_path, "SELECT COUNT(*) FROM long_metrics")
    assert rows[0][0] == 4


def test_wide_metrics_has_rows(tmp_path):
    db_path = tmp_path / "store.duckdb"
    build_store(_sample_metrics(tmp_path), _empty_report(), db_path)
    rows = _query(db_path, "SELECT COUNT(*) FROM wide_metrics")
    assert rows[0][0] == 1


def test_metric_dictionary_has_rows(tmp_path):
    db_path = tmp_path / "store.duckdb"
    build_store(_sample_metrics(tmp_path), _empty_report(), db_path)
    rows = _query(db_path, "SELECT COUNT(*) FROM metric_dictionary")
    assert rows[0][0] == 1


def test_metrics_validation_summary_has_one_row(tmp_path):
    db_path = tmp_path / "store.duckdb"
    build_store(_sample_metrics(tmp_path), _empty_report(), db_path)
    rows = _query(db_path, "SELECT COUNT(*) FROM metrics_validation_summary")
    assert rows[0][0] == 1


# --- metrics_validation_summary: content ---

def test_metrics_validation_summary_status(tmp_path):
    db_path = tmp_path / "store.duckdb"
    build_store(_sample_metrics(tmp_path), _empty_report(), db_path)
    rows = _query(db_path, "SELECT status FROM metrics_validation_summary")
    assert rows[0][0] == "passed"


def test_metrics_validation_summary_error_count(tmp_path):
    db_path = tmp_path / "store.duckdb"
    metrics = MetricsData(
        metrics_dir=tmp_path,
        validation_status="failed",
        validation_errors=["err1", "err2"],
        validation_warnings=[],
        long_metrics=_long_metrics_df(),
        wide_metrics=_wide_metrics_df(),
        metric_dictionary=_metric_dict_df(),
    )
    build_store(metrics, _empty_report(), db_path)
    rows = _query(db_path, "SELECT error_count FROM metrics_validation_summary")
    assert rows[0][0] == 2


def test_metrics_validation_summary_warning_count(tmp_path):
    db_path = tmp_path / "store.duckdb"
    build_store(_sample_metrics(tmp_path), _empty_report(), db_path)
    rows = _query(db_path, "SELECT warning_count FROM metrics_validation_summary")
    assert rows[0][0] == 1


# --- report_insights: empty vs populated ---

def test_report_insights_empty_when_no_report(tmp_path):
    db_path = tmp_path / "store.duckdb"
    build_store(_sample_metrics(tmp_path), _empty_report(), db_path)
    rows = _query(db_path, "SELECT COUNT(*) FROM report_insights")
    assert rows[0][0] == 0


def test_report_insights_populated_when_report_provided(tmp_path):
    db_path = tmp_path / "store.duckdb"
    build_store(_sample_metrics(tmp_path), _sample_report(tmp_path), db_path)
    rows = _query(db_path, "SELECT COUNT(*) FROM report_insights")
    assert rows[0][0] == 1


# --- report_summary: empty vs populated ---

def test_report_summary_empty_when_no_report(tmp_path):
    db_path = tmp_path / "store.duckdb"
    build_store(_sample_metrics(tmp_path), _empty_report(), db_path)
    rows = _query(db_path, "SELECT COUNT(*) FROM report_summary")
    assert rows[0][0] == 0


def test_report_summary_has_row_when_provided(tmp_path):
    db_path = tmp_path / "store.duckdb"
    build_store(_sample_metrics(tmp_path), _sample_report(tmp_path), db_path)
    rows = _query(db_path, "SELECT COUNT(*) FROM report_summary")
    assert rows[0][0] == 1


def test_report_summary_date_range_extracted(tmp_path):
    db_path = tmp_path / "store.duckdb"
    build_store(_sample_metrics(tmp_path), _sample_report(tmp_path), db_path)
    rows = _query(db_path, "SELECT date_min, date_max FROM report_summary")
    assert str(rows[0][0]) == "2024-01-01"
    assert str(rows[0][1]) == "2024-03-01"


def test_report_summary_template(tmp_path):
    db_path = tmp_path / "store.duckdb"
    build_store(_sample_metrics(tmp_path), _sample_report(tmp_path), db_path)
    rows = _query(db_path, "SELECT template FROM report_summary")
    assert rows[0][0] == "full_report"


def test_report_summary_metric_count(tmp_path):
    db_path = tmp_path / "store.duckdb"
    build_store(_sample_metrics(tmp_path), _sample_report(tmp_path), db_path)
    rows = _query(db_path, "SELECT metric_count FROM report_summary")
    assert rows[0][0] == 1


# --- Views: existence ---

def test_v_latest_kpis_view_exists(tmp_path):
    db_path = tmp_path / "store.duckdb"
    build_store(_sample_metrics(tmp_path), _empty_report(), db_path)
    assert "v_latest_kpis" in _views(db_path)


def test_v_metric_trends_view_exists(tmp_path):
    db_path = tmp_path / "store.duckdb"
    build_store(_sample_metrics(tmp_path), _empty_report(), db_path)
    assert "v_metric_trends" in _views(db_path)


def test_v_report_insights_view_exists(tmp_path):
    db_path = tmp_path / "store.duckdb"
    build_store(_sample_metrics(tmp_path), _empty_report(), db_path)
    assert "v_report_insights" in _views(db_path)


# --- Views: content ---

def test_v_latest_kpis_returns_only_latest_date(tmp_path):
    db_path = tmp_path / "store.duckdb"
    build_store(_sample_metrics(tmp_path), _empty_report(), db_path)
    rows = _query(db_path, "SELECT DISTINCT CAST(date AS VARCHAR) FROM v_latest_kpis")
    dates = {r[0] for r in rows}
    assert dates == {"2024-03-01"}


def test_v_latest_kpis_excludes_non_date_only_rollup(tmp_path):
    db_path = tmp_path / "store.duckdb"
    build_store(_sample_metrics(tmp_path), _empty_report(), db_path)
    rows = _query(db_path, "SELECT DISTINCT rollup_level FROM v_latest_kpis")
    assert all(r[0] == "date_only" for r in rows)


def test_v_metric_trends_excludes_non_date_only(tmp_path):
    db_path = tmp_path / "store.duckdb"
    build_store(_sample_metrics(tmp_path), _empty_report(), db_path)
    rows = _query(db_path, "SELECT DISTINCT rollup_level FROM v_metric_trends")
    assert all(r[0] == "date_only" for r in rows)


def test_v_metric_trends_has_all_date_only_rows(tmp_path):
    db_path = tmp_path / "store.duckdb"
    build_store(_sample_metrics(tmp_path), _empty_report(), db_path)
    rows = _query(db_path, "SELECT COUNT(*) FROM v_metric_trends")
    assert rows[0][0] == 3  # 3 date_only rows in _long_metrics_df


def test_v_report_insights_reflects_report_insights_table(tmp_path):
    db_path = tmp_path / "store.duckdb"
    build_store(_sample_metrics(tmp_path), _sample_report(tmp_path), db_path)
    rows = _query(db_path, "SELECT COUNT(*) FROM v_report_insights")
    assert rows[0][0] == 1


# --- Edge cases ---

def test_build_store_with_fully_empty_dataframes(tmp_path):
    db_path = tmp_path / "store.duckdb"
    empty_metrics = MetricsData(
        metrics_dir=tmp_path,
        validation_status="passed",
        validation_errors=[],
        validation_warnings=[],
        long_metrics=pd.DataFrame(),
        wide_metrics=pd.DataFrame(),
        metric_dictionary=pd.DataFrame(),
    )
    result = build_store(empty_metrics, _empty_report(), db_path)
    assert isinstance(result, list)
    assert db_path.exists()


def test_build_store_idempotent(tmp_path):
    db_path = tmp_path / "store.duckdb"
    build_store(_sample_metrics(tmp_path), _empty_report(), db_path)
    build_store(_sample_metrics(tmp_path), _empty_report(), db_path)
    rows = _query(db_path, "SELECT COUNT(*) FROM long_metrics")
    assert rows[0][0] == 4
