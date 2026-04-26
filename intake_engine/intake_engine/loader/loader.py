import csv
import io
import logging
from pathlib import Path

import polars as pl

from intake_engine.utils.errors import LoadError

_NULL_VALUES = ["", "NA", "N/A", "null", "NULL", "none", "None", "NaN"]
_CSV_KWARGS = {"infer_schema_length": 1000, "null_values": _NULL_VALUES}
_log = logging.getLogger("intake")

_SNIFF_DELIMITERS = ",\t;|"
_SNIFF_LINES = 10


def _sniff_delimiter(text: str) -> str:
    """Detect the field delimiter from the first few lines of text.

    Uses csv.Sniffer then validates the result by confirming the detected
    delimiter splits the header into more than one field. Falls back to comma.
    """
    lines = [ln for ln in text.splitlines()[:_SNIFF_LINES] if ln.strip()]
    if not lines:
        return ","
    try:
        dialect = csv.Sniffer().sniff("\n".join(lines), delimiters=_SNIFF_DELIMITERS)
        sep = dialect.delimiter
    except csv.Error:
        return ","
    # Reject if the header doesn't actually split on the detected delimiter
    if len(lines[0].split(sep)) <= 1:
        return ","
    return sep


def load_file(path: Path, sheet: str | None = None) -> pl.DataFrame:
    """Load a .csv or .xlsx file into a polars DataFrame.

    For Excel files, sheet=None loads the first sheet; sheet="SheetName" loads by name.
    Use list_excel_sheets() to enumerate available sheets before loading.
    """
    if not path.exists():
        raise LoadError(f"File not found: {path}")

    suffix = path.suffix.lower()

    if suffix in (".csv", ".tsv"):
        return _load_csv(path)

    if suffix in (".xlsx", ".xls"):
        return _load_excel(path, sheet)

    raise LoadError(f"Unsupported file type '{suffix}'. Expected .csv, .tsv, or .xlsx")


def list_excel_sheets(path: Path) -> list[str]:
    """Return the sheet names of an Excel workbook in order."""
    if not path.exists():
        raise LoadError(f"File not found: {path}")
    try:
        import openpyxl
        wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
        names = list(wb.sheetnames)
        wb.close()
        return names
    except Exception as e:
        raise LoadError(f"Failed to list sheets in '{path.name}': {e}") from e


def _load_excel(path: Path, sheet: str | None = None) -> pl.DataFrame:
    try:
        if sheet is None:
            return pl.read_excel(path, sheet_id=1)
        return pl.read_excel(path, sheet_name=sheet)
    except Exception as e:
        sheet_info = f" sheet '{sheet}'" if sheet else ""
        raise LoadError(f"Failed to read Excel '{path.name}'{sheet_info}: {e}") from e


def _load_csv(path: Path) -> pl.DataFrame:
    """Detect delimiter, strict read, then tolerant fallback on ragged/malformed rows."""
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    sep = _sniff_delimiter(text)
    if sep != ",":
        _log.info(f"'{path.name}': detected delimiter {sep!r}")

    def _buf() -> io.BytesIO:
        return io.BytesIO(text.encode("utf-8"))

    kwargs = {**_CSV_KWARGS, "separator": sep}

    try:
        return pl.read_csv(_buf(), **kwargs)
    except Exception:
        pass

    try:
        df = pl.read_csv(_buf(), **kwargs, truncate_ragged_lines=True, ignore_errors=True)
        _log.warning(f"'{path.name}': malformed rows detected — ragged or unparseable values may have been truncated")
        return df
    except Exception as e:
        raise LoadError(f"Failed to read CSV '{path.name}': {e}") from e
