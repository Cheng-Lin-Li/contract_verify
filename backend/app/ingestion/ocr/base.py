"""OCR engine adapter interface (Foundation Rule f; TDD §4.3).

The OCR engine is selected via ``OCR_ENGINE`` and swapped without touching call
sites. Tesseract is the local default; PaddleOCR/PP-Structure (tables & images)
is the 3-month addition; PaddleOCR-VL / EasyOCR / cloud Vision are backlog. All
implement :class:`OCREngine`.
"""

from __future__ import annotations

import abc
from dataclasses import dataclass


@dataclass
class OCRResult:
    """Text recovered from an image, with an aggregate confidence.

    Attributes:
        text: The recognised text.
        confidence: Mean confidence in ``[0, 1]``.
    """

    text: str
    confidence: float = 0.0


class OCREngine(abc.ABC):
    """Abstract OCR engine."""

    name: str = "base"

    @abc.abstractmethod
    def image_to_text(self, image_bytes: bytes, lang: str = "eng") -> OCRResult:
        """Recognise text in an image.

        Args:
            image_bytes: Raw image bytes (PNG/JPEG/TIFF).
            lang: Tesseract-style language code (``eng``, ``jpn`` ...).

        Returns:
            An :class:`OCRResult`.
        """
        raise NotImplementedError
