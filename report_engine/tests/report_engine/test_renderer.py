from datetime import date
from pathlib import Path

import pandas as pd
import pytest

from report_engine.html import render_html
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
    # Only the date_only row renders; its formatted value appears
    assert "$5,900,000.00" in md
    # The date_region row value must NOT appear
    assert "$3,000,000.00" not in md
    # rollup_level column value must NOT appear in the table
    assert "date_only" not in md
    assert "date_region" not in md


from datetime import date

from report_engine.html import render_html


# ── HTML tests ─────────────────────────────────────────────────────────────────

def test_render_html_returns_string(minimal_data):
    html = render_html(minimal_data)
    assert isinstance(html, str)


def test_render_html_is_valid_document(minimal_data):
    html = render_html(minimal_data)
    assert "<!DOCTYPE html>" in html
    assert "<html" in html
    assert "</html>" in html


def test_render_html_has_title_heading(minimal_data):
    html = render_html(minimal_data)
    assert "<h1>Metrics Report</h1>" in html


def test_render_html_shows_validation_status(minimal_data):
    html = render_html(minimal_data)
    assert "passed" in html


def test_render_html_shows_warnings(minimal_data):
    html = render_html(minimal_data)
    assert "Some warning" in html


def test_render_html_shows_errors(failed_data):
    html = render_html(failed_data)
    assert "Missing column: revenue" in html


def test_render_html_shows_metric_value(minimal_data):
    html = render_html(minimal_data)
    assert "total_revenue" in html


def test_render_html_empty_metrics_shows_placeholder(empty_data):
    html = render_html(empty_data)
    assert "No metrics data available" in html


def test_render_html_empty_dictionary_shows_placeholder(empty_data):
    html = render_html(empty_data)
    assert "No metric dictionary available" in html


def test_render_html_escapes_special_characters():
    data = ReportData(
        input_dir=Path("outputs/<test>"),
        validation_status="passed",
        validation_errors=[],
        validation_warnings=["Warning with <b>tags</b> & ampersand"],
        long_metrics=pd.DataFrame(),
        wide_metrics=pd.DataFrame(),
        metric_dictionary=pd.DataFrame(),
    )
    html = render_html(data)
    assert "<b>tags</b>" not in html
    assert "&lt;b&gt;" in html
    assert "&lt;test&gt;" in html


def test_render_html_filters_to_date_only_rollup():
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
    html = render_html(data)
    # Only the date_only row renders; its formatted value appears
    assert "$5,900,000.00" in html
    # The date_region row value must NOT appear
    assert "$3,000,000.00" not in html
    assert "date_only" not in html
    assert "date_region" not in html


def test_render_html_has_inline_style(minimal_data):
    html = render_html(minimal_data)
    assert "<style>" in html


def test_render_html_report_date_is_deterministic(minimal_data):
    fixed = date(2024, 6, 1)
    html = render_html(minimal_data, report_date=fixed)
    assert "2024-06-01" in html


# ── Formatting tests ───────────────────────────────────────────────────────────

@pytest.fixture
def multi_metric_data():
    return ReportData(
        input_dir=Path("/absolute/path/to/intake_test"),
        validation_status="passed",
        validation_errors=[],
        validation_warnings=[],
        long_metrics=pd.DataFrame({
            "rollup_level": ["date_only", "date_only", "date_only", "date_only"],
            "date": ["2024-02-01", "2024-01-01", "2024-01-01", "2024-02-01"],
            "metric_id": ["total_revenue", "utilization_pct", "total_revenue", "utilization_pct"],
            "label": ["Total Revenue", "Utilization Rate", "Total Revenue", "Utilization Rate"],
            "value": [6150000.0, 84.8, 5900000.0, 81.2],
            "unit": ["USD", "%", "USD", "%"],
        }),
        wide_metrics=pd.DataFrame(),
        metric_dictionary=pd.DataFrame(),
    )


def test_render_markdown_formats_usd_value_as_currency(multi_metric_data):
    md = render_markdown(multi_metric_data)
    assert "$5,900,000.00" in md
    assert "5900000.0" not in md


def test_render_markdown_formats_percent_value_with_symbol(multi_metric_data):
    md = render_markdown(multi_metric_data)
    assert "81.2%" in md
    assert "| 81.2 |" not in md


def test_render_markdown_formats_comma_separates_large_whole_number():
    data = ReportData(
        input_dir=Path("outputs/test"),
        validation_status="passed",
        validation_errors=[],
        validation_warnings=[],
        long_metrics=pd.DataFrame({
            "rollup_level": ["date_only"],
            "date": ["2024-01-01"],
            "metric_id": ["contracted_kw"],
            "label": ["Total Contracted (KW)"],
            "value": [178700.0],
            "unit": ["KW"],
        }),
        wide_metrics=pd.DataFrame(),
        metric_dictionary=pd.DataFrame(),
    )
    md = render_markdown(data)
    assert "178,700" in md
    assert "178700.0" not in md


def test_render_html_formats_usd_value_as_currency(multi_metric_data):
    html = render_html(multi_metric_data)
    assert "$5,900,000.00" in html
    assert "5900000.0" not in html


def test_render_html_formats_percent_value_with_symbol(multi_metric_data):
    html = render_html(multi_metric_data)
    assert "81.2%" in html
    assert ">81.2<" not in html


# ── Sort tests ─────────────────────────────────────────────────────────────────

def test_render_markdown_sorts_rows_by_date_then_metric_id(multi_metric_data):
    md = render_markdown(multi_metric_data)
    summary_start = md.index("## Metrics Summary")
    rows = [
        line for line in md[summary_start:].splitlines()
        if line.startswith("| 2024")
    ]
    assert rows[0].startswith("| 2024-01-01")
    assert "total_revenue" in rows[0]
    assert rows[1].startswith("| 2024-01-01")
    assert "utilization_pct" in rows[1]
    assert rows[2].startswith("| 2024-02-01")
    assert "total_revenue" in rows[2]


def test_render_html_sorts_rows_by_date_then_metric_id(multi_metric_data):
    html = render_html(multi_metric_data)
    pos_jan_revenue = html.index("2024-01-01")
    pos_jan_util = html.index("utilization_pct")
    pos_feb_revenue = html.rindex("2024-02-01")
    assert pos_jan_revenue < pos_jan_util < pos_feb_revenue


# ── Path display tests ─────────────────────────────────────────────────────────

def test_render_markdown_shows_folder_name_only_not_full_path():
    abs_path = Path("/absolute/path/to/intake_test")
    data = ReportData(
        input_dir=abs_path,
        validation_status="passed",
        validation_errors=[],
        validation_warnings=[],
        long_metrics=pd.DataFrame(),
        wide_metrics=pd.DataFrame(),
        metric_dictionary=pd.DataFrame(),
    )
    md = render_markdown(data)
    assert "intake_test" in md
    assert str(abs_path.parent) not in md


def test_render_html_shows_folder_name_only_not_full_path():
    abs_path = Path("/absolute/path/to/intake_test")
    data = ReportData(
        input_dir=abs_path,
        validation_status="passed",
        validation_errors=[],
        validation_warnings=[],
        long_metrics=pd.DataFrame(),
        wide_metrics=pd.DataFrame(),
        metric_dictionary=pd.DataFrame(),
    )
    html = render_html(data)
    assert "intake_test" in html
    assert str(abs_path.parent) not in html


# ── Period-over-period tests ────────────────────────────────────────────────────

@pytest.fixture
def time_enriched_data():
    # prior_period_value uses 5_850_000 (distinct from value=5_900_000 and value=6_150_000)
    # so format assertions cannot pass vacuously from the value column.
    return ReportData(
        input_dir=Path("outputs/intake_test"),
        validation_status="passed",
        validation_errors=[],
        validation_warnings=[],
        long_metrics=pd.DataFrame({
            "rollup_level": ["date_only", "date_only"],
            "date": ["2024-01-01", "2024-02-01"],
            "metric_id": ["total_revenue", "total_revenue"],
            "label": ["Total Revenue", "Total Revenue"],
            "value": [5900000.0, 6150000.0],
            "unit": ["USD", "USD"],
            "prior_period_value": [float("nan"), 5850000.0],
            "period_change": [float("nan"), 300000.0],
            "period_change_pct": [float("nan"), 5.13],
        }),
        wide_metrics=pd.DataFrame(),
        metric_dictionary=pd.DataFrame(),
    )


def test_render_markdown_shows_time_columns_when_present(time_enriched_data):
    md = render_markdown(time_enriched_data)
    assert "Prior Period" in md
    assert "Change" in md
    assert "Change %" in md
    assert "prior_period_value" not in md
    assert "period_change" not in md
    assert "period_change_pct" not in md


def test_render_markdown_formats_prior_period_value_using_unit(time_enriched_data):
    md = render_markdown(time_enriched_data)
    assert "$5,850,000.00" in md


def test_render_markdown_formats_period_change_using_unit(time_enriched_data):
    md = render_markdown(time_enriched_data)
    assert "$300,000.00" in md


def test_render_markdown_formats_period_change_pct_as_percent(time_enriched_data):
    md = render_markdown(time_enriched_data)
    assert "5.13%" in md


def test_render_markdown_shows_empty_for_first_period_time_values(time_enriched_data):
    md = render_markdown(time_enriched_data)
    assert "nan" not in md.lower()


def test_render_markdown_omits_time_columns_when_absent(minimal_data):
    md = render_markdown(minimal_data)
    assert "prior_period_value" not in md
    assert "period_change" not in md
    assert "period_change_pct" not in md


def test_render_html_shows_time_columns_when_present(time_enriched_data):
    html = render_html(time_enriched_data)
    assert "Prior Period" in html
    assert "Change" in html
    assert "Change %" in html
    assert "prior_period_value" not in html
    assert "period_change" not in html
    assert "period_change_pct" not in html


def test_render_html_formats_prior_period_value_using_unit(time_enriched_data):
    html = render_html(time_enriched_data)
    assert "$5,850,000.00" in html


def test_render_html_formats_period_change_using_unit(time_enriched_data):
    html = render_html(time_enriched_data)
    assert "$300,000.00" in html


def test_render_html_formats_period_change_pct_as_percent(time_enriched_data):
    html = render_html(time_enriched_data)
    assert "5.13%" in html


def test_render_html_omits_time_columns_when_absent(minimal_data):
    html = render_html(minimal_data)
    assert "prior_period_value" not in html
    assert "period_change" not in html
    assert "period_change_pct" not in html


# ── Base column display-label tests ────────────────────────────────────────────

def test_render_markdown_base_columns_use_display_labels(minimal_data):
    md = render_markdown(minimal_data)
    summary_start = md.index("## Metrics Summary")
    header_row = next(
        line for line in md[summary_start:].splitlines()
        if line.startswith("|")
    )
    assert "Date" in header_row
    assert "Metric ID" in header_row
    assert "Value" in header_row
    assert "Unit" in header_row
    assert "date" not in header_row
    assert "metric_id" not in header_row
    assert "| label |" not in header_row
    assert "| value |" not in header_row
    assert "| unit |" not in header_row


def test_render_html_base_columns_use_display_labels(minimal_data):
    html = render_html(minimal_data)
    # Scope assertions to the Metrics Summary table only; Metric Dictionary
    # still renders raw names like "label" and "unit" (out of scope).
    summary_start = html.index("<h2>Metrics Summary</h2>")
    dict_start = html.index("<h2>Metric Dictionary</h2>")
    summary_html = html[summary_start:dict_start]
    assert "<th>Date</th>" in summary_html
    assert "<th>Metric ID</th>" in summary_html
    assert "<th>Value</th>" in summary_html
    assert "<th>Unit</th>" in summary_html
    assert "<th>date</th>" not in summary_html
    assert "<th>metric_id</th>" not in summary_html
    assert "<th>label</th>" not in summary_html
    assert "<th>value</th>" not in summary_html
    assert "<th>unit</th>" not in summary_html
