import pandas as pd
import pytest

from metrics_engine.loader import LoaderError, load


def test_csv_loads(sample_csv_path):
    df = load(sample_csv_path)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 12
    assert "date" in df.columns


def test_excel_loads(tmp_path):
    excel_path = tmp_path / "test.xlsx"
    pd.DataFrame({"a": [1, 2], "b": [3, 4]}).to_excel(excel_path, index=False)
    df = load(excel_path)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 2
    assert list(df.columns) == ["a", "b"]


def test_missing_file_raises():
    with pytest.raises(LoaderError, match="File not found"):
        load("nonexistent_file.csv")


def test_unsupported_extension_raises(tmp_path):
    bad = tmp_path / "data.json"
    bad.write_text('{"a": 1}')
    with pytest.raises(LoaderError, match="Unsupported file type"):
        load(bad)


def test_xls_extension_raises(tmp_path):
    # .xls is explicitly unsupported in v1; xlrd is not a dependency
    bad = tmp_path / "data.xls"
    bad.write_text("fake xls content")
    with pytest.raises(LoaderError, match="Unsupported file type"):
        load(bad)


def test_empty_csv_raises(tmp_path):
    empty = tmp_path / "empty.csv"
    empty.write_text("")
    with pytest.raises(LoaderError, match="empty"):
        load(empty)


def test_headers_only_csv_raises(tmp_path):
    headers_only = tmp_path / "headers.csv"
    headers_only.write_text("date,revenue,capacity_mw\n")
    with pytest.raises(LoaderError, match="empty"):
        load(headers_only)


def test_raw_df_is_unmodified(sample_csv_path):
    df = load(sample_csv_path)
    # loader must not rename or cast — raw column names come through as-is
    assert "date" in df.columns
    assert "revenue" in df.columns
    assert df["revenue"].dtype != "object"
