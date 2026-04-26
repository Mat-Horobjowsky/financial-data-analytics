import polars as pl

from intake_engine.cleaner.cleaner import to_snake
from intake_engine.models.config import ColumnRule


def apply_column_selection(df: pl.DataFrame, select_columns: list[str]) -> pl.DataFrame:
    """Return df with only the specified columns in the given order.

    Columns in select_columns that are absent from df are silently skipped
    (caller should warn). Returns df unchanged if select_columns is empty.
    """
    if not select_columns:
        return df
    available = [col for col in select_columns if col in df.columns]
    return df.select(available) if available else df


def apply_column_map(df: pl.DataFrame, columns: dict[str, ColumnRule]) -> pl.DataFrame:
    """Apply rename rules from the columns config block.

    Resolves each key by exact match first, then by to_snake(key), so the config
    can use either the raw header name ("Total Revenue") or the snake_cased name
    ("total_revenue") — whichever is more natural to write.
    """
    rename_map: dict[str, str] = {}
    for key, rule in columns.items():
        if not rule.rename:
            continue
        if key in df.columns:
            rename_map[key] = rule.rename
        else:
            snake = to_snake(key)
            if snake in df.columns:
                rename_map[snake] = rule.rename
    return df.rename(rename_map) if rename_map else df
