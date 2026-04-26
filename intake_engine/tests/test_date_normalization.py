"""Regression tests for v1.2.1 and v1.2.3: date normalization and typed dates."""
import datetime
from pathlib import Path

import openpyxl
import polars as pl
import pytest

from intake_engine.cleaner.cleaner import clean
from intake_engine.profiler.profiler import build_profile


# --- helpers ---

def _make_excel(path: Path, sheet_data: dict) -> Path:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = list(sheet_data)[0]
    headers, rows = next(iter(sheet_data.values()))
    ws.append(headers)
    for row in rows:
        ws.append(row)
    wb.save(path)
    return path


# --- 1. CSV mixed dates: 4 valid + 1 garbage → String, date_mixed_invalid ---

def test_mixed_csv_dates_stay_string_with_semantic_type(tmp_path):
    csv = tmp_path / "events.csv"
    csv.write_text(
        "date,value\n"
        "2024-01-01,1\n"
        "2024-02-05,2\n"
        "2024-03-10,3\n"
        "2024-04-15,4\n"
        "not-a-date,5\n"
    )
    raw = pl.read_csv(csv)
    cleaned = clean(raw)

    assert cleaned["date"].dtype == pl.String
    assert "not-a-date" in cleaned["date"].to_list()

    report = build_profile(csv, raw, cleaned, [])
    assert report.semantic_types["date"] == "date_mixed_invalid"


# --- 2. Excel date objects → Datetime in fastexcel → pl.Date after clean ---

def test_excel_datetime_columns_cast_to_date(tmp_path):
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Data"
    ws.append(["event_date", "score"])
    ws.append([datetime.date(2024, 1, 15), 10])
    ws.append([datetime.date(2024, 2, 20), 20])
    ws.append([datetime.date(2024, 3, 25), 30])
    wb.save(tmp_path / "dates.xlsx")

    raw = pl.read_excel(tmp_path / "dates.xlsx", sheet_id=1)
    cleaned = clean(raw)

    assert cleaned["event_date"].dtype == pl.Date


# --- 3. Timestamp strings → pl.Date ---

def test_timestamp_strings_cast_to_date():
    df = pl.DataFrame({
        "ts": ["2024-03-05 14:30:00", "2024-04-10 09:15:00", "2024-05-20 18:00:00"]
    })
    cleaned = clean(df)

    assert cleaned["ts"].dtype == pl.Date
    assert cleaned["ts"][0] == datetime.date(2024, 3, 5)
    assert cleaned["ts"][2] == datetime.date(2024, 5, 20)


# --- 4. Majority valid + one bad text → stays String, bad value preserved ---

def test_majority_valid_one_bad_stays_string():
    df = pl.DataFrame({
        "d": ["2024-01-01", "2024-02-01", "2024-03-01", "2024-04-01", "INVALID_VALUE"]
    })
    cleaned = clean(df)

    assert cleaned["d"].dtype == pl.String
    assert "INVALID_VALUE" in cleaned["d"].to_list()


# --- 5. All valid diverse formats → pl.Date ---

def test_all_valid_dates_cast_to_date():
    df = pl.DataFrame({
        "d": ["2024-01-01", "03/15/2024", "5-Jan-2024", "April 20, 2024"]
    })
    cleaned = clean(df)

    assert cleaned["d"].dtype == pl.Date


# --- 6. DuckDB preserves DATE type ---

def test_duckdb_preserves_date_type(tmp_path):
    try:
        import duckdb
    except ImportError:
        pytest.skip("duckdb not installed")

    from intake_engine.db.writer import load_to_duckdb

    df = pl.DataFrame({
        "event_date": pl.Series(["2024-01-01", "2024-02-01"]).str.to_date(),
        "value": [10, 20],
    })
    load_to_duckdb(df, tmp_path / "test.duckdb", "events")

    with duckdb.connect(str(tmp_path / "test.duckdb")) as con:
        col_type = con.execute(
            "SELECT data_type FROM information_schema.columns "
            "WHERE table_name = 'events' AND column_name = 'event_date'"
        ).fetchone()[0]

    assert col_type == "DATE"


# --- 7. Parquet DATE schema preserved on round-trip ---

def test_parquet_date_schema_preserved(tmp_path):
    df = pl.DataFrame({
        "event_date": pl.Series(["2024-01-01", "2024-06-15", "2024-12-31"]).str.to_date(),
        "value": [1, 2, 3],
    })
    pq_path = tmp_path / "data.parquet"
    df.write_parquet(pq_path)

    df_back = pl.read_parquet(pq_path)

    assert df_back["event_date"].dtype == pl.Date
    assert df_back["event_date"][0] == datetime.date(2024, 1, 1)


# --- v1.2.3 regression tests: mixed-date normalization ---

def test_mixed_dates_with_placeholder_normalizes_valid_values():
    """2/3 valid dates + 'TBD' should normalize ISO dates and preserve TBD as String."""
    df = pl.DataFrame({
        "event_date": ["03/15/2024", "2024-04-01", "TBD"]
    })
    cleaned = clean(df)
    assert cleaned["event_date"].dtype == pl.String
    values = cleaned["event_date"].to_list()
    assert values[0] == "2024-03-15"
    assert values[1] == "2024-04-01"
    assert values[2] == "TBD"


def test_mixed_dates_invalid_value_preserved_verbatim():
    """Invalid non-date values must pass through unchanged after normalization."""
    df = pl.DataFrame({
        "date": ["01/05/2024", "N/A", "02/10/2024", "unknown", "03/20/2024"]
    })
    cleaned = clean(df)
    assert cleaned["date"].dtype == pl.String
    values = cleaned["date"].to_list()
    assert "N/A" in values
    assert "unknown" in values
    assert "2024-01-05" in values
    assert "2024-02-10" in values
    assert "2024-03-20" in values


def test_mixed_dates_at_normalize_threshold():
    """Exactly 50% parse (2 of 4) — should still normalize valid values."""
    df = pl.DataFrame({
        "date": ["03/15/2024", "bad", "2024-06-01", "also-bad"]
    })
    cleaned = clean(df)
    assert cleaned["date"].dtype == pl.String
    values = cleaned["date"].to_list()
    assert values[0] == "2024-03-15"
    assert values[2] == "2024-06-01"
    assert values[1] == "bad"
    assert values[3] == "also-bad"


def test_mixed_dates_below_threshold_unchanged():
    """< 50% parse — column should be left completely untouched."""
    df = pl.DataFrame({
        "date": ["2024-01-01", "text", "more text", "even more text"]
    })
    cleaned = clean(df)
    assert cleaned["date"].dtype == pl.String
    assert cleaned["date"].to_list() == ["2024-01-01", "text", "more text", "even more text"]


def test_validator_warns_on_mixed_normalized_column(tmp_path):
    """Validation warning is preserved after mixed-date normalization."""
    from intake_engine.validator.validator import validate_file

    csv = tmp_path / "events.csv"
    csv.write_text("event_date,value\n03/15/2024,10\n2024-04-01,20\nTBD,30\n")

    raw = pl.read_csv(csv)
    cleaned = clean(raw)

    report = validate_file(csv, raw, cleaned)
    date_warnings = [w for w in report.warnings if "event_date" in w and "date" in w]
    assert len(date_warnings) == 1
    assert "mixed" in date_warnings[0]
