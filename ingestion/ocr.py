from __future__ import annotations

import logging
from pathlib import Path

logger = logging.getLogger(__name__)


def extract_text_pdfplumber(pdf_path: Path) -> list[dict]:
    """Extract text per page using pdfplumber. Returns list of {page, text, is_scanned}."""
    raise NotImplementedError


def extract_text_tesseract(image_path: Path) -> str:
    """OCR a single page image using pytesseract."""
    raise NotImplementedError


def convert_pdf_to_images(pdf_path: Path, output_dir: Path, dpi: int = 300) -> list[Path]:
    """Convert each PDF page to a PNG image using pdf2image."""
    raise NotImplementedError


def extract_math_latex(image_path: Path) -> str:
    """Extract LaTeX from a mathematical expression image using pix2tex."""
    raise NotImplementedError
