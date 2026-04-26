"""Tests for column mapping and column-level config rules."""
from pathlib import Path

import polars as pl
import pytest
from typer.testing import CliRunner

from intake_engine.cleaner import apply_column_map
from intake_engine.cleaner.cleaner import clean
from intake_engine.cli.main import app
from intake_engine.models.config import ColumnRule, load_config
from intake_engine.validator.validator import validate_file

runner = CliRunner()


# --- apply_column_map ---

def test_rename_by_exact_snake_key():
    df = pl.DataFrame({"total_revenue": [100], "name": ["Alice"]})
    rules = {"total_revenue": ColumnRule(rename="revenue")}
    result = apply_column_map(df, rules)
    assert "revenue" in result.columns
    assert "total_revenue" not in result.columns


def test_rename_by_original_unsnakedname():
    """Config key uses original header capitalisation; still resolved via to_snake."""
    df = pl.DataFrame({"total_revenue": [100]})
    rules = {"Total Revenue": ColumnRule(rename="revenue")}
    result = apply_column_map(df, rules)
    assert "revenue" in result.columns


def test_rename_multiple_columns():
    df = pl.DataFrame({"rev": [1], "cst": [2]})
    rules = {"rev": ColumnRule(rename="revenue"), "cst": ColumnRule(rename="cost")}
    result = apply_column_map(df, rules)
    assert set(result.columns) == {"revenue", "cost"}


def test_rename_nonexistent_key_ignored():
    df = pl.DataFrame({"name": ["Alice"]})
    rules = {"ghost_col": ColumnRule(rename="x")}
    result = apply_column_map(df, rules)
    assert result.columns == ["name"]


def test_rule_without_rename_leaves_column_unchanged():
    df = pl.DataFrame({"revenue": [100]})
    rules = {"revenue": ColumnRule(type="numeric")}
    result = apply_column_map(df, rules)
    assert result.columns == ["revenue"]


def test_empty_rules_returns_df_unchanged():
    df = pl.DataFrame({"a": [1], "b": [2]})
    assert apply_column_map(df, {}).columns == ["a", "b"]


# --- validate_file: type checks ---

def test_type_check_numeric_passes():
    df = pl.DataFrame({"revenue": [100, 200]})
    rules = {"revenue": ColumnRule(type="numeric")}
    report = validate_file(Path("f.csv"), df, df, column_rules=rules)
    assert not any("expected type" in w for w in report.warnings)


def test_type_check_warns_on_string_when_numeric_expected():
    df = pl.DataFrame({"revenue": ["a", "b"]})
    rules = {"revenue": ColumnRule(type="numeric")}
    report = validate_file(Path("f.csv"), df, df, column_rules=rules)
    assert any("expected type 'numeric'" in w for w in report.warnings)


def test_type_check_date_passes():
    import datetime
    df = pl.DataFrame({"event_date": pl.Series(["2024-01-01"]).str.to_date()})
    rules = {"event_date": ColumnRule(type="date")}
    report = validate_file(Path("f.csv"), df, df, column_rules=rules)
    assert not any("expected type" in w for w in report.warnings)


def test_type_check_string_passes():
    df = pl.DataFrame({"notes": ["hello", "world"]})
    rules = {"notes": ColumnRule(type="string")}
    report = validate_file(Path("f.csv"), df, df, column_rules=rules)
    assert not any("expected type" in w for w in report.warnings)


def test_type_check_resolves_original_name():
    """Rule keyed by original header still resolves to the snake_cased column."""
    df = pl.DataFrame({"total_revenue": [100, 200]})
    rules = {"Total Revenue": ColumnRule(type="numeric")}
    report = validate_file(Path("f.csv"), df, df, column_rules=rules)
    assert not any("expected type" in w for w in report.warnings)


# --- validate_file: nullable checks ---

def test_nullable_false_warns_when_nulls_present():
    df = pl.DataFrame({"id": [1, None, 3]})
    rules = {"id": ColumnRule(nullable=False)}
    report = validate_file(Path("f.csv"), df, df, column_rules=rules)
    assert any("nullable: false" in w for w in report.warnings)


def test_nullable_false_no_warning_when_clean():
    df = pl.DataFrame({"id": [1, 2, 3]})
    rules = {"id": ColumnRule(nullable=False)}
    report = validate_file(Path("f.csv"), df, df, column_rules=rules)
    assert not any("nullable" in w for w in report.warnings)


def test_nullable_true_never_warns():
    df = pl.DataFrame({"notes": ["a", None, "c"]})
    rules = {"notes": ColumnRule(nullable=True)}
    report = validate_file(Path("f.csv"), df, df, column_rules=rules)
    assert not any("nullable" in w for w in report.warnings)


def test_rule_for_renamed_column_applies_after_map():
    """Rule keyed by original name, with rename, checks the post-rename column."""
    df = pl.DataFrame({"total_revenue": ["bad", "also_bad"]})
    rules = {"total_revenue": ColumnRule(rename="revenue", type="numeric")}
    mapped = apply_column_map(df, rules)
    assert "revenue" in mapped.columns
    report = validate_file(Path("f.csv"), df, mapped, column_rules=rules)
    assert any("expected type 'numeric'" in w for w in report.warnings)


# --- config YAML parsing ---

def test_config_parses_columns_block(tmp_path):
    (tmp_path / "cfg.yaml").write_text(
        "columns:\n"
        "  total_revenue:\n"
        "    rename: revenue\n"
        "    type: numeric\n"
        "    nullable: false\n"
        "  event_date:\n"
        "    type: date\n"
    )
    cfg = load_config(tmp_path / "cfg.yaml")
    assert "total_revenue" in cfg.columns
    rule = cfg.columns["total_revenue"]
    assert rule.rename == "revenue"
    assert rule.type == "numeric"
    assert rule.nullable is False
    assert cfg.columns["event_date"].type == "date"


def test_config_without_columns_block_defaults_empty(tmp_path):
    (tmp_path / "cfg.yaml").write_text("null_threshold: 0.5\n")
    cfg = load_config(tmp_path / "cfg.yaml")
    assert cfg.columns == {}


# --- backward compatibility ---

def test_required_columns_still_works():
    df = pl.DataFrame({"name": ["Alice"], "revenue": [100]})
    report = validate_file(Path("f.csv"), df, df, required_columns=["name", "revenue"])
    assert report.status == "pass"


def test_required_columns_and_column_rules_coexist():
    df = pl.DataFrame({"name": ["Alice"], "revenue": [100]})
    rules = {"revenue": ColumnRule(type="numeric")}
    report = validate_file(Path("f.csv"), df, df, required_columns=["name"], column_rules=rules)
    assert report.status == "pass"


# --- CLI integration ---

def test_cli_column_map_renames_output(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data.csv").write_text("total_revenue,name\n100,Alice\n200,Bob\n")
    (tmp_path / "cfg.yaml").write_text(
        "columns:\n  total_revenue:\n    rename: revenue\n"
    )
    result = runner.invoke(app, ["run", "data.csv", "--config", "cfg.yaml"])
    assert result.exit_code == 0, result.output
    out = pl.read_csv(tmp_path / "outputs" / "data_clean.csv")
    assert "revenue" in out.columns
    assert "total_revenue" not in out.columns


def test_cli_nullable_false_warn_appears_in_validation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data.csv").write_text("id,name\n1,Alice\n,Bob\n")
    (tmp_path / "cfg.yaml").write_text(
        "run_validate: true\n"
        "columns:\n  id:\n    nullable: false\n"
    )
    result = runner.invoke(app, ["run", "data.csv", "--config", "cfg.yaml"])
    assert result.exit_code == 0, result.output
    assert "nullable" in result.output


def test_cli_type_mismatch_warn_appears_in_validation(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data.csv").write_text("revenue,name\nhello,Alice\nworld,Bob\n")
    (tmp_path / "cfg.yaml").write_text(
        "run_validate: true\n"
        "columns:\n  revenue:\n    type: numeric\n"
    )
    result = runner.invoke(app, ["run", "data.csv", "--config", "cfg.yaml"])
    assert result.exit_code == 0, result.output
    assert "expected type" in result.output
