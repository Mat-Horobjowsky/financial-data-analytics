"""
End-to-end CLI tests using subprocess so exit codes and stdout are real.
cwd=ROOT ensures default relative paths (config/, data/) resolve correctly.
"""
import json
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
SAMPLE_CSV = ROOT / "data" / "sample_data_centers.csv"


def _cli(*args):
    return subprocess.run(
        [sys.executable, "-m", "metrics_engine.cli"] + list(args),
        cwd=str(ROOT),
        capture_output=True,
        text=True,
    )


@pytest.fixture
def bad_csv(tmp_path):
    """All schema columns present; revenue is null → validator returns status='failed'."""
    p = tmp_path / "bad.csv"
    p.write_text(
        "date,revenue,capacity_mw,leased_mw,contracted_kw\n"
        "2024-01-01,,10.0,8.0,5000.0\n"
    )
    return p


@pytest.fixture
def custom_config_dir(tmp_path):
    shutil.copy(ROOT / "config" / "metrics.yaml", tmp_path / "metrics.yaml")
    shutil.copy(ROOT / "config" / "schema.yaml", tmp_path / "schema.yaml")
    return tmp_path


# ── run command: happy path ───────────────────────────────────────────────────

def test_run_exits_zero_on_valid_data(tmp_path):
    result = _cli("run", "--input", str(SAMPLE_CSV), "--output", str(tmp_path / "out"))
    assert result.returncode == 0


def test_run_writes_long_metrics_csv(tmp_path):
    out = tmp_path / "out"
    _cli("run", "--input", str(SAMPLE_CSV), "--output", str(out))
    assert (out / "long_metrics.csv").exists()


def test_run_writes_wide_metrics_csv(tmp_path):
    out = tmp_path / "out"
    _cli("run", "--input", str(SAMPLE_CSV), "--output", str(out))
    assert (out / "wide_metrics.csv").exists()


def test_run_writes_metric_dictionary_csv(tmp_path):
    out = tmp_path / "out"
    _cli("run", "--input", str(SAMPLE_CSV), "--output", str(out))
    assert (out / "metric_dictionary.csv").exists()


def test_run_writes_validation_report_json(tmp_path):
    out = tmp_path / "out"
    _cli("run", "--input", str(SAMPLE_CSV), "--output", str(out))
    assert (out / "validation_report.json").exists()


def test_run_prints_output_file_names(tmp_path):
    out = tmp_path / "out"
    result = _cli("run", "--input", str(SAMPLE_CSV), "--output", str(out))
    assert "long_metrics.csv" in result.stdout
    assert "wide_metrics.csv" in result.stdout


def test_run_prints_status(tmp_path):
    result = _cli("run", "--input", str(SAMPLE_CSV), "--output", str(tmp_path / "out"))
    assert "Status:" in result.stdout


def test_run_creates_output_directory_when_missing(tmp_path):
    out = tmp_path / "nested" / "output"
    assert not out.exists()
    _cli("run", "--input", str(SAMPLE_CSV), "--output", str(out))
    assert out.exists()


# ── validate command ──────────────────────────────────────────────────────────

def test_validate_exits_zero_on_valid_data():
    result = _cli("validate", "--input", str(SAMPLE_CSV))
    assert result.returncode == 0


def test_validate_prints_status_to_stdout():
    result = _cli("validate", "--input", str(SAMPLE_CSV))
    assert "Status:" in result.stdout


def test_validate_does_not_write_metric_csvs(tmp_path):
    _cli("validate", "--input", str(SAMPLE_CSV))
    for fname in ["long_metrics.csv", "wide_metrics.csv", "metric_dictionary.csv"]:
        assert not (tmp_path / fname).exists()


# ── failed validation ─────────────────────────────────────────────────────────

def test_failed_validation_exits_nonzero(bad_csv, tmp_path):
    result = _cli("run", "--input", str(bad_csv), "--output", str(tmp_path / "out"))
    assert result.returncode != 0


def test_failed_validation_does_not_write_metric_csvs(bad_csv, tmp_path):
    out = tmp_path / "out"
    _cli("run", "--input", str(bad_csv), "--output", str(out))
    assert not (out / "long_metrics.csv").exists()
    assert not (out / "wide_metrics.csv").exists()
    assert not (out / "metric_dictionary.csv").exists()


def test_failed_validation_writes_validation_report_json(bad_csv, tmp_path):
    out = tmp_path / "out"
    _cli("run", "--input", str(bad_csv), "--output", str(out))
    assert (out / "validation_report.json").exists()


def test_failed_validation_report_json_has_failed_status(bad_csv, tmp_path):
    out = tmp_path / "out"
    _cli("run", "--input", str(bad_csv), "--output", str(out))
    data = json.loads((out / "validation_report.json").read_text())
    assert data["status"] == "failed"


def test_failed_validation_prints_error_summary(bad_csv, tmp_path):
    result = _cli("run", "--input", str(bad_csv), "--output", str(tmp_path / "out"))
    assert "failed" in result.stdout.lower()


def test_validate_command_exits_nonzero_on_failed_data(bad_csv):
    result = _cli("validate", "--input", str(bad_csv))
    assert result.returncode != 0


# ── custom flags ──────────────────────────────────────────────────────────────

def test_custom_output_directory(tmp_path):
    custom_out = tmp_path / "my_custom_dir"
    _cli("run", "--input", str(SAMPLE_CSV), "--output", str(custom_out))
    assert (custom_out / "long_metrics.csv").exists()


def test_custom_config_path(custom_config_dir, tmp_path):
    out = tmp_path / "out"
    result = _cli(
        "run",
        "--input", str(SAMPLE_CSV),
        "--config", str(custom_config_dir / "metrics.yaml"),
        "--output", str(out),
    )
    assert result.returncode == 0
    assert (out / "long_metrics.csv").exists()


def test_custom_schema_path(custom_config_dir, tmp_path):
    out = tmp_path / "out"
    result = _cli(
        "run",
        "--input", str(SAMPLE_CSV),
        "--schema", str(custom_config_dir / "schema.yaml"),
        "--output", str(out),
    )
    assert result.returncode == 0
    assert (out / "long_metrics.csv").exists()


# ── dry-run ───────────────────────────────────────────────────────────────────

def test_dry_run_exits_zero_on_valid_data(tmp_path):
    result = _cli("run", "--input", str(SAMPLE_CSV), "--output", str(tmp_path / "out"), "--dry-run")
    assert result.returncode == 0


def test_dry_run_does_not_write_metric_csvs(tmp_path):
    out = tmp_path / "out"
    _cli("run", "--input", str(SAMPLE_CSV), "--output", str(out), "--dry-run")
    for fname in ["long_metrics.csv", "wide_metrics.csv", "metric_dictionary.csv"]:
        assert not (out / fname).exists()


def test_dry_run_prints_validation_status(tmp_path):
    result = _cli("run", "--input", str(SAMPLE_CSV), "--output", str(tmp_path / "out"), "--dry-run")
    assert "Status:" in result.stdout
