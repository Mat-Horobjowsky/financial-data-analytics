import polars as pl
import pytest
from pathlib import Path
from typer.testing import CliRunner

from intake_engine.cleaner.column_map import apply_column_selection
from intake_engine.cli.main import app

runner = CliRunner()


# --- unit: apply_column_selection ---

def test_basic_selection_keeps_only_specified():
    df = pl.DataFrame({"a": [1], "b": [2], "c": [3]})
    result = apply_column_selection(df, ["a", "c"])
    assert result.columns == ["a", "c"]


def test_selection_respects_order():
    df = pl.DataFrame({"a": [1], "b": [2], "c": [3]})
    result = apply_column_selection(df, ["c", "a"])
    assert result.columns == ["c", "a"]


def test_missing_column_is_skipped():
    df = pl.DataFrame({"a": [1], "b": [2]})
    result = apply_column_selection(df, ["a", "z"])
    assert result.columns == ["a"]


def test_all_missing_returns_original():
    df = pl.DataFrame({"a": [1], "b": [2]})
    result = apply_column_selection(df, ["x", "y"])
    assert result.columns == ["a", "b"]


def test_empty_list_returns_all_columns():
    df = pl.DataFrame({"a": [1], "b": [2], "c": [3]})
    result = apply_column_selection(df, [])
    assert result.columns == ["a", "b", "c"]


def test_values_are_preserved():
    df = pl.DataFrame({"a": [10, 20], "b": [30, 40], "c": [50, 60]})
    result = apply_column_selection(df, ["b", "a"])
    assert result["b"].to_list() == [30, 40]
    assert result["a"].to_list() == [10, 20]


# --- CLI: select_columns from YAML config ---

def test_cli_select_columns_from_yaml(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data.csv").write_text("name,score,notes\nAlice,90,good\nBob,80,ok\n")
    cfg = tmp_path / "pipeline.yaml"
    cfg.write_text("select_columns:\n  - name\n  - score\n")

    result = runner.invoke(app, ["run", "data.csv", "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    import csv as _csv
    out = (tmp_path / "outputs" / "data_clean.csv").read_text()
    header = next(_csv.reader(out.splitlines()))
    assert header == ["name", "score"]
    assert "notes" not in out


def test_cli_select_columns_ordering_preserved(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data.csv").write_text("a,b,c\n1,2,3\n")
    cfg = tmp_path / "pipeline.yaml"
    cfg.write_text("select_columns:\n  - c\n  - a\n")

    result = runner.invoke(app, ["run", "data.csv", "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    import csv as _csv
    out = (tmp_path / "outputs" / "data_clean.csv").read_text()
    header = next(_csv.reader(out.splitlines()))
    assert header == ["c", "a"]


def test_cli_no_select_columns_exports_all(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data.csv").write_text("a,b,c\n1,2,3\n")

    result = runner.invoke(app, ["run", "data.csv"])

    assert result.exit_code == 0, result.output
    import csv as _csv
    out = (tmp_path / "outputs" / "data_clean.csv").read_text()
    header = next(_csv.reader(out.splitlines()))
    assert set(header) == {"a", "b", "c"}


def test_cli_select_columns_with_rename(tmp_path, monkeypatch):
    """Column selected by its post-rename name."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data.csv").write_text("Total Revenue,Cost\n100,40\n")
    cfg = tmp_path / "pipeline.yaml"
    cfg.write_text(
        "columns:\n"
        "  Total Revenue:\n"
        "    rename: revenue\n"
        "select_columns:\n"
        "  - revenue\n"
    )

    result = runner.invoke(app, ["run", "data.csv", "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    import csv as _csv
    out = (tmp_path / "outputs" / "data_clean.csv").read_text()
    header = next(_csv.reader(out.splitlines()))
    assert header == ["revenue"]
    assert "cost" not in out.lower()


def test_cli_select_missing_column_still_succeeds(tmp_path, monkeypatch):
    """Missing column in select_columns is skipped without error."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data.csv").write_text("a,b\n1,2\n")
    cfg = tmp_path / "pipeline.yaml"
    cfg.write_text("select_columns:\n  - a\n  - does_not_exist\n")

    result = runner.invoke(app, ["run", "data.csv", "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    import csv as _csv
    out = (tmp_path / "outputs" / "data_clean.csv").read_text()
    header = next(_csv.reader(out.splitlines()))
    assert header == ["a"]
