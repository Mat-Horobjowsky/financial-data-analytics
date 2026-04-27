import json
from pathlib import Path

import pandas as pd
import pytest

from metrics_engine.exporter import export
from metrics_engine.validator import ValidationReport


@pytest.fixture
def long_metrics():
    return pd.DataFrame({
        "rollup_level": ["date_only", "date_only"],
        "date": pd.to_datetime(["2024-01-01", "2024-01-01"]),
        "metric_id": ["total_revenue", "utilization_pct"],
        "label": ["Total Revenue", "Utilization Rate"],
        "value": [1500.0, 80.0],
        "unit": ["USD", "%"],
    })


@pytest.fixture
def wide_metrics():
    return pd.DataFrame({
        "rollup_level": ["date_only"],
        "date": pd.to_datetime(["2024-01-01"]),
        "total_revenue": [1500.0],
        "utilization_pct": [80.0],
    })


@pytest.fixture
def metric_dictionary():
    return pd.DataFrame({
        "id": ["total_revenue", "utilization_pct"],
        "label": ["Total Revenue", "Utilization Rate"],
        "type": ["sum", "ratio"],
        "unit": ["USD", "%"],
        "decimals": [0, 1],
        "description": ["Sum of revenue", "leased/capacity*100"],
    })


@pytest.fixture
def report_passed():
    return ValidationReport(status="passed", errors=[], warnings=[])


@pytest.fixture
def report_with_issues():
    return ValidationReport(
        status="passed_with_warnings",
        errors=[],
        warnings=["Column 'extra' was dropped", "2 duplicate rows found"],
    )


# ── directory creation ────────────────────────────────────────────────────────

def test_creates_output_directory_when_missing(
    tmp_path, long_metrics, wide_metrics, metric_dictionary, report_passed
):
    out_dir = tmp_path / "new_output_dir"
    assert not out_dir.exists()
    export(long_metrics, wide_metrics, metric_dictionary, report_passed, out_dir)
    assert out_dir.exists()


def test_does_not_fail_when_directory_already_exists(
    tmp_path, long_metrics, wide_metrics, metric_dictionary, report_passed
):
    tmp_path.mkdir(exist_ok=True)
    export(long_metrics, wide_metrics, metric_dictionary, report_passed, tmp_path)


# ── file creation ─────────────────────────────────────────────────────────────

def test_writes_long_metrics_csv(
    tmp_path, long_metrics, wide_metrics, metric_dictionary, report_passed
):
    export(long_metrics, wide_metrics, metric_dictionary, report_passed, tmp_path)
    assert (tmp_path / "long_metrics.csv").exists()


def test_writes_wide_metrics_csv(
    tmp_path, long_metrics, wide_metrics, metric_dictionary, report_passed
):
    export(long_metrics, wide_metrics, metric_dictionary, report_passed, tmp_path)
    assert (tmp_path / "wide_metrics.csv").exists()


def test_writes_metric_dictionary_csv(
    tmp_path, long_metrics, wide_metrics, metric_dictionary, report_passed
):
    export(long_metrics, wide_metrics, metric_dictionary, report_passed, tmp_path)
    assert (tmp_path / "metric_dictionary.csv").exists()


def test_writes_validation_report_json(
    tmp_path, long_metrics, wide_metrics, metric_dictionary, report_passed
):
    export(long_metrics, wide_metrics, metric_dictionary, report_passed, tmp_path)
    assert (tmp_path / "validation_report.json").exists()


# ── CSV readability ───────────────────────────────────────────────────────────

def test_long_metrics_csv_is_readable(
    tmp_path, long_metrics, wide_metrics, metric_dictionary, report_passed
):
    export(long_metrics, wide_metrics, metric_dictionary, report_passed, tmp_path)
    df = pd.read_csv(tmp_path / "long_metrics.csv")
    assert len(df) == len(long_metrics)


def test_long_metrics_csv_has_expected_columns(
    tmp_path, long_metrics, wide_metrics, metric_dictionary, report_passed
):
    export(long_metrics, wide_metrics, metric_dictionary, report_passed, tmp_path)
    df = pd.read_csv(tmp_path / "long_metrics.csv")
    for col in ["rollup_level", "metric_id", "label", "value", "unit"]:
        assert col in df.columns


def test_wide_metrics_csv_is_readable(
    tmp_path, long_metrics, wide_metrics, metric_dictionary, report_passed
):
    export(long_metrics, wide_metrics, metric_dictionary, report_passed, tmp_path)
    df = pd.read_csv(tmp_path / "wide_metrics.csv")
    assert len(df) == len(wide_metrics)


def test_wide_metrics_csv_has_expected_columns(
    tmp_path, long_metrics, wide_metrics, metric_dictionary, report_passed
):
    export(long_metrics, wide_metrics, metric_dictionary, report_passed, tmp_path)
    df = pd.read_csv(tmp_path / "wide_metrics.csv")
    for col in ["rollup_level", "total_revenue", "utilization_pct"]:
        assert col in df.columns


def test_metric_dictionary_csv_is_readable(
    tmp_path, long_metrics, wide_metrics, metric_dictionary, report_passed
):
    export(long_metrics, wide_metrics, metric_dictionary, report_passed, tmp_path)
    df = pd.read_csv(tmp_path / "metric_dictionary.csv")
    assert len(df) == len(metric_dictionary)


def test_metric_dictionary_csv_has_expected_columns(
    tmp_path, long_metrics, wide_metrics, metric_dictionary, report_passed
):
    export(long_metrics, wide_metrics, metric_dictionary, report_passed, tmp_path)
    df = pd.read_csv(tmp_path / "metric_dictionary.csv")
    for col in ["id", "label", "type", "unit", "decimals", "description"]:
        assert col in df.columns


# ── validation_report.json ────────────────────────────────────────────────────

def test_validation_report_json_is_valid_json(
    tmp_path, long_metrics, wide_metrics, metric_dictionary, report_passed
):
    export(long_metrics, wide_metrics, metric_dictionary, report_passed, tmp_path)
    data = json.loads((tmp_path / "validation_report.json").read_text())
    assert isinstance(data, dict)


def test_validation_report_json_has_status_key(
    tmp_path, long_metrics, wide_metrics, metric_dictionary, report_passed
):
    export(long_metrics, wide_metrics, metric_dictionary, report_passed, tmp_path)
    data = json.loads((tmp_path / "validation_report.json").read_text())
    assert "status" in data


def test_validation_report_json_has_errors_key(
    tmp_path, long_metrics, wide_metrics, metric_dictionary, report_passed
):
    export(long_metrics, wide_metrics, metric_dictionary, report_passed, tmp_path)
    data = json.loads((tmp_path / "validation_report.json").read_text())
    assert "errors" in data


def test_validation_report_json_has_warnings_key(
    tmp_path, long_metrics, wide_metrics, metric_dictionary, report_passed
):
    export(long_metrics, wide_metrics, metric_dictionary, report_passed, tmp_path)
    data = json.loads((tmp_path / "validation_report.json").read_text())
    assert "warnings" in data


def test_validation_report_status_value_written_correctly(
    tmp_path, long_metrics, wide_metrics, metric_dictionary, report_with_issues
):
    export(long_metrics, wide_metrics, metric_dictionary, report_with_issues, tmp_path)
    data = json.loads((tmp_path / "validation_report.json").read_text())
    assert data["status"] == "passed_with_warnings"


def test_validation_report_errors_list_written_correctly(
    tmp_path, long_metrics, wide_metrics, metric_dictionary
):
    report = ValidationReport(
        status="failed", errors=["Missing column 'revenue'"], warnings=[]
    )
    export(long_metrics, wide_metrics, metric_dictionary, report, tmp_path)
    data = json.loads((tmp_path / "validation_report.json").read_text())
    assert data["errors"] == ["Missing column 'revenue'"]


def test_validation_report_warnings_list_written_correctly(
    tmp_path, long_metrics, wide_metrics, metric_dictionary, report_with_issues
):
    export(long_metrics, wide_metrics, metric_dictionary, report_with_issues, tmp_path)
    data = json.loads((tmp_path / "validation_report.json").read_text())
    assert data["warnings"] == ["Column 'extra' was dropped", "2 duplicate rows found"]


def test_validation_report_empty_errors_and_warnings(
    tmp_path, long_metrics, wide_metrics, metric_dictionary, report_passed
):
    export(long_metrics, wide_metrics, metric_dictionary, report_passed, tmp_path)
    data = json.loads((tmp_path / "validation_report.json").read_text())
    assert data["errors"] == []
    assert data["warnings"] == []
