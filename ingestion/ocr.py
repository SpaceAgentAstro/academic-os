from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from PIL.Image import Image


def extract_text_pdfplumber(pdf_path: Path) -> list[dict]:
    """Extract text per page using pdfplumber.

    Returns list of {page: int, text: str, is_scanned: bool}.
    A page is marked is_scanned when pdfplumber yields no meaningful text
    (empty or only whitespace), indicating an image-based page.
    """
    import pdfplumber

    results: list[dict] = []
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages, start=1):
            text = page.extract_text() or ""
            is_scanned = len(text.strip()) < 20
            results.append({"page": i, "text": text, "is_scanned": is_scanned})
            if is_scanned:
                logger.debug("Page %d of %s appears scanned", i, pdf_path.name)
    return results


def extract_text_tesseract(image_path: Path) -> str:
    """OCR a single page image using pytesseract."""
    import pytesseract
    from PIL import Image

    img = Image.open(image_path)
    # oem 3 = LSTM; psm 6 = assume a uniform block of text
    config = "--oem 3 --psm 6"
    return pytesseract.image_to_string(img, lang="eng", config=config)


def convert_pdf_to_images(
    pdf_path: Path,
    output_dir: Path,
    dpi: int = 300,
) -> list[Path]:
    """Convert each PDF page to a PNG image using pdf2image.

    Images are named <stem>_page_<n>.png inside output_dir.
    """
    from pdf2image import convert_from_path

    output_dir.mkdir(parents=True, exist_ok=True)
    stem = pdf_path.stem
    pil_images = convert_from_path(str(pdf_path), dpi=dpi)
    paths: list[Path] = []
    for i, img in enumerate(pil_images, start=1):
        out_path = output_dir / f"{stem}_page_{i:04d}.png"
        img.save(str(out_path), "PNG")
        paths.append(out_path)
    logger.info("Converted %d pages of %s to images", len(paths), pdf_path.name)
    return paths


def extract_math_latex(image_path: Path) -> str:
    """Extract LaTeX from a mathematical expression image using pix2tex.

    Returns empty string if pix2tex is unavailable or extraction fails.
    pix2tex is expensive to load — caller should cache the LatexOCR instance.
    """
    try:
        from pix2tex.cli import LatexOCR
        from PIL import Image
    except ImportError:
        logger.debug("pix2tex not installed; skipping LaTeX OCR for %s", image_path.name)
        return ""

    try:
        model = LatexOCR()
        img = Image.open(image_path)
        return model(img)
    except Exception as exc:
        logger.warning("pix2tex failed on %s: %s", image_path.name, exc)
        return ""


def ocr_page_with_fallback(
    pdf_path: Path,
    page_number: int,
    tmp_dir: Path,
    dpi: int = 300,
) -> str:
    """OCR a single page: pdfplumber first, tesseract if scanned.

    page_number is 1-indexed.
    """
    pages = extract_text_pdfplumber(pdf_path)
    if page_number < 1 or page_number > len(pages):
        raise ValueError(f"Page {page_number} out of range for {pdf_path.name}")

    page_data = pages[page_number - 1]
    if not page_data["is_scanned"]:
        return page_data["text"]

    # Scanned page — convert just this page to image, then tesseract
    from pdf2image import convert_from_path

    pil_pages = convert_from_path(str(pdf_path), dpi=dpi, first_page=page_number, last_page=page_number)
    if not pil_pages:
        return ""

    tmp_dir.mkdir(parents=True, exist_ok=True)
    img_path = tmp_dir / f"{pdf_path.stem}_p{page_number:04d}.png"
    pil_pages[0].save(str(img_path), "PNG")
    return extract_text_tesseract(img_path)


def extract_full_text(pdf_path: Path, tmp_dir: Path | None = None) -> str:
    """Extract full text from a PDF, using Tesseract fallback on scanned pages."""
    if tmp_dir is None:
        tmp_dir = pdf_path.parent / ".ocr_tmp"

    pages = extract_text_pdfplumber(pdf_path)
    full_parts: list[str] = []
    for page_data in pages:
        if not page_data["is_scanned"]:
            full_parts.append(page_data["text"])
        else:
            try:
                text = ocr_page_with_fallback(pdf_path, page_data["page"], tmp_dir)
            except Exception as exc:
                logger.warning(
                    "OCR skipped page %d of %s (poppler/tesseract unavailable?): %s",
                    page_data["page"], pdf_path.name, exc,
                )
                text = ""
            full_parts.append(text)

    return "\n\n".join(full_parts)
