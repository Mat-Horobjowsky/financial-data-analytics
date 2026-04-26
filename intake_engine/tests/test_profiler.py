from pathlib import Path

import polars as pl

from intake_engine.profiler.profiler import build_profile


def test_profile_basic_counts(tmp_path):
    raw = pl.DataFrame({
        "Name":  ["Alice", "Bob", "Alice"],
        "Score": ["95.5", "87.0", "95.5"],
    })
    clean = pl.DataFrame({
        "name":  ["Alice", "Bob"],
        "score": [95.5, 87.0],
    })
    report = build_profile(tmp_path / "test.csv", raw, clean, warnings=[])

    assert report.file_name == "test.csv"
    assert report.rows_loaded == 3
    assert report.rows_output == 2
    assert report.duplicate_rows_removed == 1
    assert report.columns == 2


def test_profile_detects_renamed_columns(tmp_path):
    raw = pl.DataFrame({"First Name": ["Alice"], "Last-Name": ["Smith"]})
    clean = pl.DataFrame({"first_name": ["Alice"], "last_name": ["Smith"]})
    report = build_profile(tmp_path / "test.csv", raw, clean, warnings=[])
    assert report.columns_renamed == {"First Name": "first_name", "Last-Name": "last_name"}


def test_profile_detects_numeric_normalization(tmp_path):
    raw = pl.DataFrame({"amount": ["100", "200", "300"]})
    clean = pl.DataFrame({"amount": [100, 200, 300]})
    report = build_profile(tmp_path / "test.csv", raw, clean, warnings=[])
    assert "amount" in report.numeric_columns_normalized


def test_profile_detects_date_normalization(tmp_path):
    raw = pl.DataFrame({"event_date": ["03/05/2024", "03/06/2024"]})
    clean = pl.DataFrame({"event_date": ["2024-03-05", "2024-03-06"]})
    report = build_profile(tmp_path / "test.csv", raw, clean, warnings=[])
    assert "event_date" in report.date_columns_normalized


def test_profile_captures_warnings(tmp_path):
    raw = pl.DataFrame({"a": [1]})
    clean = pl.DataFrame({"a": [1]})
    report = build_profile(tmp_path / "test.csv", raw, clean, warnings=["malformed rows detected"])
    assert report.warnings == ["malformed rows detected"]


def test_profile_serialises_to_json(tmp_path):
    raw = pl.DataFrame({"x": ["1", "2"]})
    clean = pl.DataFrame({"x": [1, 2]})
    report = build_profile(tmp_path / "test.csv", raw, clean, warnings=[])
    json_str = report.model_dump_json()
    assert "file_name" in json_str
    assert "run_timestamp" in json_str


# --- semantic_types tests ---

def test_semantic_type_date_all_valid(tmp_path):
    raw = pl.DataFrame({"event_date": ["03/05/2024", "03/06/2024"]})
    clean = pl.DataFrame({"event_date": ["2024-03-05", "2024-03-06"]})
    report = build_profile(tmp_path / "test.csv", raw, clean, warnings=[])
    assert report.semantic_types["event_date"] == "date"


def test_semantic_type_date_mixed_invalid(tmp_path):
    # 4/5 = 80% — meets threshold but not 100%
    raw = pl.DataFrame({"posted": ["03/05/2024", "03/06/2024", "03/07/2024", "03/08/2024", "TBD"]})
    clean = pl.DataFrame({"posted": ["2024-03-05", "2024-03-06", "2024-03-07", "2024-03-08", "TBD"]})
    report = build_profile(tmp_path / "test.csv", raw, clean, warnings=[])
    assert report.semantic_types["posted"] == "date_mixed_invalid"


def test_semantic_type_currency_by_column_name(tmp_path):
    raw = pl.DataFrame({"revenue": ["100", "200"]})
    clean = pl.DataFrame({"revenue": [100, 200]})
    report = build_profile(tmp_path / "test.csv", raw, clean, warnings=[])
    assert report.semantic_types["revenue"] == "currency"


def test_semantic_type_currency_by_raw_symbol(tmp_path):
    # Column name "total" has no currency keyword — detected from raw $ prefix
    raw = pl.DataFrame({"total": ["$100", "$200"]})
    clean = pl.DataFrame({"total": [100, 200]})
    report = build_profile(tmp_path / "test.csv", raw, clean, warnings=[])
    assert report.semantic_types["total"] == "currency"


def test_semantic_type_power_kw(tmp_path):
    raw = pl.DataFrame({"capacity_kw": ["4.5 MW", "15kW"]})
    clean = pl.DataFrame({"capacity_kw": [4500, 15]})
    report = build_profile(tmp_path / "test.csv", raw, clean, warnings=[])
    assert report.semantic_types["capacity_kw"] == "power_kw"


def test_semantic_type_numeric(tmp_path):
    raw = pl.DataFrame({"score": ["95.5", "87.0"]})
    clean = pl.DataFrame({"score": [95.5, 87.0]})
    report = build_profile(tmp_path / "test.csv", raw, clean, warnings=[])
    assert report.semantic_types["score"] == "numeric"


def test_semantic_type_identifier(tmp_path):
    raw = pl.DataFrame({"site_id": ["S001", "S002", "S003"]})
    clean = pl.DataFrame({"site_id": ["S001", "S002", "S003"]})
    report = build_profile(tmp_path / "test.csv", raw, clean, warnings=[])
    assert report.semantic_types["site_id"] == "identifier"


def test_semantic_type_price_kw_is_currency_not_power(tmp_path):
    # "price" is a currency keyword and must take precedence over "kw" (power keyword)
    raw = pl.DataFrame({"price_kw": ["$15", "$20"]})
    clean = pl.DataFrame({"price_kw": [15, 20]})
    report = build_profile(tmp_path / "test.csv", raw, clean, warnings=[])
    assert report.semantic_types["price_kw"] == "currency"


def test_semantic_type_contract_start_3_valid_1_bad_is_date_mixed_invalid(tmp_path):
    # 3/4 = 75% >= 70% threshold — was incorrectly classified as text
    raw = pl.DataFrame({"contract_start": ["01/01/2024", "06/15/2024", "09/30/2024", "TBD"]})
    clean = pl.DataFrame({"contract_start": ["2024-01-01", "2024-06-15", "2024-09-30", "TBD"]})
    report = build_profile(tmp_path / "test.csv", raw, clean, warnings=[])
    assert report.semantic_types["contract_start"] == "date_mixed_invalid"


def test_semantic_type_text(tmp_path):
    raw = pl.DataFrame({"notes": ["hello world", "maintenance required"]})
    clean = pl.DataFrame({"notes": ["hello world", "maintenance required"]})
    report = build_profile(tmp_path / "test.csv", raw, clean, warnings=[])
    assert report.semantic_types["notes"] == "text"
