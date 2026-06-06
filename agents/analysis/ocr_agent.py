from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class OCRResult:
    text: str
    latex_blocks: list[str] = field(default_factory=list)
    image_paths: list[Path] = field(default_factory=list)
    page_count: int = 0
    used_fallback_ocr: bool = False


def extract_text(pdf_path: Path) -> OCRResult:
    """Extract text from a PDF using pdfplumber. Falls back to pytesseract for scanned pages."""
    raise NotImplementedError


def extract_images(pdf_path: Path, output_dir: Path) -> list[Path]:
    """Extract all images from a PDF to output_dir. Returns paths to extracted images."""
    raise NotImplementedError


def extract_latex(image_path: Path) -> str:
    """Convert a math expression image to LaTeX using pix2tex."""
    raise NotImplementedError


def ocr_page(pdf_path: Path, page_number: int) -> str:
    """OCR a single page using pytesseract. Used for scanned pages."""
    raise NotImplementedError
