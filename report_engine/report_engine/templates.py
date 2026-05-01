from __future__ import annotations

_REGISTRY: dict[str, list[str]] = {
    "full_report": [
        "header",
        "validation",
        "kpi_snapshot",
        "key_insights",
        "metrics_summary",
        "metric_dictionary",
    ],
    "executive_summary": [
        "header",
        "validation",
        "kpi_snapshot",
        "key_insights",
    ],
    "metrics_detail": [
        "header",
        "validation",
        "metrics_summary",
        "metric_dictionary",
    ],
}

DEFAULT_TEMPLATE = "full_report"
VALID_TEMPLATES = list(_REGISTRY)


class TemplateError(ValueError):
    pass


def get_sections(template_name: str) -> list[str]:
    if template_name not in _REGISTRY:
        raise TemplateError(
            f"Unknown template '{template_name}'. "
            f"Valid options: {', '.join(VALID_TEMPLATES)}"
        )
    return list(_REGISTRY[template_name])
