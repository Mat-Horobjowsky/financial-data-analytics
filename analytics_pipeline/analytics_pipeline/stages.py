from __future__ import annotations

import dataclasses
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


def build_intake_cmd(ctx: StageContext) -> list[str]:
    intake_exe = shutil.which("intake") or "intake"
    return [
        intake_exe,
        "run",
        str(ctx.input_file),
        "--output-dir",
        str(ctx.output_root / "intake"),
        "--validate",
    ]


def build_metrics_cmd(ctx: StageContext) -> list[str]:
    import metrics_engine as _me

    stem = ctx.input_file.stem
    clean_csv = ctx.output_root / "intake" / f"{stem}_clean.csv"
    config_dir = Path(_me.__file__).parent.parent / "config"
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
        str(config_dir / "metrics.yaml"),
        "--schema",
        str(config_dir / "schema.yaml"),
    ]
    if ctx.with_time:
        cmd.append("--with-time")
    return cmd


def build_report_cmd(ctx: StageContext) -> list[str]:
    return [
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


ACTIVE_STAGES: list[tuple[str, Callable]] = [
    ("intake", build_intake_cmd),
    ("metrics", build_metrics_cmd),
    ("report", build_report_cmd),
]

FUTURE_STAGES: list[str] = ["store", "visuals"]
