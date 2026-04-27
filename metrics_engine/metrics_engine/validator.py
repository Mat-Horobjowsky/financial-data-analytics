from dataclasses import dataclass, field

import pandas as pd

from metrics_engine.schema import NormalizeResult


@dataclass
class ValidationReport:
    status: str
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def _required_cols(metrics: dict) -> set[str]:
    cols: set[str] = set()
    for m in metrics.values():
        t = m["type"]
        if t == "sum":
            cols.add(m["source_col"])
        else:
            cols.add(m["numerator"])
            cols.add(m["denominator"])
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

    req_cols = _required_cols(metrics)
    denom_cols = _denominator_cols(metrics)

    # Hard errors: missing metric input columns
    missing_cols = {c for c in req_cols if c not in df.columns}
    for col in sorted(missing_cols):
        errors.append(f"Missing required metric input column: '{col}'")

    present_req = req_cols - missing_cols

    # Hard errors: nulls in metric inputs
    for col in sorted(present_req):
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

    # Warnings: leased_mw > capacity_mw
    if "leased_mw" in df.columns and "capacity_mw" in df.columns:
        mask = df["leased_mw"] > df["capacity_mw"]
        n = int(mask.sum())
        if n > 0:
            warnings.append(
                f"{n} row(s) where leased_mw exceeds capacity_mw"
            )

    # Warnings: negative revenue
    if "revenue" in df.columns:
        n = int((df["revenue"] < 0).sum())
        if n > 0:
            warnings.append(f"{n} row(s) with negative revenue")

    # Warnings: numeric outliers in metric input columns
    for col in sorted(present_req):
        if pd.api.types.is_numeric_dtype(df[col]):
            _check_outliers(df[col], col, warnings)

    if errors:
        status = "failed"
    elif warnings:
        status = "passed_with_warnings"
    else:
        status = "passed"
    return ValidationReport(status=status, errors=errors, warnings=warnings)
