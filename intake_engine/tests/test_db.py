import duckdb
import polars as pl
import pytest
from pathlib import Path
from typer.testing import CliRunner

from intake_engine.cli.main import app
from intake_engine.db.writer import load_to_duckdb, sanitize_table_name

runner = CliRunner()


# --- unit: load_to_duckdb ---

def test_load_to_duckdb_creates_file(tmp_path):
    df = pl.DataFrame({"name": ["Alice", "Bob"], "score": [90, 80]})
    db_path = tmp_path / "test.duckdb"
    count = load_to_duckdb(df, db_path, "my_table")
    assert db_path.exists()
    assert count == 2


def test_load_to_duckdb_table_row_count(tmp_path):
    df = pl.DataFrame({"name": ["Alice", "Bob", "Carol"], "score": [90, 80, 70]})
    db_path = tmp_path / "test.duckdb"
    load_to_duckdb(df, db_path, "my_table")
    with duckdb.connect(str(db_path)) as con:
        result = con.execute("SELECT COUNT(*) FROM my_table").fetchone()[0]
    assert result == 3


def test_load_to_duckdb_replaces_existing_table(tmp_path):
    db_path = tmp_path / "test.duckdb"
    df_big = pl.DataFrame({"name": ["Alice", "Bob"], "score": [90, 80]})
    df_small = pl.DataFrame({"name": ["Carol"], "score": [70]})
    load_to_duckdb(df_big, db_path, "my_table")
    load_to_duckdb(df_small, db_path, "my_table")
    with duckdb.connect(str(db_path)) as con:
        result = con.execute("SELECT COUNT(*) FROM my_table").fetchone()[0]
    assert result == 1


def test_load_to_duckdb_creates_parent_dirs(tmp_path):
    df = pl.DataFrame({"x": [1, 2]})
    db_path = tmp_path / "nested" / "dir" / "test.duckdb"
    load_to_duckdb(df, db_path, "t")
    assert db_path.exists()


# --- unit: sanitize_table_name ---

def test_sanitize_table_name_appends_clean():
    assert sanitize_table_name("sales") == "sales_clean"


def test_sanitize_table_name_replaces_hyphens():
    assert sanitize_table_name("my-file") == "my_file_clean"


def test_sanitize_table_name_replaces_spaces():
    assert sanitize_table_name("my file") == "my_file_clean"


def test_sanitize_table_name_provider_example():
    assert sanitize_table_name("provider_test") == "provider_test_clean"


# --- CLI: single file ---

def test_cli_run_db_creates_duckdb_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "sales.csv"
    f.write_text("name,score\nAlice,90\nBob,80\n")
    db_path = tmp_path / "analytics.duckdb"

    result = runner.invoke(app, ["run", str(f), "--db", str(db_path)])

    assert result.exit_code == 0, result.output
    assert db_path.exists()


def test_cli_run_db_table_name_is_stem_clean(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "provider_test.csv"
    f.write_text("name,score\nAlice,90\n")
    db_path = tmp_path / "out.duckdb"

    result = runner.invoke(app, ["run", str(f), "--db", str(db_path)])

    assert result.exit_code == 0, result.output
    with duckdb.connect(str(db_path)) as con:
        tables = [row[0] for row in con.execute("SHOW TABLES").fetchall()]
    assert "provider_test_clean" in tables


def test_cli_run_db_row_count_correct(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "data.csv"
    f.write_text("name,score\nAlice,90\nBob,80\nCarol,70\n")
    db_path = tmp_path / "analytics.duckdb"

    result = runner.invoke(app, ["run", str(f), "--db", str(db_path)])

    assert result.exit_code == 0, result.output
    with duckdb.connect(str(db_path)) as con:
        count = con.execute("SELECT COUNT(*) FROM data_clean").fetchone()[0]
    assert count == 3


def test_cli_run_db_output_line_printed(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "data.csv"
    f.write_text("name,score\nAlice,90\n")
    db_path = tmp_path / "analytics.duckdb"

    result = runner.invoke(app, ["run", str(f), "--db", str(db_path)])

    assert "DB ->" in result.output
    assert "data_clean" in result.output


def test_cli_run_no_db_does_not_create_duckdb_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "data.csv"
    f.write_text("name,score\nAlice,90\n")

    result = runner.invoke(app, ["run", str(f)])

    assert result.exit_code == 0
    assert not any(tmp_path.glob("*.duckdb"))


def test_cli_run_db_works_with_parquet_format(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    f = tmp_path / "data.csv"
    f.write_text("name,score\nAlice,90\nBob,80\n")
    db_path = tmp_path / "analytics.duckdb"

    result = runner.invoke(app, ["run", str(f), "--format", "parquet", "--db", str(db_path)])

    assert result.exit_code == 0, result.output
    assert (tmp_path / "outputs" / "data_clean.parquet").exists()
    assert db_path.exists()
    with duckdb.connect(str(db_path)) as con:
        count = con.execute("SELECT COUNT(*) FROM data_clean").fetchone()[0]
    assert count == 2


# --- CLI: batch mode ---

def test_cli_run_db_batch_creates_multiple_tables(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    folder = tmp_path / "incoming"
    folder.mkdir()
    (folder / "a.csv").write_text("name,score\nAlice,90\n")
    (folder / "b.csv").write_text("name,score\nBob,80\nCarol,70\n")
    db_path = tmp_path / "batch.duckdb"

    result = runner.invoke(app, ["run", str(folder), "--db", str(db_path)])

    assert result.exit_code == 0, result.output
    assert db_path.exists()
    with duckdb.connect(str(db_path)) as con:
        tables = {row[0] for row in con.execute("SHOW TABLES").fetchall()}
        a_count = con.execute("SELECT COUNT(*) FROM a_clean").fetchone()[0]
        b_count = con.execute("SELECT COUNT(*) FROM b_clean").fetchone()[0]
    assert "a_clean" in tables
    assert "b_clean" in tables
    assert a_count == 1
    assert b_count == 2


# --- unit: append mode ---

def test_append_creates_table_on_first_load(tmp_path):
    df = pl.DataFrame({"name": ["Alice", "Bob"], "score": [90, 80]})
    db_path = tmp_path / "test.duckdb"
    count = load_to_duckdb(df, db_path, "t", mode="append")
    assert count == 2


def test_append_adds_new_rows(tmp_path):
    db_path = tmp_path / "test.duckdb"
    df1 = pl.DataFrame({"name": ["Alice", "Bob"], "score": [90, 80]})
    df2 = pl.DataFrame({"name": ["Carol", "Dave"], "score": [70, 60]})
    load_to_duckdb(df1, db_path, "t", mode="append")
    count = load_to_duckdb(df2, db_path, "t", mode="append")
    assert count == 4


def test_append_skips_exact_duplicates(tmp_path):
    db_path = tmp_path / "test.duckdb"
    df = pl.DataFrame({"name": ["Alice", "Bob"], "score": [90, 80]})
    load_to_duckdb(df, db_path, "t", mode="append")
    count = load_to_duckdb(df, db_path, "t", mode="append")
    assert count == 2  # unchanged — all rows already present


def test_append_inserts_only_new_subset(tmp_path):
    db_path = tmp_path / "test.duckdb"
    df1 = pl.DataFrame({"name": ["Alice", "Bob", "Carol"], "score": [90, 80, 70]})
    df2 = pl.DataFrame({"name": ["Bob", "Carol", "Dave"], "score": [80, 70, 60]})
    load_to_duckdb(df1, db_path, "t", mode="append")
    count = load_to_duckdb(df2, db_path, "t", mode="append")
    assert count == 4  # Bob + Carol already present; only Dave inserted


def test_replace_mode_still_replaces(tmp_path):
    db_path = tmp_path / "test.duckdb"
    df_big = pl.DataFrame({"name": ["Alice", "Bob"], "score": [90, 80]})
    df_small = pl.DataFrame({"name": ["Carol"], "score": [70]})
    load_to_duckdb(df_big, db_path, "t", mode="replace")
    count = load_to_duckdb(df_small, db_path, "t", mode="replace")
    assert count == 1


def test_invalid_mode_raises(tmp_path):
    from intake_engine.utils.errors import DBError
    df = pl.DataFrame({"x": [1]})
    with pytest.raises(DBError, match="Invalid db_mode"):
        load_to_duckdb(df, tmp_path / "t.duckdb", "t", mode="upsert")


# --- CLI: append mode ---

def test_cli_db_append_mode_accumulates_rows(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    db_path = tmp_path / "analytics.duckdb"
    cfg = tmp_path / "pipeline.yaml"
    cfg.write_text("db_mode: append\n")

    (tmp_path / "week1.csv").write_text("name,score\nAlice,90\nBob,80\n")
    runner.invoke(app, ["run", "week1.csv", "--db", str(db_path), "--config", str(cfg)])

    (tmp_path / "week2.csv").write_text("name,score\nCarol,70\nDave,60\n")
    result = runner.invoke(app, ["run", "week2.csv", "--db", str(db_path), "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    with duckdb.connect(str(db_path)) as con:
        # Both weekly tables exist (different stems), each correct
        assert con.execute("SELECT COUNT(*) FROM week1_clean").fetchone()[0] == 2
        assert con.execute("SELECT COUNT(*) FROM week2_clean").fetchone()[0] == 2


def test_cli_db_append_same_table_deduplicates(tmp_path, monkeypatch):
    """Same file processed twice in append mode — second run adds 0 rows."""
    monkeypatch.chdir(tmp_path)
    db_path = tmp_path / "analytics.duckdb"
    cfg = tmp_path / "pipeline.yaml"
    cfg.write_text("db_mode: append\n")

    (tmp_path / "data.csv").write_text("name,score\nAlice,90\nBob,80\n")
    runner.invoke(app, ["run", "data.csv", "--db", str(db_path), "--config", str(cfg)])
    runner.invoke(app, ["run", "data.csv", "--db", str(db_path), "--config", str(cfg)])

    with duckdb.connect(str(db_path)) as con:
        count = con.execute("SELECT COUNT(*) FROM data_clean").fetchone()[0]
    assert count == 2  # still 2 — duplicates skipped


def test_cli_db_append_mode_from_config(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data.csv").write_text("name,score\nAlice,90\n")
    cfg = tmp_path / "pipeline.yaml"
    cfg.write_text("db_mode: append\n")
    db_path = tmp_path / "out.duckdb"

    result = runner.invoke(app, ["run", "data.csv", "--db", str(db_path), "--config", str(cfg)])

    assert result.exit_code == 0, result.output
    assert db_path.exists()


def test_cli_run_db_batch_summary_mentions_db_path(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    folder = tmp_path / "incoming"
    folder.mkdir()
    (folder / "a.csv").write_text("name,score\nAlice,90\n")
    db_path = tmp_path / "analytics.duckdb"

    result = runner.invoke(app, ["run", str(folder), "--db", str(db_path)])

    assert result.exit_code == 0, result.output
    assert "analytics.duckdb" in result.output


# --- CLI: --db-mode flag ---

def test_cli_db_mode_flag_append_recognized(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data.csv").write_text("name,score\nAlice,90\nBob,80\n")
    db_path = tmp_path / "out.duckdb"

    result = runner.invoke(app, ["run", "data.csv", "--db", str(db_path), "--db-mode", "append"])

    assert result.exit_code == 0, result.output
    with duckdb.connect(str(db_path)) as con:
        assert con.execute("SELECT COUNT(*) FROM data_clean").fetchone()[0] == 2


def test_cli_db_mode_flag_replace_recognized(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data.csv").write_text("name,score\nAlice,90\nBob,80\n")
    db_path = tmp_path / "out.duckdb"

    # First load
    runner.invoke(app, ["run", "data.csv", "--db", str(db_path), "--db-mode", "replace"])
    # Replace with fewer rows
    (tmp_path / "data.csv").write_text("name,score\nCarol,70\n")
    result = runner.invoke(app, ["run", "data.csv", "--db", str(db_path), "--db-mode", "replace"])

    assert result.exit_code == 0, result.output
    with duckdb.connect(str(db_path)) as con:
        assert con.execute("SELECT COUNT(*) FROM data_clean").fetchone()[0] == 1


def test_cli_db_mode_flag_invalid_exits_with_error(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "data.csv").write_text("name,score\nAlice,90\n")
    db_path = tmp_path / "out.duckdb"

    result = runner.invoke(app, ["run", "data.csv", "--db", str(db_path), "--db-mode", "upsert"])

    assert result.exit_code == 1
    assert "upsert" in result.output


def test_cli_db_mode_flag_overrides_yaml_config(tmp_path, monkeypatch):
    """--db-mode flag takes precedence over config file db_mode."""
    monkeypatch.chdir(tmp_path)
    (tmp_path / "pipeline.yaml").write_text("db_mode: replace\n")
    db_path = tmp_path / "out.duckdb"

    # Run twice with --db-mode append, overriding the replace in config
    (tmp_path / "data.csv").write_text("name,score\nAlice,90\nBob,80\n")
    runner.invoke(app, ["run", "data.csv", "--db", str(db_path),
                        "--config", "pipeline.yaml", "--db-mode", "append"])
    (tmp_path / "data.csv").write_text("name,score\nCarol,70\n")
    result = runner.invoke(app, ["run", "data.csv", "--db", str(db_path),
                                 "--config", "pipeline.yaml", "--db-mode", "append"])

    assert result.exit_code == 0, result.output
    with duckdb.connect(str(db_path)) as con:
        # All three rows present — flag overrode the replace config
        assert con.execute("SELECT COUNT(*) FROM data_clean").fetchone()[0] == 3
