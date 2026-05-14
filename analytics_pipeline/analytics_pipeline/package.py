from __future__ import annotations

import json
import shutil
from pathlib import Path

# Canonical rename map: manifest relative_path → package filename.
# Paths not in this map keep their original filename.
_RENAME: dict[str, str] = {
    "report/report.html": "executive_report.html",
    "report/report.pdf": "executive_report.pdf",
    "visuals/readiness_dashboard.html": "readiness_dashboard.html",
    "visuals/readiness_dashboard.pdf": "readiness_dashboard.pdf",
}

_PACKAGE_DIR_NAME = "client_package"
_PACKAGED_AUDIENCES = {"client_facing", "bi_facing"}


def _package_path(artifact: dict) -> str:
    """Return destination path within client_package/ for one artifact."""
    rel = artifact["relative_path"]
    if artifact["audience"] == "bi_facing":
        return f"powerbi/{Path(rel).name}"
    return _RENAME.get(rel, Path(rel).name)


def build_client_package(manifest: dict, output_root: Path) -> dict:
    """Assemble a client delivery package from artifact_manifest.json classifications.

    Copies client_facing artifacts to the package root (rename map applied) and
    bi_facing artifacts to powerbi/. Generates README.md and package_manifest.json.
    Missing source files are skipped gracefully and recorded in the returned result.

    Returns:
        {
            "package_dir": Path,
            "copied": [{"name": ..., "package_path": ...}],
            "missing": [{"name": ..., "relative_path": ...}],
        }
    """
    package_dir = output_root / _PACKAGE_DIR_NAME
    package_dir.mkdir(parents=True, exist_ok=True)
    (package_dir / "powerbi").mkdir(exist_ok=True)

    copied: list[dict] = []
    missing: list[dict] = []
    package_artifacts: list[dict] = []

    for artifact in manifest.get("artifacts", []):
        if artifact.get("audience") not in _PACKAGED_AUDIENCES:
            continue

        src = output_root / artifact["relative_path"]
        dest_rel = _package_path(artifact)
        dest = package_dir / dest_rel

        if not src.exists():
            missing.append({
                "name": artifact["name"],
                "relative_path": artifact["relative_path"],
            })
            continue

        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)
        copied.append({"name": artifact["name"], "package_path": dest_rel})
        package_artifacts.append({
            "name": artifact["name"],
            "audience": artifact["audience"],
            "category": artifact["category"],
            "description": artifact["description"],
            "source_stage": artifact["source_stage"],
            "source_path": artifact["relative_path"],
            "package_path": dest_rel,
        })

    _write_readme(package_dir, manifest, copied, missing)
    _write_package_manifest(package_dir, manifest, package_artifacts)

    return {
        "package_dir": package_dir,
        "copied": copied,
        "missing": missing,
    }


def _write_readme(
    package_dir: Path,
    manifest: dict,
    copied: list[dict],
    missing: list[dict],
) -> None:
    client = manifest.get("client") or {}
    client_name = client.get("client_name") or "Client"
    project_name = client.get("project_name") or ""
    project_id = client.get("project_id") or ""
    generated_at = manifest.get("generated_at", "")
    pipeline_version = manifest.get("pipeline_version", "")

    table_rows = "\n".join(
        f"| `{e['package_path']}` | {e['name']} |"
        for e in copied
    ) if copied else "| _(none)_ | |"

    missing_section = ""
    if missing:
        items = "\n".join(
            f"- {m['name']} (`{m['relative_path']}`)" for m in missing
        )
        missing_section = (
            "\n## Missing Artifacts\n\n"
            "The following expected deliverables were not found and have been omitted "
            "from this package:\n\n"
            f"{items}\n"
        )

    readme = (
        f"# {client_name} — Readiness Analysis Deliverables\n\n"
        f"**Project:** {project_name}  \n"
        f"**Project ID:** {project_id}  \n"
        f"**Generated:** {generated_at}  \n"
        f"**Pipeline version:** {pipeline_version}\n\n"
        "## About This Package\n\n"
        "This folder contains the client-facing deliverables produced by the Data Center\n"
        "Transaction Readiness analytics pipeline. All artifacts were generated from a\n"
        "single validated pipeline run.\n\n"
        "Internal pipeline files (raw metrics, DuckDB store, validation logs, Markdown\n"
        "source) are not included in this package.\n\n"
        "## Deliverables\n\n"
        "| File | Description |\n"
        "|------|-------------|\n"
        f"{table_rows}\n\n"
        "## Power BI Handoff\n\n"
        "The `powerbi/` folder contains CSV exports ready for the Power BI readiness\n"
        "dashboard template. Load all CSV files as data sources in the template.\n"
        "Do not rename the files; the template references them by name.\n"
        f"{missing_section}"
    )

    (package_dir / "README.md").write_text(readme, encoding="utf-8")


def _write_package_manifest(
    package_dir: Path,
    manifest: dict,
    package_artifacts: list[dict],
) -> None:
    pkg_manifest = {
        "manifest_version": manifest.get("manifest_version", "1.0"),
        "generated_at": manifest.get("generated_at", ""),
        "pipeline_version": manifest.get("pipeline_version", ""),
        "client": manifest.get("client"),
        "artifacts": package_artifacts,
    }
    (package_dir / "package_manifest.json").write_text(
        json.dumps(pkg_manifest, indent=2), encoding="utf-8"
    )
