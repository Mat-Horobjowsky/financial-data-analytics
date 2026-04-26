from pathlib import Path

import polars as pl

from intake_engine.utils.errors import ExportError


def export_csv(df: pl.DataFrame, output_path: Path) -> None:
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.write_csv(output_path)
    except Exception as e:
        raise ExportError(f"Failed to write '{output_path}': {e}") from e


def export_parquet(df: pl.DataFrame, output_path: Path) -> None:
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        df.write_parquet(output_path)
    except Exception as e:
        raise ExportError(f"Failed to write '{output_path}': {e}") from e
