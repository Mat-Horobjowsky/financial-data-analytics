import pandas as pd


class CalculatorError(Exception):
    pass


_AGG_TYPES = {"sum", "ratio", "per_unit"}
_COUNT_TYPES = {"count", "conditional_count", "completion_pct"}


def _rollup_label(rollup: list) -> str:
    return "date_only" if not rollup else "date_" + "_".join(rollup)


def _input_cols(metrics: dict) -> set[str]:
    """Numeric columns required for aggregation-based metrics."""
    cols: set[str] = set()
    for m in metrics.values():
        t = m["type"]
        if t == "sum":
            cols.add(m["source_col"])
        elif t in ("ratio", "per_unit"):
            cols.add(m["numerator"])
            cols.add(m["denominator"])
    return cols


def _condition_cols(metrics: dict) -> set[str]:
    """String columns required for count-based metrics."""
    cols: set[str] = set()
    for m in metrics.values():
        if m["type"] in ("conditional_count", "completion_pct"):
            cols.add(m["source_col"])
    return cols


def _compute_rollup(
    df: pd.DataFrame,
    group_cols: list[str],
    metrics: dict,
    rollup_label: str,
) -> pd.DataFrame:
    agg_metrics = {mid: m for mid, m in metrics.items() if m["type"] in _AGG_TYPES}
    count_metrics = {mid: m for mid, m in metrics.items() if m["type"] in _COUNT_TYPES}

    frames = []

    if agg_metrics:
        agg_cols = sorted(_input_cols(agg_metrics))
        grouped = df.groupby(group_cols)[agg_cols].sum().reset_index()

        for metric_id, m in agg_metrics.items():
            t = m["type"]
            if t == "sum":
                grouped[metric_id] = grouped[m["source_col"]]
            elif t == "ratio":
                grouped[metric_id] = grouped[m["numerator"]] / grouped[m["denominator"]] * m["scale"]
            elif t == "per_unit":
                grouped[metric_id] = grouped[m["numerator"]] / grouped[m["denominator"]]

        long = grouped.melt(
            id_vars=group_cols,
            value_vars=list(agg_metrics.keys()),
            var_name="metric_id",
            value_name="value",
        )
        long["label"] = long["metric_id"].map({mid: m["label"] for mid, m in agg_metrics.items()})
        long["unit"] = long["metric_id"].map({mid: m["unit"] for mid, m in agg_metrics.items()})
        long["rollup_level"] = rollup_label
        frames.append(long)

    if count_metrics:
        rows = []
        for key, gdf in df.groupby(group_cols):
            if not isinstance(key, tuple):
                key = (key,)
            gd = dict(zip(group_cols, key))
            for mid, m in count_metrics.items():
                t = m["type"]
                if t == "count":
                    val = float(len(gdf))
                elif t == "conditional_count":
                    val = float(gdf[m["source_col"]].isin(m["condition_values"]).sum())
                elif t == "completion_pct":
                    total = len(gdf)
                    complete = gdf[m["source_col"]].isin(m["complete_values"]).sum()
                    val = float(complete) / total * m["scale"] if total > 0 else 0.0
                else:
                    raise CalculatorError(f"Unsupported metric type: {t!r}")
                rows.append({
                    **gd,
                    "metric_id": mid,
                    "label": m["label"],
                    "value": val,
                    "unit": m["unit"],
                    "rollup_level": rollup_label,
                })
        if rows:
            frames.append(pd.DataFrame(rows))

    if not frames:
        return pd.DataFrame(
            columns=["rollup_level", "date", "metric_id", "label", "value", "unit"]
        )

    return _order_columns(pd.concat(frames, ignore_index=True))


def _order_columns(df: pd.DataFrame) -> pd.DataFrame:
    fixed_start = ["rollup_level", "date"]
    fixed_end = ["metric_id", "label", "value", "unit"]
    seg_cols = sorted(c for c in df.columns if c not in fixed_start + fixed_end)
    return df[fixed_start + seg_cols + fixed_end]


def calculate(df: pd.DataFrame, registry: dict) -> pd.DataFrame:
    metrics = registry["metrics"]
    segment_rollups = registry["segment_rollups"]

    missing = (_input_cols(metrics) | _condition_cols(metrics)) - set(df.columns)
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
