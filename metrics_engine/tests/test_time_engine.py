"""
Tests for metrics_engine.time_engine.
Covers add_prior_period_metrics and get_group_columns.
CLI flag tests at bottom.
"""
import math
import subprocess
import sys
from pathlib import Path

import pandas as pd
import pytest

from metrics_engine.time_engine import add_prior_period_metrics, get_group_columns

ROOT = Path(__file__).parent.parent
SAMPLE_CSV = ROOT / "data" / "sample_data_centers.csv"


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def two_date_df():
    """Single segment, single metric, two dates."""
    return pd.DataFrame({
        "rollup_level": ["date_region", "date_region"],
        "date": pd.to_datetime(["2024-01-01", "2024-02-01"]),
        "region": ["east", "east"],
        "metric_id": ["revenue", "revenue"],
        "label": ["Revenue", "Revenue"],
        "value": [1000.0, 1200.0],
        "unit": ["USD", "USD"],
    })


@pytest.fixture
def multi_metric_df():
    """Two metrics, two dates, one segment."""
    return pd.DataFrame({
        "rollup_level": ["date_region"] * 4,
        "date": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-01-01", "2024-02-01"]),
        "region": ["east"] * 4,
        "metric_id": ["revenue", "revenue", "utilization", "utilization"],
        "label": ["Revenue", "Revenue", "Utilization", "Utilization"],
        "value": [1000.0, 1200.0, 80.0, 85.0],
        "unit": ["USD", "USD", "%", "%"],
    })


@pytest.fixture
def multi_segment_df():
    """Two segments, one metric, two dates each."""
    return pd.DataFrame({
        "rollup_level": ["date_region"] * 4,
        "date": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-01-01", "2024-02-01"]),
        "region": ["east", "east", "west", "west"],
        "metric_id": ["revenue"] * 4,
        "label": ["Revenue"] * 4,
        "value": [1000.0, 1200.0, 500.0, 600.0],
        "unit": ["USD"] * 4,
    })


@pytest.fixture
def multi_rollup_df():
    """Two rollup levels, same metric and dates."""
    return pd.DataFrame({
        "rollup_level": ["date_only", "date_only", "date_region", "date_region"],
        "date": pd.to_datetime(["2024-01-01", "2024-02-01", "2024-01-01", "2024-02-01"]),
        "region": [None, None, "east", "east"],
        "metric_id": ["revenue"] * 4,
        "label": ["Revenue"] * 4,
        "value": [1500.0, 1800.0, 1000.0, 1200.0],
        "unit": ["USD"] * 4,
    })


@pytest.fixture
def zero_prior_df():
    """Prior period value is zero."""
    return pd.DataFrame({
        "rollup_level": ["date_only", "date_only"],
        "date": pd.to_datetime(["2024-01-01", "2024-02-01"]),
        "metric_id": ["revenue", "revenue"],
        "label": ["Revenue", "Revenue"],
        "value": [0.0, 100.0],
        "unit": ["USD", "USD"],
    })


# ── get_group_columns ─────────────────────────────────────────────────────────

def test_get_group_columns_returns_segment_col():
    df = pd.DataFrame(columns=["rollup_level", "date", "region", "metric_id", "label", "value", "unit"])
    assert get_group_columns(df) == ["region"]


def test_get_group_columns_returns_multiple_segment_cols():
    df = pd.DataFrame(columns=["rollup_level", "date", "region", "provider", "metric_id", "label", "value", "unit"])
    assert set(get_group_columns(df)) == {"region", "provider"}


def test_get_group_columns_returns_empty_when_no_segments():
    df = pd.DataFrame(columns=["rollup_level", "date", "metric_id", "label", "value", "unit"])
    assert get_group_columns(df) == []


# ── output column presence ────────────────────────────────────────────────────

def test_adds_prior_period_value_column(two_date_df):
    result = add_prior_period_metrics(two_date_df)
    assert "prior_period_value" in result.columns


def test_adds_period_change_column(two_date_df):
    result = add_prior_period_metrics(two_date_df)
    assert "period_change" in result.columns


def test_adds_period_change_pct_column(two_date_df):
    result = add_prior_period_metrics(two_date_df)
    assert "period_change_pct" in result.columns


def test_preserves_all_original_columns(two_date_df):
    result = add_prior_period_metrics(two_date_df)
    for col in two_date_df.columns:
        assert col in result.columns


def test_preserves_row_count(two_date_df):
    result = add_prior_period_metrics(two_date_df)
    assert len(result) == len(two_date_df)


# ── first period is null ──────────────────────────────────────────────────────

def test_first_period_has_null_prior_value(two_date_df):
    result = add_prior_period_metrics(two_date_df)
    first = result[result["date"] == pd.Timestamp("2024-01-01")].iloc[0]
    assert pd.isna(first["prior_period_value"])


def test_first_period_has_null_period_change(two_date_df):
    result = add_prior_period_metrics(two_date_df)
    first = result[result["date"] == pd.Timestamp("2024-01-01")].iloc[0]
    assert pd.isna(first["period_change"])


def test_first_period_has_null_period_change_pct(two_date_df):
    result = add_prior_period_metrics(two_date_df)
    first = result[result["date"] == pd.Timestamp("2024-01-01")].iloc[0]
    assert pd.isna(first["period_change_pct"])


# ── second period values ──────────────────────────────────────────────────────

def test_second_period_prior_value_equals_first_value(two_date_df):
    result = add_prior_period_metrics(two_date_df)
    second = result[result["date"] == pd.Timestamp("2024-02-01")].iloc[0]
    assert second["prior_period_value"] == pytest.approx(1000.0)


def test_period_change_is_value_minus_prior(two_date_df):
    result = add_prior_period_metrics(two_date_df)
    second = result[result["date"] == pd.Timestamp("2024-02-01")].iloc[0]
    assert second["period_change"] == pytest.approx(200.0)


def test_period_change_pct_is_correct(two_date_df):
    result = add_prior_period_metrics(two_date_df)
    second = result[result["date"] == pd.Timestamp("2024-02-01")].iloc[0]
    assert second["period_change_pct"] == pytest.approx(20.0)


# ── zero prior value → NaN pct ────────────────────────────────────────────────

def test_zero_prior_value_gives_nan_pct_not_inf(zero_prior_df):
    result = add_prior_period_metrics(zero_prior_df)
    second = result[result["date"] == pd.Timestamp("2024-02-01")].iloc[0]
    pct = second["period_change_pct"]
    assert pd.isna(pct), f"Expected NaN but got {pct}"


def test_zero_prior_value_period_change_is_still_computed(zero_prior_df):
    result = add_prior_period_metrics(zero_prior_df)
    second = result[result["date"] == pd.Timestamp("2024-02-01")].iloc[0]
    assert second["period_change"] == pytest.approx(100.0)


# ── grouping isolation ────────────────────────────────────────────────────────

def test_grouping_does_not_cross_metrics(multi_metric_df):
    result = add_prior_period_metrics(multi_metric_df)
    rev_first = result[
        (result["metric_id"] == "revenue") & (result["date"] == pd.Timestamp("2024-01-01"))
    ].iloc[0]
    util_first = result[
        (result["metric_id"] == "utilization") & (result["date"] == pd.Timestamp("2024-01-01"))
    ].iloc[0]
    assert pd.isna(rev_first["prior_period_value"])
    assert pd.isna(util_first["prior_period_value"])


def test_grouping_does_not_cross_segments(multi_segment_df):
    result = add_prior_period_metrics(multi_segment_df)
    east_first = result[
        (result["region"] == "east") & (result["date"] == pd.Timestamp("2024-01-01"))
    ].iloc[0]
    west_first = result[
        (result["region"] == "west") & (result["date"] == pd.Timestamp("2024-01-01"))
    ].iloc[0]
    assert pd.isna(east_first["prior_period_value"])
    assert pd.isna(west_first["prior_period_value"])


def test_grouping_does_not_cross_rollup_level(multi_rollup_df):
    result = add_prior_period_metrics(multi_rollup_df)
    date_only_first = result[
        (result["rollup_level"] == "date_only") & (result["date"] == pd.Timestamp("2024-01-01"))
    ].iloc[0]
    date_region_first = result[
        (result["rollup_level"] == "date_region") & (result["date"] == pd.Timestamp("2024-01-01"))
    ].iloc[0]
    assert pd.isna(date_only_first["prior_period_value"])
    assert pd.isna(date_region_first["prior_period_value"])


def test_date_only_rollup_with_nan_segment_gets_prior_period():
    """Rows with NaN segment columns must not be dropped from groupby."""
    df = pd.DataFrame({
        "rollup_level": ["date_only", "date_only"],
        "date": pd.to_datetime(["2024-01-01", "2024-02-01"]),
        "region": [None, None],
        "metric_id": ["revenue", "revenue"],
        "label": ["Revenue", "Revenue"],
        "value": [1000.0, 1200.0],
        "unit": ["USD", "USD"],
    })
    result = add_prior_period_metrics(df)
    feb = result[result["date"] == pd.Timestamp("2024-02-01")].iloc[0]
    assert feb["prior_period_value"] == pytest.approx(1000.0)


# ── unsorted input ────────────────────────────────────────────────────────────

def test_unsorted_input_produces_correct_prior_period():
    df = pd.DataFrame({
        "rollup_level": ["date_only", "date_only"],
        "date": pd.to_datetime(["2024-02-01", "2024-01-01"]),  # reversed
        "metric_id": ["revenue", "revenue"],
        "label": ["Revenue", "Revenue"],
        "value": [1200.0, 1000.0],
        "unit": ["USD", "USD"],
    })
    result = add_prior_period_metrics(df)
    feb = result[result["date"] == pd.Timestamp("2024-02-01")].iloc[0]
    assert feb["prior_period_value"] == pytest.approx(1000.0)
    assert feb["period_change"] == pytest.approx(200.0)
    assert feb["period_change_pct"] == pytest.approx(20.0)


# ── input not mutated ─────────────────────────────────────────────────────────

def test_input_dataframe_is_not_mutated(two_date_df):
    original_cols = list(two_date_df.columns)
    original_values = two_date_df["value"].tolist()
    add_prior_period_metrics(two_date_df)
    assert list(two_date_df.columns) == original_cols
    assert two_date_df["value"].tolist() == original_values


# ── empty DataFrame ───────────────────────────────────────────────────────────

def test_empty_dataframe_returns_empty():
    df = pd.DataFrame(columns=["rollup_level", "date", "metric_id", "label", "value", "unit"])
    result = add_prior_period_metrics(df)
    assert result.empty


def test_empty_dataframe_has_new_columns():
    df = pd.DataFrame(columns=["rollup_level", "date", "metric_id", "label", "value", "unit"])
    result = add_prior_period_metrics(df)
    assert "prior_period_value" in result.columns
    assert "period_change" in result.columns
    assert "period_change_pct" in result.columns


# ── CLI --with-time flag ──────────────────────────────────────────────────────

def _cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "metrics_engine.cli"] + list(args),
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )


def test_with_time_adds_new_columns_to_long_metrics(tmp_path):
    out = tmp_path / "out"
    result = _cli("run", "--input", str(SAMPLE_CSV), "--output", str(out), "--with-time")
    assert result.returncode == 0, result.stderr
    df = pd.read_csv(out / "long_metrics.csv")
    assert "prior_period_value" in df.columns
    assert "period_change" in df.columns
    assert "period_change_pct" in df.columns


def test_default_run_does_not_add_time_columns(tmp_path):
    out = tmp_path / "out"
    _cli("run", "--input", str(SAMPLE_CSV), "--output", str(out))
    df = pd.read_csv(out / "long_metrics.csv")
    assert "prior_period_value" not in df.columns
    assert "period_change" not in df.columns
    assert "period_change_pct" not in df.columns
