"""Tests for ingestion/ocr.py using fixture PDFs."""
from __future__ import annotations

from pathlib import Path

import pytest

# Skip (don't fail) when the optional PDF stack is unavailable.
pytest.importorskip("pdfplumber")

FIXTURES = Path(__file__).parent.parent / "fixtures" / "pdfs"
QP_PDF   = FIXTURES / "sample_question_paper.pdf"
MS_PDF   = FIXTURES / "sample_mark_scheme.pdf"
ER_PDF   = FIXTURES / "sample_examiner_report.pdf"


@pytest.mark.skipif(not QP_PDF.exists(), reason="Fixture PDF not generated")
def test_extract_text_pdfplumber_returns_pages():
    from ingestion.ocr import extract_text_pdfplumber
    pages = extract_text_pdfplumber(QP_PDF)
    assert len(pages) >= 1
    for p in pages:
        assert "page" in p
        assert "text" in p
        assert "is_scanned" in p


@pytest.mark.skipif(not QP_PDF.exists(), reason="Fixture PDF not generated")
def test_extract_text_pdfplumber_text_not_empty():
    from ingestion.ocr import extract_text_pdfplumber
    pages = extract_text_pdfplumber(QP_PDF)
    combined = " ".join(p["text"] for p in pages)
    assert "WME01" in combined or "Mathematics" in combined or "Find" in combined


@pytest.mark.skipif(not QP_PDF.exists(), reason="Fixture PDF not generated")
def test_extract_full_text_returns_string(tmp_path):
    from ingestion.ocr import extract_full_text
    text = extract_full_text(QP_PDF, tmp_dir=tmp_path)
    assert isinstance(text, str)
    assert len(text) > 10


@pytest.mark.skipif(not QP_PDF.exists(), reason="Fixture PDF not generated")
def test_scanned_flag_false_for_text_pdf():
    from ingestion.ocr import extract_text_pdfplumber
    pages = extract_text_pdfplumber(QP_PDF)
    # Our test fixture is a real text PDF — at least page 1 should not be scanned
    assert not pages[0]["is_scanned"]
