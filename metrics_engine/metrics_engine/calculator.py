import pandas as pd


class CalculatorError(Exception):
    pass


def _rollup_label(rollup: list) -> str:
    return "date_only" if not rollup else "date_" + "_".join(rollup)


def _input_cols(metrics: dict) -> set[str]:
    cols: set[str] = set()
    for m in metrics.values():
        if m["type"] == "sum":
            cols.add(m["source_col"])
        else:
            cols.add(m["numerator"])
            cols.add(m["denominator"])
    return cols


def _compute_rollup(
    df: pd.DataFrame,
    group_cols: list[str],
    metrics: dict,
    rollup_label: str,
) -> pd.DataFrame:
    agg_cols = sorted(_input_cols(metrics))
    grouped = df.groupby(group_cols)[agg_cols].sum().reset_index()

    for metric_id, m in metrics.items():
        t = m["type"]
        if t == "sum":
            grouped[metric_id] = grouped[m["source_col"]]
        elif t == "ratio":
            grouped[metric_id] = grouped[m["numerator"]] / grouped[m["denominator"]] * m["scale"]
        elif t == "per_unit":
            grouped[metric_id] = grouped[m["numerator"]] / grouped[m["denominator"]]
        else:
            raise CalculatorError(f"Unsupported metric type: {t!r}")

    metric_ids = list(metrics.keys())
    long = grouped.melt(
        id_vars=group_cols,
        value_vars=metric_ids,
        var_name="metric_id",
        value_name="value",
    )
    long["label"] = long["metric_id"].map({mid: m["label"] for mid, m in metrics.items()})
    long["unit"] = long["metric_id"].map({mid: m["unit"] for mid, m in metrics.items()})
    long["rollup_level"] = rollup_label
    return long


def _order_columns(df: pd.DataFrame) -> pd.DataFrame:
    fixed_start = ["rollup_level", "date"]
    fixed_end = ["metric_id", "label", "value", "unit"]
    seg_cols = sorted(c for c in df.columns if c not in fixed_start + fixed_end)
    return df[fixed_start + seg_cols + fixed_end]


def calculate(df: pd.DataFrame, registry: dict) -> pd.DataFrame:
    metrics = registry["metrics"]
    segment_rollups = registry["segment_rollups"]

    missing = _input_cols(metrics) - set(df.columns)
    if missing:
        raise CalculatorError(
            f"DataFrame missing required metric input column(s): {sorted(missing)}"
        )

    frames = []
    for rollup in segment_rollups:
        if any(c not in df.columns for c in rollup):
            continue
        frames.append(
            _compute_rollup(df, ["date"] + list(rollup), metrics, _rollup_label(rollup))
        )

    if not frames:
        return pd.DataFrame(
            columns=["rollup_level", "date", "metric_id", "label", "value", "unit"]
        )

    return _order_columns(pd.concat(frames, ignore_index=True))
