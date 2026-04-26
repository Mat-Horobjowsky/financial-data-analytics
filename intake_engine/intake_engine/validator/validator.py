import re
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

from intake_engine.cleaner import to_snake
from intake_engine.models.config import ColumnRule
from intake_engine.models.validation import ValidationReport

_EXPECTED_TYPES: dict[str, set] = {
    "numeric": {pl.Int64, pl.Float64},
    "date": {pl.Date},
    "string": {pl.String},
}


def _resolve_col(name: str, columns: list[str]) -> str | None:
    """Return the column name as it appears in columns, trying exact then snake_case."""
    if name in columns:
        return name
    snake = to_snake(name)
    return snake if snake in columns else None

_LOOKS_LIKE_DATE_RE = re.compile(r"\b\d{1,4}[/\-]\d{1,2}[/\-]\d{1,4}\b")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_DATE_NAME_HINTS = frozenset({"date", "time", "posted", "created", "updated", "start", "end", "due", "expir", "at", "on"})

_NULL_RATE_WARN = 0.3
_DUPE_RATE_WARN = 0.3
_DATE_LOOKS_LIKE_THRESHOLD = 0.2


def validate_file(
    path: Path,
    raw_df: pl.DataFrame,
    clean_df: pl.DataFrame,
    required_columns: list[str] | None = None,
    null_threshold: float = _NULL_RATE_WARN,
    duplicate_threshold: float = _DUPE_RATE_WARN,
    column_rules: dict[str, ColumnRule] | None = None,
) -> ValidationReport:
    """Run quality checks against the cleaned dataframe.

    raw_df is used only for parse-quality checks (empty file, single-column
    detection) and to compute duplicate_rate versus clean_df.  All data-quality
    checks — null rates, required columns, date column inspection — operate
    exclusively on clean_df and its column names (snake_case after cleaning).
    required_columns must therefore be specified in snake_case.

    null_threshold and duplicate_threshold control the warn level (0.0–1.0);
    defaults match module constants but can be overridden via pipeline config.
    """
    issues: list[str] = []
    warnings: list[str] = []

    rows_raw = raw_df.shape[0]
    rows_clean = clean_df.shape[0]

    # parse-quality checks (raw_df)
    if rows_raw == 0:
        issues.append("empty file: 0 rows loaded")
    elif rows_clean == 0:
        issues.append("0 rows remain after cleaning")

    if raw_df.shape[1] == 1 and path.suffix.lower() == ".csv":
        warnings.append(
            "suspicious single-column parse: CSV loaded as 1 column — file may use a non-comma delimiter"
        )

    # data-quality checks (clean_df) ----------------------------------------

    for col in (required_columns or []):
        if col not in clean_df.columns:
            snake = to_snake(col)
            if snake in clean_df.columns:
                warnings.append(
                    f"required column '{col}' was renamed to '{snake}' during cleaning"
                    f" — update required_columns to use '{snake}'"
                )
            else:
                issues.append(f"required column missing: '{col}'")

    dup_count = rows_raw - rows_clean
    dup_rate = dup_count / rows_raw if rows_raw > 0 else 0.0
    if dup_rate > duplicate_threshold and dup_count >= 2:
        warnings.append(f"high duplicate rate: {dup_rate:.1%} of rows are duplicates")

    null_summary: dict[str, float] = {}
    for col in clean_df.columns:
        rate = clean_df[col].null_count() / rows_clean if rows_clean > 0 else 0.0
        null_summary[col] = round(rate, 4)
        if rate > null_threshold:
            warnings.append(f"high null rate in '{col}': {rate:.1%}")

    for col in clean_df.columns:
        if not (set(col.split("_")) & _DATE_NAME_HINTS):
            continue
        series = clean_df[col].drop_nulls()
        if len(series) == 0 or series.dtype != pl.String:
            continue
        sample = [str(v) for v in series[:50]]
        date_like = sum(1 for v in sample if _LOOKS_LIKE_DATE_RE.search(v))
        if date_like / len(sample) >= _DATE_LOOKS_LIKE_THRESHOLD:
            iso_count = sum(1 for v in sample if _ISO_DATE_RE.match(v))
            if iso_count < len(sample):
                warnings.append(
                    f"date-like column '{col}': mixed valid/invalid date values remain after cleaning"
                )

    for key, rule in (column_rules or {}).items():
        # After apply_column_map the column lives under rule.rename (if set) or the key
        col = _resolve_col(rule.rename or key, clean_df.columns)
        if col is None:
            continue
        if not rule.nullable and clean_df[col].null_count() > 0:
            warnings.append(
                f"column '{col}' has {clean_df[col].null_count()} null(s) but is configured as nullable: false"
            )
        if rule.type:
            valid_types = _EXPECTED_TYPES.get(rule.type)
            if valid_types and clean_df[col].dtype not in valid_types:
                warnings.append(
                    f"column '{col}': expected type '{rule.type}' but got '{clean_df[col].dtype}'"
                )

    status = "fail" if issues else ("warn" if warnings else "pass")

    return ValidationReport(
        file_name=path.name,
        status=status,
        issues=issues,
        warnings=warnings,
        rows_loaded=rows_raw,
        row_count=rows_clean,
        columns=clean_df.shape[1],
        duplicate_rate=round(dup_rate, 4),
        null_summary=null_summary,
        run_timestamp=datetime.now(timezone.utc).isoformat(),
    )
