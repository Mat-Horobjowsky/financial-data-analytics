import importlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

_XHTML2PDF_AVAILABLE = importlib.util.find_spec("xhtml2pdf") is not None

SPEC_PATH = str(Path(__file__).parent.parent / "visuals_engine" / "specs" / "readiness_dashboard.yaml")


def _run(args: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(
        [sys.executable, "-m", "visuals_engine.cli"] + args,
        capture_output=True,
        text=True,
        **kwargs,
    )


def test_cli_build_exits_zero(sample_store, tmp_path):
    result = _run(["build", "--store", sample_store, "--spec", SPEC_PATH, "--output", str(tmp_path / "out")])
    assert result.returncode == 0, result.stderr


def test_cli_build_creates_html(sample_store, tmp_path):
    out = tmp_path / "out"
    _run(["build", "--store", sample_store, "--spec", SPEC_PATH, "--output", str(out)])
    assert (out / "readiness_dashboard.html").exists()


def test_cli_build_creates_json(sample_store, tmp_path):
    out = tmp_path / "out"
    _run(["build", "--store", sample_store, "--spec", SPEC_PATH, "--output", str(out)])
    assert (out / "visuals_summary.json").exists()


def test_cli_build_json_has_required_keys(sample_store, tmp_path):
    out = tmp_path / "out"
    _run(["build", "--store", sample_store, "--spec", SPEC_PATH, "--output", str(out)])
    data = json.loads((out / "visuals_summary.json").read_text())
    for key in ("metrics_rendered", "sections_rendered", "sections_skipped", "validation_status"):
        assert key in data, f"Missing key: {key}"


def test_cli_build_html_is_valid_document(sample_store, tmp_path):
    out = tmp_path / "out"
    _run(["build", "--store", sample_store, "--spec", SPEC_PATH, "--output", str(out)])
    html = (out / "readiness_dashboard.html").read_text()
    assert "<!DOCTYPE html>" in html
    assert "</html>" in html


def test_cli_build_missing_store(tmp_path):
    result = _run(["build", "--store", "no_such.duckdb", "--spec", SPEC_PATH, "--output", str(tmp_path)])
    assert result.returncode == 1
    assert "error" in result.stderr.lower()


def test_cli_build_missing_spec(sample_store, tmp_path):
    result = _run(["build", "--store", sample_store, "--spec", "no_such.yaml", "--output", str(tmp_path)])
    assert result.returncode == 1
    assert "error" in result.stderr.lower()


def test_cli_build_creates_output_dir(sample_store, tmp_path):
    out = tmp_path / "deep" / "nested" / "out"
    result = _run(["build", "--store", sample_store, "--spec", SPEC_PATH, "--output", str(out)])
    assert result.returncode == 0
    assert out.exists()


# --- export-powerbi subcommand ---


def test_cli_export_powerbi_exits_zero(sample_store, tmp_path):
    result = _run(["export-powerbi", "--store", sample_store, "--output", str(tmp_path / "powerbi")])
    assert result.returncode == 0, result.stderr


def test_cli_export_powerbi_creates_all_csvs(sample_store, tmp_path):
    out = tmp_path / "powerbi"
    _run(["export-powerbi", "--store", sample_store, "--output", str(out)])
    for fname in [
        "readiness_kpis.csv",
        "readiness_by_category.csv",
        "readiness_by_market.csv",
        "validation_summary.csv",
        "metric_dictionary.csv",
    ]:
        assert (out / fname).exists(), f"Missing: {fname}"


def test_cli_export_powerbi_creates_output_dir(sample_store, tmp_path):
    out = tmp_path / "deep" / "nested" / "powerbi"
    result = _run(["export-powerbi", "--store", sample_store, "--output", str(out)])
    assert result.returncode == 0
    assert out.exists()


def test_cli_export_powerbi_missing_store(tmp_path):
    result = _run(["export-powerbi", "--store", "no_such.duckdb", "--output", str(tmp_path)])
    assert result.returncode == 1
    assert "error" in result.stderr.lower()


def test_cli_export_powerbi_prints_file_paths(sample_store, tmp_path):
    result = _run(["export-powerbi", "--store", sample_store, "--output", str(tmp_path / "powerbi")])
    assert result.returncode == 0
    assert ".csv" in result.stdout


# --- export-powerbi --client-context ---


def _make_client_context_csv(path, *, client_name="CLI Corp", project_name="", project_id="CLI-001") -> str:
    import csv
    from pathlib import Path as _P
    p = _P(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=["project_id", "client_name", "project_name"])
        writer.writeheader()
        writer.writerow({"project_id": project_id, "client_name": client_name, "project_name": project_name})
    return str(p)


def test_cli_export_powerbi_with_client_context_exits_zero(sample_store, tmp_path):
    ctx = _make_client_context_csv(tmp_path / "client_context.csv")
    result = _run([
        "export-powerbi", "--store", sample_store,
        "--output", str(tmp_path / "powerbi"),
        "--client-context", ctx,
    ])
    assert result.returncode == 0, result.stderr


def test_cli_export_powerbi_with_client_context_creates_csv(sample_store, tmp_path):
    ctx = _make_client_context_csv(tmp_path / "client_context.csv")
    out = tmp_path / "powerbi"
    _run(["export-powerbi", "--store", sample_store, "--output", str(out), "--client-context", ctx])
    assert (out / "client_context.csv").exists()


def test_cli_export_powerbi_missing_client_context_file_exits_nonzero(sample_store, tmp_path):
    result = _run([
        "export-powerbi", "--store", sample_store,
        "--output", str(tmp_path / "powerbi"),
        "--client-context", str(tmp_path / "no_such.csv"),
    ])
    assert result.returncode == 1
    assert "error" in result.stderr.lower()


def test_cli_export_powerbi_without_client_context_still_passes(sample_store, tmp_path):
    result = _run(["export-powerbi", "--store", sample_store, "--output", str(tmp_path / "powerbi")])
    assert result.returncode == 0
    assert not (tmp_path / "powerbi" / "client_context.csv").exists()


# --- build: --client-context ---


def test_cli_build_with_client_context_exits_zero(sample_store, tmp_path):
    ctx = _make_client_context_csv(
        tmp_path / "client_context.csv",
        client_name="Acme Corp",
        project_name="Midwest Campus",
        project_id="P-001",
    )
    result = _run([
        "build", "--store", sample_store,
        "--spec", SPEC_PATH,
        "--output", str(tmp_path / "out"),
        "--client-context", ctx,
    ])
    assert result.returncode == 0, result.stderr


def test_cli_build_with_client_context_html_contains_client_name(sample_store, tmp_path):
    ctx = _make_client_context_csv(
        tmp_path / "client_context.csv",
        client_name="Acme Corp",
        project_name="Midwest Campus",
        project_id="P-001",
    )
    out = tmp_path / "out"
    _run([
        "build", "--store", sample_store,
        "--spec", SPEC_PATH,
        "--output", str(out),
        "--client-context", ctx,
    ])
    html = (out / "readiness_dashboard.html").read_text()
    assert "Acme Corp" in html
    assert "Midwest Campus" in html
    assert "P-001" in html


def test_cli_build_without_client_context_omits_identity(sample_store, tmp_path):
    out = tmp_path / "out"
    _run(["build", "--store", sample_store, "--spec", SPEC_PATH, "--output", str(out)])
    html = (out / "readiness_dashboard.html").read_text()
    assert '<p class="header__client">' not in html


def test_cli_build_missing_client_context_file_exits_nonzero(sample_store, tmp_path):
    result = _run([
        "build", "--store", sample_store,
        "--spec", SPEC_PATH,
        "--output", str(tmp_path / "out"),
        "--client-context", str(tmp_path / "no_such.csv"),
    ])
    assert result.returncode == 1
    assert "error" in result.stderr.lower()


# --- build: PDF artifact ---


def test_cli_build_summary_has_pdf_artifact_key(sample_store, tmp_path):
    out = tmp_path / "out"
    _run(["build", "--store", sample_store, "--spec", SPEC_PATH, "--output", str(out)])
    data = json.loads((out / "visuals_summary.json").read_text())
    assert "pdf_artifact" in data


def test_cli_build_summary_has_pdf_status_key(sample_store, tmp_path):
    out = tmp_path / "out"
    _run(["build", "--store", sample_store, "--spec", SPEC_PATH, "--output", str(out)])
    data = json.loads((out / "visuals_summary.json").read_text())
    assert "pdf_status" in data
    assert data["pdf_status"] in ("generated", "skipped")


@pytest.mark.skipif(_XHTML2PDF_AVAILABLE, reason="xhtml2pdf is installed; test covers unavailable case")
def test_cli_build_pdf_status_skipped_when_xhtml2pdf_unavailable(sample_store, tmp_path):
    out = tmp_path / "out"
    result = _run(["build", "--store", sample_store, "--spec", SPEC_PATH, "--output", str(out)])
    assert result.returncode == 0, result.stderr
    data = json.loads((out / "visuals_summary.json").read_text())
    assert data["pdf_status"] == "skipped"
    assert data["pdf_artifact"] is None


@pytest.mark.skipif(_XHTML2PDF_AVAILABLE, reason="xhtml2pdf is installed; test covers unavailable case")
def test_cli_build_no_pdf_file_when_xhtml2pdf_unavailable(sample_store, tmp_path):
    out = tmp_path / "out"
    _run(["build", "--store", sample_store, "--spec", SPEC_PATH, "--output", str(out)])
    assert not (out / "readiness_dashboard.pdf").exists()


@pytest.mark.skipif(_XHTML2PDF_AVAILABLE, reason="xhtml2pdf is installed; test covers unavailable case")
def test_cli_build_html_still_created_when_pdf_skipped(sample_store, tmp_path):
    out = tmp_path / "out"
    result = _run(["build", "--store", sample_store, "--spec", SPEC_PATH, "--output", str(out)])
    assert result.returncode == 0, result.stderr
    assert (out / "readiness_dashboard.html").exists()


@pytest.mark.skipif(not _XHTML2PDF_AVAILABLE, reason="xhtml2pdf not installed")
def test_cli_build_creates_pdf_when_xhtml2pdf_available(sample_store, tmp_path):
    out = tmp_path / "out"
    result = _run(["build", "--store", sample_store, "--spec", SPEC_PATH, "--output", str(out)])
    assert result.returncode == 0, result.stderr
    assert (out / "readiness_dashboard.pdf").exists()
    data = json.loads((out / "visuals_summary.json").read_text())
    assert data["pdf_status"] == "generated"
    assert data["pdf_artifact"] is not None
