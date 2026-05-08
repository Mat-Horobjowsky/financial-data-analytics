import json
from pathlib import Path
from unittest.mock import patch

import pytest

from analytics_pipeline import __version__
from analytics_pipeline.stages import StageContext, StageResult
from analytics_pipeline.summary import build_pipeline_summary, write_summary


def _ctx(tmp_path, with_time=False, template="full_report", with_store=False, with_visuals=False):
    return StageContext(
        input_file=tmp_path / "data.csv",
        output_root=tmp_path / "out",
        with_time=with_time,
        template=template,
        results={},
        with_store=with_store,
        with_visuals=with_visuals,
    )


def _result(name, status="success", template_extra=False):
    extra = {"template": "full_report"} if template_extra else {}
    return StageResult(
        name=name,
        status=status,
        command=["echo", name],
        output_dir=Path(f"/out/{name}"),
        generated_files=["a.csv"],
        extra=extra,
    )


def _all_success_results():
    return {
        "intake": _result("intake"),
        "metrics": _result("metrics"),
        "report": _result("report", template_extra=True),
    }


# --- build_pipeline_summary structure ---


def test_summary_has_pipeline_version(tmp_path):
    ctx = _ctx(tmp_path)
    s = build_pipeline_summary(ctx, _all_success_results())
    assert s["pipeline_version"] == __version__


def test_summary_has_generated_at(tmp_path):
    ctx = _ctx(tmp_path)
    s = build_pipeline_summary(ctx, _all_success_results())
    assert "generated_at" in s
    assert "T" in s["generated_at"]  # ISO 8601


def test_summary_has_input_path(tmp_path):
    ctx = _ctx(tmp_path)
    s = build_pipeline_summary(ctx, _all_success_results())
    assert s["input_path"] == str(tmp_path / "data.csv")


def test_summary_has_output_dir(tmp_path):
    ctx = _ctx(tmp_path)
    s = build_pipeline_summary(ctx, _all_success_results())
    assert s["output_dir"] == str(tmp_path / "out")


def test_summary_with_time_false(tmp_path):
    ctx = _ctx(tmp_path, with_time=False)
    s = build_pipeline_summary(ctx, _all_success_results())
    assert s["with_time"] is False


def test_summary_with_time_true(tmp_path):
    ctx = _ctx(tmp_path, with_time=True)
    s = build_pipeline_summary(ctx, _all_success_results())
    assert s["with_time"] is True


def test_summary_template(tmp_path):
    ctx = _ctx(tmp_path, template="executive_summary")
    s = build_pipeline_summary(ctx, _all_success_results())
    assert s["template"] == "executive_summary"


def test_summary_status_success_when_all_pass(tmp_path):
    ctx = _ctx(tmp_path)
    s = build_pipeline_summary(ctx, _all_success_results())
    assert s["status"] == "success"


def test_summary_status_failed_when_any_fails(tmp_path):
    ctx = _ctx(tmp_path)
    results = _all_success_results()
    results["metrics"] = _result("metrics", status="failed")
    s = build_pipeline_summary(ctx, results)
    assert s["status"] == "failed"


def test_summary_status_failed_when_empty_results(tmp_path):
    ctx = _ctx(tmp_path)
    s = build_pipeline_summary(ctx, {})
    assert s["status"] == "failed"


def test_summary_stages_has_all_active_names(tmp_path):
    ctx = _ctx(tmp_path)
    s = build_pipeline_summary(ctx, _all_success_results())
    assert set(s["stages"].keys()) == {"intake", "metrics", "report"}


def test_summary_skipped_stage_when_early_failure(tmp_path):
    ctx = _ctx(tmp_path)
    partial = {"intake": _result("intake", status="failed")}
    s = build_pipeline_summary(ctx, partial)
    assert s["stages"]["metrics"]["status"] == "skipped"
    assert s["stages"]["report"]["status"] == "skipped"


def test_summary_stage_has_command_string(tmp_path):
    ctx = _ctx(tmp_path)
    s = build_pipeline_summary(ctx, _all_success_results())
    assert isinstance(s["stages"]["intake"]["command"], str)
    assert "echo" in s["stages"]["intake"]["command"]


def test_summary_stage_has_output_dir(tmp_path):
    ctx = _ctx(tmp_path)
    s = build_pipeline_summary(ctx, _all_success_results())
    assert "output_dir" in s["stages"]["intake"]


def test_summary_stage_has_generated_files(tmp_path):
    ctx = _ctx(tmp_path)
    s = build_pipeline_summary(ctx, _all_success_results())
    assert s["stages"]["intake"]["generated_files"] == ["a.csv"]


def test_summary_report_stage_has_template_extra(tmp_path):
    ctx = _ctx(tmp_path)
    s = build_pipeline_summary(ctx, _all_success_results())
    assert s["stages"]["report"]["template"] == "full_report"


def test_summary_future_stages(tmp_path):
    ctx = _ctx(tmp_path)
    s = build_pipeline_summary(ctx, _all_success_results())
    assert "store" in s["future_stages"]
    assert "visuals" not in s["future_stages"]


# --- write_summary ---


def test_write_summary_creates_file(tmp_path):
    summary = {"status": "success"}
    path = write_summary(summary, tmp_path / "out")
    assert path.exists()
    assert path.name == "pipeline_summary.json"


def test_write_summary_valid_json(tmp_path):
    summary = {"status": "success", "value": 42}
    path = write_summary(summary, tmp_path / "out")
    loaded = json.loads(path.read_text(encoding="utf-8"))
    assert loaded == summary


def test_write_summary_creates_parent_dir(tmp_path):
    out = tmp_path / "deep" / "nested" / "out"
    write_summary({"x": 1}, out)
    assert (out / "pipeline_summary.json").exists()


def test_write_summary_returns_path(tmp_path):
    path = write_summary({}, tmp_path / "out")
    assert isinstance(path, Path)
    assert path.name == "pipeline_summary.json"


# --- with_store in summary ---


def test_summary_has_with_store_false_by_default(tmp_path):
    ctx = _ctx(tmp_path)
    s = build_pipeline_summary(ctx, _all_success_results())
    assert s["with_store"] is False


def test_summary_has_with_store_true_when_set(tmp_path):
    ctx = _ctx(tmp_path, with_store=True)
    store_result = _result("store")
    results = {**_all_success_results(), "store": store_result}
    s = build_pipeline_summary(ctx, results)
    assert s["with_store"] is True


def test_summary_store_not_in_stages_when_without_store(tmp_path):
    ctx = _ctx(tmp_path, with_store=False)
    s = build_pipeline_summary(ctx, _all_success_results())
    assert "store" not in s["stages"]


def test_summary_store_in_stages_when_with_store_and_ran(tmp_path):
    ctx = _ctx(tmp_path, with_store=True)
    store_result = _result("store")
    results = {**_all_success_results(), "store": store_result}
    s = build_pipeline_summary(ctx, results)
    assert "store" in s["stages"]
    assert s["stages"]["store"]["status"] == "success"


def test_summary_store_skipped_when_with_store_but_not_in_results(tmp_path):
    ctx = _ctx(tmp_path, with_store=True)
    partial = {"intake": _result("intake", status="failed")}
    s = build_pipeline_summary(ctx, partial)
    assert s["stages"]["store"]["status"] == "skipped"


def test_summary_future_stages_excludes_store_when_with_store(tmp_path):
    ctx = _ctx(tmp_path, with_store=True)
    store_result = _result("store")
    results = {**_all_success_results(), "store": store_result}
    s = build_pipeline_summary(ctx, results)
    assert "store" not in s["future_stages"]
    assert "visuals" not in s["future_stages"]


# --- with_visuals in summary ---


def test_summary_has_with_visuals_false_by_default(tmp_path):
    ctx = _ctx(tmp_path)
    s = build_pipeline_summary(ctx, _all_success_results())
    assert s["with_visuals"] is False


def test_summary_has_with_visuals_true_when_set(tmp_path):
    ctx = _ctx(tmp_path, with_store=True, with_visuals=True)
    results = {**_all_success_results(), "store": _result("store"), "visuals": _result("visuals")}
    s = build_pipeline_summary(ctx, results)
    assert s["with_visuals"] is True


def test_summary_visuals_not_in_stages_when_without_visuals(tmp_path):
    ctx = _ctx(tmp_path, with_visuals=False)
    s = build_pipeline_summary(ctx, _all_success_results())
    assert "visuals" not in s["stages"]


def test_summary_visuals_in_stages_when_with_visuals_and_ran(tmp_path):
    ctx = _ctx(tmp_path, with_store=True, with_visuals=True)
    results = {**_all_success_results(), "store": _result("store"), "visuals": _result("visuals")}
    s = build_pipeline_summary(ctx, results)
    assert "visuals" in s["stages"]
    assert s["stages"]["visuals"]["status"] == "success"


def test_summary_visuals_skipped_when_with_visuals_but_not_in_results(tmp_path):
    ctx = _ctx(tmp_path, with_store=True, with_visuals=True)
    partial = {"intake": _result("intake", status="failed")}
    s = build_pipeline_summary(ctx, partial)
    assert s["stages"]["visuals"]["status"] == "skipped"
