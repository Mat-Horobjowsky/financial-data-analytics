from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from analytics_pipeline import __version__
from .stages import ACTIVE_STAGES, FUTURE_STAGES, StageContext, StageResult


def build_pipeline_summary(ctx: StageContext, results: dict[str, StageResult]) -> dict:
    all_names = [name for name, _ in ACTIVE_STAGES]
    overall = (
        "success"
        if results and all(r.status == "success" for r in results.values())
        else "failed"
    )
    stages_out: dict[str, dict] = {}
    for name in all_names:
        if name in results:
            r = results[name]
            stages_out[name] = {
                "status": r.status,
                "command": " ".join(str(a) for a in r.command),
                "output_dir": str(r.output_dir),
                "generated_files": r.generated_files,
                **r.extra,
            }
        else:
            stages_out[name] = {"status": "skipped"}
    return {
        "pipeline_version": __version__,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_path": str(ctx.input_file),
        "output_dir": str(ctx.output_root),
        "with_time": ctx.with_time,
        "template": ctx.template,
        "status": overall,
        "stages": stages_out,
        "future_stages": FUTURE_STAGES,
    }


def write_summary(summary: dict, output_root: Path) -> Path:
    path = output_root / "pipeline_summary.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return path
