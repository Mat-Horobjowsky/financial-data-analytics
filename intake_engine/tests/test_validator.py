import json

import polars as pl
import pytest
from typer.testing import CliRunner

from intake_engine.cli.main import app
from intake_engine.validator.validator import validate_file

runner = CliRunner()


# --- unit tests: validate_file ---

def test_validate_passes_clean_file(tmp_path):
    raw = pl.DataFrame({"name": ["Alice", "Bob"], "score": ["90", "80"]})
    clean = pl.DataFrame({"name": ["Alice", "Bob"], "score": [90, 80]})
    report = validate_file(tmp_path / "test.csv", raw, clean)
    assert report.status == "pass"
    assert report.issues == []
    assert report.warnings == []
    assert report.row_count == 2
    assert report.columns == 2
    assert report.duplicate_rate == 0.0


def test_validate_fails_empty_file(tmp_path):
    raw = pl.DataFrame({"name": [], "score": []}, schema={"name": pl.String, "score": pl.String})
    clean = pl.DataFrame({"name": [], "score": []}, schema={"name": pl.String, "score": pl.Int64})
    report = validate_file(tmp_path / "test.csv", raw, clean)
    assert report.status == "fail"
    assert any("empty file" in i for i in report.issues)


def test_validate_fails_zero_rows_after_clean(tmp_path):
    raw = pl.DataFrame({"name": ["Alice"]})
    clean = pl.DataFrame({"name": []}, schema={"name": pl.String})
    report = validate_file(tmp_path / "test.csv", raw, clean)
    assert report.status == "fail"
    assert any("0 rows" in i for i in report.issues)


def test_validate_warns_single_column_csv(tmp_path):
    raw = pl.DataFrame({"name;score": ["Alice;90", "Bob;80"]})
    clean = pl.DataFrame({"name;score": ["Alice;90", "Bob;80"]})
    report = validate_file(tmp_path / "test.csv", raw, clean)
    assert report.status == "warn"
    assert any("single-column" in w for w in report.warnings)


def test_validate_single_column_xlsx_no_warning(tmp_path):
    raw = pl.DataFrame({"notes": ["a", "b"]})
    clean = pl.DataFrame({"notes": ["a", "b"]})
    report = validate_file(tmp_path / "test.xlsx", raw, clean)
    assert report.status == "pass"


def test_validate_fails_required_column_missing(tmp_path):
    raw = pl.DataFrame({"name": ["Alice"]})
    clean = pl.DataFrame({"name": ["Alice"]})
    report = validate_file(tmp_path / "test.csv", raw, clean, required_columns=["score"])
    assert report.status == "fail"
    assert any("score" in i for i in report.issues)


def test_validate_passes_required_columns_present(tmp_path):
    raw = pl.DataFrame({"name": ["Alice"], "score": ["90"]})
    clean = pl.DataFrame({"name": ["Alice"], "score": [90]})
    report = validate_file(tmp_path / "test.csv", raw, clean, required_columns=["name", "score"])
    assert report.status == "pass"


def test_validate_warns_high_duplicate_rate(tmp_path):
    raw = pl.DataFrame({"name": ["Alice"] * 10})
    clean = pl.DataFrame({"name": ["Alice"]})
    report = validate_file(tmp_path / "test.csv", raw, clean)
    assert report.status == "warn"
    assert any("duplicate" in w.lower() for w in report.warnings)
    assert abs(report.duplicate_rate - 0.9) < 0.01


def test_validate_passes_low_duplicate_rate(tmp_path):
    raw = pl.DataFrame({"name": ["Alice", "Alice", "Bob", "Carol", "Dave", "Eve"], "score": [1, 1, 2, 3, 4, 5]})
    clean = pl.DataFrame({"name": ["Alice", "Bob", "Carol", "Dave", "Eve"], "score": [1, 2, 3, 4, 5]})
    report = validate_file(tmp_path / "test.csv", raw, clean)
    # dup_rate = 1/6 ~= 16.7% < 30% threshold
    assert report.status == "pass"


def test_validate_warns_high_null_rate(tmp_path):
    raw = pl.DataFrame({"name": ["Alice", None, None, None, None]})
    clean = pl.DataFrame({"name": ["Alice", None, None, None, None]})
    report = validate_file(tmp_path / "test.csv", raw, clean)
    assert report.status == "warn"
    assert any("null" in w.lower() for w in report.warnings)
    assert abs(report.null_summary["name"] - 0.8) < 0.01


def test_validate_warns_invalid_date_column(tmp_path):
    raw = pl.DataFrame({"start_date": ["01/05/2024", "02/06/2024", "03/07/2024"]})
    clean = pl.DataFrame({"start_date": ["01/05/2024", "02/06/2024", "03/07/2024"]})
    report = validate_file(tmp_path / "test.csv", raw, clean)
    assert report.status == "warn"
    assert any("start_date" in w for w in report.warnings)


def test_validate_no_warn_iso_date_column(tmp_path):
    raw = pl.DataFrame({"start_date": ["2024-01-05", "2024-02-06"], "name": ["a", "b"]})
    clean = pl.DataFrame({"start_date": ["2024-01-05", "2024-02-06"], "name": ["a", "b"]})
    report = validate_file(tmp_path / "test.csv", raw, clean)
    assert report.status == "pass"


def test_validate_report_serialises(tmp_path):
    raw = pl.DataFrame({"x": ["1", "2"]})
    clean = pl.DataFrame({"x": [1, 2]})
    report = validate_file(tmp_path / "test.csv", raw, clean)
    data = json.loads(report.model_dump_json())
    assert "status" in data
    assert "issues" in data
    assert "warnings" in data
    assert "null_summary" in data
    assert "run_timestamp" in data


# --- CLI integration tests ---

def test_validate_command_writes_json_and_passes(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "data.csv"
    f.write_text("name,score\nAlice,90\nBob,80\n")

    result = runner.invoke(app, ["validate", str(f)])

    assert result.exit_code == 0, result.output
    assert "PASS" in result.output
    report_path = tmp_path / "outputs" / "data_validation.json"
    assert report_path.exists()
    data = json.loads(report_path.read_text())
    assert data["status"] == "pass"


def test_validate_command_exits_1_on_fail(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "empty.csv"
    f.write_text("name,score\n")  # header only — 0 data rows

    result = runner.invoke(app, ["validate", str(f)])

    assert result.exit_code == 1
    assert "FAIL" in result.output


def test_validate_command_required_flag(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "data.csv"
    f.write_text("name,score\nAlice,90\n")

    result = runner.invoke(app, ["validate", str(f), "--require", "grade"])

    assert result.exit_code == 1
    assert "grade" in result.output


def test_run_with_validate_flag_writes_report(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    folder = tmp_path / "incoming"
    folder.mkdir()
    (folder / "good.csv").write_text("name,score\nAlice,90\nBob,80\n")

    result = runner.invoke(app, ["run", str(folder), "--validate"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "outputs" / "good_validation.json").exists()
    assert "Validation:" in result.output


def test_run_validate_counts_failures_in_summary(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    folder = tmp_path / "incoming"
    folder.mkdir()
    (folder / "good.csv").write_text("name,score\nAlice,90\nBob,80\n")
    (folder / "empty.csv").write_text("name,score\n")  # 0 rows -> validation fail

    result = runner.invoke(app, ["run", str(folder), "--validate"])

    assert result.exit_code == 0, result.output
    summary = json.loads((tmp_path / "outputs" / "run_summary.json").read_text())
    assert summary["files_failed_validation"] == 1
