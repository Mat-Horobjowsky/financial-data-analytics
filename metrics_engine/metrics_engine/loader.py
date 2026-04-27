from pathlib import Path

import pandas as pd


class LoaderError(Exception):
    pass


_SUPPORTED = {".csv", ".xlsx"}


def load(file_path: str | Path) -> pd.DataFrame:
    path = Path(file_path)

    if not path.exists():
        raise LoaderError(f"File not found: {path}")

    suffix = path.suffix.lower()
    if suffix not in _SUPPORTED:
        raise LoaderError(
            f"Unsupported file type '{suffix}'. Must be one of: {', '.join(_SUPPORTED)}"
        )

    try:
        if suffix == ".csv":
            df = pd.read_csv(path)
        else:
            df = pd.read_excel(path, engine="openpyxl")
    except pd.errors.EmptyDataError:
        raise LoaderError(f"File is empty: {path}")

    if df.empty:
        raise LoaderError(f"File is empty: {path}")

    return df
