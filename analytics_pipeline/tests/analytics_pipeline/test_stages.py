import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from analytics_pipeline.stages import (
    ACTIVE_STAGES,
    FUTURE_STAGES,
    StageContext,
    StageResult,
    _sheet_slug,
    build_intake_cmd,
    build_metrics_cmd,
    build_powerbi_export_cmd,
    build_report_cmd,
    build_store_cmd,
    build_visuals_cmd,
)


def _ctx(
    tmp_path,
    with_time=False,
    template="full_report",
    with_store=False,
    with_visuals=False,
    metrics_config=None,
    schema_config=None,
    sheet=None,
):
    return StageContext(
        input_file=tmp_path / "data.csv",
        output_root=tmp_path / "out",
        with_time=with_time,
        template=template,
        results={},
        with_store=with_store,
        with_visuals=with_visuals,
        metrics_config=metrics_config,
        schema_config=schema_config,
        sheet=sheet,
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


def test_build_intake_cmd_no_sheet_flag_by_default(tmp_path):
    ctx = _ctx(tmp_path)
    cmd = build_intake_cmd(ctx)
    assert "--sheet" not in cmd


def test_build_intake_cmd_sheet_flag_included_when_provided(tmp_path):
    ctx = _ctx(tmp_path, sheet="PowerBI_Export")
    cmd = build_intake_cmd(ctx)
    assert "--sheet" in cmd
    idx = cmd.index("--sheet")
    assert cmd[idx + 1] == "PowerBI_Export"


def test_build_intake_cmd_sheet_flag_with_arbitrary_name(tmp_path):
    ctx = _ctx(tmp_path, sheet="Sheet1")
    cmd = build_intake_cmd(ctx)
    idx = cmd.index("--sheet")
    assert cmd[idx + 1] == "Sheet1"


# --- StageContext.sheet ---


def test_stage_context_sheet_defaults_none(tmp_path):
    ctx = StageContext(
        input_file=tmp_path / "data.csv",
        output_root=tmp_path / "out",
        with_time=False,
        template="full_report",
        results={},
    )
    assert ctx.sheet is None


def test_stage_context_sheet_set(tmp_path):
    ctx = _ctx(tmp_path, sheet="PowerBI_Export")
    assert ctx.sheet == "PowerBI_Export"


# --- _sheet_slug ---


def test_sheet_slug_lowercase():
    assert _sheet_slug("PowerBI_Export") == "powerbi_export"


def test_sheet_slug_spaces_to_underscores():
    assert _sheet_slug("Sales Data") == "sales_data"


def test_sheet_slug_strips_special_chars():
    assert _sheet_slug("Q1/2024") == "q1_2024"


def test_sheet_slug_collapses_underscores():
    assert _sheet_slug("My  Sheet") == "my_sheet"


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


def test_build_metrics_cmd_input_includes_sheet_slug_when_sheet_set(tmp_path):
    ctx = _ctx(tmp_path, sheet="PowerBI_Export")
    cmd = build_metrics_cmd(ctx)
    idx = cmd.index("--input")
    expected = str(tmp_path / "out" / "intake" / "data_powerbi_export_clean.csv")
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


def test_build_report_cmd_no_pdf_by_default(tmp_path):
    ctx = _ctx(tmp_path)
    cmd = build_report_cmd(ctx)
    assert "--pdf" not in cmd


def test_build_report_cmd_pdf_flag_included_when_enabled(tmp_path):
    ctx = StageContext(
        input_file=tmp_path / "data.csv",
        output_root=tmp_path / "out",
        with_time=False,
        template="readiness_summary",
        results={},
        with_pdf=True,
    )
    cmd = build_report_cmd(ctx)
    assert "--pdf" in cmd


def test_build_report_cmd_no_title_flag_by_default(tmp_path):
    ctx = _ctx(tmp_path)
    cmd = build_report_cmd(ctx)
    assert "--title" not in cmd


def test_build_report_cmd_title_flag_included_when_set(tmp_path):
    ctx = StageContext(
        input_file=tmp_path / "data.csv",
        output_root=tmp_path / "out",
        with_time=False,
        template="readiness_summary",
        results={},
        with_pdf=True,
        report_title="Demo AI Infrastructure Co.",
    )
    cmd = build_report_cmd(ctx)
    assert "--title" in cmd
    idx = cmd.index("--title")
    assert cmd[idx + 1] == "Demo AI Infrastructure Co."


def test_build_report_cmd_title_without_pdf(tmp_path):
    ctx = StageContext(
        input_file=tmp_path / "data.csv",
        output_root=tmp_path / "out",
        with_time=False,
        template="readiness_summary",
        results={},
        with_pdf=False,
        report_title="Some Title",
    )
    cmd = build_report_cmd(ctx)
    assert "--pdf" not in cmd
    assert "--title" in cmd
    idx = cmd.index("--title")
    assert cmd[idx + 1] == "Some Title"


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


def test_future_stages_contains_store():
    assert "store" in FUTURE_STAGES


def test_future_stages_does_not_contain_visuals():
    assert "visuals" not in FUTURE_STAGES


# --- StageContext.with_store ---


def test_stage_context_with_store_defaults_false(tmp_path):
    ctx = StageContext(
        input_file=tmp_path / "data.csv",
        output_root=tmp_path / "out",
        with_time=False,
        template="full_report",
        results={},
    )
    assert ctx.with_store is False


def test_stage_context_with_store_true(tmp_path):
    ctx = _ctx(tmp_path, with_store=True)
    assert ctx.with_store is True


# --- build_store_cmd ---


def test_build_store_cmd_uses_python_m(tmp_path):
    ctx = _ctx(tmp_path, with_store=True)
    cmd = build_store_cmd(ctx)
    assert cmd[0] == sys.executable
    assert "-m" in cmd
    assert "analytics_store.cli" in cmd


def test_build_store_cmd_subcommand_is_build(tmp_path):
    ctx = _ctx(tmp_path, with_store=True)
    cmd = build_store_cmd(ctx)
    assert "build" in cmd


def test_build_store_cmd_metrics_dir(tmp_path):
    ctx = _ctx(tmp_path, with_store=True)
    cmd = build_store_cmd(ctx)
    idx = cmd.index("--metrics")
    assert cmd[idx + 1] == str(tmp_path / "out" / "metrics")


def test_build_store_cmd_report_dir(tmp_path):
    ctx = _ctx(tmp_path, with_store=True)
    cmd = build_store_cmd(ctx)
    idx = cmd.index("--report")
    assert cmd[idx + 1] == str(tmp_path / "out" / "report")


def test_build_store_cmd_output_db(tmp_path):
    ctx = _ctx(tmp_path, with_store=True)
    cmd = build_store_cmd(ctx)
    idx = cmd.index("--output")
    assert cmd[idx + 1] == str(tmp_path / "out" / "store" / "analytics.duckdb")


# --- StageContext.with_visuals ---


def test_stage_context_with_visuals_defaults_false(tmp_path):
    ctx = StageContext(
        input_file=tmp_path / "data.csv",
        output_root=tmp_path / "out",
        with_time=False,
        template="full_report",
        results={},
    )
    assert ctx.with_visuals is False


def test_stage_context_with_visuals_true(tmp_path):
    ctx = _ctx(tmp_path, with_visuals=True)
    assert ctx.with_visuals is True


# --- build_visuals_cmd ---


def test_build_visuals_cmd_uses_python_m(tmp_path):
    ctx = _ctx(tmp_path, with_visuals=True)
    cmd = build_visuals_cmd(ctx)
    assert cmd[0] == sys.executable
    assert "-m" in cmd
    assert "visuals_engine.cli" in cmd


def test_build_visuals_cmd_subcommand_is_build(tmp_path):
    ctx = _ctx(tmp_path, with_visuals=True)
    cmd = build_visuals_cmd(ctx)
    assert "build" in cmd


def test_build_visuals_cmd_store_path(tmp_path):
    ctx = _ctx(tmp_path, with_visuals=True)
    cmd = build_visuals_cmd(ctx)
    idx = cmd.index("--store")
    assert cmd[idx + 1] == str(tmp_path / "out" / "store" / "analytics.duckdb")


def test_build_visuals_cmd_spec_path_is_absolute(tmp_path):
    ctx = _ctx(tmp_path, with_visuals=True)
    cmd = build_visuals_cmd(ctx)
    idx = cmd.index("--spec")
    assert Path(cmd[idx + 1]).is_absolute()


def test_build_visuals_cmd_spec_is_yaml(tmp_path):
    ctx = _ctx(tmp_path, with_visuals=True)
    cmd = build_visuals_cmd(ctx)
    idx = cmd.index("--spec")
    assert cmd[idx + 1].endswith(".yaml")


def test_build_visuals_cmd_output_dir(tmp_path):
    ctx = _ctx(tmp_path, with_visuals=True)
    cmd = build_visuals_cmd(ctx)
    idx = cmd.index("--output")
    assert cmd[idx + 1] == str(tmp_path / "out" / "visuals")


# --- StageContext custom metrics/schema config ---


def test_stage_context_metrics_config_defaults_none(tmp_path):
    ctx = _ctx(tmp_path)
    assert ctx.metrics_config is None


def test_stage_context_schema_config_defaults_none(tmp_path):
    ctx = _ctx(tmp_path)
    assert ctx.schema_config is None


def test_stage_context_metrics_config_set(tmp_path):
    p = Path("custom/metrics.yaml")
    ctx = _ctx(tmp_path, metrics_config=p)
    assert ctx.metrics_config == p


def test_stage_context_schema_config_set(tmp_path):
    p = Path("custom/schema.yaml")
    ctx = _ctx(tmp_path, schema_config=p)
    assert ctx.schema_config == p


# --- build_metrics_cmd with custom config ---


def test_build_metrics_cmd_uses_default_config_when_none(tmp_path):
    ctx = _ctx(tmp_path)
    cmd = build_metrics_cmd(ctx)
    idx = cmd.index("--config")
    assert "metrics.yaml" in cmd[idx + 1]


def test_build_metrics_cmd_uses_default_schema_when_none(tmp_path):
    ctx = _ctx(tmp_path)
    cmd = build_metrics_cmd(ctx)
    idx = cmd.index("--schema")
    assert "schema.yaml" in cmd[idx + 1]


def test_build_metrics_cmd_default_config_is_absolute(tmp_path):
    ctx = _ctx(tmp_path)
    cmd = build_metrics_cmd(ctx)
    assert Path(cmd[cmd.index("--config") + 1]).is_absolute()
    assert Path(cmd[cmd.index("--schema") + 1]).is_absolute()


def test_build_metrics_cmd_uses_custom_config_when_provided(tmp_path):
    ctx = _ctx(tmp_path, metrics_config=Path("custom/readiness_metrics.yaml"))
    cmd = build_metrics_cmd(ctx)
    idx = cmd.index("--config")
    assert Path(cmd[idx + 1]) == Path("custom/readiness_metrics.yaml")


def test_build_metrics_cmd_uses_custom_schema_when_provided(tmp_path):
    ctx = _ctx(tmp_path, schema_config=Path("custom/readiness_schema.yaml"))
    cmd = build_metrics_cmd(ctx)
    idx = cmd.index("--schema")
    assert Path(cmd[idx + 1]) == Path("custom/readiness_schema.yaml")


def test_build_metrics_cmd_readiness_configs(tmp_path):
    """Readiness config files exist and wire into the command correctly."""
    import metrics_engine as _me
    config_dir = Path(_me.__file__).parent.parent / "config"
    readiness_metrics = config_dir / "readiness_metrics.yaml"
    readiness_schema = config_dir / "readiness_schema.yaml"
    assert readiness_metrics.exists(), f"Missing: {readiness_metrics}"
    assert readiness_schema.exists(), f"Missing: {readiness_schema}"
    ctx = _ctx(tmp_path, metrics_config=readiness_metrics, schema_config=readiness_schema)
    cmd = build_metrics_cmd(ctx)
    assert "readiness_metrics.yaml" in cmd[cmd.index("--config") + 1]
    assert "readiness_schema.yaml" in cmd[cmd.index("--schema") + 1]


# --- StageContext.with_powerbi_export ---


def test_stage_context_with_powerbi_export_defaults_false(tmp_path):
    ctx = StageContext(
        input_file=tmp_path / "data.csv",
        output_root=tmp_path / "out",
        with_time=False,
        template="full_report",
        results={},
    )
    assert ctx.with_powerbi_export is False


def test_stage_context_with_powerbi_export_true(tmp_path):
    ctx = StageContext(
        input_file=tmp_path / "data.csv",
        output_root=tmp_path / "out",
        with_time=False,
        template="full_report",
        results={},
        with_powerbi_export=True,
    )
    assert ctx.with_powerbi_export is True


# --- build_powerbi_export_cmd ---


def test_build_powerbi_export_cmd_uses_visuals_engine(tmp_path):
    ctx = _ctx(tmp_path)
    with patch("analytics_pipeline.stages.shutil.which", return_value=None):
        cmd = build_powerbi_export_cmd(ctx)
    assert cmd[0] == "visuals-engine"


def test_build_powerbi_export_cmd_uses_which_when_available(tmp_path):
    ctx = _ctx(tmp_path)
    with patch("analytics_pipeline.stages.shutil.which", return_value="/usr/bin/visuals-engine"):
        cmd = build_powerbi_export_cmd(ctx)
    assert cmd[0] == "/usr/bin/visuals-engine"


def test_build_powerbi_export_cmd_subcommand(tmp_path):
    ctx = _ctx(tmp_path)
    with patch("analytics_pipeline.stages.shutil.which", return_value=None):
        cmd = build_powerbi_export_cmd(ctx)
    assert "export-powerbi" in cmd


def test_build_powerbi_export_cmd_store_path(tmp_path):
    ctx = _ctx(tmp_path)
    with patch("analytics_pipeline.stages.shutil.which", return_value=None):
        cmd = build_powerbi_export_cmd(ctx)
    idx = cmd.index("--store")
    assert cmd[idx + 1] == str(tmp_path / "out" / "store" / "analytics.duckdb")


def test_build_powerbi_export_cmd_output_dir(tmp_path):
    ctx = _ctx(tmp_path)
    with patch("analytics_pipeline.stages.shutil.which", return_value=None):
        cmd = build_powerbi_export_cmd(ctx)
    idx = cmd.index("--output")
    assert cmd[idx + 1] == str(tmp_path / "out" / "powerbi")


# --- StageContext.client_context_path ---


def test_stage_context_client_context_defaults_none(tmp_path):
    ctx = _ctx(tmp_path)
    assert ctx.client_context_path is None


def test_stage_context_client_context_set(tmp_path):
    ctx = StageContext(
        input_file=tmp_path / "data.csv",
        output_root=tmp_path / "out",
        with_time=False,
        template="full_report",
        results={},
        client_context_path=tmp_path / "client_context.csv",
    )
    assert ctx.client_context_path == tmp_path / "client_context.csv"


def test_build_powerbi_export_cmd_includes_client_context_when_set(tmp_path):
    ctx = StageContext(
        input_file=tmp_path / "data.csv",
        output_root=tmp_path / "out",
        with_time=False,
        template="full_report",
        results={},
        client_context_path=tmp_path / "client_context.csv",
    )
    with patch("analytics_pipeline.stages.shutil.which", return_value=None):
        cmd = build_powerbi_export_cmd(ctx)
    assert "--client-context" in cmd
    idx = cmd.index("--client-context")
    assert cmd[idx + 1] == str(tmp_path / "client_context.csv")


def test_build_powerbi_export_cmd_no_client_context_flag_when_none(tmp_path):
    ctx = _ctx(tmp_path)
    with patch("analytics_pipeline.stages.shutil.which", return_value=None):
        cmd = build_powerbi_export_cmd(ctx)
    assert "--client-context" not in cmd
