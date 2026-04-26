"""Tests for delimiter auto-detection (v1.3)."""
import pytest

from intake_engine.loader.loader import _sniff_delimiter, load_file
from intake_engine.utils.errors import LoadError


# --- _sniff_delimiter unit tests ---

def test_sniff_comma():
    text = "name,revenue,date\nAlice,100,2024-01-01\nBob,200,2024-02-01\n"
    assert _sniff_delimiter(text) == ","


def test_sniff_tab():
    text = "name\trevenue\tdate\nAlice\t100\t2024-01-01\nBob\t200\t2024-02-01\n"
    assert _sniff_delimiter(text) == "\t"


def test_sniff_semicolon():
    text = "name;revenue;date\nAlice;100;2024-01-01\nBob;200;2024-02-01\n"
    assert _sniff_delimiter(text) == ";"


def test_sniff_pipe():
    text = "name|revenue|date\nAlice|100|2024-01-01\nBob|200|2024-02-01\n"
    assert _sniff_delimiter(text) == "|"


def test_sniff_single_column_falls_back_to_comma():
    # No delimiter present — must not guess a wrong one
    text = "name\nAlice\nBob\n"
    assert _sniff_delimiter(text) == ","


def test_sniff_empty_text_falls_back_to_comma():
    assert _sniff_delimiter("") == ","
    assert _sniff_delimiter("   \n  \n") == ","


# --- load_file integration tests ---

def test_load_tsv_via_csv_extension(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text("name\trevenue\tcity\nAlice\t950\tLondon\nBob\t1200\tParis\n")
    df = load_file(f)
    assert df.shape == (2, 3)
    assert df.columns == ["name", "revenue", "city"]
    assert df["revenue"].to_list() == [950, 1200]


def test_load_tsv_extension(tmp_path):
    f = tmp_path / "data.tsv"
    f.write_text("name\trevenue\tcity\nAlice\t950\tLondon\nBob\t1200\tParis\n")
    df = load_file(f)
    assert df.shape == (2, 3)
    assert df["city"].to_list() == ["London", "Paris"]


def test_load_semicolon_csv(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text("name;revenue;city\nAlice;950;London\nBob;1200;Paris\n")
    df = load_file(f)
    assert df.shape == (2, 3)
    assert df["revenue"].to_list() == [950, 1200]


def test_load_pipe_csv(tmp_path):
    f = tmp_path / "data.csv"
    f.write_text("name|revenue|city\nAlice|950|London\nBob|1200|Paris\n")
    df = load_file(f)
    assert df.shape == (2, 3)
    assert df["name"].to_list() == ["Alice", "Bob"]


def test_comma_csv_regression(tmp_path):
    """Standard comma CSV must be unaffected."""
    f = tmp_path / "data.csv"
    f.write_text("name,revenue,city\nAlice,950,London\nBob,1200,Paris\n")
    df = load_file(f)
    assert df.shape == (2, 3)
    assert df["revenue"].to_list() == [950, 1200]


def test_semicolon_csv_with_quoted_commas(tmp_path):
    """Semicolon file where values contain commas (quoted) — delimiter still detected."""
    f = tmp_path / "data.csv"
    f.write_text('name;notes;revenue\nAlice;"hello, world";950\nBob;"foo, bar";1200\n')
    df = load_file(f)
    assert df.shape == (2, 3)
    assert df["revenue"].to_list() == [950, 1200]


def test_tsv_unsupported_extension_raises(tmp_path):
    """Non-CSV/TSV/Excel extensions still raise LoadError."""
    f = tmp_path / "data.json"
    f.write_text("{}")
    with pytest.raises(LoadError, match="Unsupported file type"):
        load_file(f)


def test_tsv_null_values_recognised(tmp_path):
    """NULL sentinel values in TSV files are converted to null."""
    f = tmp_path / "data.tsv"
    f.write_text("name\trevenue\nAlice\t950\nBob\tN/A\n")
    df = load_file(f)
    assert df["revenue"].null_count() == 1
