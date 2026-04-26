from pathlib import Path

import polars as pl
import pytest
from typer.testing import CliRunner

from intake_engine.cli.main import app
from intake_engine.models.profile import ProfileReport
from intake_engine.models.validation import ValidationReport
from intake_engine.reporter.reporter import _bar, build_html_report

runner = CliRunner()


# --- helpers ---

def _make_validation(status="pass", issues=None, warnings=None, rows_loaded=4, row_count=3,
                     dup_rate=0.25, null_summary=None) -> ValidationReport:
    return ValidationReport(
        file_name="test.csv",
        status=status,
        issues=issues or [],
        warnings=warnings or [],
        rows_loaded=rows_loaded,
        row_count=row_count,
        columns=2,
        duplicate_rate=dup_rate,
        null_summary=null_summary or {"name": 0.0, "score": 0.0},
        run_timestamp="2026-04-23T12:00:00+00:00",
    )


def _make_profile() -> ProfileReport:
    return ProfileReport(
        file_name="test.csv",
        rows_loaded=4,
        rows_output=3,
        columns=2,
        column_names=["name", "score"],
        inferred_types={"name": "String", "score": "Float64"},
        null_counts={"name": 0, "score": 1},
        duplicate_rows_removed=1,
        columns_renamed={"Name": "name"},
        numeric_columns_normalized=["score"],
        date_columns_normalized=[],
        semantic_types={"name": "text", "score": "numeric"},
        warnings=[],
        run_timestamp="2026-04-23T12:00:00+00:00",
    )


# --- unit tests: build_html_report ---

def test_html_validation_only_contains_status_and_filename():
    v = _make_validation(status="pass")
    html = build_html_report("test.csv", validation=v)
    assert "test.csv" in html
    assert "PASS" in html
    assert 'class="badge pass"' in html


def test_html_warn_badge():
    v = _make_validation(status="warn", warnings=["high null rate in 'score': 40.0%"])
    html = build_html_report("test.csv", validation=v)
    assert 'class="badge warn"' in html
    assert "WARN" in html


def test_html_fail_badge():
    v = _make_validation(status="fail", issues=["empty file: 0 rows loaded"])
    html = build_html_report("test.csv", validation=v)
    assert 'class="badge fail"' in html
    assert "FAIL" in html


def test_html_issues_rendered_with_err_class():
    v = _make_validation(status="fail", issues=["required column missing: 'revenue'"])
    html = build_html_report("test.csv", validation=v)
    assert 'class="err"' in html
    assert "required column missing" in html


def test_html_warnings_rendered_with_wrn_class():
    v = _make_validation(status="warn", warnings=["high duplicate rate: 33.3%"])
    html = build_html_report("test.csv", validation=v)
    assert 'class="wrn"' in html
    assert "high duplicate rate" in html


def test_html_profile_only_no_badge():
    p = _make_profile()
    html = build_html_report("test.csv", profile=p)
    assert "test.csv" in html
    assert 'class="badge' not in html


def test_html_profile_column_types_section():
    p = _make_profile()
    html = build_html_report("test.csv", profile=p)
    assert "Column Types" in html
    assert "Semantic Type" in html
    assert "numeric" in html
    assert "Float64" in html


def test_html_profile_renamed_columns_section():
    p = _make_profile()
    html = build_html_report("test.csv", profile=p)
    assert "Columns Renamed" in html
    assert "Name" in html  # original column name appears


def test_html_combined_has_all_sections():
    p = _make_profile()
    v = _make_validation(status="warn", warnings=["high duplicate rate: 33.3%"])
    html = build_html_report("test.csv", profile=p, validation=v)
    assert 'class="badge warn"' in html
    assert "Column Types" in html
    assert "Null Rates" in html
    assert "Columns Renamed" in html
    assert "Warnings" in html


def test_html_null_bar_green_for_zero():
    bar = _bar(0.0)
    assert 'class="fill ok"' in bar
    assert "0.0%" in bar


def test_html_null_bar_amber_for_mid():
    bar = _bar(0.2)  # 20%
    assert 'class="fill mid"' in bar


def test_html_null_bar_red_for_high():
    bar = _bar(0.5)  # 50%
    assert 'class="fill hi"' in bar


def test_html_no_data_returns_placeholder():
    html = build_html_report("ghost.csv")
    assert "ghost.csv" in html


def test_html_escapes_special_chars():
    v = _make_validation(issues=["column '<revenue>' missing"])
    v = ValidationReport(
        file_name="test<>.csv",
        status="fail",
        issues=["column '<revenue>' missing"],
        warnings=[],
        rows_loaded=2,
        row_count=2,
        columns=1,
        duplicate_rate=0.0,
        null_summary={},
        run_timestamp="2026-04-23T12:00:00+00:00",
    )
    html = build_html_report("test<>.csv", validation=v)
    assert "&lt;" in html  # < is escaped
    assert "<revenue>" not in html


# --- CLI integration tests ---

def test_validate_cmd_writes_html(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "data.csv"
    f.write_text("name,score\nAlice,90\nBob,80\n")

    result = runner.invoke(app, ["validate", str(f)])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "outputs" / "data_report.html").exists()
    html = (tmp_path / "outputs" / "data_report.html").read_text(encoding="utf-8")
    assert "data.csv" in html
    assert "PASS" in html


def test_profile_cmd_writes_html(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "data.csv"
    f.write_text("name,score\nAlice,90\nBob,80\n")

    result = runner.invoke(app, ["profile", str(f)])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "outputs" / "data_report.html").exists()
    html = (tmp_path / "outputs" / "data_report.html").read_text(encoding="utf-8")
    assert "Column Types" in html


def test_run_validate_flag_writes_html(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "data.csv"
    f.write_text("name,score\nAlice,90\nBob,80\n")

    result = runner.invoke(app, ["run", str(f), "--validate"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "outputs" / "data_report.html").exists()


def test_run_profile_flag_writes_html(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "data.csv"
    f.write_text("name,score\nAlice,90\nBob,80\n")

    result = runner.invoke(app, ["run", str(f), "--profile"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "outputs" / "data_report.html").exists()


def test_run_both_flags_writes_combined_html(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "data.csv"
    f.write_text("name,score\nAlice,90\nBob,80\n")

    result = runner.invoke(app, ["run", str(f), "--profile", "--validate"])

    assert result.exit_code == 0, result.output
    html = (tmp_path / "outputs" / "data_report.html").read_text(encoding="utf-8")
    # Badge from validation + column types from profile
    assert 'class="badge' in html
    assert "Column Types" in html


def test_run_batch_validate_writes_html_per_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    folder = tmp_path / "incoming"
    folder.mkdir()
    (folder / "a.csv").write_text("name,score\nAlice,90\n")
    (folder / "b.csv").write_text("name,score\nBob,80\n")

    result = runner.invoke(app, ["run", str(folder), "--validate"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "outputs" / "a_report.html").exists()
    assert (tmp_path / "outputs" / "b_report.html").exists()
