import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from analytics_pipeline.stages import StageResult


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


def _all_success():
    return {
        "intake": _result("intake"),
        "metrics": _result("metrics"),
        "report": _result("report", template_extra=True),
    }


def _run_cli(args, input_exists=True):
    """Invoke cli.main() with mocked run_pipeline and file existence."""
    from analytics_pipeline import cli

    with patch.object(Path, "exists", return_value=input_exists), \
         patch("analytics_pipeline.cli.run_pipeline", return_value=_all_success()), \
         patch("analytics_pipeline.cli.write_summary", return_value=Path("/out/pipeline_summary.json")):
        try:
            with patch("sys.argv", ["analytics-pipeline"] + args):
                cli.main()
            return 0
        except SystemExit as e:
            return e.code


# --- basic argument parsing ---


def test_run_exits_zero_on_success(tmp_path):
    code = _run_cli(["run", "--input", "data.csv", "--output", str(tmp_path)])
    assert code is None or code == 0


def test_run_missing_input_arg_exits_nonzero():
    code = _run_cli(["run", "--output", "out"])
    assert code != 0


def test_run_input_not_found_exits_nonzero():
    code = _run_cli(["run", "--input", "missing.csv", "--output", "out"], input_exists=False)
    assert code != 0


def test_no_subcommand_exits_nonzero():
    from analytics_pipeline import cli
    with patch("sys.argv", ["analytics-pipeline"]):
        try:
            cli.main()
            code = 0
        except SystemExit as e:
            code = e.code
    assert code != 0


# --- --with-time flag ---


def test_with_time_flag_passed_to_context(tmp_path):
    from analytics_pipeline import cli
    captured = {}

    def _capture_pipeline(ctx):
        captured["ctx"] = ctx
        return _all_success()

    with patch.object(Path, "exists", return_value=True), \
         patch("analytics_pipeline.cli.run_pipeline", side_effect=_capture_pipeline), \
         patch("analytics_pipeline.cli.write_summary", return_value=Path("/out/pipeline_summary.json")), \
         patch("sys.argv", ["analytics-pipeline", "run", "--input", "x.csv", "--with-time"]):
        try:
            cli.main()
        except SystemExit:
            pass

    assert captured["ctx"].with_time is True


def test_with_time_defaults_to_false(tmp_path):
    from analytics_pipeline import cli
    captured = {}

    def _capture_pipeline(ctx):
        captured["ctx"] = ctx
        return _all_success()

    with patch.object(Path, "exists", return_value=True), \
         patch("analytics_pipeline.cli.run_pipeline", side_effect=_capture_pipeline), \
         patch("analytics_pipeline.cli.write_summary", return_value=Path("/out/pipeline_summary.json")), \
         patch("sys.argv", ["analytics-pipeline", "run", "--input", "x.csv"]):
        try:
            cli.main()
        except SystemExit:
            pass

    assert captured["ctx"].with_time is False


# --- --template flag ---


def test_template_defaults_to_full_report(tmp_path):
    from analytics_pipeline import cli
    captured = {}

    def _capture_pipeline(ctx):
        captured["ctx"] = ctx
        return _all_success()

    with patch.object(Path, "exists", return_value=True), \
         patch("analytics_pipeline.cli.run_pipeline", side_effect=_capture_pipeline), \
         patch("analytics_pipeline.cli.write_summary", return_value=Path("/out/pipeline_summary.json")), \
         patch("sys.argv", ["analytics-pipeline", "run", "--input", "x.csv"]):
        try:
            cli.main()
        except SystemExit:
            pass

    assert captured["ctx"].template == "full_report"


def test_template_executive_summary(tmp_path):
    from analytics_pipeline import cli
    captured = {}

    def _capture_pipeline(ctx):
        captured["ctx"] = ctx
        return _all_success()

    with patch.object(Path, "exists", return_value=True), \
         patch("analytics_pipeline.cli.run_pipeline", side_effect=_capture_pipeline), \
         patch("analytics_pipeline.cli.write_summary", return_value=Path("/out/pipeline_summary.json")), \
         patch("sys.argv", ["analytics-pipeline", "run", "--input", "x.csv",
                            "--template", "executive_summary"]):
        try:
            cli.main()
        except SystemExit:
            pass

    assert captured["ctx"].template == "executive_summary"


def test_invalid_template_exits_nonzero():
    from analytics_pipeline import cli
    with patch("sys.argv", ["analytics-pipeline", "run", "--input", "x.csv",
                            "--template", "not_a_real_template"]):
        try:
            cli.main()
            code = 0
        except SystemExit as e:
            code = e.code
    assert code != 0


# --- failure propagation ---


def test_pipeline_failure_exits_nonzero(tmp_path):
    from analytics_pipeline import cli
    failed_results = {
        "intake": _result("intake", status="failed"),
    }
    with patch.object(Path, "exists", return_value=True), \
         patch("analytics_pipeline.cli.run_pipeline", return_value=failed_results), \
         patch("analytics_pipeline.cli.write_summary", return_value=Path("/out/pipeline_summary.json")), \
         patch("sys.argv", ["analytics-pipeline", "run", "--input", "x.csv"]):
        try:
            cli.main()
            code = 0
        except SystemExit as e:
            code = e.code
    assert code != 0


# --- output path ---


def test_output_defaults_to_outputs_pipeline():
    from analytics_pipeline import cli
    captured = {}

    def _capture_pipeline(ctx):
        captured["ctx"] = ctx
        return _all_success()

    with patch.object(Path, "exists", return_value=True), \
         patch("analytics_pipeline.cli.run_pipeline", side_effect=_capture_pipeline), \
         patch("analytics_pipeline.cli.write_summary", return_value=Path("/out/pipeline_summary.json")), \
         patch("sys.argv", ["analytics-pipeline", "run", "--input", "x.csv"]):
        try:
            cli.main()
        except SystemExit:
            pass

    assert captured["ctx"].output_root == Path("outputs/pipeline")
