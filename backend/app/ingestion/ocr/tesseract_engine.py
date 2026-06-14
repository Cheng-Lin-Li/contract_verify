"""Tesseract OCR engine (local default) and the OCR engine factory.

Tesseract is fully local and offline -- the right default for data-sovereign /
air-gapped deployments and the 2-day MVP. ``pytesseract`` is imported lazily so
the module imports cleanly even when OCR is not installed (the text-layer
pipeline never needs it).
"""

from __future__ import annotations

from typing import Optional

from app.config import Settings, get_settings
from app.ingestion.ocr.base import OCREngine, OCRResult
from app.logging_setup import get_logger

log = get_logger("ingestion.ocr")


class TesseractEngine(OCREngine):
    """OCR engine backed by Tesseract 5 via ``pytesseract``."""

    name = "tesseract"

    def image_to_text(self, image_bytes: bytes, lang: str = "eng") -> OCRResult:
        """Recognise text using Tesseract.

        Raises:
            RuntimeError: If ``pytesseract``/``Pillow`` are unavailable.
        """
        try:  # pragma: no cover - requires native tesseract
            import io

            import pytesseract  # type: ignore
            from PIL import Image  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("pytesseract and Pillow are required for OCR") from exc

        image = Image.open(io.BytesIO(image_bytes))
        data = pytesseract.image_to_data(image, lang=lang, output_type=pytesseract.Output.DICT)
        words = [w for w in data["text"] if w.strip()]
        confs = [int(c) for c in data["conf"] if str(c).lstrip("-").isdigit() and int(c) >= 0]
        mean_conf = (sum(confs) / len(confs) / 100.0) if confs else 0.0
        return OCRResult(text=" ".join(words), confidence=round(mean_conf, 4))


def get_ocr_engine(settings: Optional[Settings] = None) -> OCREngine:
    """Return the configured OCR engine.

    Args:
        settings: Optional settings override.

    Raises:
        ValueError: If ``OCR_ENGINE`` names an engine not available in this tier.
    """
    settings = settings or get_settings()
    engine = settings.ocr_engine.lower()
    log.info("select_ocr_engine", extra={"engine": engine})
    if engine == "tesseract":
        return TesseractEngine()
    if engine in ("paddleocr", "pp-structure"):
        # 3-month scope (TDD §4.3): PaddleOCR/PP-Structure for tables & images.
        raise ValueError(f"OCR engine '{engine}' is delivered in the 3-month build")
    if engine in ("paddleocr_vl", "easyocr", "google_vision"):
        # Backlog (TDD §20).
        raise ValueError(f"OCR engine '{engine}' is on the backlog")
    raise ValueError(f"Unknown OCR_ENGINE: {engine!r}")
