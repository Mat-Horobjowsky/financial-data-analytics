import pytest
from pathlib import Path
from visuals_engine.renderer import (
    build_template_context,
    render_html,
    render_summary,
)

TEMPLATE_PATH = Path(__file__).parent.parent / "visuals_engine" / "templates" / "readiness_dashboard.html"


@pytest.fixture
def sample_data():
    return {
        "kpi_cards": [
            {"metric_id": "readiness_completion_pct", "label": "Readiness Completion %", "value": 50.0, "unit": "%"},
            {"metric_id": "total_requirement_count", "label": "Total Requirement Count", "value": 20.0, "unit": "requirements"},
            {"metric_id": "open_gap_count", "label": "Open Gap Count", "value": 10.0, "unit": "gaps"},
            {"metric_id": "critical_item_count", "label": "Critical Item Count", "value": 4.0, "unit": "items"},
        ],
        "category_breakdown": [
            {"category": "capital", "metric_id": "readiness_completion_pct", "label": "Readiness Completion %", "value": 33.3, "unit": "%"},
            {"category": "capital", "metric_id": "open_gap_count", "label": "Open Gap Count", "value": 2.0, "unit": "gaps"},
            {"category": "commercial", "metric_id": "readiness_completion_pct", "label": "Readiness Completion %", "value": 66.7, "unit": "%"},
            {"category": "commercial", "metric_id": "open_gap_count", "label": "Open Gap Count", "value": 1.0, "unit": "gaps"},
        ],
        "market_breakdown": None,
        "metric_dictionary": {
            "readiness_completion_pct": {"id": "readiness_completion_pct", "label": "Readiness Completion %", "unit": "%", "decimals": 1, "description": "Percentage complete or closed"},
            "total_requirement_count": {"id": "total_requirement_count", "label": "Total Requirement Count", "unit": "requirements", "decimals": 0, "description": "Total requirements in scope"},
            "open_gap_count": {"id": "open_gap_count", "label": "Open Gap Count", "unit": "gaps", "decimals": 0, "description": "Requirements not yet complete"},
            "critical_item_count": {"id": "critical_item_count", "label": "Critical Item Count", "unit": "items", "decimals": 0, "description": "Requirements marked critical"},
        },
        "validation_summary": {"status": "passed_with_warnings", "error_count": 0, "warning_count": 5},
        "as_of_date": "2025-01-15",
        "sections_skipped": ["market_breakdown"],
    }


def test_context_has_four_kpi_cards(sample_spec, sample_data):
    ctx = build_template_context(sample_spec, sample_data)
    assert len(ctx["kpi_cards"]) == 4


def test_context_completion_card_is_primary(sample_spec, sample_data):
    ctx = build_template_context(sample_spec, sample_data)
    primary = next(c for c in ctx["kpi_cards"] if c["metric_id"] == "readiness_completion_pct")
    assert primary["is_primary"] is True


def test_context_completion_pct_formatted(sample_spec, sample_data):
    ctx = build_template_context(sample_spec, sample_data)
    card = next(c for c in ctx["kpi_cards"] if c["metric_id"] == "readiness_completion_pct")
    assert card["formatted_value"] == "50.0%"


def test_context_count_metrics_formatted_as_integers(sample_spec, sample_data):
    ctx = build_template_context(sample_spec, sample_data)
    count_card = next(c for c in ctx["kpi_cards"] if c["metric_id"] == "total_requirement_count")
    assert count_card["formatted_value"] == "20"


def test_context_category_rows_sorted_descending(sample_spec, sample_data):
    ctx = build_template_context(sample_spec, sample_data)
    rows = ctx["category_rows"]
    assert len(rows) == 2
    assert rows[0]["completion_pct"] >= rows[1]["completion_pct"]


def test_context_market_rows_empty_when_none(sample_spec, sample_data):
    ctx = build_template_context(sample_spec, sample_data)
    assert ctx["market_rows"] == []


def test_html_contains_completion_value(sample_spec, sample_data):
    html = render_html(TEMPLATE_PATH, sample_spec, sample_data)
    assert "50.0%" in html


def test_html_contains_kpi_labels(sample_spec, sample_data):
    html = render_html(TEMPLATE_PATH, sample_spec, sample_data)
    assert "Readiness Completion" in html
    assert "Open Gap" in html


def test_html_contains_category_names(sample_spec, sample_data):
    html = render_html(TEMPLATE_PATH, sample_spec, sample_data)
    assert "capital" in html
    assert "commercial" in html


def test_html_omits_market_section_when_no_rows(sample_spec, sample_data):
    html = render_html(TEMPLATE_PATH, sample_spec, sample_data)
    assert "Readiness by Market" not in html


# --- Polish: subtitle ---


def test_html_contains_subtitle_when_configured(sample_spec, sample_data):
    sample_spec["dashboard"]["subtitle"] = "Client-facing project snapshot."
    html = render_html(TEMPLATE_PATH, sample_spec, sample_data)
    assert "Client-facing project snapshot." in html


def test_html_no_subtitle_element_when_not_configured(sample_spec, sample_data):
    sample_spec["dashboard"].pop("subtitle", None)
    html = render_html(TEMPLATE_PATH, sample_spec, sample_data)
    assert '<p class="header__subtitle">' not in html


def test_context_subtitle_from_spec(sample_spec, sample_data):
    sample_spec["dashboard"]["subtitle"] = "Demo subtitle text."
    ctx = build_template_context(sample_spec, sample_data)
    assert ctx["subtitle"] == "Demo subtitle text."


def test_context_subtitle_empty_when_absent(sample_spec, sample_data):
    sample_spec["dashboard"].pop("subtitle", None)
    ctx = build_template_context(sample_spec, sample_data)
    assert ctx["subtitle"] == ""


# --- Polish: KPI label overrides ---


def test_html_kpi_label_override_renders(sample_spec, sample_data):
    sample_spec["dashboard"]["kpi_labels"] = {
        "readiness_completion_pct": "Overall Readiness",
        "open_gap_count": "Open Items",
    }
    html = render_html(TEMPLATE_PATH, sample_spec, sample_data)
    assert "Overall Readiness" in html
    assert "Open Items" in html


def test_kpi_label_falls_back_to_row_label_when_no_override(sample_spec, sample_data):
    ctx = build_template_context(sample_spec, sample_data)
    card = next(c for c in ctx["kpi_cards"] if c["metric_id"] == "readiness_completion_pct")
    assert card["label"] == "Readiness Completion %"


def test_kpi_description_override_renders(sample_spec, sample_data):
    sample_spec["dashboard"]["kpi_descriptions"] = {
        "readiness_completion_pct": "Custom description text.",
    }
    html = render_html(TEMPLATE_PATH, sample_spec, sample_data)
    assert "Custom description text." in html


# --- Polish: category label mapping ---


def test_html_category_label_mapping_renders(sample_spec, sample_data):
    sample_spec["dashboard"]["category_labels"] = {
        "capital": "Capital Readiness",
        "commercial": "Commercial Model",
    }
    html = render_html(TEMPLATE_PATH, sample_spec, sample_data)
    assert "Capital Readiness" in html
    assert "Commercial Model" in html


def test_pivot_breakdown_uses_label_map():
    from visuals_engine.renderer import _pivot_breakdown
    rows = [
        {"category": "power", "metric_id": "readiness_completion_pct", "value": 50.0},
        {"category": "power", "metric_id": "open_gap_count", "value": 1.0},
    ]
    result = _pivot_breakdown(rows, "category", label_map={"power": "Power Strategy"})
    assert result[0]["name"] == "Power Strategy"


def test_pivot_breakdown_falls_back_to_raw_name_without_map():
    from visuals_engine.renderer import _pivot_breakdown
    rows = [
        {"category": "power", "metric_id": "readiness_completion_pct", "value": 50.0},
        {"category": "power", "metric_id": "open_gap_count", "value": 1.0},
    ]
    result = _pivot_breakdown(rows, "category")
    assert result[0]["name"] == "power"


# --- Polish: footer validation wording ---


def test_html_footer_no_raw_validation_status(sample_spec, sample_data):
    html = render_html(TEMPLATE_PATH, sample_spec, sample_data)
    assert "passed_with_warnings" not in html


def test_html_footer_shows_error_count(sample_spec, sample_data):
    html = render_html(TEMPLATE_PATH, sample_spec, sample_data)
    assert "0 errors" in html


def test_html_footer_shows_informational_warnings(sample_spec, sample_data):
    html = render_html(TEMPLATE_PATH, sample_spec, sample_data)
    assert "5 informational warnings" in html


def test_html_footer_source_note(sample_spec, sample_data):
    html = render_html(TEMPLATE_PATH, sample_spec, sample_data)
    assert "Metrics Engine" in html
    assert "Analytics Store" in html
    assert "Visuals Engine" in html


def test_html_is_valid_document(sample_spec, sample_data):
    html = render_html(TEMPLATE_PATH, sample_spec, sample_data)
    assert "<!DOCTYPE html>" in html
    assert "</html>" in html


def test_html_zero_completion(sample_spec, sample_data):
    sample_data["kpi_cards"][0]["value"] = 0.0
    html = render_html(TEMPLATE_PATH, sample_spec, sample_data)
    assert "0.0%" in html


def test_html_full_completion(sample_spec, sample_data):
    sample_data["kpi_cards"][0]["value"] = 100.0
    html = render_html(TEMPLATE_PATH, sample_spec, sample_data)
    assert "100.0%" in html


def test_summary_required_keys(sample_spec, sample_data):
    summary = render_summary(sample_spec, sample_data, "test.duckdb", "test.yaml")
    for key in ("metrics_rendered", "sections_rendered", "sections_skipped", "validation_status", "generated_at"):
        assert key in summary


def test_summary_sections_rendered(sample_spec, sample_data):
    summary = render_summary(sample_spec, sample_data, "test.duckdb", "test.yaml")
    assert "kpi_cards" in summary["sections_rendered"]
    assert "category_breakdown" in summary["sections_rendered"]


def test_summary_market_skipped(sample_spec, sample_data):
    summary = render_summary(sample_spec, sample_data, "test.duckdb", "test.yaml")
    assert "market_breakdown" in summary["sections_skipped"]


def test_summary_validation_status(sample_spec, sample_data):
    summary = render_summary(sample_spec, sample_data, "test.duckdb", "test.yaml")
    assert summary["validation_status"] == "passed_with_warnings"


# --- render_pdf_html ---


def test_pdf_html_is_valid_document(sample_spec, sample_data):
    from visuals_engine.renderer import render_pdf_html
    html = render_pdf_html(sample_spec, sample_data)
    assert "<!DOCTYPE html>" in html
    assert "</html>" in html


def test_pdf_html_contains_page_landscape_directive(sample_spec, sample_data):
    from visuals_engine.renderer import render_pdf_html
    html = render_pdf_html(sample_spec, sample_data)
    assert "@page" in html
    assert "landscape" in html


def test_pdf_html_contains_completion_value(sample_spec, sample_data):
    from visuals_engine.renderer import render_pdf_html
    html = render_pdf_html(sample_spec, sample_data)
    assert "50.0%" in html


def test_pdf_html_contains_kpi_labels(sample_spec, sample_data):
    from visuals_engine.renderer import render_pdf_html
    html = render_pdf_html(sample_spec, sample_data)
    assert "Readiness Completion" in html
    assert "Open Gap" in html


def test_pdf_html_contains_category_names(sample_spec, sample_data):
    from visuals_engine.renderer import render_pdf_html
    html = render_pdf_html(sample_spec, sample_data)
    assert "capital" in html
    assert "commercial" in html


def test_pdf_html_omits_market_section_when_no_rows(sample_spec, sample_data):
    from visuals_engine.renderer import render_pdf_html
    html = render_pdf_html(sample_spec, sample_data)
    assert "Readiness by Market" not in html


def test_pdf_html_contains_subtitle_when_configured(sample_spec, sample_data):
    sample_spec["dashboard"]["subtitle"] = "Client PDF snapshot."
    from visuals_engine.renderer import render_pdf_html
    html = render_pdf_html(sample_spec, sample_data)
    assert "Client PDF snapshot." in html
