"""
file_utils.py
Shared helpers for turning uploaded files (PDF or image) into the bytes/text
the rest of the pipeline needs.
"""
from __future__ import annotations
from pathlib import Path

import fitz  # PyMuPDF

IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}


def to_image_bytes(file_path: str | Path, dpi: int = 220) -> bytes:
    """Returns PNG bytes for page 1 of a PDF, or the raw image re-encoded as PNG."""
    path = Path(file_path)

    if path.suffix.lower() in IMAGE_EXTS:
        doc = fitz.open(path)
        pix = doc[0].get_pixmap()
        return pix.tobytes("png")

    if path.suffix.lower() != ".pdf":
        raise ValueError(f"Unsupported file type: {path.suffix}")

    zoom = dpi / 72
    with fitz.open(path) as doc:
        pix = doc[0].get_pixmap(matrix=fitz.Matrix(zoom, zoom))
        return pix.tobytes("png")


def extract_text_if_possible(file_path: str | Path) -> str | None:
    """For text-based PDFs (e.g. a CV exported from Word), grab the raw text directly.
    Returns None if the file is an image or the PDF has no extractable text
    (e.g. a scanned CV) -- caller should fall back to the multimodal route."""
    path = Path(file_path)
    if path.suffix.lower() != ".pdf":
        return None

    with fitz.open(path) as doc:
        text = "\n".join(page.get_text() for page in doc)

    return text.strip() or None
