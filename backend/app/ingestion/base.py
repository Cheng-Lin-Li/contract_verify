"""Document parser interface (TDD §4.3, §5).

Each format parser turns raw bytes into a list of :class:`CIRBlock`. The
:class:`IngestService` wraps the chosen parser, computes the document hash, and
assembles the final :class:`CIRDocument`.
"""

from __future__ import annotations

import abc

from app.core.models import CIRBlock


def block_id(index: int) -> str:
    """Return a zero-padded block id like ``b-001`` for ``index`` (0-based)."""
    return f"b-{index + 1:03d}"


class DocumentParser(abc.ABC):
    """Abstract base for a single-format parser."""

    #: File extensions (without dot) this parser handles.
    extensions: tuple[str, ...] = ()
    #: The CIR ``format`` label emitted (e.g. ``pdf``).
    format: str = "unknown"

    @abc.abstractmethod
    def parse(
        self,
        data: bytes,
        filename: str,
        progress_callback=None,
    ) -> tuple[list[CIRBlock], dict, int]:
        """Parse ``data`` into blocks.

        Args:
            data: Raw file bytes.
            filename: Original filename (used for metadata / hints).
            progress_callback: Optional ``(current, total) -> None`` called after
                each page/section during parsing so callers can report progress.

        Returns:
            A tuple ``(blocks, metadata, page_count)``.
        """
        raise NotImplementedError
