import pandas as pd

_NON_SEGMENT = {"rollup_level", "date", "metric_id", "label", "value", "unit"}
_NEW_COLS = ["prior_period_value", "period_change", "period_change_pct"]


def get_group_columns(df: pd.DataFrame) -> list[str]:
    return [c for c in df.columns if c not in _NON_SEGMENT]


def add_prior_period_metrics(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        result = df.copy()
        for col in _NEW_COLS:
            result[col] = pd.Series(dtype=float)
        return result

    result = df.copy()
    seg_cols = get_group_columns(result)
    group_cols = ["rollup_level"] + seg_cols + ["metric_id"]

    result = result.sort_values(group_cols + ["date"]).reset_index(drop=True)

    result["prior_period_value"] = (
        result.groupby(group_cols, dropna=False)["value"].shift(1)
    )
    result["period_change"] = result["value"] - result["prior_period_value"]

    prior = result["prior_period_value"]
    safe_prior = prior.where(prior != 0)
    result["period_change_pct"] = result["period_change"] / safe_prior * 100

    return result
