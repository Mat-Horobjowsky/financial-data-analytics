import pytest
from visuals_engine.loader import (
    connect,
    load_kpi_cards,
    load_breakdown,
    load_metric_dictionary,
    load_validation_summary,
    load_all,
)


def test_connect_valid(sample_store):
    con = connect(sample_store)
    assert con is not None
    con.close()


def test_connect_missing_store():
    with pytest.raises(FileNotFoundError, match="not found"):
        connect("nonexistent.duckdb")


def test_load_kpi_cards_returns_four_metrics(sample_store):
    con = connect(sample_store)
    rows = load_kpi_cards(
        con,
        "date_only",
        ["readiness_completion_pct", "total_requirement_count", "open_gap_count", "critical_item_count"],
    )
    con.close()
    assert len(rows) == 4


def test_load_kpi_cards_completion_value(sample_store):
    con = connect(sample_store)
    rows = load_kpi_cards(con, "date_only", ["readiness_completion_pct"])
    con.close()
    assert len(rows) == 1
    assert rows[0]["value"] == pytest.approx(50.0)
    assert rows[0]["unit"] == "%"


def test_load_kpi_cards_returns_correct_fields(sample_store):
    con = connect(sample_store)
    rows = load_kpi_cards(con, "date_only", ["open_gap_count"])
    con.close()
    assert "metric_id" in rows[0]
    assert "label" in rows[0]
    assert "value" in rows[0]
    assert "unit" in rows[0]


def test_load_category_breakdown(sample_store):
    con = connect(sample_store)
    rows = load_breakdown(con, "date_category", "category", ["readiness_completion_pct", "open_gap_count"])
    con.close()
    assert len(rows) > 0
    assert all("category" in r for r in rows)
    assert all("metric_id" in r for r in rows)


def test_load_breakdown_empty_when_rollup_missing(sample_store):
    """date_market rows do not exist in sample_store — must return [] not crash."""
    con = connect(sample_store)
    rows = load_breakdown(con, "date_market", "market", ["readiness_completion_pct"])
    con.close()
    assert rows == []


def test_load_breakdown_invalid_segment_column(sample_store):
    con = connect(sample_store)
    with pytest.raises(ValueError, match="Unknown segment_column"):
        load_breakdown(con, "date_category", "injected; DROP TABLE", ["readiness_completion_pct"])
    con.close()


def test_load_metric_dictionary(sample_store):
    con = connect(sample_store)
    d = load_metric_dictionary(con)
    con.close()
    assert "readiness_completion_pct" in d
    assert d["readiness_completion_pct"]["unit"] == "%"
    assert "description" in d["readiness_completion_pct"]


def test_load_validation_summary(sample_store):
    con = connect(sample_store)
    summary = load_validation_summary(con)
    con.close()
    assert summary is not None
    assert summary["status"] == "passed_with_warnings"
    assert summary["error_count"] == 0
    assert summary["warning_count"] == 5


def test_load_validation_summary_empty(sample_store_no_breakdowns):
    con = connect(sample_store_no_breakdowns)
    summary = load_validation_summary(con)
    con.close()
    assert summary is None


def test_load_all_populates_kpi_cards(sample_store, sample_spec):
    con = connect(sample_store)
    data = load_all(con, sample_spec)
    con.close()
    assert len(data["kpi_cards"]) == 4


def test_load_all_populates_category_breakdown(sample_store, sample_spec):
    con = connect(sample_store)
    data = load_all(con, sample_spec)
    con.close()
    assert data["category_breakdown"] is not None
    assert len(data["category_breakdown"]) > 0


def test_load_all_skips_missing_market(sample_store, sample_spec):
    con = connect(sample_store)
    data = load_all(con, sample_spec)
    con.close()
    assert data["market_breakdown"] is None
    assert "market_breakdown" in data["sections_skipped"]


def test_load_all_as_of_date(sample_store, sample_spec):
    con = connect(sample_store)
    data = load_all(con, sample_spec)
    con.close()
    assert data["as_of_date"] == "2025-01-15"


def test_load_all_no_breakdowns_skips_both(sample_store_no_breakdowns, sample_spec):
    con = connect(sample_store_no_breakdowns)
    data = load_all(con, sample_spec)
    con.close()
    assert data["category_breakdown"] is None
    assert data["market_breakdown"] is None
    assert "category_breakdown" in data["sections_skipped"]
    assert "market_breakdown" in data["sections_skipped"]
