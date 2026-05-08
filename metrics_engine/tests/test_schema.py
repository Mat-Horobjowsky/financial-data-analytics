import pandas as pd
import pytest

from metrics_engine.schema import NormalizeResult, SchemaError, load_schema, normalize, _normalize_col_name


# ── _normalize_col_name ───────────────────────────────────────────────────────

def test_normalize_strips_whitespace():
    assert _normalize_col_name("  date  ") == "date"


def test_normalize_lowercases():
    assert _normalize_col_name("Revenue") == "revenue"


def test_normalize_spaces_to_underscores():
    assert _normalize_col_name("Capacity MW") == "capacity_mw"


def test_normalize_punctuation_to_underscores():
    assert _normalize_col_name("avg-price/kw") == "avg_price_kw"


def test_normalize_collapses_multiple_separators():
    assert _normalize_col_name("revenue  ($)") == "revenue"


def test_normalize_already_clean():
    assert _normalize_col_name("capacity_mw") == "capacity_mw"


# ── load_schema ───────────────────────────────────────────────────────────────

def test_schema_loads(schema_path):
    schema = load_schema(schema_path)
    assert "base_columns" in schema
    assert "segment_columns" in schema


def test_schema_base_column_count(schema_path):
    schema = load_schema(schema_path)
    assert len(schema["base_columns"]) == 5


# ── normalize: return type ────────────────────────────────────────────────────

def test_normalize_returns_result_object(schema_path, raw_df):
    schema = load_schema(schema_path)
    result = normalize(raw_df, schema)
    assert isinstance(result, NormalizeResult)
    assert isinstance(result.df, pd.DataFrame)
    assert isinstance(result.dropped_columns, list)
    assert isinstance(result.missing_segments, list)


# ── normalize: standard names and aliases ─────────────────────────────────────

def test_standard_names_pass_through(schema_path, raw_df):
    schema = load_schema(schema_path)
    result = normalize(raw_df, schema)
    for col in ["date", "revenue", "capacity_mw", "leased_mw", "contracted_kw"]:
        assert col in result.df.columns


def test_alias_resolution(schema_path):
    schema = load_schema(schema_path)
    df = pd.DataFrame({
        "Date": ["2024-01-01"],
        "Revenue": [1200000.0],
        "Capacity_MW": [50.0],
        "Leased_MW": [38.5],
        "Contracted_KW": [38500.0],
    })
    result = normalize(df, schema)
    assert "date" in result.df.columns
    assert "revenue" in result.df.columns
    assert "capacity_mw" in result.df.columns
    assert "Date" not in result.df.columns


def test_whitespace_in_column_names_resolved(schema_path):
    schema = load_schema(schema_path)
    df = pd.DataFrame({
        "  date  ": ["2024-01-01"],
        "  Revenue  ": [1200000.0],
        "Capacity_MW": [50.0],
        "Leased_MW": [38.5],
        "Contracted_KW": [38500.0],
    })
    result = normalize(df, schema)
    assert "date" in result.df.columns
    assert "revenue" in result.df.columns


# ── normalize: type casting ───────────────────────────────────────────────────

def test_date_column_is_datetime(schema_path, raw_df):
    schema = load_schema(schema_path)
    result = normalize(raw_df, schema)
    assert pd.api.types.is_datetime64_any_dtype(result.df["date"])


def test_numeric_columns_are_float(schema_path, raw_df):
    schema = load_schema(schema_path)
    result = normalize(raw_df, schema)
    for col in ["revenue", "capacity_mw", "leased_mw", "contracted_kw"]:
        assert pd.api.types.is_numeric_dtype(result.df[col]), f"{col} is not numeric"


def test_invalid_numeric_raises(schema_path):
    schema = load_schema(schema_path)
    df = pd.DataFrame({
        "date": ["2024-01-01"],
        "revenue": ["not_a_number"],
        "capacity_mw": [50.0],
        "leased_mw": [38.5],
        "contracted_kw": [38500.0],
    })
    with pytest.raises(SchemaError, match="cannot be cast to float"):
        normalize(df, schema)


# ── normalize: missing required columns ──────────────────────────────────────

def test_missing_required_column_raises(schema_path):
    schema = load_schema(schema_path)
    df = pd.DataFrame({
        "date": ["2024-01-01"],
        "revenue": [1000000.0],
    })
    with pytest.raises(SchemaError, match="Missing required columns"):
        normalize(df, schema)


def test_missing_required_column_lists_all_missing(schema_path):
    schema = load_schema(schema_path)
    df = pd.DataFrame({"date": ["2024-01-01"]})
    with pytest.raises(SchemaError) as exc_info:
        normalize(df, schema)
    msg = str(exc_info.value)
    assert "revenue" in msg or "capacity_mw" in msg


# ── normalize: alias collision detection ─────────────────────────────────────

def test_alias_collision_raises(schema_path):
    schema = load_schema(schema_path)
    # "Date" and "date" both normalize to "date" → same standard column
    df = pd.DataFrame({
        "Date": ["2024-01-01"],
        "date": ["2024-01-01"],
        "revenue": [1200000.0],
        "capacity_mw": [50.0],
        "leased_mw": [38.5],
        "contracted_kw": [38500.0],
    })
    with pytest.raises(SchemaError, match="Alias collision"):
        normalize(df, schema)


def test_alias_collision_error_names_the_standard_column(schema_path):
    schema = load_schema(schema_path)
    df = pd.DataFrame({
        "Revenue": [1200000.0],
        "rev": [1200000.0],  # "rev" is an alias for revenue in schema.yaml
        "date": ["2024-01-01"],
        "capacity_mw": [50.0],
        "leased_mw": [38.5],
        "contracted_kw": [38500.0],
    })
    with pytest.raises(SchemaError, match="revenue"):
        normalize(df, schema)


# ── normalize: dropped column tracking ───────────────────────────────────────

def test_unknown_columns_tracked_in_dropped(schema_path, raw_df):
    schema = load_schema(schema_path)
    df = raw_df.copy()
    df["mystery_column"] = "garbage"
    df["another_unknown"] = 99
    result = normalize(df, schema)
    assert "mystery_column" in result.dropped_columns
    assert "another_unknown" in result.dropped_columns


def test_unknown_columns_removed_from_df(schema_path, raw_df):
    schema = load_schema(schema_path)
    df = raw_df.copy()
    df["mystery_column"] = "garbage"
    result = normalize(df, schema)
    assert "mystery_column" not in result.df.columns


def test_no_dropped_columns_when_clean(schema_path, raw_df):
    schema = load_schema(schema_path)
    result = normalize(raw_df, schema)
    assert result.dropped_columns == []


# ── normalize: optional segment tracking ─────────────────────────────────────

def test_optional_segment_columns_present_when_in_data(schema_path, raw_df):
    schema = load_schema(schema_path)
    result = normalize(raw_df, schema)
    assert "region" in result.df.columns
    assert "provider" in result.df.columns
    assert result.missing_segments == []


def test_missing_segments_tracked(schema_path):
    schema = load_schema(schema_path)
    df = pd.DataFrame({
        "date": ["2024-01-01"],
        "revenue": [1200000.0],
        "capacity_mw": [50.0],
        "leased_mw": [38.5],
        "contracted_kw": [38500.0],
    })
    result = normalize(df, schema)
    assert "region" in result.missing_segments
    assert "provider" in result.missing_segments


def test_partial_segments_tracked(schema_path):
    schema = load_schema(schema_path)
    df = pd.DataFrame({
        "date": ["2024-01-01"],
        "revenue": [1200000.0],
        "capacity_mw": [50.0],
        "leased_mw": [38.5],
        "contracted_kw": [38500.0],
        "region": ["EMEA"],
        # provider absent
    })
    result = normalize(df, schema)
    assert "provider" in result.missing_segments
    assert "region" not in result.missing_segments


# ── normalize: row count and shape ───────────────────────────────────────────

def test_row_count_preserved(schema_path, raw_df):
    schema = load_schema(schema_path)
    result = normalize(raw_df, schema)
    assert len(result.df) == len(raw_df)


def test_missing_segment_not_required(schema_path):
    schema = load_schema(schema_path)
    df = pd.DataFrame({
        "date": ["2024-01-01"],
        "revenue": [1200000.0],
        "capacity_mw": [50.0],
        "leased_mw": [38.5],
        "contracted_kw": [38500.0],
    })
    result = normalize(df, schema)
    assert len(result.df) == 1


# ── condition_columns support ─────────────────────────────────────────────────

def _readiness_schema():
    return {
        "base_columns": [
            {"name": "date", "type": "date", "aliases": ["Date"]},
        ],
        "segment_columns": [
            {"name": "category", "type": "string", "required": False, "aliases": ["Category"]},
        ],
        "condition_columns": [
            {"name": "status", "type": "string", "required": True, "aliases": ["Status"]},
            {"name": "severity", "type": "string", "required": True, "aliases": ["Severity"]},
        ],
    }


def _readiness_df():
    return pd.DataFrame({
        "date": ["2025-01-15"],
        "category": ["power"],
        "status": ["complete"],
        "severity": ["high"],
    })


def test_condition_columns_kept_in_df():
    schema = _readiness_schema()
    result = normalize(_readiness_df(), schema)
    assert "status" in result.df.columns
    assert "severity" in result.df.columns


def test_condition_columns_alias_resolved():
    schema = _readiness_schema()
    df = pd.DataFrame({
        "date": ["2025-01-15"],
        "Status": ["complete"],
        "Severity": ["high"],
    })
    result = normalize(df, schema)
    assert "status" in result.df.columns
    assert "severity" in result.df.columns
    assert "Status" not in result.df.columns


def test_required_condition_column_missing_raises():
    schema = _readiness_schema()
    df = pd.DataFrame({
        "date": ["2025-01-15"],
        "status": ["complete"],
        # severity missing
    })
    with pytest.raises(SchemaError, match="severity"):
        normalize(df, schema)


def test_optional_condition_column_missing_does_not_raise():
    schema = {
        "base_columns": [{"name": "date", "type": "date", "aliases": []}],
        "condition_columns": [
            {"name": "status", "type": "string", "required": False, "aliases": []},
        ],
    }
    df = pd.DataFrame({"date": ["2025-01-15"]})
    result = normalize(df, schema)
    assert isinstance(result, NormalizeResult)


def test_condition_columns_not_dropped_as_unknown():
    schema = _readiness_schema()
    result = normalize(_readiness_df(), schema)
    assert "status" not in result.dropped_columns
    assert "severity" not in result.dropped_columns


def test_string_type_column_preserved_as_string():
    schema = _readiness_schema()
    result = normalize(_readiness_df(), schema)
    assert pd.api.types.is_string_dtype(result.df["status"])


def test_schema_without_condition_columns_unchanged(schema_path, raw_df):
    from metrics_engine.schema import load_schema
    schema = load_schema(schema_path)
    result = normalize(raw_df, schema)
    assert isinstance(result, NormalizeResult)
