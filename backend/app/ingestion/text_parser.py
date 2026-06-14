"""Plain-text / Markdown parser.

A dependency-free parser that splits text into paragraph blocks on blank lines.
It lets the full pipeline run end-to-end offline (with ``.txt``/``.md`` sample
sources) for demos and CI, and is the fallback when richer parsers are absent.
"""

from __future__ import annotations

from app.core.models import CIRBlock
from app.ingestion.base import DocumentParser, block_id


class TextParser(DocumentParser):
    """Parse ``.txt`` / ``.md`` into one paragraph block per blank-line group."""

    extensions = ("txt", "md", "markdown")
    format = "txt"

    def parse(self, data: bytes, filename: str) -> tuple[list[CIRBlock], dict, int]:
        """Split decoded text into paragraph blocks.

        Args:
            data: Raw UTF-8 (best-effort) bytes.
            filename: Original filename (unused beyond metadata).

        Returns:
            ``(blocks, metadata, page_count=1)``.
        """
        text = data.decode("utf-8", errors="replace")
        chunks = [c.strip() for c in text.split("\n\n") if c.strip()]
        blocks = [
            CIRBlock(block_id=block_id(i), type="paragraph", page=1, text=chunk)
            for i, chunk in enumerate(chunks)
        ]
        return blocks, {"filename": filename}, 1
