import datetime
import logging

import polars as pl
import pytest

from intake_engine.cleaner.cleaner import clean
from intake_engine.loader.loader import load_file
from intake_engine.utils.errors import LoadError


# --- load_file integration tests ---

def test_load_csv_clean_file(tmp_path):
    csv = tmp_path / "clean.csv"
    csv.write_text("name,capacity,notes\nAlice,100,standard\nBob,200,standard\n")
    df = load_file(csv)
    assert df.shape == (2, 3)
    assert df["name"].to_list() == ["Alice", "Bob"]


# --- v1.2.2 regression tests: thousands-comma fix ---

def test_date_field_and_next_field_not_merged(tmp_path):
    """03/15/2024,950 must parse as two separate fields, not merge into 03/152024950."""
    csv = tmp_path / "data.csv"
    csv.write_text("name,date,revenue\nAlpha,03/15/2024,950\nBeta,05/20/2024,1200\n")
    df = load_file(csv)
    assert df.shape == (2, 3)
    assert df["date"].to_list() == ["03/15/2024", "05/20/2024"]
    assert df["revenue"].to_list() == [950, 1200]


def test_month_abbrev_date_and_next_field_not_merged(tmp_path):
    """5-Mar-24,700 must parse as two separate fields, not merge into 5-Mar-24700."""
    csv = tmp_path / "data.csv"
    csv.write_text("name,date,revenue\nAlpha,5-Mar-24,700\nBeta,10-Apr-24,800\n")
    df = load_file(csv)
    assert df.shape == (2, 3)
    assert df["date"].to_list() == ["5-Mar-24", "10-Apr-24"]
    assert df["revenue"].to_list() == [700, 800]


def test_quoted_thousands_normalized_by_cleaner(tmp_path):
    """Quoted "1,500 kW" is preserved by the loader; the cleaner normalizes it to 1500."""
    csv = tmp_path / "power.csv"
    csv.write_text('name,capacity_kw\nAlice,"1,500 kW"\nBob,"2,000 kW"\n')
    df = load_file(csv)
    assert df["capacity_kw"].to_list() == ["1,500 kW", "2,000 kW"]
    cleaned = clean(df)
    assert cleaned["capacity_kw"].to_list() == [1500, 2000]


def test_quoted_date_with_comma_normalized(tmp_path):
    """Quoted "March 20, 2024" loads correctly and the cleaner normalizes it to pl.Date."""
    csv = tmp_path / "data.csv"
    csv.write_text('name,event_date\nAlice,"March 20, 2024"\nBob,"April 5, 2024"\n')
    df = load_file(csv)
    cleaned = clean(df)
    assert cleaned["event_date"].dtype == pl.Date
    assert cleaned["event_date"][0] == datetime.date(2024, 3, 20)
    assert cleaned["event_date"][1] == datetime.date(2024, 4, 5)


def test_unquoted_thousands_now_detected_as_ragged(tmp_path, caplog):
    """Unquoted 1,500 is ambiguous CSV — now correctly flagged as ragged rows."""
    csv = tmp_path / "power.csv"
    csv.write_text("name,capacity,notes\nAlice,1,500,standard\n")
    with caplog.at_level(logging.WARNING, logger="intake"):
        df = load_file(csv)
    assert any("malformed" in msg.lower() for msg in caplog.messages)


def test_load_csv_genuinely_ragged_rows_warns(tmp_path, caplog):
    # Extra field not caused by a thousands comma — pre-processing can't fix this
    csv = tmp_path / "ragged.csv"
    csv.write_text("name,capacity,notes\nAlice,100,standard,EXTRA\nBob,200,standard\n")

    with caplog.at_level(logging.WARNING, logger="intake"):
        df = load_file(csv)

    assert df is not None
    assert df.shape[0] >= 1
    assert any("malformed" in msg.lower() for msg in caplog.messages)


def test_load_file_not_found_raises(tmp_path):
    with pytest.raises(LoadError, match="File not found"):
        load_file(tmp_path / "missing.csv")


def test_load_unsupported_format_raises(tmp_path):
    f = tmp_path / "data.json"
    f.write_text("{}")
    with pytest.raises(LoadError, match="Unsupported file type"):
        load_file(f)
