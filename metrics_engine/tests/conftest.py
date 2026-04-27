from pathlib import Path

import pandas as pd
import pytest

DATA_DIR = Path(__file__).parent.parent / "data"
CONFIG_DIR = Path(__file__).parent.parent / "config"


@pytest.fixture
def sample_csv_path() -> Path:
    return DATA_DIR / "sample_data_centers.csv"


@pytest.fixture
def schema_path() -> Path:
    return CONFIG_DIR / "schema.yaml"


@pytest.fixture
def raw_df(sample_csv_path) -> pd.DataFrame:
    from metrics_engine.loader import load
    return load(sample_csv_path)


@pytest.fixture
def normalize_result(raw_df, schema_path):
    from metrics_engine.schema import load_schema, normalize
    return normalize(raw_df, load_schema(schema_path))


@pytest.fixture
def normalized_df(normalize_result) -> pd.DataFrame:
    return normalize_result.df


@pytest.fixture
def minimal_valid_df() -> pd.DataFrame:
    return pd.DataFrame({
        "date": pd.to_datetime(["2024-01-01", "2024-01-01"]),
        "region": ["EMEA", "NAM"],
        "provider": ["Equinix", "CyrusOne"],
        "revenue": [1200000.0, 2100000.0],
        "capacity_mw": [50.0, 80.0],
        "leased_mw": [38.5, 67.2],
        "contracted_kw": [38500.0, 67200.0],
    })
