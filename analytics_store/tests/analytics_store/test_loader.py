from __future__ import annotations

import json
from pathlib import Path

import pytest

from analytics_store.loader import LoaderError, MetricsData, ReportData, load_metrics, load_report


# --- Helpers ---

def _write_validation_report(d: Path, status="passed", errors=None, warnings=None):
    (d / "validation_report.json").write_text(
        json.dumps({"status": status, "errors": errors or [], "warnings": warnings or []}),
        encoding="utf-8",
    )


def _write_long_metrics(d: Path):
    (d / "long_metrics.csv").write_text(
        "rollup_level,date,provider,region,metric_id,label,value,unit\n"
        "date_only,2024-01-01,,,total_revenue,Total Revenue,1000.0,USD\n",
        encoding="utf-8",
    )


def _write_wide_metrics(d: Path):
    (d / "wide_metrics.csv").write_text(
        "rollup_level,date,total_revenue\n"
        "date_only,2024-01-01,1000.0\n",
        encoding="utf-8",
    )


def _write_metric_dictionary(d: Path):
    (d / "metric_dictionary.csv").write_text(
        "id,label,type,unit,decimals,description\n"
        "total_revenue,Total Revenue,sum,USD,0,Sum of all revenue\n",
        encoding="utf-8",
    )


def _write_insights(d: Path, insights=None):
    payload = {
        "generated_at": "2024-01-01T00:00:00+00:00",
        "has_insights": bool(insights),
        "insights": insights or [],
    }
    (d / "insights.json").write_text(json.dumps(payload), encoding="utf-8")


def _write_summary(d: Path):
    summary = {
        "validation_status": "passed",
        "error_count": 0,
        "warning_count": 0,
        "template": "full_report",
        "metric_count": 1,
        "date_range": {"min": "2024-01-01", "max": "2024-01-01"},
        "generated_files": ["report.md"],
    }
    (d / "summary.json").write_text(json.dumps(summary), encoding="utf-8")


# --- load_metrics: return type and fields ---

def test_load_metrics_returns_metrics_data(tmp_path):
    _write_validation_report(tmp_path)
    result = load_metrics(tmp_path)
    assert isinstance(result, MetricsData)


def test_load_metrics_sets_metrics_dir(tmp_path):
    _write_validation_report(tmp_path)
    result = load_metrics(tmp_path)
    assert result.metrics_dir == tmp_path


def test_load_metrics_reads_validation_status(tmp_path):
    _write_validation_report(tmp_path, status="passed_with_warnings")
    result = load_metrics(tmp_path)
    assert result.validation_status == "passed_with_warnings"


def test_load_metrics_reads_errors(tmp_path):
    _write_validation_report(tmp_path, errors=["Missing column: revenue"])
    result = load_metrics(tmp_path)
    assert result.validation_errors == ["Missing column: revenue"]


def test_load_metrics_reads_warnings(tmp_path):
    _write_validation_report(tmp_path, warnings=["High null rate in col X"])
    result = load_metrics(tmp_path)
    assert result.validation_warnings == ["High null rate in col X"]


# --- load_metrics: CSV loading ---

def test_load_metrics_reads_long_metrics(tmp_path):
    _write_validation_report(tmp_path)
    _write_long_metrics(tmp_path)
    result = load_metrics(tmp_path)
    assert not result.long_metrics.empty
    assert "metric_id" in result.long_metrics.columns


def test_load_metrics_reads_wide_metrics(tmp_path):
    _write_validation_report(tmp_path)
    _write_wide_metrics(tmp_path)
    result = load_metrics(tmp_path)
    assert not result.wide_metrics.empty
    assert "total_revenue" in result.wide_metrics.columns


def test_load_metrics_reads_metric_dictionary(tmp_path):
    _write_validation_report(tmp_path)
    _write_metric_dictionary(tmp_path)
    result = load_metrics(tmp_path)
    assert not result.metric_dictionary.empty
    assert "id" in result.metric_dictionary.columns


def test_load_metrics_missing_csvs_return_empty_dataframes(tmp_path):
    _write_validation_report(tmp_path)
    result = load_metrics(tmp_path)
    assert result.long_metrics.empty
    assert result.wide_metrics.empty
    assert result.metric_dictionary.empty


# --- load_metrics: error cases ---

def test_load_metrics_missing_dir_raises(tmp_path):
    with pytest.raises(LoaderError, match="not found"):
        load_metrics(tmp_path / "nonexistent")


def test_load_metrics_missing_validation_report_raises(tmp_path):
    with pytest.raises(LoaderError, match="Required file missing"):
        load_metrics(tmp_path)


def test_load_metrics_corrupt_json_raises(tmp_path):
    (tmp_path / "validation_report.json").write_text("not valid json {{{", encoding="utf-8")
    with pytest.raises(LoaderError, match="not valid JSON"):
        load_metrics(tmp_path)


def test_load_metrics_accepts_string_path(tmp_path):
    _write_validation_report(tmp_path)
    result = load_metrics(str(tmp_path))
    assert isinstance(result, MetricsData)


# --- load_report: return type and fields ---

def test_load_report_returns_report_data(tmp_path):
    result = load_report(tmp_path)
    assert isinstance(result, ReportData)


def test_load_report_none_returns_empty_report_data():
    result = load_report(None)
    assert isinstance(result, ReportData)
    assert result.report_dir is None
    assert result.insights == []
    assert result.summary == {}


def test_load_report_reads_insights(tmp_path):
    insights = [
        {"metric_id": "revenue", "label": "Revenue", "date": "2024-01-01",
         "period_change_pct": 5.0, "direction": "up", "text": "Up 5%"}
    ]
    _write_insights(tmp_path, insights=insights)
    result = load_report(tmp_path)
    assert len(result.insights) == 1
    assert result.insights[0]["metric_id"] == "revenue"


def test_load_report_reads_summary(tmp_path):
    _write_summary(tmp_path)
    result = load_report(tmp_path)
    assert result.summary.get("template") == "full_report"
    assert result.summary.get("metric_count") == 1


def test_load_report_missing_files_returns_empty(tmp_path):
    result = load_report(tmp_path)
    assert result.insights == []
    assert result.summary == {}


def test_load_report_sets_report_dir(tmp_path):
    result = load_report(tmp_path)
    assert result.report_dir == tmp_path


# --- load_report: error cases ---

def test_load_report_missing_dir_raises(tmp_path):
    with pytest.raises(LoaderError, match="not found"):
        load_report(tmp_path / "nonexistent")


def test_load_report_corrupt_insights_raises(tmp_path):
    (tmp_path / "insights.json").write_text("{{bad json", encoding="utf-8")
    with pytest.raises(LoaderError, match="not valid JSON"):
        load_report(tmp_path)


def test_load_report_corrupt_summary_raises(tmp_path):
    (tmp_path / "summary.json").write_text("not json", encoding="utf-8")
    with pytest.raises(LoaderError, match="not valid JSON"):
        load_report(tmp_path)


def test_load_report_accepts_string_path(tmp_path):
    result = load_report(str(tmp_path))
    assert isinstance(result, ReportData)
