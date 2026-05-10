"""
End-to-end integration smoke test for the readiness pipeline.

Gated by environment variable — skipped by default in CI and local unit test runs.
To run:

    ANALYTICS_PIPELINE_INTEGRATION_TESTS=1 py -m pytest analytics_pipeline/tests/analytics_pipeline/test_integration_readiness.py -v

The test runs the real pipeline against the readiness demo workbook and asserts
all expected output files are produced.
"""
from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]

INTEGRATION = os.environ.get("ANALYTICS_PIPELINE_INTEGRATION_TESTS", "").lower() in ("1", "true", "yes")

pytestmark = pytest.mark.skipif(
    not INTEGRATION,
    reason="Set ANALYTICS_PIPELINE_INTEGRATION_TESTS=1 to run integration tests",
)


def test_readiness_full_pipeline(tmp_path):
    input_file = _REPO_ROOT / "examples" / "readiness_demo" / "sample_client_intake_template.xlsx"
    metrics_config = _REPO_ROOT / "metrics_engine" / "config" / "readiness_metrics.yaml"
    schema_config = _REPO_ROOT / "metrics_engine" / "config" / "readiness_schema.yaml"
    out = tmp_path / "pipeline"

    for p in (input_file, metrics_config, schema_config):
        assert p.exists(), f"Fixture not found: {p}"

    pipeline_exe = shutil.which("analytics-pipeline") or "analytics-pipeline"
    result = subprocess.run(
        [
            pipeline_exe, "run",
            "--input", str(input_file),
            "--sheet", "PowerBI_Export",
            "--output", str(out),
            "--metrics-config", str(metrics_config),
            "--schema-config", str(schema_config),
            "--with-visuals",
            "--with-powerbi-export",
        ],
        capture_output=True,
        text=True,
        cwd=str(_REPO_ROOT),
    )

    assert result.returncode == 0, (
        f"Pipeline exited with {result.returncode}\n"
        f"--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}"
    )

    expected_files = [
        out / "pipeline_summary.json",
        out / "store" / "analytics.duckdb",
        out / "visuals" / "readiness_dashboard.html",
        out / "powerbi" / "readiness_kpis.csv",
        out / "powerbi" / "readiness_by_category.csv",
        out / "powerbi" / "readiness_by_market.csv",
        out / "powerbi" / "validation_summary.csv",
        out / "powerbi" / "metric_dictionary.csv",
    ]
    for path in expected_files:
        assert path.exists(), f"Expected output not found: {path.relative_to(tmp_path)}"

    summary = json.loads((out / "pipeline_summary.json").read_text(encoding="utf-8"))
    assert summary["status"] == "success"
    assert summary["sheet"] == "PowerBI_Export"
    assert summary["with_powerbi_export"] is True
    assert summary["with_visuals"] is True
    assert "readiness_metrics.yaml" in summary["metrics_config_path"]
    assert "readiness_schema.yaml" in summary["schema_config_path"]
    for stage in ("intake", "metrics", "report", "store", "visuals", "powerbi_export"):
        assert summary["stages"][stage]["status"] == "success", f"Stage {stage!r} did not succeed"
