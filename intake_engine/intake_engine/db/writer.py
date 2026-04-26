import re
import tempfile
from pathlib import Path

import polars as pl

from intake_engine.utils.errors import DBError


def sanitize_table_name(stem: str) -> str:
    """Return a DuckDB-safe table name: {stem}_clean with non-word chars replaced by _."""
    return re.sub(r"[^\w]", "_", f"{stem}_clean")


def load_to_duckdb(
    df: pl.DataFrame,
    db_path: Path,
    table_name: str,
    mode: str = "replace",
) -> int:
    """Write df into a DuckDB table.

    mode="replace"  — CREATE OR REPLACE (default, current behaviour).
    mode="append"   — Insert rows not already present, using full-row set difference
                      (EXCEPT). Creates the table on first call; subsequent calls add
                      only rows absent from the existing table.

    Serializes df to a temporary Parquet file (Polars native, no pyarrow needed).
    Returns the total row count of the table after the operation.
    """
    try:
        import duckdb
    except ImportError as exc:
        raise ImportError(
            "duckdb is required for --db support. Install it with: pip install duckdb"
        ) from exc

    if mode not in ("replace", "append"):
        raise DBError(f"Invalid db_mode '{mode}': expected 'replace' or 'append'")

    db_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_pq = Path(tempfile.mktemp(suffix=".parquet", dir=db_path.parent))
    try:
        df.write_parquet(tmp_pq)
        with duckdb.connect(str(db_path)) as con:
            if mode == "replace":
                con.execute(
                    f'CREATE OR REPLACE TABLE "{table_name}" AS SELECT * FROM read_parquet(?)',
                    [str(tmp_pq)],
                )
            else:
                table_exists = con.execute(
                    "SELECT COUNT(*) FROM information_schema.tables "
                    "WHERE table_name = ? AND table_schema = 'main'",
                    [table_name],
                ).fetchone()[0] > 0
                if not table_exists:
                    con.execute(
                        f'CREATE TABLE "{table_name}" AS SELECT * FROM read_parquet(?)',
                        [str(tmp_pq)],
                    )
                else:
                    con.execute(
                        f'INSERT INTO "{table_name}" '
                        f'SELECT * FROM read_parquet(?) '
                        f'EXCEPT SELECT * FROM "{table_name}"',
                        [str(tmp_pq)],
                    )
            return con.execute(f'SELECT COUNT(*) FROM "{table_name}"').fetchone()[0]
    except DBError:
        raise
    except Exception as e:
        raise DBError(
            f"Failed to load into DuckDB '{db_path}' table '{table_name}': {e}"
        ) from e
    finally:
        tmp_pq.unlink(missing_ok=True)
