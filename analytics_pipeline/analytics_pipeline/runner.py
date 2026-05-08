from __future__ import annotations

import dataclasses
import subprocess
from pathlib import Path

from .stages import ACTIVE_STAGES, StageContext, StageResult, build_store_cmd, build_visuals_cmd


def run_stage(name: str, cmd: list[str], output_dir: Path) -> StageResult:
    output_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(cmd, capture_output=True, text=True)
    status = "success" if result.returncode == 0 else "failed"
    error = result.stderr.strip() if result.returncode != 0 else None
    generated = sorted(p.name for p in output_dir.iterdir()) if output_dir.exists() else []
    return StageResult(
        name=name,
        status=status,
        command=cmd,
        output_dir=output_dir,
        generated_files=generated,
        extra={},
        error=error,
    )


def run_pipeline(ctx: StageContext) -> dict[str, StageResult]:
    results: dict[str, StageResult] = {}
    for stage_name, cmd_builder in ACTIVE_STAGES:
        output_dir = ctx.output_root / stage_name
        cmd = cmd_builder(ctx)
        result = run_stage(stage_name, cmd, output_dir)
        if stage_name == "report":
            result.extra["template"] = ctx.template
        results[stage_name] = result
        ctx = dataclasses.replace(ctx, results=results)
        if result.status == "failed":
            break

    if ctx.with_store and "report" in results and results["report"].status == "success":
        store_dir = ctx.output_root / "store"
        store_result = run_stage("store", build_store_cmd(ctx), store_dir)
        store_result.extra["output_path"] = str(store_dir / "analytics.duckdb")
        results["store"] = store_result

    if ctx.with_visuals and "store" in results and results["store"].status == "success":
        visuals_dir = ctx.output_root / "visuals"
        visuals_result = run_stage("visuals", build_visuals_cmd(ctx), visuals_dir)
        results["visuals"] = visuals_result

    return results
