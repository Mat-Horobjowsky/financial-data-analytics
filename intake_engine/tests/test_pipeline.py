import json
from pathlib import Path

import polars as pl
import pytest
from typer.testing import CliRunner

from intake_engine.cli.main import app
from intake_engine.models.config import PipelineConfig, load_config
from intake_engine.validator.validator import validate_file

runner = CliRunner()


# --- PipelineConfig unit tests ---

def test_config_defaults():
    cfg = PipelineConfig()
    assert cfg.output_format == "csv"
    assert cfg.output_dir == "outputs"
    assert cfg.run_validate is False
    assert cfg.null_threshold == 0.3
    assert cfg.duplicate_threshold == 0.3
    assert cfg.required_columns == []


def test_load_config_from_yaml(tmp_path):
    f = tmp_path / "pipeline.yaml"
    f.write_text(
        "output_format: parquet\n"
        "output_dir: clean/\n"
        "run_validate: true\n"
        "null_threshold: 0.1\n"
        "required_columns:\n  - site_name\n  - revenue\n"
    )
    cfg = load_config(f)
    assert cfg.output_format == "parquet"
    assert cfg.output_dir == "clean/"
    assert cfg.run_validate is True
    assert cfg.null_threshold == 0.1
    assert cfg.required_columns == ["site_name", "revenue"]


def test_load_config_missing_file_raises(tmp_path):
    with pytest.raises(Exception):
        load_config(tmp_path / "nonexistent.yaml")


def test_load_config_empty_yaml_uses_defaults(tmp_path):
    f = tmp_path / "pipeline.yaml"
    f.write_text("")
    cfg = load_config(f)
    assert cfg.output_format == "csv"
    assert cfg.run_validate is False


# --- validator threshold tests ---

def test_validate_custom_null_threshold_warns_at_lower_rate(tmp_path):
    # 40% null — above custom threshold of 0.2 but would pass at default 0.3
    raw = pl.DataFrame({"name": ["A", "B", None, None, "E"], "score": [1, 2, 3, 4, 5]})
    clean = pl.DataFrame({"name": ["A", "B", None, None, "E"], "score": [1, 2, 3, 4, 5]})
    report = validate_file(tmp_path / "test.csv", raw, clean, null_threshold=0.2)
    assert report.status == "warn"
    assert any("null rate" in w for w in report.warnings)


def test_validate_default_null_threshold_does_not_warn(tmp_path):
    # 20% null — below default threshold of 0.3
    raw = pl.DataFrame({"name": ["A", None, "C", None, "E"], "score": [1, 2, 3, 4, 5]})
    # only 1 null in name out of 5 = 20%
    raw = pl.DataFrame({"name": ["A", "B", None, "D", "E"], "score": [1, 2, 3, 4, 5]})
    clean = raw
    report = validate_file(tmp_path / "test.csv", raw, clean)
    null_warnings = [w for w in report.warnings if "null rate" in w]
    assert len(null_warnings) == 0


def test_validate_custom_dup_threshold_no_warn(tmp_path):
    # 50% dup rate — above default 0.3 but below custom 0.6
    raw = pl.DataFrame({"name": ["A", "A", "B", "B"], "score": [1, 1, 2, 2]})
    clean = pl.DataFrame({"name": ["A", "B"], "score": [1, 2]})
    report = validate_file(tmp_path / "test.csv", raw, clean, duplicate_threshold=0.6)
    dup_warnings = [w for w in report.warnings if "duplicate" in w.lower()]
    assert len(dup_warnings) == 0


def test_validate_custom_dup_threshold_warns(tmp_path):
    # 50% dup rate — triggers warn at tight threshold 0.2
    raw = pl.DataFrame({"name": ["A", "A", "B", "B"], "score": [1, 1, 2, 2]})
    clean = pl.DataFrame({"name": ["A", "B"], "score": [1, 2]})
    report = validate_file(tmp_path / "test.csv", raw, clean, duplicate_threshold=0.2)
    assert report.status == "warn"
    assert any("duplicate" in w.lower() for w in report.warnings)


# --- --output-dir tests ---

def test_run_single_file_output_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "data.csv"
    f.write_text("name,score\nAlice,90\nBob,80\n")
    custom = tmp_path / "clean"

    result = runner.invoke(app, ["run", str(f), "--output-dir", str(custom)])

    assert result.exit_code == 0, result.output
    assert (custom / "data_clean.csv").exists()
    assert not (tmp_path / "outputs" / "data_clean.csv").exists()


def test_batch_output_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    folder = tmp_path / "incoming"
    folder.mkdir()
    (folder / "a.csv").write_text("name,score\nAlice,90\n")
    custom = tmp_path / "results"

    result = runner.invoke(app, ["run", str(folder), "--output-dir", str(custom)])

    assert result.exit_code == 0, result.output
    assert (custom / "a_clean.csv").exists()
    assert (custom / "run_summary.json").exists()


def test_validate_cmd_output_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "data.csv"
    f.write_text("name,score\nAlice,90\nBob,80\n")
    custom = tmp_path / "reports"

    result = runner.invoke(app, ["validate", str(f), "--output-dir", str(custom)])

    assert result.exit_code == 0, result.output
    assert (custom / "data_validation.json").exists()
    assert (custom / "data_report.html").exists()


def test_profile_cmd_output_dir(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "data.csv"
    f.write_text("name,score\nAlice,90\nBob,80\n")
    custom = tmp_path / "reports"

    result = runner.invoke(app, ["profile", str(f), "--output-dir", str(custom)])

    assert result.exit_code == 0, result.output
    assert (custom / "data_profile.json").exists()
    assert (custom / "data_report.html").exists()


# --- --format tests ---

def test_format_parquet_single_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "data.csv"
    f.write_text("name,score\nAlice,90\nBob,80\n")

    result = runner.invoke(app, ["run", str(f), "--format", "parquet"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "outputs" / "data_clean.parquet").exists()
    assert not (tmp_path / "outputs" / "data_clean.csv").exists()


def test_format_csv_is_default(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "data.csv"
    f.write_text("name,score\nAlice,90\nBob,80\n")

    result = runner.invoke(app, ["run", str(f)])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "outputs" / "data_clean.csv").exists()


def test_format_invalid_exits_1(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "data.csv"
    f.write_text("name,score\nAlice,90\n")

    result = runner.invoke(app, ["run", str(f), "--format", "excel"])

    assert result.exit_code == 1


def test_format_parquet_batch(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    folder = tmp_path / "incoming"
    folder.mkdir()
    (folder / "a.csv").write_text("name,score\nAlice,90\n")
    (folder / "b.csv").write_text("name,score\nBob,80\n")

    result = runner.invoke(app, ["run", str(folder), "--format", "parquet"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "outputs" / "a_clean.parquet").exists()
    assert (tmp_path / "outputs" / "b_clean.parquet").exists()


# --- --config tests ---

def test_config_output_dir_applied(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "data.csv"
    f.write_text("name,score\nAlice,90\n")
    cfg_file = tmp_path / "pipeline.yaml"
    cfg_file.write_text("output_dir: myout\n")

    result = runner.invoke(app, ["run", str(f), "--config", str(cfg_file)])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "myout" / "data_clean.csv").exists()


def test_config_output_format_parquet(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "data.csv"
    f.write_text("name,score\nAlice,90\n")
    cfg_file = tmp_path / "pipeline.yaml"
    cfg_file.write_text("output_format: parquet\n")

    result = runner.invoke(app, ["run", str(f), "--config", str(cfg_file)])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "outputs" / "data_clean.parquet").exists()


def test_config_validate_true_runs_validation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "data.csv"
    f.write_text("name,score\nAlice,90\nBob,80\n")
    cfg_file = tmp_path / "pipeline.yaml"
    cfg_file.write_text("run_validate: true\n")

    result = runner.invoke(app, ["run", str(f), "--config", str(cfg_file)])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "outputs" / "data_validation.json").exists()


def test_config_required_columns_triggers_fail(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "data.csv"
    f.write_text("name,score\nAlice,90\n")
    cfg_file = tmp_path / "pipeline.yaml"
    cfg_file.write_text("run_validate: true\nrequired_columns:\n  - revenue\n")

    result = runner.invoke(app, ["run", str(f), "--config", str(cfg_file)])

    assert result.exit_code == 0, result.output  # run itself succeeds; validation status is in JSON
    report = json.loads((tmp_path / "outputs" / "data_validation.json").read_text())
    assert any("revenue" in i for i in report["issues"])
    assert report["status"] == "fail"


def test_config_missing_file_exits_1(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "data.csv"
    f.write_text("name,score\nAlice,90\n")

    result = runner.invoke(app, ["run", str(f), "--config", str(tmp_path / "ghost.yaml")])

    assert result.exit_code == 1


def test_cli_format_overrides_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "data.csv"
    f.write_text("name,score\nAlice,90\n")
    cfg_file = tmp_path / "pipeline.yaml"
    cfg_file.write_text("output_format: parquet\n")

    result = runner.invoke(app, ["run", str(f), "--config", str(cfg_file), "--format", "csv"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "outputs" / "data_clean.csv").exists()
    assert not (tmp_path / "outputs" / "data_clean.parquet").exists()


def test_cli_output_dir_overrides_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "data.csv"
    f.write_text("name,score\nAlice,90\n")
    cfg_file = tmp_path / "pipeline.yaml"
    cfg_file.write_text("output_dir: config_out\n")

    result = runner.invoke(app, ["run", str(f), "--config", str(cfg_file),
                                  "--output-dir", str(tmp_path / "cli_out")])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "cli_out" / "data_clean.csv").exists()
    assert not (tmp_path / "config_out" / "data_clean.csv").exists()


# --- block_export_on_fail / --fail-on-validation tests ---

def test_fail_on_validation_config_blocks_export(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "data.csv"
    f.write_text("name,score\nAlice,90\n")
    cfg_file = tmp_path / "pipeline.yaml"
    cfg_file.write_text("run_validate: true\nblock_export_on_fail: true\nrequired_columns:\n  - revenue\n")

    result = runner.invoke(app, ["run", str(f), "--config", str(cfg_file)])

    assert result.exit_code == 0, result.output
    assert not (tmp_path / "outputs" / "data_clean.csv").exists()
    assert (tmp_path / "outputs" / "data_validation.json").exists()


def test_fail_on_validation_cli_flag_blocks_export(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "data.csv"
    f.write_text("name,score\nAlice,90\n")

    result = runner.invoke(app, ["run", str(f), "--fail-on-validation", "--require", "revenue"])

    assert result.exit_code == 0, result.output
    assert not (tmp_path / "outputs" / "data_clean.csv").exists()
    assert (tmp_path / "outputs" / "data_validation.json").exists()


def test_fail_on_validation_pass_still_exports(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "data.csv"
    f.write_text("name,score\nAlice,90\nBob,80\n")

    result = runner.invoke(app, ["run", str(f), "--fail-on-validation"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "outputs" / "data_clean.csv").exists()


def test_fail_on_validation_blocked_output_in_summary(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "data.csv"
    f.write_text("name,score\nAlice,90\n")

    result = runner.invoke(app, ["run", str(f), "--fail-on-validation", "--require", "revenue"])

    assert "BLOCKED" in result.output
    assert "FAIL" in result.output


def test_fail_on_validation_batch_blocks_failing_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    folder = tmp_path / "incoming"
    folder.mkdir()
    (folder / "good.csv").write_text("name,revenue\nAlice,100\n")
    (folder / "bad.csv").write_text("name,score\nBob,80\n")
    cfg_file = tmp_path / "pipeline.yaml"
    cfg_file.write_text("block_export_on_fail: true\nrequired_columns:\n  - revenue\n")

    result = runner.invoke(app, ["run", str(folder), "--config", str(cfg_file)])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "outputs" / "good_clean.csv").exists()
    assert not (tmp_path / "outputs" / "bad_clean.csv").exists()
    summary = json.loads((tmp_path / "outputs" / "run_summary.json").read_text())
    assert summary["files_export_blocked"] == 1


# --- date warning text ---

def test_date_warning_new_text(tmp_path):
    raw = pl.DataFrame({"created_date": ["01/01/2024", "02/15/2024", "03/20/2024"]})
    report = validate_file(tmp_path / "test.csv", raw, raw)
    date_warns = [w for w in report.warnings if "created_date" in w]
    assert any("mixed valid/invalid date values remain after cleaning" in w for w in date_warns)
    assert not any("normalize_dates" in w for w in date_warns)


# --- duplicate warning requires >= 2 duplicate rows ---

def test_dup_warning_suppressed_for_single_duplicate(tmp_path):
    # 1 dup out of 2 rows = 50% rate, but only 1 dup — no warning
    raw = pl.DataFrame({"name": ["A", "A"], "score": [1, 1]})
    clean = pl.DataFrame({"name": ["A"], "score": [1]})
    report = validate_file(tmp_path / "test.csv", raw, clean, duplicate_threshold=0.1)
    dup_warnings = [w for w in report.warnings if "duplicate" in w.lower()]
    assert len(dup_warnings) == 0


def test_dup_warning_fires_with_two_or_more_duplicates(tmp_path):
    # 2 dups out of 4 rows = 50% rate, 2 dups — should warn
    raw = pl.DataFrame({"name": ["A", "A", "B", "B"], "score": [1, 1, 2, 2]})
    clean = pl.DataFrame({"name": ["A", "B"], "score": [1, 2]})
    report = validate_file(tmp_path / "test.csv", raw, clean, duplicate_threshold=0.1)
    dup_warnings = [w for w in report.warnings if "duplicate" in w.lower()]
    assert len(dup_warnings) > 0


# --- final run summary ===...=== line ---

def test_run_single_prints_final_summary(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "data.csv"
    f.write_text("name,score\nAlice,90\nBob,80\n")

    result = runner.invoke(app, ["run", str(f)])

    assert result.exit_code == 0
    assert "===" in result.output


def test_run_single_validation_summary_includes_status(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "data.csv"
    f.write_text("name,score\nAlice,90\nBob,80\n")

    result = runner.invoke(app, ["run", str(f), "--validate"])

    assert result.exit_code == 0
    assert "=== PASS" in result.output


def test_run_batch_prints_final_summary(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    folder = tmp_path / "incoming"
    folder.mkdir()
    (folder / "a.csv").write_text("name,score\nAlice,90\n")

    result = runner.invoke(app, ["run", str(folder)])

    assert result.exit_code == 0
    assert "=== Batch:" in result.output


# --- config defaults include block_export_on_fail ---

def test_config_defaults_include_block_export_on_fail():
    from intake_engine.models.config import PipelineConfig
    cfg = PipelineConfig()
    assert cfg.block_export_on_fail is False


# --- rename-aware required_columns ---

def test_required_column_renamed_produces_warning_not_fail(tmp_path):
    # clean_headers renames "Site Name" → "site_name"; validator should warn, not fail
    clean = pl.DataFrame({"site_name": ["Alpha", "Beta"], "score": [1, 2]})
    report = validate_file(tmp_path / "test.csv", clean, clean, required_columns=["Site Name"])
    assert report.status != "fail"
    assert any("renamed" in w and "site_name" in w for w in report.warnings)
    assert not any("missing" in i for i in report.issues)


def test_required_column_renamed_message_contains_snake_name(tmp_path):
    clean = pl.DataFrame({"revenue_usd": [100, 200]})
    report = validate_file(tmp_path / "test.csv", clean, clean, required_columns=["Revenue (USD)"])
    assert any("revenue_usd" in w for w in report.warnings)
    assert any("Revenue (USD)" in w for w in report.warnings)


def test_required_column_genuinely_missing_still_fails(tmp_path):
    clean = pl.DataFrame({"name": ["A"], "score": [1]})
    report = validate_file(tmp_path / "test.csv", clean, clean, required_columns=["revenue"])
    assert report.status == "fail"
    assert any("revenue" in i for i in report.issues)


def test_required_column_correct_snake_case_passes_cleanly(tmp_path):
    clean = pl.DataFrame({"site_name": ["A"], "score": [1]})
    report = validate_file(tmp_path / "test.csv", clean, clean, required_columns=["site_name"])
    assert not any("site_name" in i for i in report.issues)
    assert not any("renamed" in w for w in report.warnings)


def test_required_column_mixed_renamed_and_missing(tmp_path):
    # "Site Name" → renamed to "site_name" (warn); "revenue" → genuinely missing (fail)
    clean = pl.DataFrame({"site_name": ["A"], "score": [1]})
    report = validate_file(
        tmp_path / "test.csv", clean, clean,
        required_columns=["Site Name", "revenue"],
    )
    assert report.status == "fail"
    assert any("renamed" in w for w in report.warnings)
    assert any("revenue" in i for i in report.issues)


def test_required_column_rename_hyphen_separator(tmp_path):
    # "start-date" → "start_date"
    clean = pl.DataFrame({"start_date": ["2024-01-01"]})
    report = validate_file(tmp_path / "test.csv", clean, clean, required_columns=["start-date"])
    assert report.status != "fail"
    assert any("start_date" in w for w in report.warnings)


def test_cli_required_column_original_case_warns_not_fails(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "data.csv"
    f.write_text("Site Name,Revenue\nAlpha,100\nBeta,200\n")
    cfg_file = tmp_path / "pipeline.yaml"
    cfg_file.write_text("run_validate: true\nrequired_columns:\n  - Site Name\n  - Revenue\n")

    result = runner.invoke(app, ["run", str(f), "--config", str(cfg_file)])

    assert result.exit_code == 0, result.output
    report = json.loads((tmp_path / "outputs" / "data_validation.json").read_text())
    assert report["status"] != "fail"
    assert any("renamed" in w for w in report["warnings"])
