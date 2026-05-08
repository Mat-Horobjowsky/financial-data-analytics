"""End-to-end test for the readiness metrics pack v0.1."""
from pathlib import Path

import pandas as pd
import pytest

DATA_DIR = Path(__file__).parent.parent / "data"
CONFIG_DIR = Path(__file__).parent.parent / "config"

READINESS_CSV = DATA_DIR / "sample_readiness.csv"
READINESS_METRICS = CONFIG_DIR / "readiness_metrics.yaml"
READINESS_SCHEMA = CONFIG_DIR / "readiness_schema.yaml"


@pytest.fixture
def readiness_result(tmp_path):
    from metrics_engine import calculator as calc_mod
    from metrics_engine import loader, metric_registry as registry_mod
    from metrics_engine import output_builder
    from metrics_engine import schema as schema_mod
    from metrics_engine import validator as validator_mod
    from metrics_engine.exporter import export

    raw_df = loader.load(READINESS_CSV)
    schema_config = schema_mod.load_schema(READINESS_SCHEMA)
    norm_result = schema_mod.normalize(raw_df, schema_config)
    registry = registry_mod.load_metric_registry(READINESS_METRICS)
    report = validator_mod.validate(norm_result, registry)
    result_df = calc_mod.calculate(norm_result.df, registry)
    long_metrics = output_builder.build_long_metrics(result_df, registry)
    long_metrics = output_builder.apply_output_rounding(long_metrics, registry)
    wide_metrics = output_builder.build_wide_metrics(long_metrics)
    metric_dict = output_builder.build_metric_dictionary(registry)
    export(long_metrics, wide_metrics, metric_dict, report, tmp_path)

    return {
        "long": long_metrics,
        "wide": wide_metrics,
        "dict": metric_dict,
        "report": report,
        "output_dir": tmp_path,
    }


# ── validation ────────────────────────────────────────────────────────────────

def test_validation_passes(readiness_result):
    assert readiness_result["report"].status in ("passed", "passed_with_warnings")


def test_validation_has_no_errors(readiness_result):
    assert readiness_result["report"].errors == []


# ── output files created ──────────────────────────────────────────────────────

def test_long_metrics_csv_created(readiness_result):
    assert (readiness_result["output_dir"] / "long_metrics.csv").exists()


def test_wide_metrics_csv_created(readiness_result):
    assert (readiness_result["output_dir"] / "wide_metrics.csv").exists()


def test_metric_dictionary_csv_created(readiness_result):
    assert (readiness_result["output_dir"] / "metric_dictionary.csv").exists()


def test_validation_report_json_created(readiness_result):
    assert (readiness_result["output_dir"] / "validation_report.json").exists()


# ── all four metric ids present ───────────────────────────────────────────────

def test_total_requirement_count_present(readiness_result):
    assert "total_requirement_count" in readiness_result["long"]["metric_id"].values


def test_open_gap_count_present(readiness_result):
    assert "open_gap_count" in readiness_result["long"]["metric_id"].values


def test_critical_item_count_present(readiness_result):
    assert "critical_item_count" in readiness_result["long"]["metric_id"].values


def test_readiness_completion_pct_present(readiness_result):
    assert "readiness_completion_pct" in readiness_result["long"]["metric_id"].values


# ── date_only aggregate values (20 rows in sample data) ──────────────────────

def _date_only(long, metric_id):
    mask = (long["rollup_level"] == "date_only") & (long["metric_id"] == metric_id)
    rows = long[mask]
    assert len(rows) == 1, f"Expected 1 date_only row for {metric_id}, got {len(rows)}"
    return rows.iloc[0]["value"]


def test_total_requirement_count_is_20(readiness_result):
    assert _date_only(readiness_result["long"], "total_requirement_count") == pytest.approx(20.0)


def test_open_gap_count_is_10(readiness_result):
    # open + in_progress + not_started rows in sample data = 10
    assert _date_only(readiness_result["long"], "open_gap_count") == pytest.approx(10.0)


def test_critical_item_count_is_4(readiness_result):
    # critical severity rows in sample data = 4
    assert _date_only(readiness_result["long"], "critical_item_count") == pytest.approx(4.0)


def test_readiness_completion_pct_is_50(readiness_result):
    # complete + closed = 10 out of 20 = 50.0%
    assert _date_only(readiness_result["long"], "readiness_completion_pct") == pytest.approx(50.0)


# ── category rollup present ───────────────────────────────────────────────────

def test_category_rollup_rows_exist(readiness_result):
    assert "date_category" in readiness_result["long"]["rollup_level"].values


def test_power_category_count(readiness_result):
    long = readiness_result["long"]
    mask = (
        (long["rollup_level"] == "date_category") &
        (long["metric_id"] == "total_requirement_count") &
        (long["category"] == "power")
    )
    assert long[mask].iloc[0]["value"] == pytest.approx(4.0)


# ── metric dictionary ─────────────────────────────────────────────────────────

def test_metric_dict_has_four_entries(readiness_result):
    assert len(readiness_result["dict"]) == 4


def test_metric_dict_ids(readiness_result):
    ids = set(readiness_result["dict"]["id"])
    assert ids == {
        "total_requirement_count",
        "open_gap_count",
        "critical_item_count",
        "readiness_completion_pct",
    }


# ── project_id column is dropped (not in schema) ──────────────────────────────

def test_project_id_not_in_long_metrics(readiness_result):
    assert "project_id" not in readiness_result["long"].columns


# ── wide metrics shape ────────────────────────────────────────────────────────

def test_wide_metrics_has_metric_columns(readiness_result):
    wide = readiness_result["wide"]
    for mid in ["total_requirement_count", "open_gap_count", "critical_item_count", "readiness_completion_pct"]:
        assert mid in wide.columns


# ── no hardcoded market/operating columns required ────────────────────────────

def test_run_succeeds_without_revenue_column(readiness_result):
    assert "revenue" not in readiness_result["long"].columns
