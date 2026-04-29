from pathlib import Path

import pandas as pd
import pytest

from report_engine.loader import ReportData
from report_engine.renderer import render_markdown


@pytest.fixture
def minimal_data():
    return ReportData(
        input_dir=Path("outputs/intake_test"),
        validation_status="passed",
        validation_errors=[],
        validation_warnings=["Some warning"],
        long_metrics=pd.DataFrame({
            "rollup_level": ["date_only", "date_only"],
            "date": ["2024-01-01", "2024-02-01"],
            "metric_id": ["total_revenue", "total_revenue"],
            "label": ["Total Revenue", "Total Revenue"],
            "value": [5900000.0, 6150000.0],
            "unit": ["USD", "USD"],
        }),
        wide_metrics=pd.DataFrame(),
        metric_dictionary=pd.DataFrame({
            "id": ["total_revenue"],
            "label": ["Total Revenue"],
            "type": ["sum"],
            "unit": ["USD"],
            "description": ["Sum of all revenue"],
        }),
    )


@pytest.fixture
def empty_data():
    return ReportData(
        input_dir=Path("outputs/intake_test"),
        validation_status="passed",
        validation_errors=[],
        validation_warnings=[],
        long_metrics=pd.DataFrame(),
        wide_metrics=pd.DataFrame(),
        metric_dictionary=pd.DataFrame(),
    )


@pytest.fixture
def failed_data():
    return ReportData(
        input_dir=Path("outputs/intake_test"),
        validation_status="failed",
        validation_errors=["Missing column: revenue"],
        validation_warnings=[],
        long_metrics=pd.DataFrame(),
        wide_metrics=pd.DataFrame(),
        metric_dictionary=pd.DataFrame(),
    )


# ── Markdown tests ─────────────────────────────────────────────────────────────

def test_render_markdown_returns_string(minimal_data):
    md = render_markdown(minimal_data)
    assert isinstance(md, str)


def test_render_markdown_has_title(minimal_data):
    md = render_markdown(minimal_data)
    assert "# Metrics Report" in md


def test_render_markdown_has_validation_section(minimal_data):
    md = render_markdown(minimal_data)
    assert "## Validation" in md


def test_render_markdown_shows_validation_status(minimal_data):
    md = render_markdown(minimal_data)
    assert "passed" in md


def test_render_markdown_shows_warnings(minimal_data):
    md = render_markdown(minimal_data)
    assert "Some warning" in md


def test_render_markdown_shows_errors(failed_data):
    md = render_markdown(failed_data)
    assert "Missing column: revenue" in md


def test_render_markdown_has_metrics_section(minimal_data):
    md = render_markdown(minimal_data)
    assert "## Metrics Summary" in md


def test_render_markdown_shows_metric_value(minimal_data):
    md = render_markdown(minimal_data)
    assert "total_revenue" in md


def test_render_markdown_has_metric_dictionary_section(minimal_data):
    md = render_markdown(minimal_data)
    assert "## Metric Dictionary" in md


def test_render_markdown_empty_metrics_shows_placeholder(empty_data):
    md = render_markdown(empty_data)
    assert "No metrics data available" in md


def test_render_markdown_empty_dictionary_shows_placeholder(empty_data):
    md = render_markdown(empty_data)
    assert "No metric dictionary available" in md


def test_render_markdown_filters_to_date_only_rollup():
    data = ReportData(
        input_dir=Path("outputs/intake_test"),
        validation_status="passed",
        validation_errors=[],
        validation_warnings=[],
        long_metrics=pd.DataFrame({
            "rollup_level": ["date_only", "date_region"],
            "date": ["2024-01-01", "2024-01-01"],
            "metric_id": ["total_revenue", "total_revenue"],
            "label": ["Total Revenue", "Total Revenue"],
            "value": [5900000.0, 3000000.0],
            "unit": ["USD", "USD"],
        }),
        wide_metrics=pd.DataFrame(),
        metric_dictionary=pd.DataFrame(),
    )
    md = render_markdown(data)
    # Only the date_only row renders; its value appears
    assert "5900000.0" in md
    # The date_region row value must NOT appear
    assert "3000000.0" not in md
    # rollup_level column value must NOT appear in the table
    assert "date_only" not in md
    assert "date_region" not in md
