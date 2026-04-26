import polars as pl

from intake_engine.cleaner.cleaner import clean_cells, clean_headers, normalize_dates, normalize_numeric_strings, normalize_units, remove_duplicates


def test_clean_headers_lowercases_and_snake_cases(dirty_df):
    df = clean_headers(dirty_df)
    assert df.columns == ["first_name", "last_name", "age", "score", "notes"]


def test_clean_cells_trims_whitespace_and_nullifies_blanks(dirty_df):
    df = clean_headers(dirty_df)
    df = clean_cells(df)

    assert df["first_name"][1] == "Bob"        # " Bob " → "Bob"
    assert df["last_name"][2] == "Brown"        # "  Brown  " → "Brown"
    assert df["notes"][0] == "Active"           # "  Active " → "Active"
    assert df["notes"][1] is None               # "" → null
    assert df["notes"][2] is None               # "  " → null


def test_normalize_numeric_strings_handles_all_formats():
    df = pl.DataFrame({
        "amount": ["1,250", "$499", "33%", "(200)", "plain text"],
        "label":  ["alpha", "beta", "gamma", "delta", "epsilon"],
    })
    result = normalize_numeric_strings(df)
    assert result["amount"].to_list() == ["1250", "499", "33", "-200", "plain text"]
    assert result["label"].to_list() == ["alpha", "beta", "gamma", "delta", "epsilon"]


def test_normalize_units_converts_all_power_formats():
    df = pl.DataFrame({
        "capacity_kw": ["4.5 MW", "2 MW", "6MW", "1,500 kW", "15kW", "18 KW"],
        "name":        ["A", "B", "C", "D", "E", "F"],
    })
    result = normalize_units(df)
    assert result["capacity_kw"].to_list() == ["4500", "2000", "6000", "1500", "15", "18"]
    assert result["name"].to_list() == ["A", "B", "C", "D", "E", "F"]  # non-power column untouched


def test_normalize_units_skips_non_power_columns():
    df = pl.DataFrame({
        "description": ["4.5 MW", "2 MW", "6MW"],
        "label":       ["some text", "more text", "even more"],
    })
    result = normalize_units(df)
    assert result["description"].to_list() == ["4.5 MW", "2 MW", "6MW"]
    assert result["label"].to_list() == ["some text", "more text", "even more"]


def test_normalize_units_preserves_non_unit_values_in_power_column():
    df = pl.DataFrame({
        "power": ["4.5 MW", "N/A", "pending", "15kW"],
    })
    result = normalize_units(df)
    assert result["power"].to_list() == ["4500", "N/A", "pending", "15"]


def test_normalize_dates_converts_mixed_formats():
    import datetime
    df = pl.DataFrame({
        "event_date": ["2024-03-05", "03/05/2024", "5-Mar-24", "March 5, 2024"],
        "label":      ["alpha", "beta", "gamma", "delta"],
    })
    result = normalize_dates(df)
    # all values parse → column is cast to pl.Date
    assert result["event_date"].dtype == pl.Date
    assert result["event_date"].to_list() == [datetime.date(2024, 3, 5)] * 4
    assert result["label"].to_list() == ["alpha", "beta", "gamma", "delta"]  # text column untouched


def test_normalize_dates_skips_column_below_threshold():
    # 2 of 4 values parse (50%) — below the 80% threshold, column left unchanged
    df = pl.DataFrame({
        "mixed": ["2024-03-05", "not a date", "also text", "2024-05-15"],
    })
    result = normalize_dates(df)
    assert result["mixed"].to_list() == ["2024-03-05", "not a date", "also text", "2024-05-15"]


def test_normalize_dates_preserves_unparseable_values_above_threshold():
    # 4 of 5 values parse (80%) — column converts, bad value kept as-is
    df = pl.DataFrame({
        "date": ["2024-03-05", "2024-04-10", "2024-05-15", "2024-06-20", "bad value"],
    })
    result = normalize_dates(df)
    assert result["date"][4] == "bad value"
    assert result["date"][0] == "2024-03-05"


def test_remove_duplicates_drops_exact_duplicate_rows():
    df = pl.DataFrame({"a": [1, 2, 1, 3], "b": ["x", "y", "x", "z"]})
    result = remove_duplicates(df)
    assert result.shape[0] == 3
    assert result["a"].to_list() == [1, 2, 3]
