import importlib
import importlib.util
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

_XHTML2PDF_AVAILABLE = importlib.util.find_spec("xhtml2pdf") is not None


def test_render_pdf_raises_import_error_when_xhtml2pdf_missing(tmp_path):
    from visuals_engine.pdf import render_pdf
    with patch.dict("sys.modules", {"xhtml2pdf": None}):
        with pytest.raises(ImportError, match="xhtml2pdf"):
            render_pdf("<html><body>test</body></html>", tmp_path / "test.pdf")


def test_render_pdf_import_error_message_mentions_python_version(tmp_path):
    from visuals_engine.pdf import render_pdf
    with patch.dict("sys.modules", {"xhtml2pdf": None}):
        with pytest.raises(ImportError, match="3.12"):
            render_pdf("<html><body>test</body></html>", tmp_path / "test.pdf")


def test_render_pdf_raises_runtime_error_on_pisa_error(tmp_path):
    mock_result = MagicMock()
    mock_result.err = 1

    mock_pisa = MagicMock()
    mock_pisa.CreatePDF.return_value = mock_result

    mock_xhtml2pdf = MagicMock()
    mock_xhtml2pdf.pisa = mock_pisa

    from visuals_engine.pdf import render_pdf
    with patch.dict("sys.modules", {"xhtml2pdf": mock_xhtml2pdf}):
        with pytest.raises(RuntimeError, match="PDF generation failed"):
            render_pdf("<html><body>test</body></html>", tmp_path / "test.pdf")


def test_render_pdf_creates_file_on_pisa_success(tmp_path):
    mock_result = MagicMock()
    mock_result.err = 0

    mock_pisa = MagicMock()
    mock_pisa.CreatePDF.return_value = mock_result

    mock_xhtml2pdf = MagicMock()
    mock_xhtml2pdf.pisa = mock_pisa

    out = tmp_path / "out.pdf"
    from visuals_engine.pdf import render_pdf
    with patch.dict("sys.modules", {"xhtml2pdf": mock_xhtml2pdf}):
        render_pdf("<html><body>test</body></html>", out)

    assert out.exists()


@pytest.mark.skipif(not _XHTML2PDF_AVAILABLE, reason="xhtml2pdf not installed")
def test_render_pdf_produces_nonempty_file(tmp_path):
    from visuals_engine.pdf import render_pdf
    out = tmp_path / "out.pdf"
    render_pdf("<!DOCTYPE html><html><body><p>Hello PDF</p></body></html>", out)
    assert out.exists()
    assert out.stat().st_size > 0
