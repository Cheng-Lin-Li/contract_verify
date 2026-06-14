"""PDF text-layer parser using ``pdfminer.six`` (TDD §4.3).

Extracts character-level text with coordinates so clause citations can be
precise. Image-only / scanned PDFs are handled by routing pages with no text
layer through the OCR adapter in the 3-month build; in the MVP a page with no
text layer yields an empty block flagged for OCR.
"""

from __future__ import annotations

from app.core.models import CIRBlock
from app.ingestion.base import DocumentParser, block_id
from app.logging_setup import get_logger

log = get_logger("ingestion.pdf")


class PdfParser(DocumentParser):
    """Parse a text-layer PDF into paragraph blocks with bounding boxes."""

    extensions = ("pdf",)
    format = "pdf"

    def parse(self, data: bytes, filename: str) -> tuple[list[CIRBlock], dict, int]:
        """Extract text containers from each page.

        Imports ``pdfminer`` lazily. Each text container becomes one block with
        its page number and bounding box.

        Raises:
            RuntimeError: If ``pdfminer.six`` is not installed.
        """
        try:
            import io

            from pdfminer.high_level import extract_pages
            from pdfminer.layout import LTTextContainer
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError("pdfminer.six is required to parse PDFs") from exc

        blocks: list[CIRBlock] = []
        page_count = 0
        idx = 0
        for page_no, layout in enumerate(extract_pages(io.BytesIO(data)), start=1):
            page_count = page_no
            for element in layout:
                if isinstance(element, LTTextContainer):
                    text = element.get_text().strip()
                    if not text:
                        continue
                    x0, y0, x1, y1 = element.bbox
                    blocks.append(
                        CIRBlock(
                            block_id=block_id(idx),
                            type="paragraph",
                            page=page_no,
                            text=text,
                            bbox={"x0": round(x0, 2), "y0": round(y0, 2),
                                  "x1": round(x1, 2), "y1": round(y1, 2)},
                        )
                    )
                    idx += 1
        log.info("pdf_parsed", extra={"filename": filename, "pages": page_count, "blocks": len(blocks)})
        return blocks, {"filename": filename}, max(page_count, 1)
