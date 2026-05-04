import dataclasses
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from analytics_pipeline.runner import run_pipeline, run_stage
from analytics_pipeline.stages import ACTIVE_STAGES, StageContext, StageResult


def _ctx(tmp_path, with_time=False, template="full_report", with_store=False):
    return StageContext(
        input_file=tmp_path / "data.csv",
        output_root=tmp_path / "out",
        with_time=with_time,
        template=template,
        results={},
        with_store=with_store,
    )


def _mock_proc(returncode=0, stderr=""):
    proc = MagicMock()
    proc.returncode = returncode
    proc.stderr = stderr
    return proc


# --- run_stage ---


def test_run_stage_success_status(tmp_path):
    out_dir = tmp_path / "stage_out"
    with patch("analytics_pipeline.runner.subprocess.run", return_value=_mock_proc(0)):
        result = run_stage("intake", ["echo", "ok"], out_dir)
    assert result.status == "success"


def test_run_stage_failed_status(tmp_path):
    out_dir = tmp_path / "stage_out"
    with patch("analytics_pipeline.runner.subprocess.run", return_value=_mock_proc(1, "boom")):
        result = run_stage("intake", ["bad-cmd"], out_dir)
    assert result.status == "failed"


def test_run_stage_error_captured_on_failure(tmp_path):
    out_dir = tmp_path / "stage_out"
    with patch("analytics_pipeline.runner.subprocess.run", return_value=_mock_proc(1, "  error msg  ")):
        result = run_stage("intake", ["bad-cmd"], out_dir)
    assert result.error == "error msg"


def test_run_stage_no_error_on_success(tmp_path):
    out_dir = tmp_path / "stage_out"
    with patch("analytics_pipeline.runner.subprocess.run", return_value=_mock_proc(0)):
        result = run_stage("intake", ["echo", "ok"], out_dir)
    assert result.error is None


def test_run_stage_creates_output_dir(tmp_path):
    out_dir = tmp_path / "new_dir"
    assert not out_dir.exists()
    with patch("analytics_pipeline.runner.subprocess.run", return_value=_mock_proc(0)):
        run_stage("intake", ["echo"], out_dir)
    assert out_dir.exists()


def test_run_stage_records_command(tmp_path):
    out_dir = tmp_path / "stage_out"
    cmd = ["echo", "hello"]
    with patch("analytics_pipeline.runner.subprocess.run", return_value=_mock_proc(0)):
        result = run_stage("intake", cmd, out_dir)
    assert result.command == cmd


def test_run_stage_records_name(tmp_path):
    out_dir = tmp_path / "stage_out"
    with patch("analytics_pipeline.runner.subprocess.run", return_value=_mock_proc(0)):
        result = run_stage("metrics", ["echo"], out_dir)
    assert result.name == "metrics"


def test_run_stage_lists_generated_files(tmp_path):
    out_dir = tmp_path / "stage_out"
    out_dir.mkdir()
    (out_dir / "a.csv").write_text("x")
    (out_dir / "b.json").write_text("{}")
    with patch("analytics_pipeline.runner.subprocess.run", return_value=_mock_proc(0)):
        result = run_stage("intake", ["echo"], out_dir)
    assert result.generated_files == ["a.csv", "b.json"]


# --- run_pipeline ---


def _make_success_stages(names=("intake", "metrics", "report"), template="full_report"):
    """Return ACTIVE_STAGES-compatible list that always produces success results."""
    stages = []
    for name in names:
        def _cmd(ctx, _n=name):
            return ["echo", _n]
        stages.append((name, _cmd))
    return stages


def test_run_pipeline_returns_dict(tmp_path):
    ctx = _ctx(tmp_path)
    with patch("analytics_pipeline.runner.subprocess.run", return_value=_mock_proc(0)), \
         patch("analytics_pipeline.runner.ACTIVE_STAGES", _make_success_stages()):
        results = run_pipeline(ctx)
    assert isinstance(results, dict)


def test_run_pipeline_all_stages_present_on_success(tmp_path):
    ctx = _ctx(tmp_path)
    with patch("analytics_pipeline.runner.subprocess.run", return_value=_mock_proc(0)), \
         patch("analytics_pipeline.runner.ACTIVE_STAGES", _make_success_stages()):
        results = run_pipeline(ctx)
    assert set(results.keys()) == {"intake", "metrics", "report"}


def test_run_pipeline_stops_after_failure(tmp_path):
    ctx = _ctx(tmp_path)
    call_count = [0]

    def _side_effect(cmd, **kwargs):
        call_count[0] += 1
        if call_count[0] == 1:
            return _mock_proc(1, "intake failed")
        return _mock_proc(0)

    with patch("analytics_pipeline.runner.subprocess.run", side_effect=_side_effect), \
         patch("analytics_pipeline.runner.ACTIVE_STAGES", _make_success_stages()):
        results = run_pipeline(ctx)

    assert "intake" in results
    assert results["intake"].status == "failed"
    assert "metrics" not in results
    assert "report" not in results


def test_run_pipeline_report_stage_has_template_extra(tmp_path):
    ctx = _ctx(tmp_path, template="executive_summary")
    with patch("analytics_pipeline.runner.subprocess.run", return_value=_mock_proc(0)), \
         patch("analytics_pipeline.runner.ACTIVE_STAGES", _make_success_stages()):
        results = run_pipeline(ctx)
    assert results["report"].extra.get("template") == "executive_summary"


def test_run_pipeline_intake_stage_no_template_extra(tmp_path):
    ctx = _ctx(tmp_path)
    with patch("analytics_pipeline.runner.subprocess.run", return_value=_mock_proc(0)), \
         patch("analytics_pipeline.runner.ACTIVE_STAGES", _make_success_stages()):
        results = run_pipeline(ctx)
    assert "template" not in results["intake"].extra


def test_run_pipeline_all_success_statuses(tmp_path):
    ctx = _ctx(tmp_path)
    with patch("analytics_pipeline.runner.subprocess.run", return_value=_mock_proc(0)), \
         patch("analytics_pipeline.runner.ACTIVE_STAGES", _make_success_stages()):
        results = run_pipeline(ctx)
    assert all(r.status == "success" for r in results.values())


# --- store stage (optional) ---


def test_run_pipeline_skips_store_when_with_store_false(tmp_path):
    ctx = _ctx(tmp_path, with_store=False)
    with patch("analytics_pipeline.runner.subprocess.run", return_value=_mock_proc(0)), \
         patch("analytics_pipeline.runner.ACTIVE_STAGES", _make_success_stages()):
        results = run_pipeline(ctx)
    assert "store" not in results


def test_run_pipeline_runs_store_when_with_store_true(tmp_path):
    ctx = _ctx(tmp_path, with_store=True)
    with patch("analytics_pipeline.runner.subprocess.run", return_value=_mock_proc(0)), \
         patch("analytics_pipeline.runner.ACTIVE_STAGES", _make_success_stages()):
        results = run_pipeline(ctx)
    assert "store" in results
    assert results["store"].status == "success"


def test_run_pipeline_store_not_run_if_report_failed(tmp_path):
    ctx = _ctx(tmp_path, with_store=True)
    call_count = [0]

    def _side_effect(cmd, **kwargs):
        call_count[0] += 1
        if call_count[0] == 3:
            return _mock_proc(1, "report failed")
        return _mock_proc(0)

    with patch("analytics_pipeline.runner.subprocess.run", side_effect=_side_effect), \
         patch("analytics_pipeline.runner.ACTIVE_STAGES", _make_success_stages()):
        results = run_pipeline(ctx)

    assert results["report"].status == "failed"
    assert "store" not in results


def test_run_pipeline_store_extra_has_output_path(tmp_path):
    ctx = _ctx(tmp_path, with_store=True)
    with patch("analytics_pipeline.runner.subprocess.run", return_value=_mock_proc(0)), \
         patch("analytics_pipeline.runner.ACTIVE_STAGES", _make_success_stages()):
        results = run_pipeline(ctx)
    assert "output_path" in results["store"].extra
    assert results["store"].extra["output_path"].endswith("analytics.duckdb")
