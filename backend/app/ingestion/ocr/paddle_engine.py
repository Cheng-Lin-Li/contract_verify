"""PaddleOCR / PP-Structure OCR engine (3-month scope · SKELETON).

Adds table + embedded-image recognition on top of the MVP Tesseract engine,
behind the same ``OCREngine`` interface (selected via ``OCR_ENGINE=paddleocr``).
Requires ``paddleocr`` + ``paddlepaddle``.
"""

from __future__ import annotations

from typing import Any


class PaddleOCREngine:
    """Layout analysis + table recognition via PP-Structure (SKELETON)."""

    name = "paddleocr"

    def __init__(self, lang: str = "en") -> None:
        raise NotImplementedError

    def image_to_blocks(self, image_bytes: bytes) -> list[Any]:
        """Return CIR blocks (paragraphs + tables) with confidences."""
        raise NotImplementedError
