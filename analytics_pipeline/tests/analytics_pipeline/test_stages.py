import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from analytics_pipeline.stages import (
    ACTIVE_STAGES,
    FUTURE_STAGES,
    StageContext,
    StageResult,
    build_intake_cmd,
    build_metrics_cmd,
    build_report_cmd,
)


def _ctx(tmp_path, with_time=False, template="full_report"):
    return StageContext(
        input_file=tmp_path / "data.csv",
        output_root=tmp_path / "out",
        with_time=with_time,
        template=template,
        results={},
    )


# --- StageResult ---


def test_stage_result_fields():
    r = StageResult(
        name="intake",
        status="success",
        command=["intake", "run"],
        output_dir=Path("/tmp/out/intake"),
        generated_files=["a.csv"],
        extra={},
    )
    assert r.name == "intake"
    assert r.status == "success"
    assert r.error is None


def test_stage_result_error_field():
    r = StageResult(
        name="metrics",
        status="failed",
        command=["python"],
        output_dir=Path("/tmp/out"),
        generated_files=[],
        extra={},
        error="something broke",
    )
    assert r.error == "something broke"


# --- StageContext ---


def test_stage_context_fields(tmp_path):
    ctx = _ctx(tmp_path)
    assert ctx.input_file == tmp_path / "data.csv"
    assert ctx.output_root == tmp_path / "out"
    assert ctx.with_time is False
    assert ctx.template == "full_report"
    assert ctx.results == {}


# --- build_intake_cmd ---


def test_build_intake_cmd_contains_input(tmp_path):
    ctx = _ctx(tmp_path)
    cmd = build_intake_cmd(ctx)
    assert str(ctx.input_file) in cmd


def test_build_intake_cmd_output_dir(tmp_path):
    ctx = _ctx(tmp_path)
    cmd = build_intake_cmd(ctx)
    assert "--output-dir" in cmd
    idx = cmd.index("--output-dir")
    assert cmd[idx + 1] == str(tmp_path / "out" / "intake")


def test_build_intake_cmd_validate_flag(tmp_path):
    ctx = _ctx(tmp_path)
    cmd = build_intake_cmd(ctx)
    assert "--validate" in cmd


def test_build_intake_cmd_uses_which_when_available(tmp_path):
    ctx = _ctx(tmp_path)
    with patch("analytics_pipeline.stages.shutil.which", return_value="/usr/bin/intake"):
        cmd = build_intake_cmd(ctx)
    assert cmd[0] == "/usr/bin/intake"


def test_build_intake_cmd_falls_back_to_intake(tmp_path):
    ctx = _ctx(tmp_path)
    with patch("analytics_pipeline.stages.shutil.which", return_value=None):
        cmd = build_intake_cmd(ctx)
    assert cmd[0] == "intake"


# --- build_metrics_cmd ---


def test_build_metrics_cmd_uses_python_m(tmp_path):
    ctx = _ctx(tmp_path)
    cmd = build_metrics_cmd(ctx)
    assert cmd[0] == sys.executable
    assert "-m" in cmd
    assert "metrics_engine.cli" in cmd


def test_build_metrics_cmd_input_is_clean_csv(tmp_path):
    ctx = _ctx(tmp_path)
    cmd = build_metrics_cmd(ctx)
    idx = cmd.index("--input")
    expected = str(tmp_path / "out" / "intake" / "data_clean.csv")
    assert cmd[idx + 1] == expected


def test_build_metrics_cmd_output_dir(tmp_path):
    ctx = _ctx(tmp_path)
    cmd = build_metrics_cmd(ctx)
    idx = cmd.index("--output")
    assert cmd[idx + 1] == str(tmp_path / "out" / "metrics")


def test_build_metrics_cmd_no_with_time_by_default(tmp_path):
    ctx = _ctx(tmp_path, with_time=False)
    cmd = build_metrics_cmd(ctx)
    assert "--with-time" not in cmd


def test_build_metrics_cmd_with_time_flag(tmp_path):
    ctx = _ctx(tmp_path, with_time=True)
    cmd = build_metrics_cmd(ctx)
    assert "--with-time" in cmd


def test_build_metrics_cmd_has_config_flags(tmp_path):
    ctx = _ctx(tmp_path)
    cmd = build_metrics_cmd(ctx)
    assert "--config" in cmd
    assert "--schema" in cmd


def test_build_metrics_cmd_config_paths_are_absolute(tmp_path):
    ctx = _ctx(tmp_path)
    cmd = build_metrics_cmd(ctx)
    config_idx = cmd.index("--config")
    schema_idx = cmd.index("--schema")
    assert Path(cmd[config_idx + 1]).is_absolute()
    assert Path(cmd[schema_idx + 1]).is_absolute()


# --- build_report_cmd ---


def test_build_report_cmd_uses_python_m(tmp_path):
    ctx = _ctx(tmp_path)
    cmd = build_report_cmd(ctx)
    assert cmd[0] == sys.executable
    assert "-m" in cmd
    assert "report_engine.cli" in cmd


def test_build_report_cmd_input_is_metrics_dir(tmp_path):
    ctx = _ctx(tmp_path)
    cmd = build_report_cmd(ctx)
    idx = cmd.index("--input")
    assert cmd[idx + 1] == str(tmp_path / "out" / "metrics")


def test_build_report_cmd_output_dir(tmp_path):
    ctx = _ctx(tmp_path)
    cmd = build_report_cmd(ctx)
    idx = cmd.index("--output")
    assert cmd[idx + 1] == str(tmp_path / "out" / "report")


def test_build_report_cmd_template_default(tmp_path):
    ctx = _ctx(tmp_path, template="full_report")
    cmd = build_report_cmd(ctx)
    idx = cmd.index("--template")
    assert cmd[idx + 1] == "full_report"


def test_build_report_cmd_template_executive_summary(tmp_path):
    ctx = _ctx(tmp_path, template="executive_summary")
    cmd = build_report_cmd(ctx)
    idx = cmd.index("--template")
    assert cmd[idx + 1] == "executive_summary"


# --- ACTIVE_STAGES ---


def test_active_stages_has_three_entries():
    assert len(ACTIVE_STAGES) == 3


def test_active_stages_order():
    names = [name for name, _ in ACTIVE_STAGES]
    assert names == ["intake", "metrics", "report"]


def test_active_stages_callables():
    for name, fn in ACTIVE_STAGES:
        assert callable(fn), f"{name} builder is not callable"


# --- FUTURE_STAGES ---


def test_future_stages_is_list():
    assert isinstance(FUTURE_STAGES, list)


def test_future_stages_contains_store_and_visuals():
    assert "store" in FUTURE_STAGES
    assert "visuals" in FUTURE_STAGES
