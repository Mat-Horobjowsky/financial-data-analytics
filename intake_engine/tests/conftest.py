import polars as pl
import pytest


@pytest.fixture
def dirty_df() -> pl.DataFrame:
    return pl.DataFrame({
        "  First Name ": ["Alice", " Bob ", "  Charlie", "Alice"],
        "Last-Name":     ["Smith", "Jones", "  Brown  ", "Smith"],
        "Age":           ["30", "25", "40", "30"],
        "Score":         ["95.5", "87.0", "92.3", "95.5"],
        "Notes":         ["  Active ", "", "  ", "  Active "],
    })
