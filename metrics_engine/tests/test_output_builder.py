import pandas as pd
import pytest

from metrics_engine.output_builder import (
    build_long_metrics,
    build_metric_dictionary,
    build_wide_metrics,
)


@pytest.fixture
def registry():
    return {
        "metrics": {
            "total_revenue": {
                "id": "total_revenue", "label": "Total Revenue",
                "type": "sum", "unit": "USD", "decimals": 0,
                "description": "Sum of revenue",
            },
            "utilization_pct": {
                "id": "utilization_pct", "label": "Utilization Rate",
                "type": "ratio", "unit": "%", "decimals": 1,
                "description": "leased/capacity*100",
            },
        },
        "segment_rollups": [[], ["region"]],
    }


@pytest.fixture
def long_df():
    """Simulates calculator output with two rollups and two metrics."""
    return pd.DataFrame({
        "rollup_level": [
            "date_only", "date_only",
            "date_region", "date_region",
            "date_region", "date_region",
        ],
        "date": pd.to_datetime(["2024-01-01"] * 6),
        "region": [None, None, "east", "east", "west", "west"],
        "metric_id": [
            "total_revenue", "utilization_pct",
            "total_revenue", "utilization_pct",
            "total_revenue", "utilization_pct",
        ],
        "label": ["Total Revenue", "Utilization Rate"] * 3,
        "value": [1500.0, 80.0, 1000.0, 80.0, 500.0, 80.0],
        "unit": ["USD", "%"] * 3,
    })


@pytest.fixture
def empty_long():
    return pd.DataFrame(
        columns=["rollup_level", "date", "metric_id", "label", "value", "unit"]
    )


# ── build_long_metrics ────────────────────────────────────────────────────────

def test_long_metrics_returns_dataframe(long_df, registry):
    assert isinstance(build_long_metrics(long_df, registry), pd.DataFrame)


def test_long_metrics_column_order(long_df, registry):
    result = build_long_metrics(long_df, registry)
    cols = list(result.columns)
    assert cols[0] == "rollup_level"
    assert cols[1] == "date"
    assert cols[-4:] == ["metric_id", "label", "value", "unit"]


def test_long_metrics_segment_col_between_date_and_metric_id(long_df, registry):
    result = build_long_metrics(long_df, registry)
    cols = list(result.columns)
    date_idx = cols.index("date")
    metric_idx = cols.index("metric_id")
    assert "region" in cols[date_idx + 1 : metric_idx]


def test_long_metrics_preserves_rollup_level_values(long_df, registry):
    result = build_long_metrics(long_df, registry)
    assert set(result["rollup_level"].unique()) == {"date_only", "date_region"}


def test_long_metrics_preserves_row_count(long_df, registry):
    result = build_long_metrics(long_df, registry)
    assert len(result) == len(long_df)


def test_long_metrics_empty_returns_empty(empty_long, registry):
    result = build_long_metrics(empty_long, registry)
    assert isinstance(result, pd.DataFrame)
    assert result.empty


# ── build_wide_metrics ────────────────────────────────────────────────────────

def test_wide_metrics_returns_dataframe(long_df, registry):
    long = build_long_metrics(long_df, registry)
    assert isinstance(build_wide_metrics(long), pd.DataFrame)


def test_wide_metrics_one_row_per_rollup_date_segment_combo(long_df, registry):
    long = build_long_metrics(long_df, registry)
    wide = build_wide_metrics(long)
    # 3 unique combos: (date_only, 2024-01-01, NaN), (date_region, east), (date_region, west)
    assert len(wide) == 3


def test_wide_metrics_has_one_column_per_metric(long_df, registry):
    long = build_long_metrics(long_df, registry)
    wide = build_wide_metrics(long)
    for metric_id in registry["metrics"]:
        assert metric_id in wide.columns


def test_wide_metrics_no_label_or_value_column(long_df, registry):
    long = build_long_metrics(long_df, registry)
    wide = build_wide_metrics(long)
    assert "label" not in wide.columns
    assert "value" not in wide.columns


def test_wide_metrics_preserves_rollup_level_column(long_df, registry):
    long = build_long_metrics(long_df, registry)
    wide = build_wide_metrics(long)
    assert "rollup_level" in wide.columns


def test_wide_metrics_date_only_row_has_correct_total(long_df, registry):
    long = build_long_metrics(long_df, registry)
    wide = build_wide_metrics(long)
    date_only_row = wide[wide["rollup_level"] == "date_only"]
    assert len(date_only_row) == 1
    assert date_only_row.iloc[0]["total_revenue"] == pytest.approx(1500.0)


def test_wide_metrics_segment_rows_have_values(long_df, registry):
    long = build_long_metrics(long_df, registry)
    wide = build_wide_metrics(long)
    east_row = wide[(wide["rollup_level"] == "date_region") & (wide["region"] == "east")]
    assert len(east_row) == 1
    assert east_row.iloc[0]["total_revenue"] == pytest.approx(1000.0)


def test_wide_metrics_empty_long_returns_empty(empty_long, registry):
    result = build_wide_metrics(empty_long)
    assert isinstance(result, pd.DataFrame)
    assert result.empty


# ── build_metric_dictionary ───────────────────────────────────────────────────

def test_metric_dictionary_returns_dataframe(registry):
    assert isinstance(build_metric_dictionary(registry), pd.DataFrame)


def test_metric_dictionary_one_row_per_metric(registry):
    md = build_metric_dictionary(registry)
    assert len(md) == len(registry["metrics"])


def test_metric_dictionary_has_required_columns(registry):
    md = build_metric_dictionary(registry)
    for col in ["id", "label", "type", "unit", "decimals", "description"]:
        assert col in md.columns


def test_metric_dictionary_column_order(registry):
    md = build_metric_dictionary(registry)
    assert list(md.columns) == ["id", "label", "type", "unit", "decimals", "description"]


def test_metric_dictionary_id_values_match_registry(registry):
    md = build_metric_dictionary(registry)
    assert set(md["id"]) == set(registry["metrics"].keys())


def test_metric_dictionary_label_values_match_registry(registry):
    md = build_metric_dictionary(registry)
    expected_labels = {m["label"] for m in registry["metrics"].values()}
    assert set(md["label"]) == expected_labels


def test_metric_dictionary_decimals_are_numeric(registry):
    md = build_metric_dictionary(registry)
    assert pd.api.types.is_numeric_dtype(md["decimals"])


def test_metric_dictionary_populated_even_with_empty_long(registry):
    md = build_metric_dictionary(registry)
    assert not md.empty
    assert len(md) == len(registry["metrics"])
