from __future__ import annotations

from pathlib import Path


def render_pdf(html: str, output_path: Path) -> None:
    try:
        from xhtml2pdf import pisa
    except ImportError:
        raise SystemExit(
            "PDF generation requires xhtml2pdf. Install it with:\n"
            "  pip install xhtml2pdf"
        )

    with output_path.open("wb") as f:
        result = pisa.CreatePDF(html, dest=f)

    if result.err:
        raise SystemExit(
            f"PDF generation failed ({result.err} error(s)). "
            "Check report.html is valid HTML."
        )
