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
    # Scope assertions to the Metrics Summary table only.
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


# ── KPI Snapshot section tests ─────────────────────────────────────────────────

def test_render_markdown_has_kpi_snapshot_section(minimal_data):
    md = render_markdown(minimal_data)
    assert "## KPI Snapshot" in md


def test_render_markdown_kpi_snapshot_omitted_when_no_metrics(empty_data):
    md = render_markdown(empty_data)
    assert "## KPI Snapshot" not in md


def test_render_markdown_kpi_snapshot_shows_latest_period_only(minimal_data):
    # minimal_data has total_revenue at 2024-01-01 and 2024-02-01;
    # snapshot should show only the Feb row.
    md = render_markdown(minimal_data)
    snapshot_start = md.index("## KPI Snapshot")
    next_section = md.index("##", snapshot_start + 3)
    snapshot_section = md[snapshot_start:next_section]
    assert "2024-02-01" in snapshot_section
    assert "2024-01-01" not in snapshot_section


def test_render_markdown_kpi_snapshot_formats_value(minimal_data):
    md = render_markdown(minimal_data)
    snapshot_start = md.index("## KPI Snapshot")
    next_section = md.index("##", snapshot_start + 3)
    snapshot_section = md[snapshot_start:next_section]
    assert "$6,150,000.00" in snapshot_section


def test_render_html_has_kpi_snapshot_section(minimal_data):
    html = render_html(minimal_data)
    assert "<h2>KPI Snapshot</h2>" in html


def test_render_html_kpi_snapshot_omitted_when_no_metrics(empty_data):
    html = render_html(empty_data)
    assert "<h2>KPI Snapshot</h2>" not in html


def test_render_html_kpi_snapshot_shows_latest_period_only(minimal_data):
    html = render_html(minimal_data)
    snapshot_start = html.index("<h2>KPI Snapshot</h2>")
    next_section = html.index("<h2>", snapshot_start + 5)
    snapshot_section = html[snapshot_start:next_section]
    assert "2024-02-01" in snapshot_section
    assert "2024-01-01" not in snapshot_section


def test_render_html_kpi_snapshot_formats_value(minimal_data):
    html = render_html(minimal_data)
    snapshot_start = html.index("<h2>KPI Snapshot</h2>")
    next_section = html.index("<h2>", snapshot_start + 5)
    snapshot_section = html[snapshot_start:next_section]
    assert "$6,150,000.00" in snapshot_section


# ── Key Insights section tests ─────────────────────────────────────────────────

def test_render_markdown_has_key_insights_section_when_period_data(time_enriched_data):
    md = render_markdown(time_enriched_data)
    assert "## Key Insights" in md


def test_render_markdown_omits_key_insights_when_no_period_columns(minimal_data):
    md = render_markdown(minimal_data)
    assert "## Key Insights" not in md


def test_render_markdown_key_insights_shows_insight_text(time_enriched_data):
    md = render_markdown(time_enriched_data)
    assert "increased" in md or "decreased" in md or "remained flat" in md


def test_render_markdown_key_insights_uses_label(time_enriched_data):
    md = render_markdown(time_enriched_data)
    insights_start = md.index("## Key Insights")
    next_section = md.index("##", insights_start + 3)
    insights_section = md[insights_start:next_section]
    assert "Total Revenue" in insights_section


def test_render_markdown_key_insights_omitted_when_all_nan():
    # All period_change_pct values are NaN — no valid insights, section omitted
    data = ReportData(
        input_dir=Path("outputs/test"),
        validation_status="passed",
        validation_errors=[],
        validation_warnings=[],
        long_metrics=pd.DataFrame({
            "rollup_level": ["date_only"],
            "date": ["2024-01-01"],
            "metric_id": ["total_revenue"],
            "label": ["Total Revenue"],
            "value": [5900000.0],
            "unit": ["USD"],
            "prior_period_value": [float("nan")],
            "period_change": [float("nan")],
            "period_change_pct": [float("nan")],
        }),
        wide_metrics=pd.DataFrame(),
        metric_dictionary=pd.DataFrame(),
    )
    md = render_markdown(data)
    assert "## Key Insights" not in md


def test_render_html_has_key_insights_section_when_period_data(time_enriched_data):
    html = render_html(time_enriched_data)
    assert "<h2>Key Insights</h2>" in html


def test_render_html_omits_key_insights_when_no_period_columns(minimal_data):
    html = render_html(minimal_data)
    assert "<h2>Key Insights</h2>" not in html


def test_render_html_key_insights_uses_label(time_enriched_data):
    html = render_html(time_enriched_data)
    insights_start = html.index("<h2>Key Insights</h2>")
    next_section = html.index("<h2>", insights_start + 5)
    insights_section = html[insights_start:next_section]
    assert "Total Revenue" in insights_section


# ── Metric Dictionary display header tests ─────────────────────────────────────

def test_render_markdown_metric_dictionary_uses_display_headers(minimal_data):
    md = render_markdown(minimal_data)
    dict_start = md.index("## Metric Dictionary")
    header_row = next(
        line for line in md[dict_start:].splitlines()
        if line.startswith("|")
    )
    assert "Metric ID" in header_row
    assert "Metric" in header_row
    assert "Type" in header_row
    assert "Unit" in header_row
    assert "Description" in header_row
    assert "| id |" not in header_row
    assert "| label |" not in header_row
    assert "| type |" not in header_row


def test_render_html_metric_dictionary_uses_display_headers(minimal_data):
    html = render_html(minimal_data)
    dict_start = html.index("<h2>Metric Dictionary</h2>")
    header_end = html.index("</thead>", dict_start)
    dict_header = html[dict_start:header_end]
    assert "<th>Metric ID</th>" in dict_header
    assert "<th>Metric</th>" in dict_header
    assert "<th>Type</th>" in dict_header
    assert "<th>Unit</th>" in dict_header
    assert "<th>Description</th>" in dict_header
    assert "<th>id</th>" not in dict_header
    assert "<th>label</th>" not in dict_header
    assert "<th>type</th>" not in dict_header


# ── Template section selection tests ───────────────────────────────────────────

from report_engine.templates import get_sections


def test_render_markdown_default_matches_full_report(minimal_data):
    full_sections = get_sections("full_report")
    assert render_markdown(minimal_data) == render_markdown(minimal_data, sections=full_sections)


def test_render_html_default_matches_full_report(minimal_data):
    full_sections = get_sections("full_report")
    fixed = date(2024, 6, 1)
    assert render_html(minimal_data, report_date=fixed) == render_html(
        minimal_data, report_date=fixed, sections=full_sections
    )


def test_render_markdown_executive_summary_includes_kpi_snapshot(minimal_data):
    sections = get_sections("executive_summary")
    md = render_markdown(minimal_data, sections=sections)
    assert "## KPI Snapshot" in md


def test_render_markdown_executive_summary_includes_key_insights(time_enriched_data):
    sections = get_sections("executive_summary")
    md = render_markdown(time_enriched_data, sections=sections)
    assert "## Key Insights" in md


def test_render_markdown_executive_summary_omits_metrics_summary(minimal_data):
    sections = get_sections("executive_summary")
    md = render_markdown(minimal_data, sections=sections)
    assert "## Metrics Summary" not in md


def test_render_markdown_executive_summary_omits_metric_dictionary(minimal_data):
    sections = get_sections("executive_summary")
    md = render_markdown(minimal_data, sections=sections)
    assert "## Metric Dictionary" not in md


def test_render_markdown_metrics_detail_includes_metrics_summary(minimal_data):
    sections = get_sections("metrics_detail")
    md = render_markdown(minimal_data, sections=sections)
    assert "## Metrics Summary" in md


def test_render_markdown_metrics_detail_includes_metric_dictionary(minimal_data):
    sections = get_sections("metrics_detail")
    md = render_markdown(minimal_data, sections=sections)
    assert "## Metric Dictionary" in md


def test_render_markdown_metrics_detail_omits_kpi_snapshot(minimal_data):
    sections = get_sections("metrics_detail")
    md = render_markdown(minimal_data, sections=sections)
    assert "## KPI Snapshot" not in md


def test_render_markdown_metrics_detail_omits_key_insights(time_enriched_data):
    # time_enriched_data has period columns so key_insights would render under full_report;
    # metrics_detail explicitly excludes it.
    sections = get_sections("metrics_detail")
    md = render_markdown(time_enriched_data, sections=sections)
    assert "## Key Insights" not in md


def test_render_html_executive_summary_omits_metrics_summary(minimal_data):
    sections = get_sections("executive_summary")
    html = render_html(minimal_data, sections=sections)
    assert "<h2>Metrics Summary</h2>" not in html


def test_render_html_executive_summary_omits_metric_dictionary(minimal_data):
    sections = get_sections("executive_summary")
    html = render_html(minimal_data, sections=sections)
    assert "<h2>Metric Dictionary</h2>" not in html


def test_render_html_metrics_detail_omits_kpi_snapshot(minimal_data):
    sections = get_sections("metrics_detail")
    html = render_html(minimal_data, sections=sections)
    assert "<h2>KPI Snapshot</h2>" not in html


def test_render_html_metrics_detail_omits_key_insights(time_enriched_data):
    sections = get_sections("metrics_detail")
    html = render_html(time_enriched_data, sections=sections)
    assert "<h2>Key Insights</h2>" not in html


# ── render_readiness_pdf_html tests ───────────────────────────────────────────

from report_engine.html import render_readiness_pdf_html


@pytest.fixture
def readiness_pdf_data():
    date_rows = [
        ("date_only", "2025-01-15", "readiness_completion_pct", "Readiness Completion %", 50.0, "%"),
        ("date_only", "2025-01-15", "open_gap_count", "Open Gap Count", 10.0, "gaps"),
        ("date_only", "2025-01-15", "critical_item_count", "Critical Item Count", 4.0, "items"),
        ("date_only", "2025-01-15", "total_requirement_count", "Total Requirement Count", 20.0, "requirements"),
    ]
    cat_rows = [
        ("date_category", "2025-01-15", "readiness_completion_pct", "Readiness Completion %", 66.7, "%"),
        ("date_category", "2025-01-15", "open_gap_count", "Open Gap Count", 1.0, "gaps"),
        ("date_category", "2025-01-15", "critical_item_count", "Critical Item Count", 1.0, "items"),
        ("date_category", "2025-01-15", "total_requirement_count", "Total Requirement Count", 3.0, "requirements"),
    ]
    n_date = len(date_rows)
    n_cat = len(cat_rows)
    return ReportData(
        input_dir=Path("outputs/test_metrics"),
        validation_status="passed_with_warnings",
        validation_errors=[],
        validation_warnings=["Some internal warning about schema"],
        long_metrics=pd.DataFrame({
            "rollup_level": ["date_only"] * n_date + ["date_category"] * n_cat,
            "date": ["2025-01-15"] * (n_date + n_cat),
            "metric_id": [r[2] for r in date_rows] + [r[2] for r in cat_rows],
            "label": [r[3] for r in date_rows] + [r[3] for r in cat_rows],
            "value": [r[4] for r in date_rows] + [r[4] for r in cat_rows],
            "unit": [r[5] for r in date_rows] + [r[5] for r in cat_rows],
            "category": [None] * n_date + ["site_control"] * n_cat,
        }),
        wide_metrics=pd.DataFrame(),
        metric_dictionary=pd.DataFrame(),
    )


def test_render_readiness_pdf_html_returns_string(readiness_pdf_data):
    result = render_readiness_pdf_html(readiness_pdf_data, title="Test Client")
    assert isinstance(result, str)


def test_render_readiness_pdf_html_is_valid_html_document(readiness_pdf_data):
    html = render_readiness_pdf_html(readiness_pdf_data, title="Test Client")
    assert "<!DOCTYPE html>" in html
    assert "<html" in html
    assert "</html>" in html


def test_render_readiness_pdf_html_has_dark_header(readiness_pdf_data):
    html = render_readiness_pdf_html(readiness_pdf_data, title="Test Client")
    assert "#1a202c" in html


def test_render_readiness_pdf_html_uses_provided_title(readiness_pdf_data):
    html = render_readiness_pdf_html(readiness_pdf_data, title="NovaTech Systems")
    assert "NovaTech Systems" in html


def test_render_readiness_pdf_html_has_rfp_readiness_suffix(readiness_pdf_data):
    html = render_readiness_pdf_html(readiness_pdf_data, title="NovaTech Systems")
    assert "RFP Readiness Summary" in html


def test_render_readiness_pdf_html_derives_title_from_folder(readiness_pdf_data):
    html = render_readiness_pdf_html(readiness_pdf_data)
    assert "Test Metrics" in html


def test_render_readiness_pdf_html_has_kpi_completion_value(readiness_pdf_data):
    html = render_readiness_pdf_html(readiness_pdf_data, title="Test Client")
    assert "50%" in html


def test_render_readiness_pdf_html_has_next_steps_section(readiness_pdf_data):
    html = render_readiness_pdf_html(readiness_pdf_data, title="Test Client")
    assert "RECOMMENDED NEXT STEPS" in html


def test_render_readiness_pdf_html_omits_validation_status(readiness_pdf_data):
    html = render_readiness_pdf_html(readiness_pdf_data, title="Test Client")
    assert "passed_with_warnings" not in html


def test_render_readiness_pdf_html_omits_validation_warnings(readiness_pdf_data):
    html = render_readiness_pdf_html(readiness_pdf_data, title="Test Client")
    assert "Some internal warning about schema" not in html


def test_render_readiness_pdf_html_omits_metric_dictionary(readiness_pdf_data):
    html = render_readiness_pdf_html(readiness_pdf_data, title="Test Client")
    assert "Metric Dictionary" not in html
    assert "METRIC DICTIONARY" not in html


def test_render_readiness_pdf_html_is_landscape(readiness_pdf_data):
    html = render_readiness_pdf_html(readiness_pdf_data, title="Test Client")
    assert "landscape" in html


def test_render_readiness_pdf_html_has_no_page_break(readiness_pdf_data):
    html = render_readiness_pdf_html(readiness_pdf_data, title="Test Client")
    assert "page-break-before:always" not in html


def test_render_readiness_pdf_html_formats_segment_labels(readiness_pdf_data):
    html = render_readiness_pdf_html(readiness_pdf_data, title="Test Client")
    assert "Site Control" in html
    assert "site_control" not in html


def test_render_readiness_pdf_html_as_of_date_from_data_not_report_date(readiness_pdf_data):
    far_future = date(2999, 12, 31)
    html = render_readiness_pdf_html(readiness_pdf_data, title="Test Client", report_date=far_future)
    # Data metric period date appears as "As of..." in the header band
    assert "As of 2025-01-15" in html
    # Generation date appears as "Generated 2999-12-31" in the footer
    assert "Generated 2999-12-31" in html
    # Generation date must not appear before KEY METRICS (i.e. not in the header)
    pos_kpi = html.index("KEY METRICS")
    pos_gen = html.index("2999-12-31")
    assert pos_gen > pos_kpi


def test_render_readiness_pdf_html_footer_has_generated_marker(readiness_pdf_data):
    html = render_readiness_pdf_html(readiness_pdf_data, title="Test Client")
    assert "Generated from Metrics Engine" in html


def test_render_readiness_pdf_html_footer_has_source_line(readiness_pdf_data):
    html = render_readiness_pdf_html(readiness_pdf_data, title="Test Client")
    assert "Report Engine" in html


# ── Executive Assessment section tests ────────────────────────────────────────

from report_engine.insights import build_readiness_assessment


def test_render_readiness_pdf_html_has_executive_assessment_section(readiness_pdf_data):
    html = render_readiness_pdf_html(readiness_pdf_data, title="Test Client")
    assert "EXECUTIVE ASSESSMENT" in html


def test_render_readiness_pdf_html_assessment_before_next_steps(readiness_pdf_data):
    html = render_readiness_pdf_html(readiness_pdf_data, title="Test Client")
    pos_assess = html.index("EXECUTIVE ASSESSMENT")
    pos_steps = html.index("RECOMMENDED NEXT STEPS")
    assert pos_assess < pos_steps


def test_render_readiness_pdf_html_assessment_includes_completion_pct(readiness_pdf_data):
    # fixture has readiness_completion_pct = 50.0 → "50%"
    html = render_readiness_pdf_html(readiness_pdf_data, title="Test Client")
    assess_start = html.index("EXECUTIVE ASSESSMENT")
    next_steps_start = html.index("RECOMMENDED NEXT STEPS")
    assess_block = html[assess_start:next_steps_start]
    assert "50%" in assess_block


def test_render_readiness_pdf_html_assessment_includes_gap_count(readiness_pdf_data):
    # fixture has open_gap_count = 10
    html = render_readiness_pdf_html(readiness_pdf_data, title="Test Client")
    assess_start = html.index("EXECUTIVE ASSESSMENT")
    next_steps_start = html.index("RECOMMENDED NEXT STEPS")
    assess_block = html[assess_start:next_steps_start]
    assert "10 open gaps" in assess_block


def test_render_readiness_pdf_html_assessment_includes_critical_count(readiness_pdf_data):
    # fixture has critical_item_count = 4
    html = render_readiness_pdf_html(readiness_pdf_data, title="Test Client")
    assess_start = html.index("EXECUTIVE ASSESSMENT")
    next_steps_start = html.index("RECOMMENDED NEXT STEPS")
    assess_block = html[assess_start:next_steps_start]
    assert "4 critical items unresolved" in assess_block


def test_render_readiness_pdf_html_assessment_identifies_weakest_category(readiness_pdf_data):
    # fixture has one category: site_control → formatted as "Site Control"
    html = render_readiness_pdf_html(readiness_pdf_data, title="Test Client")
    assess_start = html.index("EXECUTIVE ASSESSMENT")
    next_steps_start = html.index("RECOMMENDED NEXT STEPS")
    assess_block = html[assess_start:next_steps_start]
    assert "Site Control" in assess_block


def test_render_readiness_pdf_html_assessment_holds_when_below_60pct(readiness_pdf_data):
    # fixture has 50% completion → transaction posture = hold
    html = render_readiness_pdf_html(readiness_pdf_data, title="Test Client")
    assess_start = html.index("EXECUTIVE ASSESSMENT")
    next_steps_start = html.index("RECOMMENDED NEXT STEPS")
    assess_block = html[assess_start:next_steps_start]
    assert "Hold" in assess_block


def test_render_readiness_pdf_html_assessment_before_next_steps_and_gaps(readiness_pdf_data):
    # In landscape layout, assessment (left col) appears before next steps and gap sections.
    html = render_readiness_pdf_html(readiness_pdf_data, title="Test Client")
    pos_assess = html.index("EXECUTIVE ASSESSMENT")
    pos_steps = html.index("RECOMMENDED NEXT STEPS")
    pos_gaps = html.index('sec-title">OPEN GAPS')
    assert pos_assess < pos_steps
    assert pos_assess < pos_gaps


# ── build_readiness_assessment unit tests ─────────────────────────────────────

def test_build_readiness_assessment_returns_expected_keys(readiness_pdf_data):
    result = build_readiness_assessment(readiness_pdf_data)
    for key in ("posture", "summary", "weakness_note", "transaction_posture",
                "overall_pct", "gap_count", "crit_count", "weakest_category", "weakest_pct"):
        assert key in result


def test_build_readiness_assessment_not_rfp_ready_when_low_completion_and_crits(readiness_pdf_data):
    # fixture: 50% completion, 4 critical items → "Not RFP-Ready"
    result = build_readiness_assessment(readiness_pdf_data)
    assert result["posture"] == "Not RFP-Ready"


def test_build_readiness_assessment_hold_posture_when_below_60pct(readiness_pdf_data):
    result = build_readiness_assessment(readiness_pdf_data)
    assert "Hold" in result["transaction_posture"]


def test_build_readiness_assessment_summary_contains_completion_pct(readiness_pdf_data):
    result = build_readiness_assessment(readiness_pdf_data)
    assert "50%" in result["summary"]


def test_build_readiness_assessment_summary_contains_gap_count(readiness_pdf_data):
    result = build_readiness_assessment(readiness_pdf_data)
    assert "10 open gaps" in result["summary"]


def test_build_readiness_assessment_identifies_weakest_category(readiness_pdf_data):
    result = build_readiness_assessment(readiness_pdf_data)
    assert result["weakest_category"] == "site_control"


def test_build_readiness_assessment_rfp_ready_when_high_completion_no_crits():
    data = ReportData(
        input_dir=Path("outputs/test"),
        validation_status="passed",
        validation_errors=[],
        validation_warnings=[],
        long_metrics=pd.DataFrame({
            "rollup_level": ["date_only", "date_only", "date_only", "date_only"],
            "date": ["2025-01-15"] * 4,
            "metric_id": [
                "readiness_completion_pct", "open_gap_count",
                "critical_item_count", "total_requirement_count",
            ],
            "label": ["Completion", "Gaps", "Critical", "Requirements"],
            "value": [85.0, 3.0, 0.0, 20.0],
            "unit": ["%", "gaps", "items", "requirements"],
        }),
        wide_metrics=pd.DataFrame(),
        metric_dictionary=pd.DataFrame(),
    )
    result = build_readiness_assessment(data)
    assert result["posture"] == "RFP-Ready"
    assert "Proceed" in result["transaction_posture"]


def test_build_readiness_assessment_at_risk_when_crits_but_high_pct():
    data = ReportData(
        input_dir=Path("outputs/test"),
        validation_status="passed",
        validation_errors=[],
        validation_warnings=[],
        long_metrics=pd.DataFrame({
            "rollup_level": ["date_only", "date_only", "date_only"],
            "date": ["2025-01-15"] * 3,
            "metric_id": [
                "readiness_completion_pct", "open_gap_count", "critical_item_count",
            ],
            "label": ["Completion", "Gaps", "Critical"],
            "value": [72.0, 2.0, 1.0],
            "unit": ["%", "gaps", "items"],
        }),
        wide_metrics=pd.DataFrame(),
        metric_dictionary=pd.DataFrame(),
    )
    result = build_readiness_assessment(data)
    assert result["posture"] == "At Risk"
    assert "critical blockers" in result["transaction_posture"]


def test_render_readiness_pdf_html_has_open_gaps_section(readiness_pdf_data):
    html = render_readiness_pdf_html(readiness_pdf_data, title="Test Client")
    assert 'sec-title">OPEN GAPS' in html


def test_render_readiness_pdf_html_has_critical_items_section(readiness_pdf_data):
    html = render_readiness_pdf_html(readiness_pdf_data, title="Test Client")
    assert 'sec-title">CRITICAL ITEMS' in html


def test_render_readiness_pdf_html_has_readiness_by_category(readiness_pdf_data):
    html = render_readiness_pdf_html(readiness_pdf_data, title="Test Client")
    assert "READINESS BY CATEGORY" in html


def test_render_readiness_pdf_html_next_steps_before_open_gaps_section(readiness_pdf_data):
    # Next steps (left column) appears before gap section heading (right column) in HTML order.
    html = render_readiness_pdf_html(readiness_pdf_data, title="Test Client")
    pos_steps = html.index("RECOMMENDED NEXT STEPS")
    pos_gaps = html.index('sec-title">OPEN GAPS')
    assert pos_steps < pos_gaps


# ── PDF zero-row filtering tests ──────────────────────────────────────────────
# Open Gaps and Critical Items summaries omit categories with zero counts.
# Full Readiness by Category table is unaffected.

@pytest.fixture
def readiness_pdf_mixed_data():
    """Three categories: alpha (non-zero gaps+crits), beta (zero gaps, zero crits), gamma (non-zero gaps, zero crits)."""
    date_rows = [
        ("date_only", "2025-03-01", "readiness_completion_pct", "Readiness Completion %", 55.0, "%"),
        ("date_only", "2025-03-01", "open_gap_count", "Open Gap Count", 5.0, "gaps"),
        ("date_only", "2025-03-01", "critical_item_count", "Critical Item Count", 2.0, "items"),
        ("date_only", "2025-03-01", "total_requirement_count", "Total Requirement Count", 18.0, "requirements"),
    ]
    cat_rows = [
        # alpha: 3 gaps, 2 crits
        ("date_category", "2025-03-01", "readiness_completion_pct", "Readiness Completion %", 40.0, "%"),
        ("date_category", "2025-03-01", "open_gap_count", "Open Gap Count", 3.0, "gaps"),
        ("date_category", "2025-03-01", "critical_item_count", "Critical Item Count", 2.0, "items"),
        # beta: 0 gaps, 0 crits
        ("date_category", "2025-03-01", "readiness_completion_pct", "Readiness Completion %", 80.0, "%"),
        ("date_category", "2025-03-01", "open_gap_count", "Open Gap Count", 0.0, "gaps"),
        ("date_category", "2025-03-01", "critical_item_count", "Critical Item Count", 0.0, "items"),
        # gamma: 2 gaps, 0 crits
        ("date_category", "2025-03-01", "readiness_completion_pct", "Readiness Completion %", 60.0, "%"),
        ("date_category", "2025-03-01", "open_gap_count", "Open Gap Count", 2.0, "gaps"),
        ("date_category", "2025-03-01", "critical_item_count", "Critical Item Count", 0.0, "items"),
    ]
    n_date = len(date_rows)
    n_cat = len(cat_rows)
    categories = ["alpha"] * 3 + ["beta"] * 3 + ["gamma"] * 3
    return ReportData(
        input_dir=Path("outputs/test_mixed"),
        validation_status="passed",
        validation_errors=[],
        validation_warnings=[],
        long_metrics=pd.DataFrame({
            "rollup_level": ["date_only"] * n_date + ["date_category"] * n_cat,
            "date": ["2025-03-01"] * (n_date + n_cat),
            "metric_id": [r[2] for r in date_rows] + [r[2] for r in cat_rows],
            "label": [r[3] for r in date_rows] + [r[3] for r in cat_rows],
            "value": [r[4] for r in date_rows] + [r[4] for r in cat_rows],
            "unit": [r[5] for r in date_rows] + [r[5] for r in cat_rows],
            "category": [None] * n_date + categories,
        }),
        wide_metrics=pd.DataFrame(),
        metric_dictionary=pd.DataFrame(),
    )


def test_readiness_pdf_gaps_omits_zero_count_category(readiness_pdf_mixed_data):
    html = render_readiness_pdf_html(readiness_pdf_mixed_data, title="Test Client")
    gaps_start = html.index('sec-title">OPEN GAPS')
    crit_start = html.index('sec-title">CRITICAL ITEMS')
    gaps_block = html[gaps_start:crit_start]
    # beta has 0 open gaps — must not appear in the gaps summary table
    assert "Beta" not in gaps_block


def test_readiness_pdf_gaps_keeps_nonzero_count_categories(readiness_pdf_mixed_data):
    html = render_readiness_pdf_html(readiness_pdf_mixed_data, title="Test Client")
    gaps_start = html.index('sec-title">OPEN GAPS')
    crit_start = html.index('sec-title">CRITICAL ITEMS')
    gaps_block = html[gaps_start:crit_start]
    # alpha (3 gaps) and gamma (2 gaps) must appear
    assert "Alpha" in gaps_block
    assert "Gamma" in gaps_block


def test_readiness_pdf_critical_omits_zero_count_categories(readiness_pdf_mixed_data):
    html = render_readiness_pdf_html(readiness_pdf_mixed_data, title="Test Client")
    crit_start = html.index('sec-title">CRITICAL ITEMS')
    seg_start = html.index("READINESS BY CATEGORY")
    crit_block = html[crit_start:seg_start]
    # beta (0 crits) and gamma (0 crits) must not appear in critical items summary table
    assert "Beta" not in crit_block
    assert "Gamma" not in crit_block


def test_readiness_pdf_critical_keeps_nonzero_count_category(readiness_pdf_mixed_data):
    html = render_readiness_pdf_html(readiness_pdf_mixed_data, title="Test Client")
    crit_start = html.index('sec-title">CRITICAL ITEMS')
    seg_start = html.index("READINESS BY CATEGORY")
    crit_block = html[crit_start:seg_start]
    # alpha (2 crits) must appear
    assert "Alpha" in crit_block


def test_readiness_pdf_segment_table_includes_all_categories(readiness_pdf_mixed_data):
    html = render_readiness_pdf_html(readiness_pdf_mixed_data, title="Test Client")
    seg_start = html.index("READINESS BY CATEGORY")
    seg_end = len(html)
    seg_block = html[seg_start:seg_end]
    # All three categories must appear in the full segment table regardless of zero counts
    assert "Alpha" in seg_block
    assert "Beta" in seg_block
    assert "Gamma" in seg_block


def test_readiness_pdf_gaps_total_count_always_shown(readiness_pdf_mixed_data):
    html = render_readiness_pdf_html(readiness_pdf_mixed_data, title="Test Client")
    gaps_start = html.index('sec-title">OPEN GAPS')
    crit_start = html.index('sec-title">CRITICAL ITEMS')
    gaps_block = html[gaps_start:crit_start]
    # The overall total (5) must still be shown even when rows are filtered
    assert "Total: 5" in gaps_block


def test_readiness_pdf_critical_total_count_always_shown(readiness_pdf_mixed_data):
    html = render_readiness_pdf_html(readiness_pdf_mixed_data, title="Test Client")
    crit_start = html.index('sec-title">CRITICAL ITEMS')
    seg_start = html.index("READINESS BY CATEGORY")
    crit_block = html[crit_start:seg_start]
    # The overall total (2) must still be shown
    assert "Total: 2" in crit_block
