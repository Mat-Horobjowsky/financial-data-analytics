import pandas as pd

_FIXED_START = ["rollup_level", "date"]
_FIXED_END = ["metric_id", "label", "value", "unit"]
_FIXED = set(_FIXED_START + _FIXED_END)


def build_long_metrics(df: pd.DataFrame, registry: dict) -> pd.DataFrame:
    if df.empty:
        return df.copy()
    seg_cols = sorted(c for c in df.columns if c not in _FIXED)
    return df[_FIXED_START + seg_cols + _FIXED_END].reset_index(drop=True)


def build_wide_metrics(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame()
    seg_cols = [c for c in df.columns if c not in _FIXED]
    index_cols = _FIXED_START + seg_cols
    wide = (
        df.set_index(index_cols + ["metric_id"])["value"]
        .unstack("metric_id")
        .reset_index()
    )
    wide.columns.name = None
    return wide


def build_metric_dictionary(registry: dict) -> pd.DataFrame:
    rows = [
        {
            "id": m["id"],
            "label": m["label"],
            "type": m["type"],
            "unit": m["unit"],
            "decimals": m["decimals"],
            "description": m["description"],
        }
        for m in registry["metrics"].values()
    ]
    return pd.DataFrame(rows, columns=["id", "label", "type", "unit", "decimals", "description"])
