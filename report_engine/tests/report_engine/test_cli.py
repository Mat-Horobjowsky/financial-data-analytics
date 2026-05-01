import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent.parent


def _cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "report_engine.cli"] + list(args),
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )


@pytest.fixture
def valid_input_dir(tmp_path):
    (tmp_path / "validation_report.json").write_text(
        json.dumps({"status": "passed", "errors": [], "warnings": []}),
        encoding="utf-8",
    )
    (tmp_path / "long_metrics.csv").write_text(
        "rollup_level,date,metric_id,label,value,unit\n"
        "date_only,2024-01-01,total_revenue,Total Revenue,5900000.0,USD\n"
        "date_only,2024-02-01,total_revenue,Total Revenue,6150000.0,USD\n",
        encoding="utf-8",
    )
    (tmp_path / "wide_metrics.csv").write_text(
        "rollup_level,date,total_revenue\n"
        "date_only,2024-01-01,5900000.0\n"
        "date_only,2024-02-01,6150000.0\n",
        encoding="utf-8",
    )
    (tmp_path / "metric_dictionary.csv").write_text(
        "id,label,type,unit,decimals,description\n"
        "total_revenue,Total Revenue,sum,USD,0,Sum of all revenue\n",
        encoding="utf-8",
    )
    return tmp_path


def test_build_exits_zero(valid_input_dir, tmp_path):
    result = _cli("build", "--input", str(valid_input_dir), "--output", str(tmp_path / "out"))
    assert result.returncode == 0


def test_build_writes_report_md(valid_input_dir, tmp_path):
    out = tmp_path / "out"
    _cli("build", "--input", str(valid_input_dir), "--output", str(out))
    assert (out / "report.md").exists()


def test_build_writes_report_html(valid_input_dir, tmp_path):
    out = tmp_path / "out"
    _cli("build", "--input", str(valid_input_dir), "--output", str(out))
    assert (out / "report.html").exists()


def test_build_writes_summary_json(valid_input_dir, tmp_path):
    out = tmp_path / "out"
    _cli("build", "--input", str(valid_input_dir), "--output", str(out))
    assert (out / "summary.json").exists()


def test_build_summary_has_validation_status(valid_input_dir, tmp_path):
    out = tmp_path / "out"
    _cli("build", "--input", str(valid_input_dir), "--output", str(out))
    data = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert data["validation_status"] == "passed"


def test_build_summary_has_metric_count(valid_input_dir, tmp_path):
    out = tmp_path / "out"
    _cli("build", "--input", str(valid_input_dir), "--output", str(out))
    data = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert data["metric_count"] == 1


def test_build_summary_has_date_range(valid_input_dir, tmp_path):
    out = tmp_path / "out"
    _cli("build", "--input", str(valid_input_dir), "--output", str(out))
    data = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert data["date_range"]["min"] == "2024-01-01"
    assert data["date_range"]["max"] == "2024-02-01"


def test_build_summary_has_generated_at(valid_input_dir, tmp_path):
    out = tmp_path / "out"
    _cli("build", "--input", str(valid_input_dir), "--output", str(out))
    data = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert "generated_at" in data


def test_build_summary_has_generated_files(valid_input_dir, tmp_path):
    out = tmp_path / "out"
    _cli("build", "--input", str(valid_input_dir), "--output", str(out))
    data = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert data["generated_files"] == ["report.md", "report.html", "summary.json", "insights.json"]


def test_build_prints_output_files(valid_input_dir, tmp_path):
    result = _cli("build", "--input", str(valid_input_dir), "--output", str(tmp_path / "out"))
    assert "report.md" in result.stdout
    assert "report.html" in result.stdout
    assert "summary.json" in result.stdout


def test_build_creates_nested_output_directory(valid_input_dir, tmp_path):
    out = tmp_path / "nested" / "output"
    assert not out.exists()
    _cli("build", "--input", str(valid_input_dir), "--output", str(out))
    assert out.exists()


def test_build_missing_input_exits_nonzero(tmp_path):
    result = _cli("build", "--input", str(tmp_path / "nonexistent"), "--output", str(tmp_path / "out"))
    assert result.returncode != 0


def test_build_missing_input_prints_to_stderr(tmp_path):
    result = _cli("build", "--input", str(tmp_path / "nonexistent"), "--output", str(tmp_path / "out"))
    assert "Error" in result.stderr


def test_build_only_requires_validation_report(tmp_path):
    (tmp_path / "validation_report.json").write_text(
        json.dumps({"status": "passed", "errors": [], "warnings": []}),
        encoding="utf-8",
    )
    out = tmp_path / "out"
    result = _cli("build", "--input", str(tmp_path), "--output", str(out))
    assert result.returncode == 0
    assert (out / "report.md").exists()
    assert (out / "report.html").exists()
    assert (out / "summary.json").exists()


def test_build_report_md_contains_status(valid_input_dir, tmp_path):
    out = tmp_path / "out"
    _cli("build", "--input", str(valid_input_dir), "--output", str(out))
    md = (out / "report.md").read_text(encoding="utf-8")
    assert "passed" in md


def test_build_report_html_is_valid_document(valid_input_dir, tmp_path):
    out = tmp_path / "out"
    _cli("build", "--input", str(valid_input_dir), "--output", str(out))
    html = (out / "report.html").read_text(encoding="utf-8")
    assert "<!DOCTYPE html>" in html
    assert "</html>" in html


# ── insights.json tests ────────────────────────────────────────────────────────

def test_build_writes_insights_json(valid_input_dir, tmp_path):
    out = tmp_path / "out"
    _cli("build", "--input", str(valid_input_dir), "--output", str(out))
    assert (out / "insights.json").exists()


def test_build_insights_json_is_valid_json(valid_input_dir, tmp_path):
    out = tmp_path / "out"
    _cli("build", "--input", str(valid_input_dir), "--output", str(out))
    data = json.loads((out / "insights.json").read_text(encoding="utf-8"))
    assert isinstance(data, dict)


def test_build_insights_json_has_required_keys(valid_input_dir, tmp_path):
    out = tmp_path / "out"
    _cli("build", "--input", str(valid_input_dir), "--output", str(out))
    data = json.loads((out / "insights.json").read_text(encoding="utf-8"))
    assert "generated_at" in data
    assert "has_insights" in data
    assert "insights" in data


def test_build_insights_json_empty_list_when_no_period_data(valid_input_dir, tmp_path):
    # valid_input_dir has no period_change_pct column — insights list should be empty
    out = tmp_path / "out"
    _cli("build", "--input", str(valid_input_dir), "--output", str(out))
    data = json.loads((out / "insights.json").read_text(encoding="utf-8"))
    assert data["insights"] == []
    assert data["has_insights"] is False


def test_build_insights_json_has_insights_when_period_data(tmp_path):
    (tmp_path / "validation_report.json").write_text(
        json.dumps({"status": "passed", "errors": [], "warnings": []}),
        encoding="utf-8",
    )
    (tmp_path / "long_metrics.csv").write_text(
        "rollup_level,date,metric_id,label,value,unit,prior_period_value,period_change,period_change_pct\n"
        "date_only,2024-01-01,total_revenue,Total Revenue,5900000.0,USD,,, \n"
        "date_only,2024-02-01,total_revenue,Total Revenue,6150000.0,USD,5850000.0,300000.0,5.13\n",
        encoding="utf-8",
    )
    out = tmp_path / "out"
    _cli("build", "--input", str(tmp_path), "--output", str(out))
    data = json.loads((out / "insights.json").read_text(encoding="utf-8"))
    assert data["has_insights"] is True
    assert len(data["insights"]) == 1
    assert data["insights"][0]["metric_id"] == "total_revenue"
    assert data["insights"][0]["direction"] == "up"


def test_build_prints_insights_json(valid_input_dir, tmp_path):
    result = _cli("build", "--input", str(valid_input_dir), "--output", str(tmp_path / "out"))
    assert "insights.json" in result.stdout


# ── Template flag tests ────────────────────────────────────────────────────────

def test_build_default_template_is_full_report(valid_input_dir, tmp_path):
    out = tmp_path / "out"
    _cli("build", "--input", str(valid_input_dir), "--output", str(out))
    data = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert data["template"] == "full_report"


def test_build_summary_records_selected_template(valid_input_dir, tmp_path):
    out = tmp_path / "out"
    _cli("build", "--input", str(valid_input_dir), "--output", str(out), "--template", "executive_summary")
    data = json.loads((out / "summary.json").read_text(encoding="utf-8"))
    assert data["template"] == "executive_summary"


def test_build_executive_summary_exits_zero(valid_input_dir, tmp_path):
    result = _cli("build", "--input", str(valid_input_dir), "--output", str(tmp_path / "out"), "--template", "executive_summary")
    assert result.returncode == 0


def test_build_executive_summary_omits_metrics_summary(valid_input_dir, tmp_path):
    out = tmp_path / "out"
    _cli("build", "--input", str(valid_input_dir), "--output", str(out), "--template", "executive_summary")
    md = (out / "report.md").read_text(encoding="utf-8")
    assert "## Metrics Summary" not in md


def test_build_executive_summary_omits_metric_dictionary(valid_input_dir, tmp_path):
    out = tmp_path / "out"
    _cli("build", "--input", str(valid_input_dir), "--output", str(out), "--template", "executive_summary")
    md = (out / "report.md").read_text(encoding="utf-8")
    assert "## Metric Dictionary" not in md


def test_build_executive_summary_html_omits_metrics_summary(valid_input_dir, tmp_path):
    out = tmp_path / "out"
    _cli("build", "--input", str(valid_input_dir), "--output", str(out), "--template", "executive_summary")
    html = (out / "report.html").read_text(encoding="utf-8")
    assert "<h2>Metrics Summary</h2>" not in html


def test_build_metrics_detail_omits_kpi_snapshot(valid_input_dir, tmp_path):
    out = tmp_path / "out"
    _cli("build", "--input", str(valid_input_dir), "--output", str(out), "--template", "metrics_detail")
    md = (out / "report.md").read_text(encoding="utf-8")
    assert "## KPI Snapshot" not in md


def test_build_metrics_detail_html_omits_kpi_snapshot(valid_input_dir, tmp_path):
    out = tmp_path / "out"
    _cli("build", "--input", str(valid_input_dir), "--output", str(out), "--template", "metrics_detail")
    html = (out / "report.html").read_text(encoding="utf-8")
    assert "<h2>KPI Snapshot</h2>" not in html


def test_build_metrics_detail_includes_metrics_summary(valid_input_dir, tmp_path):
    out = tmp_path / "out"
    _cli("build", "--input", str(valid_input_dir), "--output", str(out), "--template", "metrics_detail")
    md = (out / "report.md").read_text(encoding="utf-8")
    assert "## Metrics Summary" in md


def test_build_invalid_template_exits_nonzero(valid_input_dir, tmp_path):
    result = _cli("build", "--input", str(valid_input_dir), "--output", str(tmp_path / "out"), "--template", "nonexistent")
    assert result.returncode != 0


def test_build_invalid_template_prints_error(valid_input_dir, tmp_path):
    result = _cli("build", "--input", str(valid_input_dir), "--output", str(tmp_path / "out"), "--template", "nonexistent")
    assert "nonexistent" in result.stderr or "invalid choice" in result.stderr


def test_build_insights_json_written_for_executive_summary(valid_input_dir, tmp_path):
    out = tmp_path / "out"
    _cli("build", "--input", str(valid_input_dir), "--output", str(out), "--template", "executive_summary")
    assert (out / "insights.json").exists()


def test_build_summary_json_written_for_metrics_detail(valid_input_dir, tmp_path):
    out = tmp_path / "out"
    _cli("build", "--input", str(valid_input_dir), "--output", str(out), "--template", "metrics_detail")
    assert (out / "summary.json").exists()
