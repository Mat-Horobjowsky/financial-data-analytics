"""Tests for Excel multi-sheet support."""
import json
from pathlib import Path

import openpyxl
import polars as pl
import pytest
from typer.testing import CliRunner

from intake_engine.cli.main import app
from intake_engine.loader.loader import list_excel_sheets, load_file
from intake_engine.utils.errors import LoadError

runner = CliRunner()


# --- fixtures ---

def _make_workbook(path: Path, sheets: dict[str, list[list]]) -> Path:
    """Create an .xlsx file with named sheets. Each sheet value is rows (header first)."""
    wb = openpyxl.Workbook()
    first = True
    for sheet_name, rows in sheets.items():
        if first:
            ws = wb.active
            ws.title = sheet_name
            first = False
        else:
            ws = wb.create_sheet(sheet_name)
        for row in rows:
            ws.append(row)
    wb.save(path)
    return path


# --- list_excel_sheets ---

def test_list_sheets_returns_names_in_order(tmp_path):
    wb_path = _make_workbook(tmp_path / "wb.xlsx", {
        "Sales": [["name", "revenue"], ["Alice", 100]],
        "Costs": [["name", "cost"], ["Bob", 50]],
        "Summary": [["metric", "value"], ["total", 150]],
    })
    sheets = list_excel_sheets(wb_path)
    assert sheets == ["Sales", "Costs", "Summary"]


def test_list_sheets_single_sheet(tmp_path):
    wb_path = _make_workbook(tmp_path / "wb.xlsx", {
        "Sheet1": [["a", "b"], [1, 2]],
    })
    assert list_excel_sheets(wb_path) == ["Sheet1"]


def test_list_sheets_not_found_raises(tmp_path):
    with pytest.raises(LoadError, match="File not found"):
        list_excel_sheets(tmp_path / "missing.xlsx")


# --- load_file with sheet param ---

def test_load_file_default_loads_first_sheet(tmp_path):
    wb_path = _make_workbook(tmp_path / "wb.xlsx", {
        "Sales": [["name", "revenue"], ["Alice", 100], ["Bob", 200]],
        "Costs": [["name", "cost"], ["Carol", 50]],
    })
    df = load_file(wb_path)
    assert df.shape == (2, 2)
    assert "revenue" in df.columns


def test_load_file_named_sheet(tmp_path):
    wb_path = _make_workbook(tmp_path / "wb.xlsx", {
        "Sales": [["name", "revenue"], ["Alice", 100]],
        "Costs": [["name", "cost"], ["Bob", 50], ["Carol", 30]],
    })
    df = load_file(wb_path, sheet="Costs")
    assert df.shape == (2, 2)
    assert "cost" in df.columns


def test_load_file_invalid_sheet_raises(tmp_path):
    wb_path = _make_workbook(tmp_path / "wb.xlsx", {
        "Sheet1": [["a"], [1]],
    })
    with pytest.raises(LoadError, match="NoSuchSheet"):
        load_file(wb_path, sheet="NoSuchSheet")


def test_load_file_sheet_none_and_sheet_name_same_data(tmp_path):
    wb_path = _make_workbook(tmp_path / "wb.xlsx", {
        "Data": [["x", "y"], [1, 2], [3, 4]],
    })
    df_default = load_file(wb_path)
    df_named = load_file(wb_path, sheet="Data")
    assert df_default.equals(df_named)


# --- CLI: single file named sheet ---

def test_cli_sheet_loads_named_sheet(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    wb_path = _make_workbook(tmp_path / "report.xlsx", {
        "Sales": [["name", "revenue"], ["Alice", 100], ["Bob", 200]],
        "Costs": [["name", "cost"], ["Carol", 50]],
    })

    result = runner.invoke(app, ["run", str(wb_path), "--sheet", "Costs"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "outputs" / "report_costs_clean.csv").exists()
    df = pl.read_csv(tmp_path / "outputs" / "report_costs_clean.csv")
    assert df.shape[0] == 1
    assert "cost" in df.columns


def test_cli_sheet_output_includes_sheet_name_in_stem(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    wb_path = _make_workbook(tmp_path / "Q1.xlsx", {
        "Sales Data": [["name", "revenue"], ["Alice", 100]],
    })

    result = runner.invoke(app, ["run", str(wb_path), "--sheet", "Sales Data"])

    assert result.exit_code == 0, result.output
    # "Sales Data" → to_snake → "sales_data"
    assert (tmp_path / "outputs" / "Q1_sales_data_clean.csv").exists()


def test_cli_no_sheet_backward_compat(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    wb_path = _make_workbook(tmp_path / "data.xlsx", {
        "Sheet1": [["name", "score"], ["Alice", 90]],
    })

    result = runner.invoke(app, ["run", str(wb_path)])

    assert result.exit_code == 0, result.output
    # no sheet → original stem, no sheet suffix
    assert (tmp_path / "outputs" / "data_clean.csv").exists()


# --- CLI: --sheet all (single file) ---

def test_cli_sheet_all_creates_output_per_sheet(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    wb_path = _make_workbook(tmp_path / "report.xlsx", {
        "Sales": [["name", "revenue"], ["Alice", 100], ["Bob", 200]],
        "Costs": [["name", "cost"], ["Carol", 50]],
    })

    result = runner.invoke(app, ["run", str(wb_path), "--sheet", "all"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "outputs" / "report_sales_clean.csv").exists()
    assert (tmp_path / "outputs" / "report_costs_clean.csv").exists()


def test_cli_sheet_all_row_counts_correct(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    wb_path = _make_workbook(tmp_path / "wb.xlsx", {
        "A": [["x"], [1], [2], [3]],
        "B": [["x"], [10]],
    })

    result = runner.invoke(app, ["run", str(wb_path), "--sheet", "all"])

    assert result.exit_code == 0, result.output
    df_a = pl.read_csv(tmp_path / "outputs" / "wb_a_clean.csv")
    df_b = pl.read_csv(tmp_path / "outputs" / "wb_b_clean.csv")
    assert df_a.shape[0] == 3
    assert df_b.shape[0] == 1


def test_cli_sheet_all_summary_line(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    wb_path = _make_workbook(tmp_path / "wb.xlsx", {
        "Alpha": [["x"], [1]],
        "Beta": [["x"], [2]],
    })

    result = runner.invoke(app, ["run", str(wb_path), "--sheet", "all"])

    assert "2 sheets" in result.output


# --- CLI: --sheet all (batch folder) ---

def test_cli_batch_sheet_all_creates_tables_per_sheet(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    folder = tmp_path / "incoming"
    folder.mkdir()
    _make_workbook(folder / "report.xlsx", {
        "Sales": [["name", "rev"], ["Alice", 100]],
        "Costs": [["name", "cost"], ["Bob", 50]],
    })
    (folder / "extra.csv").write_text("name,score\nCarol,70\n")

    result = runner.invoke(app, ["run", str(folder), "--sheet", "all"])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "outputs" / "report_sales_clean.csv").exists()
    assert (tmp_path / "outputs" / "report_costs_clean.csv").exists()
    assert (tmp_path / "outputs" / "extra_clean.csv").exists()


def test_cli_batch_sheet_all_summary_says_items(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    folder = tmp_path / "incoming"
    folder.mkdir()
    _make_workbook(folder / "wb.xlsx", {
        "A": [["x"], [1]],
        "B": [["x"], [2]],
    })

    result = runner.invoke(app, ["run", str(folder), "--sheet", "all"])

    assert result.exit_code == 0, result.output
    assert "items" in result.output


# --- CLI: config sheet setting ---

def test_config_sheet_loads_named_sheet(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    wb_path = _make_workbook(tmp_path / "data.xlsx", {
        "Summary": [["metric", "value"], ["rev", 999]],
        "Detail": [["name", "score"], ["Alice", 90]],
    })
    cfg = tmp_path / "pipeline.yaml"
    cfg.write_text("sheet: Detail\n")

    result = runner.invoke(app, ["run", str(wb_path), "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "outputs" / "data_detail_clean.csv").exists()
    df = pl.read_csv(tmp_path / "outputs" / "data_detail_clean.csv")
    assert "score" in df.columns
