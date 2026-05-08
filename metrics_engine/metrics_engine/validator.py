from dataclasses import dataclass, field

import pandas as pd

from metrics_engine.schema import NormalizeResult


@dataclass
class ValidationReport:
    status: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _required_numeric_cols(metrics: dict) -> set[str]:
    """Numeric source columns required for sum/ratio/per_unit metrics."""
    cols: set[str] = set()
    for m in metrics.values():
        t = m["type"]
        if t == "sum":
            cols.add(m["source_col"])
        elif t in ("ratio", "per_unit"):
            cols.add(m["numerator"])
            cols.add(m["denominator"])
    return cols


def _required_condition_cols(metrics: dict) -> set[str]:
    """String source columns required for conditional_count/completion_pct metrics."""
    cols: set[str] = set()
    for m in metrics.values():
        if m["type"] in ("conditional_count", "completion_pct"):
            cols.add(m["source_col"])
    return cols


def _denominator_cols(metrics: dict) -> set[str]:
    return {
        m["denominator"]
        for m in metrics.values()
        if m["type"] in ("ratio", "per_unit")
    }


def _check_outliers(series: pd.Series, col_name: str, warnings: list[str]) -> None:
    s = series.dropna()
    if len(s) < 4:
        return
    q1 = s.quantile(0.25)
    q3 = s.quantile(0.75)
    iqr = q3 - q1
    if iqr == 0:
        return
    lo = q1 - 1.5 * iqr
    hi = q3 + 1.5 * iqr
    n = int(((s < lo) | (s > hi)).sum())
    if n > 0:
        warnings.append(
            f"{n} outlier value(s) in '{col_name}' (outside [{lo:.2f}, {hi:.2f}])"
        )


def validate(result: NormalizeResult, registry: dict) -> ValidationReport:
    errors: list[str] = []
    warnings: list[str] = []

    df = result.df
    metrics = registry["metrics"]
    segment_rollups = registry["segment_rollups"]

    numeric_cols = _required_numeric_cols(metrics)
    cond_cols = _required_condition_cols(metrics)
    denom_cols = _denominator_cols(metrics)

    # Hard errors: missing numeric metric input columns
    missing_numeric = {c for c in numeric_cols if c not in df.columns}
    for col in sorted(missing_numeric):
        errors.append(f"Missing required metric input column: '{col}'")

    # Hard errors: missing condition columns
    missing_cond = {c for c in cond_cols if c not in df.columns}
    for col in sorted(missing_cond):
        errors.append(f"Missing required condition column: '{col}'")

    present_numeric = numeric_cols - missing_numeric

    # Hard errors: nulls in numeric metric inputs
    for col in sorted(present_numeric):
        if df[col].isna().any():
            errors.append(f"Null values found in metric input column: '{col}'")

    # Hard errors: null dates
    if "date" in df.columns and df["date"].isna().any():
        errors.append("Null/unparseable values found in 'date' column")

    # Hard errors: zero denominators
    for col in sorted(denom_cols):
        if col in df.columns and not df[col].isna().any():
            if (df[col] == 0).any():
                errors.append(f"Zero values in denominator column: '{col}'")

    # Warnings: dropped columns from schema normalization
    for col in result.dropped_columns:
        warnings.append(f"Column '{col}' was dropped (not recognized by schema)")

    # Warnings: missing optional segments + affected rollups
    missing_segs = set(result.missing_segments)
    for seg in sorted(missing_segs):
        affected = [r for r in segment_rollups if seg in r]
        warnings.append(
            f"Optional segment column '{seg}' is missing from data; "
            f"rollup(s) {affected} will be skipped"
        )

    # Warnings: duplicate full rows
    n_full_dup = int(df.duplicated().sum())
    if n_full_dup > 0:
        warnings.append(f"{n_full_dup} duplicate row(s) found (exact match)")

    # Warnings: duplicate date+segment key rows — one check per registry rollup
    if "date" in df.columns:
        for rollup in segment_rollups:
            if all(c in df.columns for c in rollup):
                key_cols = ["date"] + list(rollup)
                n_dup = int(df.duplicated(subset=key_cols).sum())
                if n_dup > 0:
                    rollup_name = "date_only" if not rollup else "date_" + "_".join(rollup)
                    key_desc = (
                        "the same date"
                        if not rollup
                        else "the same date+" + "+".join(rollup) + " key"
                    )
                    warnings.append(
                        f"{n_dup} additional row(s) share {key_desc} "
                        f"for rollup {rollup_name}; values will be aggregated."
                    )

    # Domain-specific warnings — guarded by column presence; safe for non-market data
    if "leased_mw" in df.columns and "capacity_mw" in df.columns:
        mask = df["leased_mw"] > df["capacity_mw"]
        n = int(mask.sum())
        if n > 0:
            warnings.append(
                f"{n} row(s) where leased_mw exceeds capacity_mw"
            )

    if "revenue" in df.columns:
        n = int((df["revenue"] < 0).sum())
        if n > 0:
            warnings.append(f"{n} row(s) with negative revenue")

    # Warnings: numeric outliers in numeric metric input columns only
    for col in sorted(present_numeric):
        if pd.api.types.is_numeric_dtype(df[col]):
            _check_outliers(df[col], col, warnings)

    if errors:
        status = "failed"
    elif warnings:
        status = "passed_with_warnings"
    else:
        status = "passed"
    return ValidationReport(status=status, errors=errors, warnings=warnings)
