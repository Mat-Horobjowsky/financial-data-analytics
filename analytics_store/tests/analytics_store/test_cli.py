from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from analytics_store.loader import LoaderError, MetricsData, ReportData


def _mock_metrics() -> MetricsData:
    import pandas as pd
    return MetricsData(
        metrics_dir=Path("/fake/metrics"),
        validation_status="passed",
        validation_errors=[],
        validation_warnings=[],
        long_metrics=pd.DataFrame(),
        wide_metrics=pd.DataFrame(),
        metric_dictionary=pd.DataFrame(),
    )


def _mock_report() -> ReportData:
    return ReportData(report_dir=None, insights=[], summary={})


def _run_cli(args: list[str], metrics_exists: bool = True) -> int | None:
    from analytics_store import cli
    with patch.object(Path, "exists", return_value=metrics_exists), \
         patch("analytics_store.cli.load_metrics", return_value=_mock_metrics()), \
         patch("analytics_store.cli.load_report", return_value=_mock_report()), \
         patch("analytics_store.cli.build_store", return_value=["long_metrics", "v_latest_kpis"]):
        try:
            with patch("sys.argv", ["analytics-store"] + args):
                cli.main()
            return 0
        except SystemExit as e:
            return e.code


# --- subcommand parsing ---

def test_no_subcommand_exits_nonzero():
    from analytics_store import cli
    with patch("sys.argv", ["analytics-store"]):
        try:
            cli.main()
            code = 0
        except SystemExit as e:
            code = e.code
    assert code != 0


def test_build_exits_zero_on_success(tmp_path):
    code = _run_cli(["build", "--metrics", "m/", "--output", str(tmp_path / "s.duckdb")])
    assert code is None or code == 0


# --- required flags ---

def test_build_missing_metrics_arg_exits_nonzero():
    code = _run_cli(["build", "--output", "out.duckdb"])
    assert code != 0


def test_build_metrics_dir_not_found_exits_nonzero():
    code = _run_cli(["build", "--metrics", "missing/", "--output", "out.duckdb"], metrics_exists=False)
    assert code != 0


# --- optional --report flag ---

def test_report_flag_is_optional(tmp_path):
    code = _run_cli(["build", "--metrics", "m/", "--output", str(tmp_path / "s.duckdb")])
    assert code is None or code == 0


def test_report_none_passed_to_load_report_when_omitted():
    from analytics_store import cli
    captured: dict = {}

    def _capture(report_dir):
        captured["report_dir"] = report_dir
        return _mock_report()

    with patch.object(Path, "exists", return_value=True), \
         patch("analytics_store.cli.load_metrics", return_value=_mock_metrics()), \
         patch("analytics_store.cli.load_report", side_effect=_capture), \
         patch("analytics_store.cli.build_store", return_value=[]), \
         patch("sys.argv", ["analytics-store", "build", "--metrics", "m/"]):
        try:
            cli.main()
        except SystemExit:
            pass

    assert captured.get("report_dir") is None


def test_report_path_passed_to_load_report_when_provided():
    from analytics_store import cli
    captured: dict = {}

    def _capture(report_dir):
        captured["report_dir"] = report_dir
        return _mock_report()

    with patch.object(Path, "exists", return_value=True), \
         patch("analytics_store.cli.load_metrics", return_value=_mock_metrics()), \
         patch("analytics_store.cli.load_report", side_effect=_capture), \
         patch("analytics_store.cli.build_store", return_value=[]), \
         patch("sys.argv", ["analytics-store", "build", "--metrics", "m/", "--report", "r/"]):
        try:
            cli.main()
        except SystemExit:
            pass

    assert captured.get("report_dir") == "r/"


# --- default --output ---

def test_output_defaults_to_outputs_store_duckdb():
    from analytics_store import cli
    captured: dict = {}

    def _capture(metrics_data, report_data, db_path):
        captured["db_path"] = db_path
        return []

    with patch.object(Path, "exists", return_value=True), \
         patch("analytics_store.cli.load_metrics", return_value=_mock_metrics()), \
         patch("analytics_store.cli.load_report", return_value=_mock_report()), \
         patch("analytics_store.cli.build_store", side_effect=_capture), \
         patch("sys.argv", ["analytics-store", "build", "--metrics", "m/"]):
        try:
            cli.main()
        except SystemExit:
            pass

    assert captured.get("db_path") == Path("outputs/analytics.duckdb")


# --- error propagation ---

def test_loader_error_on_metrics_exits_nonzero():
    from analytics_store import cli
    with patch.object(Path, "exists", return_value=True), \
         patch("analytics_store.cli.load_metrics", side_effect=LoaderError("corrupt")), \
         patch("sys.argv", ["analytics-store", "build", "--metrics", "m/"]):
        try:
            cli.main()
            code = 0
        except SystemExit as e:
            code = e.code
    assert code != 0


def test_loader_error_on_report_exits_nonzero():
    from analytics_store import cli
    with patch.object(Path, "exists", return_value=True), \
         patch("analytics_store.cli.load_metrics", return_value=_mock_metrics()), \
         patch("analytics_store.cli.load_report", side_effect=LoaderError("bad report")), \
         patch("sys.argv", ["analytics-store", "build", "--metrics", "m/", "--report", "r/"]):
        try:
            cli.main()
            code = 0
        except SystemExit as e:
            code = e.code
    assert code != 0


# --- metrics path forwarded to load_metrics ---

def test_metrics_path_passed_to_load_metrics():
    from analytics_store import cli
    captured: dict = {}

    def _capture(metrics_dir):
        captured["metrics_dir"] = metrics_dir
        return _mock_metrics()

    with patch.object(Path, "exists", return_value=True), \
         patch("analytics_store.cli.load_metrics", side_effect=_capture), \
         patch("analytics_store.cli.load_report", return_value=_mock_report()), \
         patch("analytics_store.cli.build_store", return_value=[]), \
         patch("sys.argv", ["analytics-store", "build", "--metrics", "metrics/demo"]):
        try:
            cli.main()
        except SystemExit:
            pass

    assert Path(str(captured.get("metrics_dir"))) == Path("metrics/demo")
