import csv
import json
from pathlib import Path

import pytest

from analytics_pipeline import __version__
from analytics_pipeline.manifest import (
    _classify_artifact,
    build_artifact_manifest,
    parse_client_context,
    write_artifact_manifest,
)
from analytics_pipeline.stages import StageContext, StageResult

_TS = "2026-05-13T20:00:00+00:00"


# --- Helpers ---


def _make_client_context(tmp_path: Path, **overrides) -> Path:
    defaults = {
        "client_name": "Demo AI Infrastructure Co.",
        "project_name": "Midwest AI Campus Requirement",
        "project_id": "DEMO-READY-001",
    }
    row = {**defaults, **overrides}
    path = tmp_path / "client_context.csv"
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(row.keys()))
        writer.writeheader()
        writer.writerow(row)
    return path


def _ctx(tmp_path, client_context_path=None, template="readiness_summary"):
    return StageContext(
        input_file=tmp_path / "data.xlsx",
        output_root=tmp_path / "out",
        with_time=False,
        template=template,
        results={},
        client_context_path=client_context_path,
    )


def _result(stage_name, dir_name, files, tmp_path):
    return StageResult(
        name=stage_name,
        status="success",
        command=["echo", stage_name],
        output_dir=tmp_path / "out" / dir_name,
        generated_files=files,
        extra={},
    )


def _full_results(tmp_path):
    return {
        "intake": _result("intake", "intake", [
            "data_powerbi_export_clean.csv",
            "data_powerbi_export_report.html",
            "data_powerbi_export_validation.json",
        ], tmp_path),
        "metrics": _result("metrics", "metrics", [
            "long_metrics.csv", "wide_metrics.csv", "metrics_output.xlsx",
            "metric_dictionary.csv", "validation_report.json",
        ], tmp_path),
        "report": _result("report", "report", [
            "report.html", "report.pdf", "report.md", "summary.json", "insights.json",
        ], tmp_path),
        "store": _result("store", "store", ["analytics.duckdb"], tmp_path),
        "visuals": _result("visuals", "visuals", [
            "readiness_dashboard.html", "readiness_dashboard.pdf", "visuals_summary.json",
        ], tmp_path),
        "powerbi_export": _result("powerbi_export", "powerbi", [
            "readiness_kpis.csv", "readiness_by_category.csv", "readiness_by_market.csv",
            "metric_dictionary.csv", "validation_summary.csv", "client_context.csv",
        ], tmp_path),
    }


# --- Top-level manifest structure ---


def test_manifest_has_manifest_version(tmp_path):
    m = build_artifact_manifest(_ctx(tmp_path), {}, "success", _TS)
    assert m["manifest_version"] == "1.0"


def test_manifest_has_generated_at(tmp_path):
    m = build_artifact_manifest(_ctx(tmp_path), {}, "success", _TS)
    assert m["generated_at"] == _TS


def test_manifest_has_pipeline_version(tmp_path):
    m = build_artifact_manifest(_ctx(tmp_path), {}, "success", _TS)
    assert m["pipeline_version"] == __version__


def test_manifest_has_run_block(tmp_path):
    ctx = _ctx(tmp_path, template="readiness_summary")
    m = build_artifact_manifest(ctx, {}, "success", _TS)
    run = m["run"]
    assert run["status"] == "success"
    assert run["template"] == "readiness_summary"
    assert "input_file" in run
    assert "output_dir" in run


def test_manifest_has_artifacts_list(tmp_path):
    m = build_artifact_manifest(_ctx(tmp_path), {}, "success", _TS)
    assert isinstance(m["artifacts"], list)


def test_manifest_artifacts_empty_when_no_results(tmp_path):
    m = build_artifact_manifest(_ctx(tmp_path), {}, "success", _TS)
    assert m["artifacts"] == []


# --- Client block ---


def test_manifest_client_block_populated_when_context_provided(tmp_path):
    cc = _make_client_context(tmp_path)
    m = build_artifact_manifest(_ctx(tmp_path, client_context_path=cc), {}, "success", _TS)
    assert m["client"] is not None
    assert m["client"]["client_name"] == "Demo AI Infrastructure Co."
    assert m["client"]["project_name"] == "Midwest AI Campus Requirement"
    assert m["client"]["project_id"] == "DEMO-READY-001"


def test_manifest_client_block_none_when_no_context(tmp_path):
    m = build_artifact_manifest(_ctx(tmp_path, client_context_path=None), {}, "success", _TS)
    assert m["client"] is None


def test_manifest_client_name_extracted(tmp_path):
    cc = _make_client_context(tmp_path, client_name="Acme Corp")
    m = build_artifact_manifest(_ctx(tmp_path, client_context_path=cc), {}, "success", _TS)
    assert m["client"]["client_name"] == "Acme Corp"


def test_manifest_project_name_extracted(tmp_path):
    cc = _make_client_context(tmp_path, project_name="Campus Alpha")
    m = build_artifact_manifest(_ctx(tmp_path, client_context_path=cc), {}, "success", _TS)
    assert m["client"]["project_name"] == "Campus Alpha"


def test_manifest_project_id_extracted(tmp_path):
    cc = _make_client_context(tmp_path, project_id="PRJ-999")
    m = build_artifact_manifest(_ctx(tmp_path, client_context_path=cc), {}, "success", _TS)
    assert m["client"]["project_id"] == "PRJ-999"


# --- Artifact coverage ---


def test_manifest_all_generated_files_represented(tmp_path):
    results = _full_results(tmp_path)
    total_files = sum(len(r.generated_files) for r in results.values())
    m = build_artifact_manifest(_ctx(tmp_path), results, "success", _TS)
    assert len(m["artifacts"]) == total_files


def test_manifest_no_files_dropped(tmp_path):
    results = {
        "metrics": _result("metrics", "metrics", ["long_metrics.csv", "wide_metrics.csv"], tmp_path),
    }
    m = build_artifact_manifest(_ctx(tmp_path), results, "success", _TS)
    paths = [a["relative_path"] for a in m["artifacts"]]
    assert "metrics/long_metrics.csv" in paths
    assert "metrics/wide_metrics.csv" in paths


def test_manifest_partial_results_still_covered(tmp_path):
    results = {
        "intake": _result("intake", "intake", ["data_clean.csv"], tmp_path),
        "metrics": _result("metrics", "metrics", ["long_metrics.csv"], tmp_path),
    }
    m = build_artifact_manifest(_ctx(tmp_path), results, "failed", _TS)
    assert len(m["artifacts"]) == 2


# --- Client-facing artifact classification ---


def test_client_facing_report_html(tmp_path):
    results = {"report": _result("report", "report", ["report.html"], tmp_path)}
    m = build_artifact_manifest(_ctx(tmp_path), results, "success", _TS)
    assert m["artifacts"][0]["audience"] == "client_facing"
    assert m["artifacts"][0]["category"] == "report"


def test_client_facing_report_pdf(tmp_path):
    results = {"report": _result("report", "report", ["report.pdf"], tmp_path)}
    m = build_artifact_manifest(_ctx(tmp_path), results, "success", _TS)
    assert m["artifacts"][0]["audience"] == "client_facing"


def test_client_facing_dashboard_html(tmp_path):
    results = {"visuals": _result("visuals", "visuals", ["readiness_dashboard.html"], tmp_path)}
    m = build_artifact_manifest(_ctx(tmp_path), results, "success", _TS)
    assert m["artifacts"][0]["audience"] == "client_facing"
    assert m["artifacts"][0]["category"] == "dashboard"


def test_client_facing_dashboard_pdf(tmp_path):
    results = {"visuals": _result("visuals", "visuals", ["readiness_dashboard.pdf"], tmp_path)}
    m = build_artifact_manifest(_ctx(tmp_path), results, "success", _TS)
    assert m["artifacts"][0]["audience"] == "client_facing"


def test_exactly_four_client_facing_artifacts_in_full_run(tmp_path):
    m = build_artifact_manifest(_ctx(tmp_path), _full_results(tmp_path), "success", _TS)
    client_facing = [a for a in m["artifacts"] if a["audience"] == "client_facing"]
    paths = {a["relative_path"] for a in client_facing}
    assert paths == {
        "report/report.html",
        "report/report.pdf",
        "visuals/readiness_dashboard.html",
        "visuals/readiness_dashboard.pdf",
    }


# --- BI-facing artifact classification ---


def test_bi_facing_readiness_kpis(tmp_path):
    results = {"powerbi_export": _result("powerbi_export", "powerbi", ["readiness_kpis.csv"], tmp_path)}
    m = build_artifact_manifest(_ctx(tmp_path), results, "success", _TS)
    assert m["artifacts"][0]["audience"] == "bi_facing"
    assert m["artifacts"][0]["category"] == "bi_export"


def test_bi_facing_client_context_csv(tmp_path):
    results = {"powerbi_export": _result("powerbi_export", "powerbi", ["client_context.csv"], tmp_path)}
    m = build_artifact_manifest(_ctx(tmp_path), results, "success", _TS)
    assert m["artifacts"][0]["audience"] == "bi_facing"


def test_bi_facing_all_powerbi_exports(tmp_path):
    files = [
        "readiness_kpis.csv", "readiness_by_category.csv", "readiness_by_market.csv",
        "metric_dictionary.csv", "validation_summary.csv", "client_context.csv",
    ]
    results = {"powerbi_export": _result("powerbi_export", "powerbi", files, tmp_path)}
    m = build_artifact_manifest(_ctx(tmp_path), results, "success", _TS)
    assert all(a["audience"] == "bi_facing" for a in m["artifacts"])


# --- Internal artifact classification ---


def test_internal_intake_clean_csv(tmp_path):
    results = {"intake": _result("intake", "intake", ["data_powerbi_export_clean.csv"], tmp_path)}
    m = build_artifact_manifest(_ctx(tmp_path), results, "success", _TS)
    assert m["artifacts"][0]["audience"] == "internal"
    assert m["artifacts"][0]["category"] == "intake"


def test_internal_store_duckdb(tmp_path):
    results = {"store": _result("store", "store", ["analytics.duckdb"], tmp_path)}
    m = build_artifact_manifest(_ctx(tmp_path), results, "success", _TS)
    assert m["artifacts"][0]["audience"] == "internal"
    assert m["artifacts"][0]["category"] == "store"


def test_internal_report_markdown(tmp_path):
    results = {"report": _result("report", "report", ["report.md"], tmp_path)}
    m = build_artifact_manifest(_ctx(tmp_path), results, "success", _TS)
    assert m["artifacts"][0]["audience"] == "internal"


def test_internal_metrics_long_format(tmp_path):
    results = {"metrics": _result("metrics", "metrics", ["long_metrics.csv"], tmp_path)}
    m = build_artifact_manifest(_ctx(tmp_path), results, "success", _TS)
    assert m["artifacts"][0]["audience"] == "internal"
    assert m["artifacts"][0]["category"] == "metrics"


# --- Dynamic intake filename classification ---


def test_dynamic_intake_clean_csv_pattern(tmp_path):
    results = {"intake": _result("intake", "intake", ["some_sheet_name_clean.csv"], tmp_path)}
    m = build_artifact_manifest(_ctx(tmp_path), results, "success", _TS)
    assert m["artifacts"][0]["name"] == "Cleaned Input Data"
    assert m["artifacts"][0]["category"] == "intake"
    assert m["artifacts"][0]["audience"] == "internal"


def test_dynamic_intake_report_html_pattern(tmp_path):
    results = {"intake": _result("intake", "intake", ["abc_report.html"], tmp_path)}
    m = build_artifact_manifest(_ctx(tmp_path), results, "success", _TS)
    assert m["artifacts"][0]["name"] == "Intake Validation Report"


def test_dynamic_intake_validation_json_pattern(tmp_path):
    results = {"intake": _result("intake", "intake", ["abc_validation.json"], tmp_path)}
    m = build_artifact_manifest(_ctx(tmp_path), results, "success", _TS)
    assert m["artifacts"][0]["name"] == "Intake Validation Summary"


def test_dynamic_clean_csv_does_not_match_report_stage(tmp_path):
    # A *_clean.csv in the report stage is unknown, not intake
    results = {"report": _result("report", "report", ["something_clean.csv"], tmp_path)}
    m = build_artifact_manifest(_ctx(tmp_path), results, "success", _TS)
    assert m["artifacts"][0]["category"] == "unknown"


# --- Unknown / unclassified artifact handling ---


def test_unknown_artifact_category_is_unknown(tmp_path):
    results = {"report": _result("report", "report", ["mystery_file.xyz"], tmp_path)}
    m = build_artifact_manifest(_ctx(tmp_path), results, "success", _TS)
    assert m["artifacts"][0]["category"] == "unknown"


def test_unknown_artifact_audience_is_internal(tmp_path):
    results = {"report": _result("report", "report", ["mystery_file.xyz"], tmp_path)}
    m = build_artifact_manifest(_ctx(tmp_path), results, "success", _TS)
    assert m["artifacts"][0]["audience"] == "internal"


def test_unknown_artifact_name_falls_back_to_filename(tmp_path):
    results = {"intake": _result("intake", "intake", ["weird.bin"], tmp_path)}
    m = build_artifact_manifest(_ctx(tmp_path), results, "success", _TS)
    assert m["artifacts"][0]["name"] == "weird.bin"


def test_unknown_artifact_description_mentions_stage(tmp_path):
    results = {"store": _result("store", "store", ["extra.bin"], tmp_path)}
    m = build_artifact_manifest(_ctx(tmp_path), results, "success", _TS)
    assert "store" in m["artifacts"][0]["description"]


# --- Relative path format ---


def test_artifact_relative_path_uses_actual_dir_name(tmp_path):
    # powerbi_export stage writes to 'powerbi/' directory — path must reflect that
    results = {"powerbi_export": _result("powerbi_export", "powerbi", ["readiness_kpis.csv"], tmp_path)}
    m = build_artifact_manifest(_ctx(tmp_path), results, "success", _TS)
    assert m["artifacts"][0]["relative_path"] == "powerbi/readiness_kpis.csv"


def test_artifact_relative_path_report(tmp_path):
    results = {"report": _result("report", "report", ["report.html"], tmp_path)}
    m = build_artifact_manifest(_ctx(tmp_path), results, "success", _TS)
    assert m["artifacts"][0]["relative_path"] == "report/report.html"


def test_artifact_relative_path_store(tmp_path):
    results = {"store": _result("store", "store", ["analytics.duckdb"], tmp_path)}
    m = build_artifact_manifest(_ctx(tmp_path), results, "success", _TS)
    assert m["artifacts"][0]["relative_path"] == "store/analytics.duckdb"


# --- Required artifact fields ---


def test_artifact_has_all_required_fields(tmp_path):
    results = {"report": _result("report", "report", ["report.html"], tmp_path)}
    m = build_artifact_manifest(_ctx(tmp_path), results, "success", _TS)
    artifact = m["artifacts"][0]
    for field in ("name", "category", "audience", "relative_path", "description", "source_stage", "generated_at"):
        assert field in artifact, f"Missing field: {field}"


def test_artifact_source_stage_matches(tmp_path):
    results = {"store": _result("store", "store", ["analytics.duckdb"], tmp_path)}
    m = build_artifact_manifest(_ctx(tmp_path), results, "success", _TS)
    assert m["artifacts"][0]["source_stage"] == "store"


def test_artifact_generated_at_matches_pipeline_timestamp(tmp_path):
    results = {"report": _result("report", "report", ["report.html"], tmp_path)}
    m = build_artifact_manifest(_ctx(tmp_path), results, "success", _TS)
    assert m["artifacts"][0]["generated_at"] == _TS


# --- write_artifact_manifest ---


def test_write_artifact_manifest_creates_file(tmp_path):
    path = write_artifact_manifest({"manifest_version": "1.0", "artifacts": []}, tmp_path / "out")
    assert path.exists()
    assert path.name == "artifact_manifest.json"


def test_write_artifact_manifest_valid_json(tmp_path):
    manifest = {"manifest_version": "1.0", "artifacts": [{"name": "x"}]}
    path = write_artifact_manifest(manifest, tmp_path / "out")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded == manifest


def test_write_artifact_manifest_creates_parent_dir(tmp_path):
    path = write_artifact_manifest({}, tmp_path / "deep" / "nested" / "out")
    assert path.exists()


def test_write_artifact_manifest_returns_path(tmp_path):
    path = write_artifact_manifest({}, tmp_path / "out")
    assert isinstance(path, Path)
    assert path.name == "artifact_manifest.json"


# --- parse_client_context ---


def test_parse_client_context_returns_expected_fields(tmp_path):
    cc = _make_client_context(tmp_path)
    result = parse_client_context(cc)
    assert result["client_name"] == "Demo AI Infrastructure Co."
    assert result["project_name"] == "Midwest AI Campus Requirement"
    assert result["project_id"] == "DEMO-READY-001"


def test_parse_client_context_returns_none_for_empty_csv(tmp_path):
    path = tmp_path / "empty.csv"
    path.write_text("client_name,project_name,project_id\n", encoding="utf-8")
    assert parse_client_context(path) is None


def test_parse_client_context_returns_none_for_missing_file():
    assert parse_client_context(Path("/nonexistent/path/cc.csv")) is None


def test_parse_client_context_ignores_extra_columns(tmp_path):
    path = tmp_path / "cc.csv"
    path.write_text(
        "client_name,project_name,project_id,extra_col\n"
        "ACME,My Project,P-001,ignored\n",
        encoding="utf-8",
    )
    result = parse_client_context(path)
    assert result["client_name"] == "ACME"
    assert result["project_id"] == "P-001"


def test_parse_client_context_handles_missing_columns_gracefully(tmp_path):
    path = tmp_path / "cc.csv"
    path.write_text("client_name\nACME\n", encoding="utf-8")
    result = parse_client_context(path)
    assert result["client_name"] == "ACME"
    assert result["project_name"] == ""
    assert result["project_id"] == ""


# --- _classify_artifact (unit) ---


def test_classify_artifact_known_report_html():
    c = _classify_artifact("report", "report.html")
    assert c["audience"] == "client_facing"
    assert c["category"] == "report"


def test_classify_artifact_known_powerbi_kpis():
    c = _classify_artifact("powerbi_export", "readiness_kpis.csv")
    assert c["audience"] == "bi_facing"
    assert c["category"] == "bi_export"


def test_classify_artifact_intake_wildcard():
    c = _classify_artifact("intake", "any_stem_clean.csv")
    assert c["name"] == "Cleaned Input Data"
    assert c["audience"] == "internal"


def test_classify_artifact_unknown_returns_fallback():
    c = _classify_artifact("report", "not_a_real_file.bin")
    assert c["category"] == "unknown"
    assert c["audience"] == "internal"
