import re
from datetime import datetime

import polars as pl

_POWER_KEYWORDS = frozenset({"mw", "kw", "power", "density", "capacity"})
_UNIT_RE = re.compile(r"^([\d,.]+)\s*(mw|kw)\s*$", re.IGNORECASE)

_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

_DATE_FORMATS = [
    "%Y-%m-%d",               # 2024-03-05
    "%m/%d/%Y",               # 03/05/2024  (MM/DD tried before DD/MM to resolve ambiguity)
    "%d/%m/%Y",               # 05/03/2024
    "%d-%b-%y",               # 5-Jan-24
    "%d-%b-%Y",               # 5-Jan-2024
    "%B %d %Y",               # March 5 2024
    "%B %d, %Y",              # March 5, 2024
    "%b %d %Y",               # Mar 5 2024
    "%b %d, %Y",              # Mar 5, 2024
    "%Y-%m-%d %H:%M:%S",      # 2024-03-05 14:30:00
    "%Y-%m-%dT%H:%M:%S",      # 2024-03-05T14:30:00
    "%Y-%m-%d %H:%M:%S.%f",   # 2024-03-05 14:30:00.000000
    "%Y-%m-%dT%H:%M:%S.%f",   # 2024-03-05T14:30:00.000000
]

_DATE_NORMALIZE_THRESHOLD = 0.5  # fraction of non-null values that must parse to trigger normalization
# Columns where ALL non-null values parse are cast to pl.Date.
# Columns above the threshold but with some unparseable values are normalized to ISO strings
# and kept as pl.String so invalid values (e.g. "TBD") are preserved.


def clean(df: pl.DataFrame) -> pl.DataFrame:
    """Run all cleaning steps. Returns a new DataFrame; input is never mutated."""
    df = clean_headers(df)
    df = clean_cells(df)
    df = normalize_numeric_strings(df)
    df = normalize_units(df)
    df = normalize_dates(df)
    df = coerce_types(df)
    df = remove_duplicates(df)
    return df


def to_snake(name: str) -> str:
    """Convert a column name to snake_case (same transform applied during clean_headers)."""
    name = name.strip().lower()
    name = re.sub(r"[-\s/\.]+", "_", name)  # separators → underscore
    name = re.sub(r"[^\w]", "", name)         # drop remaining special chars
    name = re.sub(r"_+", "_", name)           # collapse repeated underscores
    return name.strip("_")


def clean_headers(df: pl.DataFrame) -> pl.DataFrame:
    """Lowercase, strip, and snake_case all column names."""
    return df.rename({col: to_snake(col) for col in df.columns})


def clean_cells(df: pl.DataFrame) -> pl.DataFrame:
    """Trim whitespace in string columns and convert blank strings to null."""
    exprs = []
    for col in df.columns:
        if df[col].dtype == pl.String:
            trimmed = pl.col(col).str.strip_chars()
            exprs.append(
                pl.when(trimmed == "").then(None).otherwise(trimmed).alias(col)
            )
        else:
            exprs.append(pl.col(col))
    return df.select(exprs)


def normalize_numeric_strings(df: pl.DataFrame) -> pl.DataFrame:
    """Strip numeric formatting from string columns so coerce_types can cast them.

    Handles: 1,250 -> 1250 | $499 -> 499 | 33% -> 33 | (200) -> -200
    Text columns are preserved unchanged.
    """
    def _normalize(val: str | None) -> str | None:
        if val is None:
            return None
        s = val.strip()
        if re.fullmatch(r"\([\d,.\s]+\)", s):           # (200) → -200
            s = "-" + s[1:-1].strip()
        s = re.sub(r"^[$€£¥]\s*", "", s)                # remove leading currency symbol
        s = re.sub(r"(?<=\d),(?=\d)", "", s)             # remove thousands commas
        s = re.sub(r"%$", "", s.rstrip())                # remove trailing percent
        return s.strip() or None

    exprs = []
    for col in df.columns:
        if df[col].dtype == pl.String:
            exprs.append(pl.col(col).map_elements(_normalize, return_dtype=pl.String).alias(col))
        else:
            exprs.append(pl.col(col))
    return df.select(exprs)


def normalize_units(df: pl.DataFrame) -> pl.DataFrame:
    """Convert power-unit strings to numeric kW in likely power columns.

    Column is treated as power when its name contains: mw, kw, power, density, capacity.
    MW values are multiplied by 1000. Non-unit values in matched columns are preserved.
    """
    def _to_kw(val: str | None) -> str | None:
        if val is None:
            return None
        m = _UNIT_RE.match(val.strip())
        if not m:
            return val
        number = float(m.group(1).replace(",", ""))
        kw = number * 1000 if m.group(2).lower() == "mw" else number
        return str(int(kw)) if kw == int(kw) else str(kw)

    exprs = []
    for col in df.columns:
        if df[col].dtype == pl.String and any(kw in col for kw in _POWER_KEYWORDS):
            exprs.append(pl.col(col).map_elements(_to_kw, return_dtype=pl.String).alias(col))
        else:
            exprs.append(pl.col(col))
    return df.select(exprs)


def normalize_dates(df: pl.DataFrame) -> pl.DataFrame:
    """Normalize date-like columns.

    - pl.Date: pass through unchanged.
    - pl.Datetime: cast to pl.Date (drop time component).
    - pl.String date-like (>= 50% of non-null values parse):
        - All non-null values parse → normalize to ISO and cast column to pl.Date.
        - Mixed valid/invalid → normalize valid values to ISO, leave invalid values
          as-is (e.g. "TBD"), keep column as pl.String.
    """
    def _try_parse(val: str) -> datetime | None:
        for fmt in _DATE_FORMATS:
            try:
                return datetime.strptime(val.strip(), fmt)
            except ValueError:
                continue
        return None

    def _count_parseable(series: pl.Series) -> tuple[int, int]:
        non_null = series.drop_nulls()
        hits = sum(1 for v in non_null if _try_parse(v) is not None)
        return hits, len(non_null)

    def _to_iso(val: str | None) -> str | None:
        if val is None:
            return None
        dt = _try_parse(val)
        return dt.strftime("%Y-%m-%d") if dt else val

    exprs = []
    for col in df.columns:
        s = df[col]
        if s.dtype == pl.Date:
            exprs.append(pl.col(col))
        elif str(s.dtype).startswith("Datetime"):
            exprs.append(pl.col(col).cast(pl.Date).alias(col))
        elif s.dtype == pl.String:
            hits, total = _count_parseable(s)
            if total > 0 and hits / total >= _DATE_NORMALIZE_THRESHOLD:
                normalized_expr = pl.col(col).map_elements(_to_iso, return_dtype=pl.String)
                if hits == total:
                    exprs.append(normalized_expr.str.to_date("%Y-%m-%d", strict=False).alias(col))
                else:
                    exprs.append(normalized_expr.alias(col))
            else:
                exprs.append(pl.col(col))
        else:
            exprs.append(pl.col(col))
    return df.select(exprs)


def coerce_types(df: pl.DataFrame) -> pl.DataFrame:
    """Promote all-numeric string columns to Int64 or Float64."""
    exprs = []
    for col in df.columns:
        if df[col].dtype == pl.String:
            non_null = df[col].drop_nulls()
            if len(non_null) == 0:
                exprs.append(pl.col(col))
                continue

            try:
                non_null.cast(pl.Int64, strict=True)
                exprs.append(pl.col(col).cast(pl.Int64, strict=False))
                continue
            except Exception:
                pass

            try:
                non_null.cast(pl.Float64, strict=True)
                exprs.append(pl.col(col).cast(pl.Float64, strict=False))
                continue
            except Exception:
                pass

            exprs.append(pl.col(col))
        else:
            exprs.append(pl.col(col))
    return df.select(exprs)


def remove_duplicates(df: pl.DataFrame) -> pl.DataFrame:
    """Remove exact duplicate rows, preserving original order."""
    return df.unique(maintain_order=True)
