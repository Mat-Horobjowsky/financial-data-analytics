import json
import subprocess
import sys
from pathlib import Path

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
