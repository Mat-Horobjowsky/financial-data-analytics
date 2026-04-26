import re
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

from intake_engine.cleaner.cleaner import clean_headers
from intake_engine.models.profile import ProfileReport

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_POWER_KEYWORDS = frozenset({"mw", "kw", "power", "density", "capacity"})
_CURRENCY_KEYWORDS = frozenset({"revenue", "cost", "price", "amount", "fee", "salary",
                                  "income", "spend", "budget", "payment", "charge"})
_ID_KEYWORDS = frozenset({"id", "code", "key", "uuid", "ref"})
_CURRENCY_SYMBOLS = frozenset({"$", "€", "£", "¥"})


def build_profile(
    source_path: Path,
    raw_df: pl.DataFrame,
    clean_df: pl.DataFrame,
    warnings: list[str],
) -> ProfileReport:
    """Derive a ProfileReport by comparing raw and cleaned DataFrames."""
    raw_snake = clean_headers(raw_df)

    columns_renamed = {
        old: new
        for old, new in zip(raw_df.columns, raw_snake.columns)
        if old != new
    }

    numeric_normalized = [
        col for col in raw_snake.columns
        if col in clean_df.columns
        and raw_snake[col].dtype == pl.String
        and clean_df[col].dtype in (pl.Int64, pl.Float64)
    ]

    date_normalized = _detect_date_columns(raw_snake, clean_df)

    return ProfileReport(
        file_name=source_path.name,
        rows_loaded=raw_df.shape[0],
        rows_output=clean_df.shape[0],
        columns=clean_df.shape[1],
        column_names=clean_df.columns,
        inferred_types={col: str(clean_df[col].dtype) for col in clean_df.columns},
        null_counts={col: clean_df[col].null_count() for col in clean_df.columns},
        duplicate_rows_removed=raw_df.shape[0] - clean_df.shape[0],
        columns_renamed=columns_renamed,
        numeric_columns_normalized=numeric_normalized,
        date_columns_normalized=date_normalized,
        semantic_types=_infer_semantic_types(clean_df, raw_snake),
        warnings=warnings,
        run_timestamp=datetime.now(timezone.utc).isoformat(),
    )


def _infer_semantic_types(clean_df: pl.DataFrame, raw_snake: pl.DataFrame) -> dict[str, str]:
    return {
        col: _infer_semantic_type(
            col,
            clean_df[col],
            raw_snake[col] if col in raw_snake.columns else None,
        )
        for col in clean_df.columns
    }


def _infer_semantic_type(col: str, series: pl.Series, raw_series: pl.Series | None) -> str:
    dtype = series.dtype
    non_null = series.drop_nulls()

    if dtype == pl.Date:
        return "date"

    if dtype == pl.String:
        if len(non_null) == 0:
            return "text"

        iso_count = sum(1 for v in non_null if _ISO_DATE_RE.match(v))
        ratio = iso_count / len(non_null)
        if ratio >= 0.7 or (iso_count >= 3 and iso_count > len(non_null) / 2):
            return "date" if ratio == 1.0 else "date_mixed_invalid"

        if set(col.split("_")) & _ID_KEYWORDS:
            return "identifier"

        return "text"

    if dtype in (pl.Int64, pl.Float64):
        if any(kw in col for kw in _CURRENCY_KEYWORDS):
            return "currency"

        if any(kw in col for kw in _POWER_KEYWORDS):
            return "power_kw"

        if raw_series is not None and raw_series.dtype == pl.String:
            raw_non_null = raw_series.drop_nulls()
            if len(raw_non_null) > 0 and any(
                str(v).strip()[:1] in _CURRENCY_SYMBOLS for v in raw_non_null[:20]
            ):
                return "currency"

        return "numeric"

    return "text"


def _detect_date_columns(raw_snake: pl.DataFrame, clean_df: pl.DataFrame) -> list[str]:
    """Return columns that were normalized to date type (weren't already ISO/Date in raw)."""
    result = []
    for col in raw_snake.columns:
        if col not in clean_df.columns:
            continue
        raw_dtype = raw_snake[col].dtype
        clean_dtype = clean_df[col].dtype

        # Datetime → Date: Excel numeric datetime cast to Date
        if str(raw_dtype).startswith("Datetime") and clean_dtype == pl.Date:
            result.append(col)
            continue

        # String → Date: text dates parsed and cast to pl.Date
        if raw_dtype == pl.String and clean_dtype == pl.Date:
            result.append(col)
            continue

        # String → String ISO: text dates normalized but kept as string (mixed validity)
        if raw_dtype != pl.String or clean_dtype != pl.String:
            continue
        clean_vals = clean_df[col].drop_nulls()
        if len(clean_vals) == 0:
            continue
        if not all(_ISO_DATE_RE.match(v) for v in clean_vals[:20]):
            continue
        raw_vals = raw_snake[col].drop_nulls()
        if len(raw_vals) > 0 and all(_ISO_DATE_RE.match(v) for v in raw_vals[:20]):
            continue  # already ISO in raw — not a normalization
        result.append(col)
    return result
