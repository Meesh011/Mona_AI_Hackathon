"""
pdf_utils.py
Converts an uploaded PDF (or image) work-permit document into PNG image bytes
that can be sent to Gemini's multimodal API.
"""
from __future__ import annotations
import io
from pathlib import Path

import fitz  # PyMuPDF


SUPPORTED_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def file_to_images(file_path: str | Path, dpi: int = 220, max_pages: int = 3) -> list[bytes]:
    """
    Returns a list of PNG-encoded image bytes, one per page (capped at max_pages).
    Work permits are almost always single-page, but we cap at 3 in case someone
    uploads a multi-page scan (front/back/cover letter).

    If the input is already an image file, just reads it back as PNG bytes.
    """
    path = Path(file_path)

    if path.suffix.lower() in SUPPORTED_IMAGE_EXTS:
        doc = fitz.open(path)  # fitz can also open raster images directly
        pix = doc[0].get_pixmap()
        return [pix.tobytes("png")]

    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Unsupported file type: {path.suffix}")

    images: list[bytes] = []
    zoom = dpi / 72  # PDF default is 72 dpi
    matrix = fitz.Matrix(zoom, zoom)

    with fitz.open(path) as doc:
        for i, page in enumerate(doc):
            if i >= max_pages:
                break
            pix = page.get_pixmap(matrix=matrix)
            images.append(pix.tobytes("png"))

    if not images:
        raise ValueError(f"Could not extract any pages from {path}")

    return images
