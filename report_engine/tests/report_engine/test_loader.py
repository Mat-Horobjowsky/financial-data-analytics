import json

import pandas as pd
import pytest

from report_engine.loader import LoaderError, ReportData, load


@pytest.fixture
def valid_input_dir(tmp_path):
    (tmp_path / "validation_report.json").write_text(
        json.dumps({"status": "passed", "errors": [], "warnings": ["A warning"]}),
        encoding="utf-8",
    )
    (tmp_path / "long_metrics.csv").write_text(
        "rollup_level,date,metric_id,label,value,unit\n"
        "date_only,2024-01-01,total_revenue,Total Revenue,5900000.0,USD\n",
        encoding="utf-8",
    )
    (tmp_path / "wide_metrics.csv").write_text(
        "rollup_level,date,total_revenue\n"
        "date_only,2024-01-01,5900000.0\n",
        encoding="utf-8",
    )
    (tmp_path / "metric_dictionary.csv").write_text(
        "id,label,type,unit,decimals,description\n"
        "total_revenue,Total Revenue,sum,USD,0,Sum of all revenue\n",
        encoding="utf-8",
    )
    return tmp_path


def test_load_returns_report_data(valid_input_dir):
    data = load(valid_input_dir)
    assert isinstance(data, ReportData)


def test_load_reads_validation_status(valid_input_dir):
    data = load(valid_input_dir)
    assert data.validation_status == "passed"


def test_load_reads_warnings(valid_input_dir):
    data = load(valid_input_dir)
    assert data.validation_warnings == ["A warning"]


def test_load_reads_long_metrics(valid_input_dir):
    data = load(valid_input_dir)
    assert not data.long_metrics.empty
    assert "metric_id" in data.long_metrics.columns


def test_load_reads_wide_metrics(valid_input_dir):
    data = load(valid_input_dir)
    assert not data.wide_metrics.empty
    assert "total_revenue" in data.wide_metrics.columns


def test_load_reads_metric_dictionary(valid_input_dir):
    data = load(valid_input_dir)
    assert not data.metric_dictionary.empty
    assert "id" in data.metric_dictionary.columns


def test_load_sets_input_dir(valid_input_dir):
    data = load(valid_input_dir)
    assert data.input_dir == valid_input_dir


def test_load_missing_dir_raises(tmp_path):
    with pytest.raises(LoaderError, match="not found"):
        load(tmp_path / "does_not_exist")


def test_load_missing_validation_report_raises(tmp_path):
    with pytest.raises(LoaderError, match="Required file missing"):
        load(tmp_path)


def test_load_missing_optional_csvs_returns_empty_dataframes(tmp_path):
    (tmp_path / "validation_report.json").write_text(
        json.dumps({"status": "passed", "errors": [], "warnings": []}),
        encoding="utf-8",
    )
    data = load(tmp_path)
    assert data.long_metrics.empty
    assert data.wide_metrics.empty
    assert data.metric_dictionary.empty


def test_load_reads_errors(tmp_path):
    (tmp_path / "validation_report.json").write_text(
        json.dumps({"status": "failed", "errors": ["Missing column: revenue"], "warnings": []}),
        encoding="utf-8",
    )
    data = load(tmp_path)
    assert data.validation_errors == ["Missing column: revenue"]
    assert data.validation_status == "failed"


def test_load_accepts_string_path(tmp_path):
    (tmp_path / "validation_report.json").write_text(
        json.dumps({"status": "passed", "errors": [], "warnings": []}),
        encoding="utf-8",
    )
    data = load(str(tmp_path))
    assert data.validation_status == "passed"


def test_load_corrupt_validation_report_raises(tmp_path):
    (tmp_path / "validation_report.json").write_text("not valid json {{{", encoding="utf-8")
    with pytest.raises(LoaderError, match="not valid JSON"):
        load(tmp_path)
