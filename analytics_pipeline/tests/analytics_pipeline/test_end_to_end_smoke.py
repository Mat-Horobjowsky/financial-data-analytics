"""
Minimal smoke test: CSV → Intake → Metrics → Report

Validates that each engine handoff produces the expected output files and that
at least one key metric flows through end-to-end.  Does not test every row,
format detail, or metric value.
"""
from __future__ import annotations

import textwrap
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
_SCHEMA_YAML = _REPO_ROOT / "metrics_engine" / "config" / "readiness_schema.yaml"
_METRICS_YAML = _REPO_ROOT / "metrics_engine" / "config" / "readiness_metrics.yaml"

_FIXTURE_CSV = textwrap.dedent("""\
    date,project_id,category,market,status,severity
    2025-01-15,PRJ001,power,NAM,complete,high
    2025-01-15,PRJ001,fiber,NAM,open,critical
    2025-01-15,PRJ001,permitting,NAM,not_started,medium
    2025-01-15,PRJ002,power,EMEA,complete,low
    2025-01-15,PRJ002,fiber,EMEA,in_progress,critical
    2025-01-15,PRJ002,permitting,EMEA,closed,high
""")


@pytest.fixture(scope="module")
def smoke_outputs(tmp_path_factory):
    tmp_path = tmp_path_factory.mktemp("smoke")

    # ── intake ──────────────────────────────────────────────────────────────
    from intake_engine.cleaner import clean
    from intake_engine.exporter import export_csv
    from intake_engine.loader import load_file

    raw_csv = tmp_path / "raw.csv"
    raw_csv.write_text(_FIXTURE_CSV, encoding="utf-8")

    clean_csv = tmp_path / "intake" / "clean.csv"
    df = load_file(raw_csv)
    export_csv(clean(df), clean_csv)

    # ── metrics ─────────────────────────────────────────────────────────────
    from metrics_engine import calculator as m_calc
    from metrics_engine import loader as m_loader
    from metrics_engine import metric_registry as m_registry
    from metrics_engine import output_builder as m_output
    from metrics_engine import schema as m_schema
    from metrics_engine import validator as m_validator
    from metrics_engine.exporter import export as m_export

    metrics_out = tmp_path / "metrics"
    raw_df = m_loader.load(clean_csv)
    schema_cfg = m_schema.load_schema(_SCHEMA_YAML)
    norm_result = m_schema.normalize(raw_df, schema_cfg)
    registry = m_registry.load_metric_registry(_METRICS_YAML)
    validation = m_validator.validate(norm_result, registry)
    result_df = m_calc.calculate(norm_result.df, registry)
    long_metrics = m_output.build_long_metrics(result_df, registry)
    long_metrics = m_output.apply_output_rounding(long_metrics, registry)
    wide_metrics = m_output.build_wide_metrics(long_metrics)
    metric_dict = m_output.build_metric_dictionary(registry)
    m_export(long_metrics, wide_metrics, metric_dict, validation, metrics_out)

    # ── report ───────────────────────────────────────────────────────────────
    from report_engine.loader import load as r_load
    from report_engine.renderer import render_markdown
    from report_engine.templates import DEFAULT_TEMPLATE, get_sections

    report_out = tmp_path / "report"
    report_out.mkdir()
    report_data = r_load(metrics_out)
    md = render_markdown(report_data, sections=get_sections(DEFAULT_TEMPLATE))
    report_md = report_out / "report.md"
    report_md.write_text(md, encoding="utf-8")

    return {
        "clean_csv": clean_csv,
        "metrics_dir": metrics_out,
        "report_md": report_md,
        "long_metrics": long_metrics,
    }


def test_intake_clean_csv_exists(smoke_outputs):
    assert smoke_outputs["clean_csv"].exists()


def test_metrics_long_metrics_csv_exists(smoke_outputs):
    assert (smoke_outputs["metrics_dir"] / "long_metrics.csv").exists()


def test_metrics_metric_dictionary_csv_exists(smoke_outputs):
    assert (smoke_outputs["metrics_dir"] / "metric_dictionary.csv").exists()


def test_metrics_validation_report_json_exists(smoke_outputs):
    assert (smoke_outputs["metrics_dir"] / "validation_report.json").exists()


def test_report_md_exists(smoke_outputs):
    assert smoke_outputs["report_md"].exists()


def test_long_metrics_contains_expected_metric(smoke_outputs):
    assert "total_requirement_count" in smoke_outputs["long_metrics"]["metric_id"].values


def test_report_md_has_markdown_header(smoke_outputs):
    assert "# " in smoke_outputs["report_md"].read_text(encoding="utf-8")
