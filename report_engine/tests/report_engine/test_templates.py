import pytest

from report_engine.templates import (
    DEFAULT_TEMPLATE,
    VALID_TEMPLATES,
    TemplateError,
    get_sections,
)


# ── Registry content tests ─────────────────────────────────────────────────────

def test_full_report_sections_are_ordered():
    assert get_sections("full_report") == [
        "header",
        "validation",
        "kpi_snapshot",
        "key_insights",
        "metrics_summary",
        "metric_dictionary",
    ]


def test_executive_summary_sections_are_ordered():
    assert get_sections("executive_summary") == [
        "header",
        "validation",
        "kpi_snapshot",
        "key_insights",
    ]


def test_metrics_detail_sections_are_ordered():
    assert get_sections("metrics_detail") == [
        "header",
        "validation",
        "metrics_summary",
        "metric_dictionary",
    ]


# ── Default and valid template tests ──────────────────────────────────────────

def test_default_template_is_full_report():
    assert DEFAULT_TEMPLATE == "full_report"


def test_valid_templates_contains_all_three():
    assert "full_report" in VALID_TEMPLATES
    assert "executive_summary" in VALID_TEMPLATES
    assert "metrics_detail" in VALID_TEMPLATES


def test_valid_templates_has_exactly_three():
    assert len(VALID_TEMPLATES) == 3


# ── Error handling tests ───────────────────────────────────────────────────────

def test_unknown_template_raises_template_error():
    with pytest.raises(TemplateError):
        get_sections("nonexistent")


def test_template_error_message_contains_invalid_name():
    with pytest.raises(TemplateError, match="nonexistent"):
        get_sections("nonexistent")


def test_template_error_message_lists_valid_options():
    with pytest.raises(TemplateError, match="full_report"):
        get_sections("nonexistent")


def test_template_error_is_value_error_subclass():
    with pytest.raises(ValueError):
        get_sections("nonexistent")


# ── Isolation test ─────────────────────────────────────────────────────────────

def test_get_sections_returns_copy():
    sections = get_sections("full_report")
    sections.clear()
    assert get_sections("full_report") == [
        "header",
        "validation",
        "kpi_snapshot",
        "key_insights",
        "metrics_summary",
        "metric_dictionary",
    ]
