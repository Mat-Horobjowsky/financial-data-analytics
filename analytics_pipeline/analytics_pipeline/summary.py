from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from analytics_pipeline import __version__
from .stages import ACTIVE_STAGES, FUTURE_STAGES, StageContext, StageResult


def _resolved_config_path(provided: Path | None, default_name: str) -> str:
    """Return absolute path for a config file, falling back to the metrics_engine default."""
    if provided is not None:
        return str(Path(provided).resolve())
    try:
        import metrics_engine as _me
        config_dir = Path(_me.__file__).parent.parent / "config"
        return str(config_dir / default_name)
    except Exception:
        return default_name


def build_pipeline_summary(ctx: StageContext, results: dict[str, StageResult]) -> dict:
    all_names = [name for name, _ in ACTIVE_STAGES]
    if ctx.with_store:
        all_names.append("store")
    if ctx.with_visuals:
        all_names.append("visuals")
    if ctx.with_powerbi_export:
        all_names.append("powerbi_export")
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
    future_stages = [s for s in FUTURE_STAGES if s != "store"] if ctx.with_store else FUTURE_STAGES
    return {
        "pipeline_version": __version__,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "input_path": str(ctx.input_file),
        "sheet": ctx.sheet,
        "output_dir": str(ctx.output_root),
        "with_time": ctx.with_time,
        "with_store": ctx.with_store,
        "with_visuals": ctx.with_visuals,
        "with_powerbi_export": ctx.with_powerbi_export,
        "metrics_config_path": _resolved_config_path(ctx.metrics_config, "metrics.yaml"),
        "schema_config_path": _resolved_config_path(ctx.schema_config, "schema.yaml"),
        "template": ctx.template,
        "status": overall,
        "stages": stages_out,
        "future_stages": future_stages,
    }


def write_summary(summary: dict, output_root: Path) -> Path:
    path = output_root / "pipeline_summary.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return path
