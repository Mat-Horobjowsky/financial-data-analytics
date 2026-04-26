import logging
from datetime import datetime, timezone
from pathlib import Path

import typer

from intake_engine.cleaner import apply_column_map, apply_column_selection, clean, to_snake
from intake_engine.db import load_to_duckdb
from intake_engine.db.writer import sanitize_table_name
from intake_engine.exporter import export_csv, export_parquet
from intake_engine.loader import list_excel_sheets, load_file
from intake_engine.models.config import PipelineConfig, load_config
from intake_engine.models.profile import ProfileReport
from intake_engine.models.run_summary import RunSummary
from intake_engine.models.validation import ValidationReport
from intake_engine.profiler import build_profile
from intake_engine.reporter import build_html_report
from intake_engine.utils.errors import IntakeError, LoadError
from intake_engine.utils.logging import get_logger
from intake_engine.validator import validate_file

app = typer.Typer(help="intake_engine — ingest and clean CSV/XLSX files.", add_completion=False)

_LOG_FILE = Path("logs/run.log")
_SUPPORTED_EXTENSIONS = {".csv", ".tsv", ".xlsx", ".xls"}
_SUPPORTED_FORMATS = {"csv", "parquet"}
_DEFAULT_OUTPUT_DIR = Path("outputs")


class _WarningCollector(logging.Handler):
    """Captures WARNING+ log records from the pipeline for inclusion in reports."""
    def __init__(self) -> None:
        super().__init__(logging.WARNING)
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        self.messages.append(record.getMessage())


@app.callback()
def _root() -> None:
    """intake_engine v1.0"""


@app.command("run")
def run(
    input_path: Path = typer.Argument(..., help="Path to a .csv/.xlsx file or a folder"),
    profile: bool = typer.Option(False, "--profile", help="Also write a profile report"),
    validate: bool = typer.Option(False, "--validate", help="Also run validation checks"),
    require: list[str] = typer.Option([], "--require", help="Required column names (repeatable)"),
    output_dir: Path | None = typer.Option(None, "--output-dir", help="Output directory (default: outputs/)"),
    fmt: str | None = typer.Option(None, "--format", help="Output format: csv or parquet (default: csv)"),
    config: Path | None = typer.Option(None, "--config", help="Path to YAML pipeline config file"),
    fail_on_validation: bool = typer.Option(False, "--fail-on-validation", help="Block export if validation status is FAIL"),
    db: Path | None = typer.Option(None, "--db", help="Path to DuckDB file to load cleaned data into"),
    sheet: str | None = typer.Option(None, "--sheet", help="Excel sheet name to load, or 'all' for every sheet"),
    db_mode: str | None = typer.Option(None, "--db-mode", help="DuckDB write mode: replace (default) or append"),
) -> None:
    """Load, clean, and export. Accepts a single file or a folder of files."""
    log = get_logger("intake", _LOG_FILE)

    cfg = _resolve_config(config)

    # CLI flags override config; booleans merge with OR (either source can enable)
    eff_output_dir = output_dir if output_dir is not None else Path(cfg.output_dir)
    eff_fmt = fmt if fmt is not None else cfg.output_format
    eff_block = fail_on_validation or cfg.block_export_on_fail
    eff_validate = validate or cfg.run_validate or eff_block  # block implies validate
    eff_profile = profile or cfg.run_profile
    eff_required = list(require) if require else (cfg.required_columns or None)
    eff_sheet = sheet if sheet is not None else cfg.sheet
    eff_db_mode = db_mode if db_mode is not None else cfg.db_mode

    if eff_fmt not in _SUPPORTED_FORMATS:
        typer.echo(f"Error: unsupported format '{eff_fmt}' — choose csv or parquet", err=True)
        raise typer.Exit(code=1)

    if eff_db_mode not in {"replace", "append"}:
        typer.echo(f"Error: unsupported --db-mode '{eff_db_mode}' — choose replace or append", err=True)
        raise typer.Exit(code=1)

    eff_columns = cfg.columns or None
    eff_select = cfg.select_columns or []

    if input_path.is_dir():
        _run_batch(input_path, log, eff_profile, eff_validate, eff_required,
                   eff_output_dir, eff_fmt, cfg.null_threshold, cfg.duplicate_threshold,
                   eff_block, db, eff_sheet, eff_columns, eff_db_mode, eff_select)
    elif input_path.is_file():
        _run_single(input_path, log, eff_profile, eff_validate, eff_required,
                    eff_output_dir, eff_fmt, cfg.null_threshold, cfg.duplicate_threshold,
                    eff_block, db, eff_sheet, eff_columns, eff_db_mode, eff_select)
    else:
        typer.echo(f"Error: '{input_path}' does not exist", err=True)
        raise typer.Exit(code=1)


@app.command("validate")
def validate_cmd(
    input_file: Path = typer.Argument(..., help="Path to .csv or .xlsx file"),
    require: list[str] = typer.Option([], "--require", help="Required column names (repeatable)"),
    output_dir: Path = typer.Option(_DEFAULT_OUTPUT_DIR, "--output-dir", help="Output directory"),
) -> None:
    """Load and clean a file, then write validation report and HTML report to output dir."""
    log = get_logger("intake", _LOG_FILE)
    log.info(f"Validate started: {input_file}")

    try:
        raw_df = load_file(input_file)
        clean_df = clean(raw_df)
        report = validate_file(input_file, raw_df, clean_df, require or None)
        out_path = _write_validation(report, input_file, log, output_dir)
        _write_html(_build_html(input_file.name, validation=report), input_file, log, output_dir)
        _print_validation(report, out_path)

    except IntakeError as e:
        log.error(str(e))
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)

    if report.status == "fail":
        raise typer.Exit(code=1)


@app.command("profile")
def profile_cmd(
    input_file: Path = typer.Argument(..., help="Path to .csv or .xlsx file"),
    output_dir: Path = typer.Option(_DEFAULT_OUTPUT_DIR, "--output-dir", help="Output directory"),
) -> None:
    """Load and clean a file, then write profile report and HTML report to output dir."""
    log = get_logger("intake", _LOG_FILE)
    log.info(f"Profile started: {input_file}")

    collector = _WarningCollector()
    logging.getLogger("intake").addHandler(collector)
    try:
        raw_df = load_file(input_file)
        clean_df = clean(raw_df)
        report = build_profile(input_file, raw_df, clean_df, collector.messages)
        _write_profile(report, input_file, log, output_dir)
        _write_html(_build_html(input_file.name, profile=report), input_file, log, output_dir)

    except IntakeError as e:
        log.error(str(e))
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
    finally:
        logging.getLogger("intake").removeHandler(collector)


# --- internal helpers ---

def _resolve_config(config_path: Path | None) -> PipelineConfig:
    if config_path is None:
        return PipelineConfig()
    if not config_path.exists():
        typer.echo(f"Error: config file not found: '{config_path}'", err=True)
        raise typer.Exit(code=1)
    try:
        return load_config(config_path)
    except Exception as e:
        typer.echo(f"Error loading config '{config_path}': {e}", err=True)
        raise typer.Exit(code=1)


def _run_single(
    path: Path,
    log: logging.Logger,
    do_profile: bool,
    do_validate: bool,
    required_cols: list[str] | None,
    output_dir: Path,
    fmt: str,
    null_threshold: float,
    dup_threshold: float,
    block_on_fail: bool = False,
    db_path: Path | None = None,
    sheet: str | None = None,
    column_rules: dict | None = None,
    db_mode: str = "replace",
    select_columns: list[str] | None = None,
) -> None:
    log.info(f"Run started: {path}")

    # expand "all" sheets for Excel files
    if sheet == "all" and path.suffix.lower() in (".xlsx", ".xls"):
        try:
            sheet_names = list_excel_sheets(path)
        except LoadError as e:
            typer.echo(f"Error: {e}", err=True)
            raise typer.Exit(code=1)
        if not sheet_names:
            typer.echo(f"No sheets found in '{path.name}'")
            return
        val_statuses: list[str] = []
        exported_count = 0
        for sheet_name in sheet_names:
            collector = _WarningCollector()
            logging.getLogger("intake").addHandler(collector)
            try:
                _, _, val_report, exported = _process_file(
                    path, log, collector, do_profile, do_validate,
                    required_cols, output_dir, fmt, null_threshold, dup_threshold,
                    block_on_fail, db_path, sheet_name, column_rules, db_mode, select_columns or [],
                )
                output_stem = f"{path.stem}_{to_snake(sheet_name)}"
                ext = "parquet" if fmt == "parquet" else "csv"
                clean_path = output_dir / f"{output_stem}_clean.{ext}"
                if exported:
                    typer.echo(f"Done -> {clean_path}")
                    exported_count += 1
                if val_report:
                    val_statuses.append(val_report.status)
                    _print_validation(val_report, output_dir / f"{output_stem}_validation.json")
            except IntakeError as e:
                log.error(str(e))
                typer.echo(f"Error [{sheet_name}]: {e}", err=True)
            finally:
                logging.getLogger("intake").removeHandler(collector)
        worst = "fail" if "fail" in val_statuses else ("warn" if "warn" in val_statuses else "pass")
        suffix_str = f" | {worst.upper()}" if val_statuses else ""
        typer.echo(f"\n=== {path.name}: {len(sheet_names)} sheets{suffix_str} | {exported_count}/{len(sheet_names)} exported ===")
        return

    # single sheet (named or default first sheet)
    actual_sheet = sheet if sheet != "all" else None
    output_stem = f"{path.stem}_{to_snake(actual_sheet)}" if actual_sheet else path.stem
    collector = _WarningCollector()
    logging.getLogger("intake").addHandler(collector)
    try:
        _, _, val_report, exported = _process_file(
            path, log, collector, do_profile, do_validate,
            required_cols, output_dir, fmt, null_threshold, dup_threshold,
            block_on_fail, db_path, actual_sheet, column_rules, db_mode, select_columns or [],
        )
        ext = "parquet" if fmt == "parquet" else "csv"
        clean_path = output_dir / f"{output_stem}_clean.{ext}"
        if exported:
            typer.echo(f"Done -> {clean_path}")
        if val_report:
            _print_validation(val_report, output_dir / f"{output_stem}_validation.json")
        export_label = str(clean_path) if exported else "BLOCKED"
        if val_report:
            typer.echo(f"\n=== {val_report.status.upper()} | export: {export_label} ===")
        else:
            typer.echo(f"\n=== export: {export_label} ===")
    except IntakeError as e:
        log.error(str(e))
        typer.echo(f"Error: {e}", err=True)
        raise typer.Exit(code=1)
    finally:
        logging.getLogger("intake").removeHandler(collector)


def _run_batch(
    folder: Path,
    log: logging.Logger,
    do_profile: bool,
    do_validate: bool,
    required_cols: list[str] | None,
    output_dir: Path,
    fmt: str,
    null_threshold: float,
    dup_threshold: float,
    block_on_fail: bool = False,
    db_path: Path | None = None,
    sheet: str | None = None,
    column_rules: dict | None = None,
    db_mode: str = "replace",
    select_columns: list[str] | None = None,
) -> None:
    files = sorted(p for p in folder.iterdir() if p.suffix.lower() in _SUPPORTED_EXTENSIONS)

    if not files:
        typer.echo(f"No .csv or .xlsx files found in '{folder}'")
        return

    log.info(f"Batch started: {len(files)} files in '{folder}'")

    # expand Excel files into (path, sheet_name) work items when sheet="all"
    work_items: list[tuple[Path, str | None]] = []
    failed: dict[str, str] = {}
    for f in files:
        if sheet == "all" and f.suffix.lower() in (".xlsx", ".xls"):
            try:
                for sheet_name in list_excel_sheets(f):
                    work_items.append((f, sheet_name))
            except Exception as e:
                failed[f.name] = str(e)
                log.error(f"FAILED listing sheets in '{f.name}': {e}")
        else:
            work_items.append((f, sheet if sheet != "all" else None))

    rows_loaded_total = rows_output_total = warnings_total = blocked_total = 0
    processed: list[str] = []
    val_counts: dict[str, int] = {"pass": 0, "warn": 0, "fail": 0}

    for path, sheet_name in work_items:
        item_key = f"{path.name}[{sheet_name}]" if sheet_name else path.name
        collector = _WarningCollector()
        logging.getLogger("intake").addHandler(collector)
        try:
            rows_in, rows_out, val_report, exported = _process_file(
                path, log, collector, do_profile, do_validate,
                required_cols, output_dir, fmt, null_threshold, dup_threshold,
                block_on_fail, db_path, sheet_name, column_rules, db_mode, select_columns or [],
            )
            rows_loaded_total += rows_in
            rows_output_total += rows_out
            warnings_total += len(collector.messages)
            processed.append(item_key)
            if not exported:
                blocked_total += 1
            if val_report:
                val_counts[val_report.status] += 1
        except Exception as e:
            failed[item_key] = str(e)
            log.error(f"FAILED {item_key}: {e}")
        finally:
            logging.getLogger("intake").removeHandler(collector)

    summary = RunSummary(
        files_found=len(files),
        files_processed=len(processed),
        files_failed=len(failed),
        file_names_processed=processed,
        rows_loaded_total=rows_loaded_total,
        rows_output_total=rows_output_total,
        duplicates_removed_total=rows_loaded_total - rows_output_total,
        warnings_total=warnings_total,
        failed_files=failed,
        files_failed_validation=val_counts["fail"],
        files_export_blocked=blocked_total,
        run_timestamp=datetime.now(timezone.utc).isoformat(),
    )

    summary_path = output_dir / "run_summary.json"
    summary_path.parent.mkdir(parents=True, exist_ok=True)
    summary_path.write_text(summary.model_dump_json(indent=2))
    log.info(f"Batch complete. Summary: {summary_path}")

    items_label = "items" if len(work_items) > len(files) else "files"
    typer.echo(f"Processed {len(processed)}/{len(work_items)} {items_label}")
    typer.echo(f"Rows: {rows_loaded_total:,} -> {rows_output_total:,}")
    typer.echo(f"Duplicates removed: {rows_loaded_total - rows_output_total:,}")
    if do_validate:
        typer.echo(
            f"Validation: {val_counts['pass']} pass, {val_counts['warn']} warn, {val_counts['fail']} fail"
        )
    if failed:
        typer.echo(f"Failed: {list(failed.keys())}")
    typer.echo(f"Summary -> {summary_path}")

    exported_count = len(processed) - blocked_total
    db_str = f" | DB: {db_path}" if db_path is not None else ""
    if do_validate:
        blocked_str = f" ({blocked_total} blocked)" if blocked_total else ""
        typer.echo(
            f"\n=== Batch: {val_counts['pass']} pass, {val_counts['warn']} warn, {val_counts['fail']} fail"
            f" | {exported_count}/{len(work_items)} exported{blocked_str}{db_str} ==="
        )
    else:
        typer.echo(f"\n=== Batch: {len(processed)}/{len(work_items)} exported{db_str} ===")


def _process_file(
    path: Path,
    log: logging.Logger,
    collector: _WarningCollector,
    do_profile: bool,
    do_validate: bool = False,
    required_cols: list[str] | None = None,
    output_dir: Path = _DEFAULT_OUTPUT_DIR,
    fmt: str = "csv",
    null_threshold: float = 0.3,
    dup_threshold: float = 0.3,
    block_on_fail: bool = False,
    db_path: Path | None = None,
    sheet_name: str | None = None,
    column_rules: dict | None = None,
    db_mode: str = "replace",
    select_columns: list[str] | None = None,
) -> tuple[int, int, ValidationReport | None, bool]:
    """Core pipeline: load -> clean -> [validate] -> export -> optional DB/profile/HTML.

    When block_on_fail=True, validation runs before export so a FAIL result can
    prevent the output file from being written.  Returns (rows_in, rows_out,
    val_report, exported) where exported=False means the file was blocked.
    sheet_name=None loads the first sheet (default); a string loads a named sheet.
    select_columns, when non-empty, restricts and orders the output columns while
    validation continues on the full clean_df.
    """
    raw_df = load_file(path, sheet=sheet_name)
    display_name = f"{path.name} [{sheet_name}]" if sheet_name else path.name
    log.info(f"  Loaded {raw_df.shape[0]} rows from '{display_name}'")

    # stem_path carries the sheet context into report filenames and the ValidationReport
    output_stem = f"{path.stem}_{to_snake(sheet_name)}" if sheet_name else path.stem
    stem_path = path.with_stem(output_stem)

    clean_df = clean(raw_df)
    if column_rules:
        clean_df = apply_column_map(clean_df, column_rules)
    dropped = raw_df.shape[0] - clean_df.shape[0]

    # column selection — warn on missing, applied only to output (validation uses full clean_df)
    output_df = clean_df
    if select_columns:
        missing = [c for c in select_columns if c not in clean_df.columns]
        if missing:
            log.warning(f"  select_columns: columns not found and skipped: {missing}")
        output_df = apply_column_selection(clean_df, select_columns)

    val_report: ValidationReport | None = None
    profile_report: ProfileReport | None = None

    # pre-export validation — only when export blocking is requested
    if do_validate and block_on_fail:
        val_report = validate_file(stem_path, raw_df, clean_df, required_cols, null_threshold, dup_threshold, column_rules)
        _write_validation(val_report, stem_path, log, output_dir)
        if val_report.status == "fail":
            if do_profile:
                profile_report = build_profile(stem_path, raw_df, clean_df, collector.messages)
                _write_profile(profile_report, stem_path, log, output_dir)
            _write_html(_build_html(display_name, profile_report, val_report), stem_path, log, output_dir)
            log.info(f"  Export blocked (validation FAIL): {display_name}")
            return raw_df.shape[0], clean_df.shape[0], val_report, False

    ext = ".parquet" if fmt == "parquet" else ".csv"
    output_path = output_dir / f"{output_stem}_clean{ext}"
    if fmt == "parquet":
        export_parquet(output_df, output_path)
    else:
        export_csv(output_df, output_path)
    log.info(f"  Exported: {output_path} ({dropped} dupes removed)")

    if db_path is not None:
        table_name = sanitize_table_name(output_stem)
        row_count = load_to_duckdb(output_df, db_path, table_name, mode=db_mode)
        mode_label = "appended" if db_mode == "append" else "loaded"
        log.info(f"  DB {mode_label}: {db_path} :: {table_name} ({row_count} rows total)")
        typer.echo(f"DB -> {db_path} :: {table_name} ({row_count} rows)")

    if do_profile:
        profile_report = build_profile(stem_path, raw_df, clean_df, collector.messages)
        _write_profile(profile_report, stem_path, log, output_dir)

    if do_validate and val_report is None:
        val_report = validate_file(stem_path, raw_df, clean_df, required_cols, null_threshold, dup_threshold, column_rules)
        _write_validation(val_report, stem_path, log, output_dir)

    if do_profile or do_validate:
        _write_html(_build_html(display_name, profile_report, val_report), stem_path, log, output_dir)

    return raw_df.shape[0], clean_df.shape[0], val_report, True


def _build_html(
    file_name: str,
    profile: ProfileReport | None = None,
    validation: ValidationReport | None = None,
) -> str:
    return build_html_report(file_name, profile=profile, validation=validation)


def _write_html(
    html_str: str,
    input_file: Path,
    log: logging.Logger,
    output_dir: Path = _DEFAULT_OUTPUT_DIR,
) -> Path:
    out_path = output_dir / f"{input_file.stem}_report.html"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_str, encoding="utf-8")
    log.info(f"HTML report written: {out_path}")
    typer.echo(f"HTML report -> {out_path}")
    return out_path


def _write_validation(
    report: ValidationReport,
    input_file: Path,
    log: logging.Logger,
    output_dir: Path = _DEFAULT_OUTPUT_DIR,
) -> Path:
    out_path = output_dir / f"{input_file.stem}_validation.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report.model_dump_json(indent=2))
    log.info(f"Validation written: {out_path}")
    return out_path


def _print_validation(report: ValidationReport, out_path: Path) -> None:
    typer.echo(f"\n--- Validation: {report.file_name} ---")
    typer.echo(f"Status:   {report.status.upper()}")
    typer.echo(f"Rows:     {report.rows_loaded:,} loaded -> {report.row_count:,} output")
    typer.echo(f"Dup rate: {report.duplicate_rate:.1%}")
    nonzero = {k: f"{v:.1%}" for k, v in report.null_summary.items() if v > 0}
    typer.echo(f"Nulls:    {nonzero if nonzero else 'none'}")
    if report.issues:
        typer.echo(f"Issues:   {report.issues}")
    if report.warnings:
        typer.echo(f"Warnings: {report.warnings}")
    typer.echo(f"Report -> {out_path}")


def _write_profile(
    report: ProfileReport,
    input_file: Path,
    log: logging.Logger,
    output_dir: Path = _DEFAULT_OUTPUT_DIR,
) -> None:
    out_path = output_dir / f"{input_file.stem}_profile.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report.model_dump_json(indent=2))
    log.info(f"Profile written: {out_path}")

    typer.echo(f"\n--- Profile: {report.file_name} ---")
    typer.echo(f"Rows:     {report.rows_loaded} loaded -> {report.rows_output} output  ({report.duplicate_rows_removed} duplicates removed)")
    typer.echo(f"Columns:  {report.columns}  {report.column_names}")
    typer.echo(f"Types:    {dict(report.inferred_types)}")
    typer.echo(f"Nulls:    {dict(report.null_counts)}")
    if report.columns_renamed:
        typer.echo(f"Renamed:  {report.columns_renamed}")
    if report.numeric_columns_normalized:
        typer.echo(f"Numeric:  {report.numeric_columns_normalized}")
    if report.date_columns_normalized:
        typer.echo(f"Dates:    {report.date_columns_normalized}")
    if report.warnings:
        typer.echo(f"Warnings: {report.warnings}")
    typer.echo(f"Report -> {out_path}")
