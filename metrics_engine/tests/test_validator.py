import pandas as pd
import pytest

from metrics_engine.schema import NormalizeResult
from metrics_engine.validator import ValidationReport, validate


def _make_result(df, dropped_columns=None, missing_segments=None):
    return NormalizeResult(
        df=df,
        dropped_columns=dropped_columns or [],
        missing_segments=missing_segments or [],
    )


def _base_df():
    return pd.DataFrame({
        "date": pd.to_datetime(["2024-01-01", "2024-02-01"]),
        "revenue": [1000.0, 2000.0],
        "capacity_mw": [10.0, 10.0],
        "leased_mw": [8.0, 9.0],
        "contracted_kw": [5000.0, 6000.0],
    })


def _sum_metric(id, source_col):
    return {
        "id": id, "label": id, "type": "sum",
        "unit": "u", "decimals": 0, "description": id,
        "source_col": source_col,
    }


def _ratio_metric(id, numerator, denominator, scale=100):
    return {
        "id": id, "label": id, "type": "ratio",
        "unit": "%", "decimals": 1, "description": id,
        "numerator": numerator, "denominator": denominator, "scale": scale,
    }


def _per_unit_metric(id, numerator, denominator):
    return {
        "id": id, "label": id, "type": "per_unit",
        "unit": "u", "decimals": 2, "description": id,
        "numerator": numerator, "denominator": denominator,
    }


def _full_registry():
    return {
        "metrics": {
            "total_revenue":   _sum_metric("total_revenue", "revenue"),
            "capacity_mw":     _sum_metric("capacity_mw", "capacity_mw"),
            "leased_mw":       _sum_metric("leased_mw", "leased_mw"),
            "contracted_kw":   _sum_metric("contracted_kw", "contracted_kw"),
            "utilization_pct": _ratio_metric("utilization_pct", "leased_mw", "capacity_mw"),
            "avg_price_per_kw": _per_unit_metric("avg_price_per_kw", "revenue", "contracted_kw"),
        },
        "segment_rollups": [[], ["region"], ["region", "provider"]],
    }


# ── return type ───────────────────────────────────────────────────────────────

def test_returns_validation_report():
    report = validate(_make_result(_base_df()), _full_registry())
    assert isinstance(report, ValidationReport)
    assert hasattr(report, "status")
    assert hasattr(report, "errors")
    assert hasattr(report, "warnings")


# ── happy path ────────────────────────────────────────────────────────────────

def test_clean_data_returns_passed_status():
    report = validate(_make_result(_base_df()), _full_registry())
    assert report.status == "passed"


def test_clean_data_has_no_errors():
    report = validate(_make_result(_base_df()), _full_registry())
    assert report.errors == []


# ── status logic ──────────────────────────────────────────────────────────────

def test_status_is_failed_when_errors_present():
    df = _base_df().drop(columns=["revenue"])
    report = validate(_make_result(df), _full_registry())
    assert report.status == "failed"


def test_status_is_passed_with_warnings_when_only_warnings():
    df = pd.concat([_base_df(), _base_df()], ignore_index=True)
    report = validate(_make_result(df), _full_registry())
    assert report.status == "passed_with_warnings"
    assert len(report.warnings) > 0


# ── hard errors: missing metric input columns ─────────────────────────────────

def test_missing_sum_source_col_is_error():
    df = _base_df().drop(columns=["revenue"])
    report = validate(_make_result(df), _full_registry())
    assert any("revenue" in e for e in report.errors)


def test_missing_ratio_numerator_col_is_error():
    df = _base_df().drop(columns=["leased_mw"])
    report = validate(_make_result(df), _full_registry())
    assert any("leased_mw" in e for e in report.errors)


def test_missing_ratio_denominator_col_is_error():
    df = _base_df().drop(columns=["capacity_mw"])
    report = validate(_make_result(df), _full_registry())
    assert any("capacity_mw" in e for e in report.errors)


def test_missing_per_unit_denominator_col_is_error():
    df = _base_df().drop(columns=["contracted_kw"])
    report = validate(_make_result(df), _full_registry())
    assert any("contracted_kw" in e for e in report.errors)


def test_all_missing_columns_reported_not_just_first():
    df = _base_df().drop(columns=["revenue", "capacity_mw"])
    report = validate(_make_result(df), _full_registry())
    assert any("revenue" in e for e in report.errors)
    assert any("capacity_mw" in e for e in report.errors)


# ── hard errors: nulls in metric inputs ──────────────────────────────────────

def test_null_in_source_col_is_error():
    df = _base_df()
    df.loc[0, "revenue"] = None
    report = validate(_make_result(df), _full_registry())
    assert any("revenue" in e for e in report.errors)


def test_null_in_denominator_col_is_error():
    df = _base_df()
    df.loc[0, "capacity_mw"] = None
    report = validate(_make_result(df), _full_registry())
    assert any("capacity_mw" in e for e in report.errors)


def test_null_in_date_col_is_error():
    df = _base_df()
    df["date"] = df["date"].astype(object)
    df.loc[0, "date"] = None
    report = validate(_make_result(df), _full_registry())
    assert any("date" in e for e in report.errors)


# ── hard errors: zero denominators ───────────────────────────────────────────

def test_zero_in_ratio_denominator_is_error():
    df = _base_df()
    df.loc[0, "capacity_mw"] = 0.0
    report = validate(_make_result(df), _full_registry())
    assert any("capacity_mw" in e for e in report.errors)


def test_zero_in_per_unit_denominator_is_error():
    df = _base_df()
    df.loc[0, "contracted_kw"] = 0.0
    report = validate(_make_result(df), _full_registry())
    assert any("contracted_kw" in e for e in report.errors)


# ── warnings: from NormalizeResult ───────────────────────────────────────────

def test_dropped_columns_appear_in_warnings():
    result = _make_result(_base_df(), dropped_columns=["extra_col", "junk"])
    report = validate(result, _full_registry())
    assert any("extra_col" in w for w in report.warnings)


def test_missing_segment_appears_in_warnings():
    result = _make_result(_base_df(), missing_segments=["region"])
    report = validate(result, _full_registry())
    assert any("region" in w for w in report.warnings)


def test_missing_segment_rollup_skip_mentioned_in_warnings():
    result = _make_result(_base_df(), missing_segments=["region"])
    report = validate(result, _full_registry())
    assert any("skip" in w.lower() for w in report.warnings)


# ── warnings: duplicate rows ──────────────────────────────────────────────────

def test_duplicate_full_rows_produce_warning():
    df = pd.concat([_base_df(), _base_df()], ignore_index=True)
    report = validate(_make_result(df), _full_registry())
    assert any("duplicate" in w.lower() for w in report.warnings)


def test_duplicate_check_uses_registry_rollup_not_hardcoded_columns():
    # "zone" is not region/provider; only detected if registry rollup drives the check
    df = _base_df()
    df["zone"] = ["z1", "z1"]
    df_extra = df.copy()
    df_extra["revenue"] = [999.0, 888.0]
    df_combined = pd.concat([df, df_extra], ignore_index=True)
    registry = _full_registry()
    registry["segment_rollups"] = [["zone"]]   # no [] rollup; only zone
    report = validate(_make_result(df_combined), registry)
    assert any("aggregated" in w.lower() for w in report.warnings)


def test_duplicate_date_rows_produce_warning():
    df = _base_df()
    df_extra = df.copy()
    df_extra["revenue"] = [999.0, 888.0]
    df = pd.concat([df, df_extra], ignore_index=True)
    report = validate(_make_result(df), _full_registry())
    assert any("aggregated" in w.lower() for w in report.warnings)


# ── warnings: business rules ──────────────────────────────────────────────────

def test_leased_mw_exceeds_capacity_mw_produces_warning():
    df = _base_df()
    df.loc[0, "leased_mw"] = 15.0
    report = validate(_make_result(df), _full_registry())
    assert any("leased_mw" in w and "capacity_mw" in w for w in report.warnings)


def test_negative_revenue_produces_warning():
    df = _base_df()
    df.loc[0, "revenue"] = -500.0
    report = validate(_make_result(df), _full_registry())
    assert any("revenue" in w for w in report.warnings)


def test_numeric_outlier_produces_warning():
    dates = pd.to_datetime([f"2024-{m:02d}-01" for m in range(1, 10)])
    df = pd.DataFrame({
        "date": dates,
        "revenue": [1000.0, 1100.0, 900.0, 1050.0, 950.0, 1000.0, 1100.0, 900.0, 50_000.0],
        "capacity_mw": [10.0] * 9,
        "leased_mw": [8.0] * 9,
        "contracted_kw": [5000.0] * 9,
    })
    report = validate(_make_result(df), _full_registry())
    assert any("outlier" in w.lower() for w in report.warnings)


# ── warnings: aggregation notice wording ─────────────────────────────────────

def test_aggregation_notice_date_only_rollup():
    df = _base_df()
    df_extra = df.copy()
    df_extra["revenue"] = [999.0, 888.0]
    df_combined = pd.concat([df, df_extra], ignore_index=True)
    report = validate(_make_result(df_combined), _full_registry())
    assert any("date_only" in w and "aggregated" in w for w in report.warnings)


def test_aggregation_notice_date_region_rollup():
    df = _base_df()
    df["region"] = ["East", "West"]
    df_extra = df.copy()
    df_extra["revenue"] = [999.0, 888.0]
    df_combined = pd.concat([df, df_extra], ignore_index=True)
    report = validate(_make_result(df_combined), _full_registry())
    assert any("date_region" in w and "aggregated" in w for w in report.warnings)


def test_aggregation_notice_date_provider_rollup():
    df = _base_df()
    df["provider"] = ["A", "B"]
    df_extra = df.copy()
    df_extra["revenue"] = [999.0, 888.0]
    df_combined = pd.concat([df, df_extra], ignore_index=True)
    registry = _full_registry()
    registry["segment_rollups"] = [["provider"]]
    report = validate(_make_result(df_combined), registry)
    assert any("date_provider" in w and "aggregated" in w for w in report.warnings)


def test_aggregation_notice_is_not_an_error():
    df = _base_df()
    df_extra = df.copy()
    df_extra["revenue"] = [999.0, 888.0]
    df_combined = pd.concat([df, df_extra], ignore_index=True)
    report = validate(_make_result(df_combined), _full_registry())
    assert report.status != "failed"
    assert any("aggregated" in w for w in report.warnings)


def test_aggregation_notice_wording_says_additional_rows():
    df = _base_df()
    df_extra = df.copy()
    df_extra["revenue"] = [999.0, 888.0]
    df_combined = pd.concat([df, df_extra], ignore_index=True)
    report = validate(_make_result(df_combined), _full_registry())
    assert any("additional row(s)" in w for w in report.warnings)
