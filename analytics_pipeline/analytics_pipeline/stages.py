from __future__ import annotations

import dataclasses
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass
class StageResult:
    name: str
    status: str  # "success" | "failed" | "skipped"
    command: list[str]
    output_dir: Path
    generated_files: list[str]
    extra: dict
    error: str | None = None


@dataclass
class StageContext:
    input_file: Path
    output_root: Path
    with_time: bool
    template: str
    results: dict[str, StageResult]
    with_store: bool = False
    with_visuals: bool = False
    with_powerbi_export: bool = False
    metrics_config: Path | None = None
    schema_config: Path | None = None
    sheet: str | None = None
    client_context_path: Path | None = None
    with_pdf: bool = False
    report_title: str | None = None


def build_intake_cmd(ctx: StageContext) -> list[str]:
    intake_exe = shutil.which("intake") or "intake"
    cmd = [
        intake_exe,
        "run",
        str(ctx.input_file),
        "--output-dir",
        str(ctx.output_root / "intake"),
        "--validate",
    ]
    if ctx.sheet:
        cmd.extend(["--sheet", ctx.sheet])
    return cmd


def _sheet_slug(sheet: str) -> str:
    """Convert sheet name to the slug intake_engine uses in output filenames."""
    s = sheet.strip().lower()
    s = re.sub(r"[-\s/\.]+", "_", s)
    s = re.sub(r"[^\w]", "", s)
    s = re.sub(r"_+", "_", s)
    return s.strip("_")


def build_metrics_cmd(ctx: StageContext) -> list[str]:
    import metrics_engine as _me

    stem = ctx.input_file.stem
    if ctx.sheet:
        clean_csv = ctx.output_root / "intake" / f"{stem}_{_sheet_slug(ctx.sheet)}_clean.csv"
    else:
        clean_csv = ctx.output_root / "intake" / f"{stem}_clean.csv"
    config_dir = Path(_me.__file__).parent.parent / "config"

    metrics_config = str(ctx.metrics_config) if ctx.metrics_config else str(config_dir / "metrics.yaml")
    schema_config = str(ctx.schema_config) if ctx.schema_config else str(config_dir / "schema.yaml")

    cmd = [
        sys.executable,
        "-m",
        "metrics_engine.cli",
        "run",
        "--input",
        str(clean_csv),
        "--output",
        str(ctx.output_root / "metrics"),
        "--config",
        metrics_config,
        "--schema",
        schema_config,
    ]
    if ctx.with_time:
        cmd.append("--with-time")
    return cmd


def build_report_cmd(ctx: StageContext) -> list[str]:
    cmd = [
        sys.executable,
        "-m",
        "report_engine.cli",
        "build",
        "--input",
        str(ctx.output_root / "metrics"),
        "--output",
        str(ctx.output_root / "report"),
        "--template",
        ctx.template,
    ]
    if ctx.with_pdf:
        cmd.append("--pdf")
    if ctx.report_title is not None:
        cmd.extend(["--title", ctx.report_title])
    return cmd


def build_store_cmd(ctx: StageContext) -> list[str]:
    return [
        sys.executable,
        "-m",
        "analytics_store.cli",
        "build",
        "--metrics",
        str(ctx.output_root / "metrics"),
        "--report",
        str(ctx.output_root / "report"),
        "--output",
        str(ctx.output_root / "store" / "analytics.duckdb"),
    ]


def build_powerbi_export_cmd(ctx: StageContext) -> list[str]:
    exe = shutil.which("visuals-engine") or "visuals-engine"
    cmd = [
        exe,
        "export-powerbi",
        "--store",
        str(ctx.output_root / "store" / "analytics.duckdb"),
        "--output",
        str(ctx.output_root / "powerbi"),
    ]
    if ctx.client_context_path is not None:
        cmd.extend(["--client-context", str(ctx.client_context_path)])
    return cmd


def build_visuals_cmd(ctx: StageContext) -> list[str]:
    import visuals_engine as _ve

    spec_path = Path(_ve.__file__).parent / "specs" / "readiness_dashboard.yaml"
    cmd = [
        sys.executable,
        "-m",
        "visuals_engine.cli",
        "build",
        "--store",
        str(ctx.output_root / "store" / "analytics.duckdb"),
        "--spec",
        str(spec_path),
        "--output",
        str(ctx.output_root / "visuals"),
    ]
    if ctx.client_context_path is not None:
        cmd.extend(["--client-context", str(ctx.client_context_path)])
    return cmd


ACTIVE_STAGES: list[tuple[str, Callable]] = [
    ("intake", build_intake_cmd),
    ("metrics", build_metrics_cmd),
    ("report", build_report_cmd),
]

FUTURE_STAGES: list[str] = ["store"]
