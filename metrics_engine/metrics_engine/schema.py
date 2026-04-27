import re
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import yaml


class SchemaError(Exception):
    pass


@dataclass
class NormalizeResult:
    df: pd.DataFrame
    dropped_columns: list[str] = field(default_factory=list)
    missing_segments: list[str] = field(default_factory=list)
    # missing_segments drives rollup-skipping in calculator.py:
    # any rollup that references a column in this list should be skipped
    # with a warning rather than failing hard.


def _normalize_col_name(col: str) -> str:
    col = str(col).strip().lower()
    col = re.sub(r"[^\w]+", "_", col)
    return col.strip("_")


def load_schema(schema_path: str | Path) -> dict:
    with open(schema_path) as f:
        return yaml.safe_load(f)


def normalize(df: pd.DataFrame, schema: dict) -> NormalizeResult:
    df = df.copy()

    all_col_defs = schema.get("base_columns", []) + schema.get("segment_columns", [])

    # Build alias_map: normalized alias/name → standard name
    alias_map: dict[str, str] = {}
    for col_def in all_col_defs:
        standard = col_def["name"]
        alias_map[_normalize_col_name(standard)] = standard
        for alias in col_def.get("aliases", []):
            alias_map[_normalize_col_name(alias)] = standard

    # Normalize each input column name for matching
    normalized_input: dict[str, str] = {col: _normalize_col_name(col) for col in df.columns}

    # Detect collisions: two input columns resolving to the same standard column
    standard_to_inputs: dict[str, list[str]] = {}
    for original, norm in normalized_input.items():
        if norm in alias_map:
            standard_to_inputs.setdefault(alias_map[norm], []).append(original)

    collisions = {std: srcs for std, srcs in standard_to_inputs.items() if len(srcs) > 1}
    if collisions:
        msgs = [f"'{std}' matched by {srcs}" for std, srcs in collisions.items()]
        raise SchemaError(f"Alias collision detected: {'; '.join(msgs)}")

    # Rename recognized columns to their standard names
    rename_map = {
        original: alias_map[norm]
        for original, norm in normalized_input.items()
        if norm in alias_map
    }
    df = df.rename(columns=rename_map)

    # Track dropped columns before removing them
    recognized = {col_def["name"] for col_def in all_col_defs}
    dropped_columns = [c for c in df.columns if c not in recognized]
    df = df[[c for c in df.columns if c in recognized]]

    # Check required base columns are present
    missing_required = [
        col_def["name"]
        for col_def in schema.get("base_columns", [])
        if col_def["name"] not in df.columns
    ]
    if missing_required:
        raise SchemaError(f"Missing required columns after alias resolution: {missing_required}")

    # Cast types for base columns
    for col_def in schema.get("base_columns", []):
        name = col_def["name"]
        col_type = col_def.get("type")

        if col_type == "float":
            try:
                df[name] = pd.to_numeric(df[name], errors="raise")
            except (ValueError, TypeError) as e:
                raise SchemaError(f"Column '{name}' cannot be cast to float: {e}")

        elif col_type == "date":
            try:
                df[name] = pd.to_datetime(df[name], errors="raise")
            except (ValueError, TypeError) as e:
                raise SchemaError(f"Column '{name}' cannot be parsed as dates: {e}")

    # Track missing optional segment columns for use by calculator rollup logic
    missing_segments = [
        col_def["name"]
        for col_def in schema.get("segment_columns", [])
        if col_def["name"] not in df.columns
    ]

    return NormalizeResult(df=df, dropped_columns=dropped_columns, missing_segments=missing_segments)
