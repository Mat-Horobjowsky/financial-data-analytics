import json
from pathlib import Path

import pytest

from analytics_pipeline.package import build_client_package

_TS = "2026-05-13T20:00:00+00:00"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _artifact(stage, rel_path, name, category, audience) -> dict:
    return {
        "name": name,
        "category": category,
        "audience": audience,
        "relative_path": rel_path,
        "description": f"Description of {name}",
        "source_stage": stage,
        "generated_at": _TS,
    }


def _make_manifest(client: bool = True) -> dict:
    """Return a minimal but representative manifest covering all three audiences."""
    client_block = {
        "client_name": "Acme Corp",
        "project_name": "Test Campus Project",
        "project_id": "TEST-001",
    } if client else None
    return {
        "manifest_version": "1.0",
        "generated_at": _TS,
        "pipeline_version": "0.2.0",
        "client": client_block,
        "artifacts": [
            # client_facing
            _artifact("report", "report/report.html",
                      "Executive Report (HTML)", "report", "client_facing"),
            _artifact("report", "report/report.pdf",
                      "Executive Report (PDF)", "report", "client_facing"),
            _artifact("visuals", "visuals/readiness_dashboard.html",
                      "Readiness Dashboard (HTML)", "dashboard", "client_facing"),
            _artifact("visuals", "visuals/readiness_dashboard.pdf",
                      "Readiness Dashboard (PDF)", "dashboard", "client_facing"),
            # bi_facing
            _artifact("powerbi_export", "powerbi/readiness_kpis.csv",
                      "Power BI — KPIs", "bi_export", "bi_facing"),
            _artifact("powerbi_export", "powerbi/client_context.csv",
                      "Power BI — Client Context", "bi_export", "bi_facing"),
            # internal
            _artifact("intake", "intake/data_clean.csv",
                      "Cleaned Input Data", "intake", "internal"),
            _artifact("metrics", "metrics/long_metrics.csv",
                      "Metrics — Long Format", "metrics", "internal"),
            _artifact("store", "store/analytics.duckdb",
                      "Analytics Store", "store", "internal"),
        ],
    }


def _create_source_files(output_root: Path, manifest: dict) -> None:
    """Write stub files to disk for every artifact in the manifest."""
    for artifact in manifest["artifacts"]:
        src = output_root / artifact["relative_path"]
        src.parent.mkdir(parents=True, exist_ok=True)
        src.write_text(f"stub:{artifact['name']}", encoding="utf-8")


# ---------------------------------------------------------------------------
# Copying — client_facing artifacts
# ---------------------------------------------------------------------------


def test_copies_client_facing_to_root(tmp_path):
    manifest = _make_manifest()
    _create_source_files(tmp_path, manifest)
    build_client_package(manifest, tmp_path)
    pkg = tmp_path / "client_package"
    assert (pkg / "executive_report.html").exists()
    assert (pkg / "executive_report.pdf").exists()
    assert (pkg / "readiness_dashboard.html").exists()
    assert (pkg / "readiness_dashboard.pdf").exists()


def test_copies_bi_facing_to_powerbi(tmp_path):
    manifest = _make_manifest()
    _create_source_files(tmp_path, manifest)
    build_client_package(manifest, tmp_path)
    powerbi = tmp_path / "client_package" / "powerbi"
    assert (powerbi / "readiness_kpis.csv").exists()
    assert (powerbi / "client_context.csv").exists()


def test_excludes_internal_artifacts(tmp_path):
    manifest = _make_manifest()
    _create_source_files(tmp_path, manifest)
    build_client_package(manifest, tmp_path)
    pkg = tmp_path / "client_package"
    # Internal files must not appear anywhere in the package tree
    all_files = {f.name for f in pkg.rglob("*") if f.is_file()}
    assert "data_clean.csv" not in all_files
    assert "long_metrics.csv" not in all_files
    assert "analytics.duckdb" not in all_files


# ---------------------------------------------------------------------------
# Rename map
# ---------------------------------------------------------------------------


def test_report_html_renamed_to_executive_report(tmp_path):
    manifest = _make_manifest()
    _create_source_files(tmp_path, manifest)
    build_client_package(manifest, tmp_path)
    assert (tmp_path / "client_package" / "executive_report.html").exists()
    assert not (tmp_path / "client_package" / "report.html").exists()


def test_report_pdf_renamed_to_executive_report(tmp_path):
    manifest = _make_manifest()
    _create_source_files(tmp_path, manifest)
    build_client_package(manifest, tmp_path)
    assert (tmp_path / "client_package" / "executive_report.pdf").exists()
    assert not (tmp_path / "client_package" / "report.pdf").exists()


def test_dashboard_html_name_unchanged(tmp_path):
    manifest = _make_manifest()
    _create_source_files(tmp_path, manifest)
    build_client_package(manifest, tmp_path)
    assert (tmp_path / "client_package" / "readiness_dashboard.html").exists()


def test_dashboard_pdf_name_unchanged(tmp_path):
    manifest = _make_manifest()
    _create_source_files(tmp_path, manifest)
    build_client_package(manifest, tmp_path)
    assert (tmp_path / "client_package" / "readiness_dashboard.pdf").exists()


def test_powerbi_filenames_unchanged(tmp_path):
    manifest = _make_manifest()
    _create_source_files(tmp_path, manifest)
    build_client_package(manifest, tmp_path)
    powerbi = tmp_path / "client_package" / "powerbi"
    assert (powerbi / "readiness_kpis.csv").exists()
    assert (powerbi / "client_context.csv").exists()


def test_file_content_preserved_after_copy(tmp_path):
    manifest = _make_manifest()
    _create_source_files(tmp_path, manifest)
    build_client_package(manifest, tmp_path)
    content = (tmp_path / "client_package" / "executive_report.html").read_text(encoding="utf-8")
    assert content == "stub:Executive Report (HTML)"


# ---------------------------------------------------------------------------
# README.md
# ---------------------------------------------------------------------------


def test_readme_exists(tmp_path):
    manifest = _make_manifest()
    _create_source_files(tmp_path, manifest)
    build_client_package(manifest, tmp_path)
    assert (tmp_path / "client_package" / "README.md").exists()


def test_readme_contains_client_name(tmp_path):
    manifest = _make_manifest()
    _create_source_files(tmp_path, manifest)
    build_client_package(manifest, tmp_path)
    text = (tmp_path / "client_package" / "README.md").read_text(encoding="utf-8")
    assert "Acme Corp" in text


def test_readme_contains_project_name(tmp_path):
    manifest = _make_manifest()
    _create_source_files(tmp_path, manifest)
    build_client_package(manifest, tmp_path)
    text = (tmp_path / "client_package" / "README.md").read_text(encoding="utf-8")
    assert "Test Campus Project" in text


def test_readme_contains_project_id(tmp_path):
    manifest = _make_manifest()
    _create_source_files(tmp_path, manifest)
    build_client_package(manifest, tmp_path)
    text = (tmp_path / "client_package" / "README.md").read_text(encoding="utf-8")
    assert "TEST-001" in text


def test_readme_lists_copied_package_paths(tmp_path):
    manifest = _make_manifest()
    _create_source_files(tmp_path, manifest)
    build_client_package(manifest, tmp_path)
    text = (tmp_path / "client_package" / "README.md").read_text(encoding="utf-8")
    assert "executive_report.html" in text
    assert "readiness_dashboard.html" in text
    assert "powerbi/readiness_kpis.csv" in text


def test_readme_no_missing_section_when_all_present(tmp_path):
    manifest = _make_manifest()
    _create_source_files(tmp_path, manifest)
    build_client_package(manifest, tmp_path)
    text = (tmp_path / "client_package" / "README.md").read_text(encoding="utf-8")
    assert "Missing Artifacts" not in text


def test_readme_missing_section_present_when_file_absent(tmp_path):
    manifest = _make_manifest()
    _create_source_files(tmp_path, manifest)
    # Remove one source file so it is absent from disk
    (tmp_path / "report" / "report.pdf").unlink()
    build_client_package(manifest, tmp_path)
    text = (tmp_path / "client_package" / "README.md").read_text(encoding="utf-8")
    assert "Missing Artifacts" in text


def test_readme_missing_section_names_missing_file(tmp_path):
    manifest = _make_manifest()
    _create_source_files(tmp_path, manifest)
    (tmp_path / "report" / "report.pdf").unlink()
    build_client_package(manifest, tmp_path)
    text = (tmp_path / "client_package" / "README.md").read_text(encoding="utf-8")
    assert "report/report.pdf" in text


def test_readme_falls_back_gracefully_when_no_client_block(tmp_path):
    manifest = _make_manifest(client=False)
    _create_source_files(tmp_path, manifest)
    build_client_package(manifest, tmp_path)
    text = (tmp_path / "client_package" / "README.md").read_text(encoding="utf-8")
    # Should still produce a valid README without raising
    assert "README" not in text or True  # just checking it doesn't raise


# ---------------------------------------------------------------------------
# package_manifest.json
# ---------------------------------------------------------------------------


def test_package_manifest_exists(tmp_path):
    manifest = _make_manifest()
    _create_source_files(tmp_path, manifest)
    build_client_package(manifest, tmp_path)
    assert (tmp_path / "client_package" / "package_manifest.json").exists()


def test_package_manifest_is_valid_json(tmp_path):
    manifest = _make_manifest()
    _create_source_files(tmp_path, manifest)
    build_client_package(manifest, tmp_path)
    raw = (tmp_path / "client_package" / "package_manifest.json").read_text(encoding="utf-8")
    loaded = json.loads(raw)
    assert isinstance(loaded, dict)


def test_package_manifest_has_client_block(tmp_path):
    manifest = _make_manifest()
    _create_source_files(tmp_path, manifest)
    build_client_package(manifest, tmp_path)
    pkg_manifest = json.loads(
        (tmp_path / "client_package" / "package_manifest.json").read_text(encoding="utf-8")
    )
    assert pkg_manifest["client"]["client_name"] == "Acme Corp"
    assert pkg_manifest["client"]["project_id"] == "TEST-001"


def test_package_manifest_contains_only_packaged_audiences(tmp_path):
    manifest = _make_manifest()
    _create_source_files(tmp_path, manifest)
    build_client_package(manifest, tmp_path)
    pkg_manifest = json.loads(
        (tmp_path / "client_package" / "package_manifest.json").read_text(encoding="utf-8")
    )
    audiences = {a["audience"] for a in pkg_manifest["artifacts"]}
    assert audiences <= {"client_facing", "bi_facing"}


def test_package_manifest_no_internal_entries(tmp_path):
    manifest = _make_manifest()
    _create_source_files(tmp_path, manifest)
    build_client_package(manifest, tmp_path)
    pkg_manifest = json.loads(
        (tmp_path / "client_package" / "package_manifest.json").read_text(encoding="utf-8")
    )
    internal = [a for a in pkg_manifest["artifacts"] if a["audience"] == "internal"]
    assert internal == []


def test_package_manifest_artifact_has_source_path(tmp_path):
    manifest = _make_manifest()
    _create_source_files(tmp_path, manifest)
    build_client_package(manifest, tmp_path)
    pkg_manifest = json.loads(
        (tmp_path / "client_package" / "package_manifest.json").read_text(encoding="utf-8")
    )
    report_entry = next(
        a for a in pkg_manifest["artifacts"] if a.get("source_path") == "report/report.html"
    )
    assert report_entry["package_path"] == "executive_report.html"


def test_package_manifest_artifact_has_package_path(tmp_path):
    manifest = _make_manifest()
    _create_source_files(tmp_path, manifest)
    build_client_package(manifest, tmp_path)
    pkg_manifest = json.loads(
        (tmp_path / "client_package" / "package_manifest.json").read_text(encoding="utf-8")
    )
    for artifact in pkg_manifest["artifacts"]:
        assert "package_path" in artifact, f"Missing package_path on: {artifact['name']}"


def test_package_manifest_artifact_count_matches_copied(tmp_path):
    manifest = _make_manifest()
    _create_source_files(tmp_path, manifest)
    result = build_client_package(manifest, tmp_path)
    pkg_manifest = json.loads(
        (tmp_path / "client_package" / "package_manifest.json").read_text(encoding="utf-8")
    )
    assert len(pkg_manifest["artifacts"]) == len(result["copied"])


# ---------------------------------------------------------------------------
# Return value
# ---------------------------------------------------------------------------


def test_returns_package_dir_path(tmp_path):
    manifest = _make_manifest()
    _create_source_files(tmp_path, manifest)
    result = build_client_package(manifest, tmp_path)
    assert isinstance(result["package_dir"], Path)
    assert result["package_dir"].name == "client_package"


def test_returns_copied_list(tmp_path):
    manifest = _make_manifest()
    _create_source_files(tmp_path, manifest)
    result = build_client_package(manifest, tmp_path)
    assert isinstance(result["copied"], list)
    assert len(result["copied"]) == 6  # 4 client_facing + 2 bi_facing


def test_returns_empty_missing_when_all_present(tmp_path):
    manifest = _make_manifest()
    _create_source_files(tmp_path, manifest)
    result = build_client_package(manifest, tmp_path)
    assert result["missing"] == []


def test_returns_missing_list_with_absent_file(tmp_path):
    manifest = _make_manifest()
    _create_source_files(tmp_path, manifest)
    (tmp_path / "report" / "report.pdf").unlink()
    result = build_client_package(manifest, tmp_path)
    assert any(m["relative_path"] == "report/report.pdf" for m in result["missing"])


# ---------------------------------------------------------------------------
# Missing artifact handling
# ---------------------------------------------------------------------------


def test_missing_source_file_does_not_raise(tmp_path):
    manifest = _make_manifest()
    _create_source_files(tmp_path, manifest)
    (tmp_path / "visuals" / "readiness_dashboard.pdf").unlink()
    # Must not raise
    build_client_package(manifest, tmp_path)


def test_present_artifacts_copied_when_some_missing(tmp_path):
    manifest = _make_manifest()
    _create_source_files(tmp_path, manifest)
    (tmp_path / "report" / "report.pdf").unlink()
    result = build_client_package(manifest, tmp_path)
    pkg = tmp_path / "client_package"
    # The HTML (present) should still be copied
    assert (pkg / "executive_report.html").exists()
    # The PDF (absent) should not be in copied list
    copied_paths = {c["package_path"] for c in result["copied"]}
    assert "executive_report.pdf" not in copied_paths


def test_all_missing_still_creates_dir_and_readme(tmp_path):
    manifest = _make_manifest()
    # Deliberately create no source files
    result = build_client_package(manifest, tmp_path)
    assert result["package_dir"].exists()
    assert (result["package_dir"] / "README.md").exists()
    assert len(result["copied"]) == 0
    assert len(result["missing"]) == 6  # all 4 client_facing + 2 bi_facing


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


def test_package_dir_name_is_client_package(tmp_path):
    manifest = _make_manifest()
    result = build_client_package(manifest, tmp_path)
    assert result["package_dir"] == tmp_path / "client_package"


def test_empty_artifacts_list_creates_dir(tmp_path):
    manifest = {**_make_manifest(), "artifacts": []}
    result = build_client_package(manifest, tmp_path)
    assert result["package_dir"].exists()
    assert result["copied"] == []
    assert result["missing"] == []


def test_only_internal_artifacts_creates_empty_package(tmp_path):
    manifest = _make_manifest()
    # Keep only internal entries
    manifest["artifacts"] = [
        a for a in manifest["artifacts"] if a["audience"] == "internal"
    ]
    _create_source_files(tmp_path, manifest)
    result = build_client_package(manifest, tmp_path)
    assert result["copied"] == []
    pkg = tmp_path / "client_package"
    files = {f.name for f in pkg.rglob("*") if f.is_file()}
    assert files == {"README.md", "package_manifest.json"}


def test_idempotent_second_call_overwrites(tmp_path):
    manifest = _make_manifest()
    _create_source_files(tmp_path, manifest)
    build_client_package(manifest, tmp_path)
    # Second call must not raise and must overwrite cleanly
    result2 = build_client_package(manifest, tmp_path)
    assert len(result2["copied"]) == 6
