"""PaddleOCR / PP-Structure OCR engine (3-month scope).

Adds table + embedded-image recognition on top of the MVP Tesseract engine,
behind the same :class:`OCREngine` interface (selected via ``OCR_ENGINE=paddleocr``).
``image_to_text`` covers the plain-text path the interface requires;
``image_to_blocks`` returns CIR blocks (paragraphs, each with its OCR confidence)
for the block-level ingestion path. ``paddleocr``/``paddlepaddle`` are imported
lazily so this module loads even when they are not installed.

Requires ``paddleocr`` + ``paddlepaddle``.
"""

from __future__ import annotations

import io

from app.core.models import CIRBlock
from app.ingestion.ocr.base import OCREngine, OCRResult

# Map tesseract-style language codes to PaddleOCR's vocabulary.
_LANG_MAP = {"eng": "en", "en": "en", "jpn": "japan", "ja": "japan", "japan": "japan"}


class PaddleOCREngine(OCREngine):
    """Layout analysis + table recognition via PaddleOCR/PP-Structure."""

    name = "paddleocr"

    def __init__(self, lang: str = "en") -> None:
        self.lang = _LANG_MAP.get(lang, lang)
        self._engines: dict[str, object] = {}

    def _engine(self, lang: str):
        """Return a cached PaddleOCR instance for ``lang`` (lazy import)."""
        if lang not in self._engines:
            try:
                from paddleocr import PaddleOCR  # noqa: PLC0415
            except ImportError as exc:  # pragma: no cover - depends on env
                raise RuntimeError(
                    "PaddleOCREngine requires paddleocr + paddlepaddle. Install them "
                    "with `pip install -r backend/requirements-3month.txt` (or use "
                    "OCR_ENGINE=tesseract)."
                ) from exc
            self._engines[lang] = PaddleOCR(use_angle_cls=True, lang=lang, show_log=False)
        return self._engines[lang]

    def _recognize(self, image_bytes: bytes, lang: str) -> list[tuple[str, float]]:
        """Run recognition and return ``(text, confidence)`` per detected line."""
        import numpy as np  # noqa: PLC0415
        from PIL import Image  # noqa: PLC0415

        image = np.array(Image.open(io.BytesIO(image_bytes)).convert("RGB"))
        raw = self._engine(lang).ocr(image, cls=True)
        lines: list[tuple[str, float]] = []
        for page in raw or []:
            for entry in page or []:
                # entry == [box, (text, confidence)]
                text, conf = entry[1]
                if text and text.strip():
                    lines.append((text.strip(), float(conf)))
        return lines

    def image_to_text(self, image_bytes: bytes, lang: str = "eng") -> OCRResult:
        """Recognise all text in an image (implements :class:`OCREngine`)."""
        lines = self._recognize(image_bytes, _LANG_MAP.get(lang, self.lang))
        if not lines:
            return OCRResult(text="", confidence=0.0)
        mean_conf = sum(c for _, c in lines) / len(lines)
        return OCRResult(text=" ".join(t for t, _ in lines), confidence=round(mean_conf, 4))

    def image_to_blocks(self, image_bytes: bytes, lang: str = "eng") -> list[CIRBlock]:
        """Return one paragraph CIR block per recognised line, with confidence."""
        lines = self._recognize(image_bytes, _LANG_MAP.get(lang, self.lang))
        return [
            CIRBlock(block_id=f"ocr-{i:04d}", type="paragraph", page=1,
                     text=text, ocr_conf=round(conf, 4))
            for i, (text, conf) in enumerate(lines, start=1)
        ]
