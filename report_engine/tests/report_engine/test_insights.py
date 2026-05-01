from pathlib import Path

import pandas as pd
import pytest

from report_engine.insights import build_insights, has_period_data, snapshot_rows
from report_engine.loader import ReportData


def _make_data(rows, period_cols=False):
    base = {
        "rollup_level": [r[0] for r in rows],
        "date": [r[1] for r in rows],
        "metric_id": [r[2] for r in rows],
        "label": [r[3] for r in rows],
        "value": [r[4] for r in rows],
        "unit": [r[5] for r in rows],
    }
    if period_cols:
        base["prior_period_value"] = [r[6] for r in rows]
        base["period_change"] = [r[7] for r in rows]
        base["period_change_pct"] = [r[8] for r in rows]
    return ReportData(
        input_dir=Path("outputs/test"),
        validation_status="passed",
        validation_errors=[],
        validation_warnings=[],
        long_metrics=pd.DataFrame(base),
        wide_metrics=pd.DataFrame(),
        metric_dictionary=pd.DataFrame(),
    )


@pytest.fixture
def no_period_data():
    return _make_data([
        ("date_only", "2024-01-01", "total_revenue", "Total Revenue", 5900000.0, "USD"),
        ("date_only", "2024-02-01", "total_revenue", "Total Revenue", 6150000.0, "USD"),
    ])


@pytest.fixture
def period_data():
    return _make_data([
        ("date_only", "2024-01-01", "total_revenue", "Total Revenue", 5900000.0, "USD",
         float("nan"), float("nan"), float("nan")),
        ("date_only", "2024-02-01", "total_revenue", "Total Revenue", 6150000.0, "USD",
         5850000.0, 300000.0, 5.13),
    ], period_cols=True)


@pytest.fixture
def multi_metric_period_data():
    return _make_data([
        ("date_only", "2024-01-01", "total_revenue", "Total Revenue", 5900000.0, "USD",
         float("nan"), float("nan"), float("nan")),
        ("date_only", "2024-02-01", "total_revenue", "Total Revenue", 6150000.0, "USD",
         5850000.0, 300000.0, 5.13),
        ("date_only", "2024-01-01", "utilization_pct", "Utilization Rate", 81.2, "%",
         float("nan"), float("nan"), float("nan")),
        ("date_only", "2024-02-01", "utilization_pct", "Utilization Rate", 84.8, "%",
         81.2, 3.6, 4.43),
    ], period_cols=True)


@pytest.fixture
def empty_data():
    return ReportData(
        input_dir=Path("outputs/test"),
        validation_status="passed",
        validation_errors=[],
        validation_warnings=[],
        long_metrics=pd.DataFrame(),
        wide_metrics=pd.DataFrame(),
        metric_dictionary=pd.DataFrame(),
    )


# ── has_period_data ─────────────────────────────────────────────────────────────

def test_has_period_data_false_when_empty_df(empty_data):
    assert has_period_data(empty_data) is False


def test_has_period_data_false_when_no_column(no_period_data):
    assert has_period_data(no_period_data) is False


def test_has_period_data_true_when_column_present(period_data):
    assert has_period_data(period_data) is True


# ── snapshot_rows ───────────────────────────────────────────────────────────────

def test_snapshot_rows_empty_when_no_metrics(empty_data):
    assert snapshot_rows(empty_data) == []


def test_snapshot_rows_returns_one_row_per_metric(no_period_data):
    rows = snapshot_rows(no_period_data)
    assert len(rows) == 1


def test_snapshot_rows_returns_latest_date_per_metric(no_period_data):
    rows = snapshot_rows(no_period_data)
    assert rows[0]["date"] == "2024-02-01"


def test_snapshot_rows_single_period_returns_that_period():
    data = _make_data([
        ("date_only", "2024-01-01", "total_revenue", "Total Revenue", 5900000.0, "USD"),
    ])
    rows = snapshot_rows(data)
    assert len(rows) == 1
    assert rows[0]["date"] == "2024-01-01"


def test_snapshot_rows_excludes_non_date_only_rollup():
    data = _make_data([
        ("date_only", "2024-02-01", "total_revenue", "Total Revenue", 6150000.0, "USD"),
        ("date_region", "2024-02-01", "total_revenue", "Total Revenue", 3000000.0, "USD"),
    ])
    rows = snapshot_rows(data)
    assert len(rows) == 1
    assert rows[0]["value"] == 6150000.0


def test_snapshot_rows_includes_label_date_value_unit(no_period_data):
    rows = snapshot_rows(no_period_data)
    row = rows[0]
    assert "label" in row
    assert "date" in row
    assert "value" in row
    assert "unit" in row


def test_snapshot_rows_sorted_by_label(multi_metric_period_data):
    rows = snapshot_rows(multi_metric_period_data)
    labels = [r["label"] for r in rows]
    assert labels == sorted(labels)


def test_snapshot_rows_multiple_metrics_one_row_each(multi_metric_period_data):
    rows = snapshot_rows(multi_metric_period_data)
    assert len(rows) == 2


def test_snapshot_rows_no_rollup_level_column():
    data = ReportData(
        input_dir=Path("outputs/test"),
        validation_status="passed",
        validation_errors=[],
        validation_warnings=[],
        long_metrics=pd.DataFrame({
            "date": ["2024-01-01", "2024-02-01"],
            "metric_id": ["total_revenue", "total_revenue"],
            "label": ["Total Revenue", "Total Revenue"],
            "value": [5900000.0, 6150000.0],
            "unit": ["USD", "USD"],
        }),
        wide_metrics=pd.DataFrame(),
        metric_dictionary=pd.DataFrame(),
    )
    rows = snapshot_rows(data)
    assert len(rows) == 1
    assert rows[0]["date"] == "2024-02-01"


# ── build_insights ──────────────────────────────────────────────────────────────

def test_build_insights_empty_when_no_period_column(no_period_data):
    assert build_insights(no_period_data) == []


def test_build_insights_empty_when_no_metrics(empty_data):
    assert build_insights(empty_data) == []


def test_build_insights_skips_nan_rows(period_data):
    # first period row has NaN period_change_pct — only one insight from second period
    insights = build_insights(period_data)
    assert len(insights) == 1


def test_build_insights_positive_pct_direction_up(period_data):
    insights = build_insights(period_data)
    assert insights[0]["direction"] == "up"


def test_build_insights_positive_pct_text_says_increased(period_data):
    insights = build_insights(period_data)
    assert "increased" in insights[0]["text"]


def test_build_insights_negative_pct_direction_down():
    data = _make_data([
        ("date_only", "2024-01-01", "total_revenue", "Total Revenue", 6000000.0, "USD",
         float("nan"), float("nan"), float("nan")),
        ("date_only", "2024-02-01", "total_revenue", "Total Revenue", 5700000.0, "USD",
         6000000.0, -300000.0, -5.0),
    ], period_cols=True)
    insights = build_insights(data)
    assert insights[0]["direction"] == "down"


def test_build_insights_negative_pct_text_says_decreased():
    data = _make_data([
        ("date_only", "2024-01-01", "total_revenue", "Total Revenue", 6000000.0, "USD",
         float("nan"), float("nan"), float("nan")),
        ("date_only", "2024-02-01", "total_revenue", "Total Revenue", 5700000.0, "USD",
         6000000.0, -300000.0, -5.0),
    ], period_cols=True)
    insights = build_insights(data)
    assert "decreased" in insights[0]["text"]


def test_build_insights_zero_pct_direction_flat():
    data = _make_data([
        ("date_only", "2024-01-01", "total_revenue", "Total Revenue", 6000000.0, "USD",
         float("nan"), float("nan"), float("nan")),
        ("date_only", "2024-02-01", "total_revenue", "Total Revenue", 6000000.0, "USD",
         6000000.0, 0.0, 0.0),
    ], period_cols=True)
    insights = build_insights(data)
    assert insights[0]["direction"] == "flat"


def test_build_insights_zero_pct_text_says_remained_flat():
    data = _make_data([
        ("date_only", "2024-01-01", "total_revenue", "Total Revenue", 6000000.0, "USD",
         float("nan"), float("nan"), float("nan")),
        ("date_only", "2024-02-01", "total_revenue", "Total Revenue", 6000000.0, "USD",
         6000000.0, 0.0, 0.0),
    ], period_cols=True)
    insights = build_insights(data)
    assert "remained flat" in insights[0]["text"]


def test_build_insights_text_uses_label_not_metric_id(period_data):
    insights = build_insights(period_data)
    assert "Total Revenue" in insights[0]["text"]
    assert "total_revenue" not in insights[0]["text"]


def test_build_insights_text_includes_formatted_pct(period_data):
    insights = build_insights(period_data)
    # format_metric_value(5.13, "%") → "5.13%"
    assert "5.13%" in insights[0]["text"]


def test_build_insights_text_includes_vs_prior_period(period_data):
    insights = build_insights(period_data)
    assert "vs prior period" in insights[0]["text"]


def test_build_insights_schema_has_required_keys(period_data):
    insights = build_insights(period_data)
    required = {"metric_id", "label", "date", "period_change_pct", "direction", "text"}
    assert required.issubset(set(insights[0].keys()))


def test_build_insights_multiple_metrics_sorted_by_metric_id(multi_metric_period_data):
    insights = build_insights(multi_metric_period_data)
    ids = [i["metric_id"] for i in insights]
    assert ids == sorted(ids)


def test_build_insights_multiple_metrics_count(multi_metric_period_data):
    insights = build_insights(multi_metric_period_data)
    assert len(insights) == 2


def test_build_insights_uses_latest_period_per_metric(multi_metric_period_data):
    insights = build_insights(multi_metric_period_data)
    for insight in insights:
        assert insight["date"] == "2024-02-01"
