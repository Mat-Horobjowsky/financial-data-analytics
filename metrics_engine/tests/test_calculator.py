import pandas as pd
import pytest

from metrics_engine.calculator import CalculatorError, calculate


@pytest.fixture
def base_df():
    return pd.DataFrame({
        "date": pd.to_datetime([
            "2024-01-01", "2024-01-01",
            "2024-02-01", "2024-02-01",
        ]),
        "region": ["east", "west", "east", "west"],
        "revenue": [1000.0, 500.0, 1200.0, 600.0],
        "capacity_mw": [10.0, 5.0, 10.0, 5.0],
        "leased_mw": [8.0, 4.0, 9.0, 4.5],
        "contracted_kw": [5000.0, 2500.0, 6000.0, 3000.0],
    })


def _sum_m(id, source_col, label=None, unit="u"):
    return {
        "id": id, "label": label or id, "type": "sum",
        "unit": unit, "decimals": 0, "description": id,
        "source_col": source_col,
    }


def _ratio_m(id, num, den, scale, label=None):
    return {
        "id": id, "label": label or id, "type": "ratio",
        "unit": "%", "decimals": 1, "description": id,
        "numerator": num, "denominator": den, "scale": scale,
    }


def _per_unit_m(id, num, den, label=None, unit="u"):
    return {
        "id": id, "label": label or id, "type": "per_unit",
        "unit": unit, "decimals": 2, "description": id,
        "numerator": num, "denominator": den,
    }


@pytest.fixture
def registry():
    return {
        "metrics": {
            "total_revenue": _sum_m("total_revenue", "revenue", "Total Revenue", "USD"),
            "utilization_pct": _ratio_m("utilization_pct", "leased_mw", "capacity_mw", 100, "Utilization %"),
            "avg_price_per_kw": _per_unit_m("avg_price_per_kw", "revenue", "contracted_kw", "Avg Price/KW", "USD/KW"),
        },
        "segment_rollups": [[], ["region"]],
    }


def _get(result, rollup_level, date, metric_id, **seg):
    mask = (
        (result["rollup_level"] == rollup_level) &
        (result["date"] == pd.Timestamp(date)) &
        (result["metric_id"] == metric_id)
    )
    for col, val in seg.items():
        mask &= result[col] == val
    rows = result[mask]
    assert len(rows) == 1, f"Expected 1 row, got {len(rows)} for {rollup_level}/{date}/{metric_id}/{seg}"
    return rows.iloc[0]["value"]


# ── return type ───────────────────────────────────────────────────────────────

def test_returns_dataframe(base_df, registry):
    assert isinstance(calculate(base_df, registry), pd.DataFrame)


# ── required columns ──────────────────────────────────────────────────────────

def test_output_has_rollup_level_column(base_df, registry):
    assert "rollup_level" in calculate(base_df, registry).columns


def test_output_has_date_column(base_df, registry):
    assert "date" in calculate(base_df, registry).columns


def test_output_has_metric_id_column(base_df, registry):
    assert "metric_id" in calculate(base_df, registry).columns


def test_output_has_label_column(base_df, registry):
    assert "label" in calculate(base_df, registry).columns


def test_output_has_value_column(base_df, registry):
    assert "value" in calculate(base_df, registry).columns


def test_output_has_unit_column(base_df, registry):
    assert "unit" in calculate(base_df, registry).columns


# ── column ordering ───────────────────────────────────────────────────────────

def test_rollup_level_is_first_column(base_df, registry):
    assert calculate(base_df, registry).columns[0] == "rollup_level"


def test_date_is_second_column(base_df, registry):
    assert calculate(base_df, registry).columns[1] == "date"


def test_trailing_four_columns_are_metric_cols(base_df, registry):
    assert list(calculate(base_df, registry).columns[-4:]) == ["metric_id", "label", "value", "unit"]


# ── long-format row counts ────────────────────────────────────────────────────

def test_date_only_has_one_row_per_date_per_metric(base_df, registry):
    result = calculate(base_df, registry)
    n_dates = base_df["date"].nunique()
    n_metrics = len(registry["metrics"])
    assert len(result[result["rollup_level"] == "date_only"]) == n_dates * n_metrics


def test_date_region_has_one_row_per_combo_per_metric(base_df, registry):
    result = calculate(base_df, registry)
    n_combos = base_df.groupby(["date", "region"]).ngroups
    n_metrics = len(registry["metrics"])
    assert len(result[result["rollup_level"] == "date_region"]) == n_combos * n_metrics


def test_total_row_count(base_df, registry):
    result = calculate(base_df, registry)
    n_metrics = len(registry["metrics"])
    n_date_only = base_df["date"].nunique()
    n_date_region = base_df.groupby(["date", "region"]).ngroups
    assert len(result) == (n_date_only + n_date_region) * n_metrics


# ── rollup_level values ───────────────────────────────────────────────────────

def test_rollup_level_date_only_present(base_df, registry):
    assert "date_only" in calculate(base_df, registry)["rollup_level"].values


def test_rollup_level_date_region_present(base_df, registry):
    assert "date_region" in calculate(base_df, registry)["rollup_level"].values


def test_only_configured_rollup_levels_present(base_df, registry):
    assert set(calculate(base_df, registry)["rollup_level"].unique()) == {"date_only", "date_region"}


def test_multi_segment_rollup_level_label(base_df):
    df = base_df.copy()
    df["provider"] = ["aws", "azure", "aws", "azure"]
    reg = {
        "metrics": {"rev": _sum_m("rev", "revenue")},
        "segment_rollups": [["region", "provider"]],
    }
    result = calculate(df, reg)
    assert "date_region_provider" in result["rollup_level"].values


# ── sum metric ────────────────────────────────────────────────────────────────

def test_sum_date_only(base_df, registry):
    result = calculate(base_df, registry)
    # east=1000 + west=500 = 1500
    assert _get(result, "date_only", "2024-01-01", "total_revenue") == pytest.approx(1500.0)


def test_sum_date_region(base_df, registry):
    result = calculate(base_df, registry)
    assert _get(result, "date_region", "2024-01-01", "total_revenue", region="east") == pytest.approx(1000.0)
    assert _get(result, "date_region", "2024-01-01", "total_revenue", region="west") == pytest.approx(500.0)


def test_sum_second_date(base_df, registry):
    result = calculate(base_df, registry)
    # east=1200 + west=600 = 1800
    assert _get(result, "date_only", "2024-02-01", "total_revenue") == pytest.approx(1800.0)


# ── ratio metric ──────────────────────────────────────────────────────────────

def test_ratio_date_only(base_df, registry):
    result = calculate(base_df, registry)
    # leased=12 / capacity=15 * 100 = 80.0
    assert _get(result, "date_only", "2024-01-01", "utilization_pct") == pytest.approx(80.0)


def test_ratio_date_region(base_df, registry):
    result = calculate(base_df, registry)
    # east: 8/10*100 = 80; west: 4/5*100 = 80
    assert _get(result, "date_region", "2024-01-01", "utilization_pct", region="east") == pytest.approx(80.0)
    assert _get(result, "date_region", "2024-01-01", "utilization_pct", region="west") == pytest.approx(80.0)


def test_ratio_sums_components_before_dividing(base_df, registry):
    df = base_df.copy()
    # west: leased=2.5, capacity=5 → 50%; date_only: (8+2.5)/(10+5)*100 = 70%
    df.loc[df["region"] == "west", "leased_mw"] = 2.5
    result = calculate(df, registry)
    assert _get(result, "date_only", "2024-01-01", "utilization_pct") == pytest.approx(70.0)
    assert _get(result, "date_region", "2024-01-01", "utilization_pct", region="west") == pytest.approx(50.0)


# ── per_unit metric ───────────────────────────────────────────────────────────

def test_per_unit_date_only(base_df, registry):
    result = calculate(base_df, registry)
    # revenue=1500 / contracted_kw=7500 = 0.2
    assert _get(result, "date_only", "2024-01-01", "avg_price_per_kw") == pytest.approx(0.2)


def test_per_unit_date_region(base_df, registry):
    result = calculate(base_df, registry)
    # east: 1000/5000 = 0.2; west: 500/2500 = 0.2
    assert _get(result, "date_region", "2024-01-01", "avg_price_per_kw", region="east") == pytest.approx(0.2)


def test_per_unit_sums_components_before_dividing(base_df, registry):
    df = base_df.copy()
    # west: contracted_kw=5000 → date_only: 1500/(5000+5000) = 0.15
    df.loc[df["region"] == "west", "contracted_kw"] = 5000.0
    result = calculate(df, registry)
    assert _get(result, "date_only", "2024-01-01", "avg_price_per_kw") == pytest.approx(0.15)


# ── metric_id == source_col (no aliasing confusion) ──────────────────────────

def test_metric_where_id_equals_source_col(base_df):
    reg = {
        "metrics": {"capacity_mw": _sum_m("capacity_mw", "capacity_mw", "Capacity", "MW")},
        "segment_rollups": [[]],
    }
    result = calculate(base_df, reg)
    # east=10 + west=5 = 15
    assert _get(result, "date_only", "2024-01-01", "capacity_mw") == pytest.approx(15.0)


# ── segment column in output ──────────────────────────────────────────────────

def test_segment_column_present_after_concat(base_df, registry):
    assert "region" in calculate(base_df, registry).columns


def test_date_only_rows_have_null_region(base_df, registry):
    result = calculate(base_df, registry)
    assert result[result["rollup_level"] == "date_only"]["region"].isna().all()


def test_date_region_rows_have_non_null_region(base_df, registry):
    result = calculate(base_df, registry)
    assert result[result["rollup_level"] == "date_region"]["region"].notna().all()


# ── label and unit passthrough ────────────────────────────────────────────────

def test_label_matches_registry_definition(base_df, registry):
    result = calculate(base_df, registry)
    assert (result[result["metric_id"] == "total_revenue"]["label"] == "Total Revenue").all()


def test_unit_matches_registry_definition(base_df, registry):
    result = calculate(base_df, registry)
    assert (result[result["metric_id"] == "total_revenue"]["unit"] == "USD").all()


# ── missing segment rollup skipping ──────────────────────────────────────────

def test_missing_segment_rollup_is_skipped(base_df, registry):
    reg = {**registry, "segment_rollups": [[], ["provider"]]}
    result = calculate(base_df, reg)
    assert "date_provider" not in result["rollup_level"].values
    assert "date_only" in result["rollup_level"].values


def test_partial_missing_multi_segment_rollup_skipped(base_df, registry):
    reg = {**registry, "segment_rollups": [["region", "provider"]]}
    result = calculate(base_df, reg)
    assert result.empty or "date_region_provider" not in result["rollup_level"].values


def test_all_rollups_missing_returns_empty_dataframe(base_df, registry):
    reg = {**registry, "segment_rollups": [["provider"]]}
    result = calculate(base_df, reg)
    assert isinstance(result, pd.DataFrame)
    assert result.empty


# ── defensive error ───────────────────────────────────────────────────────────

def test_raises_calculator_error_on_missing_metric_input_col(base_df, registry):
    df = base_df.drop(columns=["revenue"])
    with pytest.raises(CalculatorError):
        calculate(df, registry)
