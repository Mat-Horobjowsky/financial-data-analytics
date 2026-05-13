from __future__ import annotations

import csv
import fnmatch
import json
from pathlib import Path

from analytics_pipeline import __version__
from .stages import StageContext, StageResult

# Per-stage artifact classification catalog.
# Each entry: (stage_name, filename_pattern, display_name, category, audience, description)
# Patterns use fnmatch syntax; exact names match as-is.
_CATALOG: list[tuple[str, str, str, str, str, str]] = [
    # intake — dynamic filenames driven by input stem + sheet slug
    ("intake", "*_clean.csv",
     "Cleaned Input Data", "intake", "internal",
     "Cleaned and validated input data ready for metrics computation"),
    ("intake", "*_report.html",
     "Intake Validation Report", "intake", "internal",
     "HTML intake validation report with data profile and issue summary"),
    ("intake", "*_validation.json",
     "Intake Validation Summary", "intake", "internal",
     "Machine-readable intake validation result"),
    # metrics
    ("metrics", "long_metrics.csv",
     "Metrics — Long Format", "metrics", "internal",
     "All computed metrics in long/tidy row-per-metric format"),
    ("metrics", "wide_metrics.csv",
     "Metrics — Wide Format", "metrics", "internal",
     "All computed metrics in wide/pivoted column-per-metric format"),
    ("metrics", "metrics_output.xlsx",
     "Metrics Workbook", "metrics", "internal",
     "Metrics workbook for analyst review"),
    ("metrics", "metric_dictionary.csv",
     "Metric Dictionary", "metrics", "internal",
     "Metric registry with names, types, and definitions"),
    ("metrics", "validation_report.json",
     "Metrics Validation Report", "metadata", "internal",
     "Machine-readable metrics validation result"),
    # report
    ("report", "report.html",
     "Executive Report (HTML)", "report", "client_facing",
     "Client-facing executive summary report (HTML)"),
    ("report", "report.pdf",
     "Executive Report (PDF)", "report", "client_facing",
     "Client-facing executive summary report (PDF, print-ready)"),
    ("report", "report.md",
     "Executive Report (Markdown)", "report", "internal",
     "Executive report source in Markdown format"),
    ("report", "summary.json",
     "Report Engine Metadata", "metadata", "internal",
     "Report engine run metadata and validation summary"),
    ("report", "insights.json",
     "Report Insights", "metadata", "internal",
     "Machine-readable report insights data"),
    # store
    ("store", "analytics.duckdb",
     "Analytics Store", "store", "internal",
     "Queryable analytics store (DuckDB) for downstream dashboard and export stages"),
    # visuals
    ("visuals", "readiness_dashboard.html",
     "Readiness Dashboard (HTML)", "dashboard", "client_facing",
     "Interactive client-facing readiness dashboard (HTML)"),
    ("visuals", "readiness_dashboard.pdf",
     "Readiness Dashboard (PDF)", "dashboard", "client_facing",
     "Printable client-facing readiness dashboard (PDF)"),
    ("visuals", "visuals_summary.json",
     "Visuals Engine Metadata", "metadata", "internal",
     "Visuals engine run metadata"),
    # powerbi_export
    ("powerbi_export", "readiness_kpis.csv",
     "Power BI Export — KPIs", "bi_export", "bi_facing",
     "Top-line readiness KPI summary for Power BI template"),
    ("powerbi_export", "readiness_by_category.csv",
     "Power BI Export — By Category", "bi_export", "bi_facing",
     "Readiness breakdown by category for Power BI template"),
    ("powerbi_export", "readiness_by_market.csv",
     "Power BI Export — By Market", "bi_export", "bi_facing",
     "Readiness breakdown by market for Power BI template"),
    ("powerbi_export", "metric_dictionary.csv",
     "Power BI Export — Metric Dictionary", "bi_export", "bi_facing",
     "Metric definitions for Power BI template"),
    ("powerbi_export", "validation_summary.csv",
     "Power BI Export — Validation Summary", "bi_export", "bi_facing",
     "Validation summary for Power BI template"),
    ("powerbi_export", "client_context.csv",
     "Power BI Export — Client Context", "bi_export", "bi_facing",
     "Client identity and project context for Power BI template"),
]


def _classify_artifact(stage_name: str, filename: str) -> dict:
    """Return classification fields for a generated file.

    Falls back to category='unknown', audience='internal' for unrecognised files
    so that no artifact is silently dropped.
    """
    for s, pattern, name, category, audience, description in _CATALOG:
        if s == stage_name and fnmatch.fnmatch(filename, pattern):
            return {
                "name": name,
                "category": category,
                "audience": audience,
                "description": description,
            }
    return {
        "name": filename,
        "category": "unknown",
        "audience": "internal",
        "description": f"Unclassified artifact from the {stage_name} stage",
    }


def parse_client_context(path: Path) -> dict | None:
    """Read client_context.csv and return client identity fields.

    Returns {"client_name": ..., "project_name": ..., "project_id": ...},
    or None if the file is missing, empty, or unreadable.
    """
    try:
        with path.open(encoding="utf-8") as f:
            reader = csv.DictReader(f)
            row = next(reader, None)
        if row is None:
            return None
        return {
            "client_name": row.get("client_name") or "",
            "project_name": row.get("project_name") or "",
            "project_id": row.get("project_id") or "",
        }
    except Exception:
        return None


def build_artifact_manifest(
    ctx: StageContext,
    results: dict[str, StageResult],
    pipeline_status: str,
    generated_at: str,
) -> dict:
    """Build the artifact manifest from pipeline context and stage results.

    Every file in every StageResult.generated_files list is included.
    Relative paths use the actual output directory name (e.g. 'powerbi' rather than
    the stage key 'powerbi_export') so they match the real folder layout.
    """
    client = parse_client_context(ctx.client_context_path) if ctx.client_context_path else None

    artifacts = []
    for stage_name, result in results.items():
        stage_dir_name = Path(result.output_dir).name
        for filename in result.generated_files:
            classification = _classify_artifact(stage_name, filename)
            artifacts.append({
                "name": classification["name"],
                "category": classification["category"],
                "audience": classification["audience"],
                "relative_path": f"{stage_dir_name}/{filename}",
                "description": classification["description"],
                "source_stage": stage_name,
                "generated_at": generated_at,
            })

    return {
        "manifest_version": "1.0",
        "generated_at": generated_at,
        "pipeline_version": __version__,
        "client": client,
        "run": {
            "status": pipeline_status,
            "input_file": str(ctx.input_file),
            "template": ctx.template,
            "output_dir": str(ctx.output_root),
        },
        "artifacts": artifacts,
    }


def write_artifact_manifest(manifest: dict, output_root: Path) -> Path:
    """Write artifact_manifest.json to the pipeline output root."""
    path = output_root / "artifact_manifest.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return path
