from __future__ import annotations

from pathlib import Path


def render_pdf(html: str, output_path: Path) -> None:
    """Convert rendered HTML to a PDF file using xhtml2pdf."""
    try:
        from xhtml2pdf import pisa
    except ImportError as exc:
        raise ImportError(
            "PDF generation requires xhtml2pdf. Install it with:\n"
            "  pip install xhtml2pdf\n"
            "Note: xhtml2pdf requires Python 3.12 or 3.13 on Windows (not compatible with 3.14).\n"
            "See visuals_engine README for installation guidance."
        ) from exc

    with output_path.open("wb") as f:
        result = pisa.CreatePDF(html, dest=f)

    if result.err:
        raise RuntimeError(
            f"PDF generation failed ({result.err} error(s)). "
            "Check that the dashboard HTML is valid."
        )
