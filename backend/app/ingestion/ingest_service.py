"""Ingestion service: dispatch a file to the right parser and build the CIR.

Single entry point (:meth:`IngestService.ingest_file`) that:

1. selects a :class:`DocumentParser` by extension,
2. parses bytes into blocks + metadata,
3. recursively ingests email attachments, merging their blocks, and
4. assembles a :class:`CIRDocument` with a SHA-256 fingerprint.

This is the normalisation boundary described in TDD §5 -- every later stage sees
only the CIR, never raw files.
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.core.enums import DocRole
from app.core.models import CIRDocument, sha256_bytes
from app.ingestion.base import DocumentParser
from app.ingestion.docx_parser import DocxParser
from app.ingestion.email_parser import EmailParser
from app.ingestion.pdf_parser import PdfParser
from app.ingestion.text_parser import TextParser
from app.logging_setup import get_logger, log_stage

log = get_logger("ingestion.service")


class IngestService:
    """Routes raw documents to format parsers and emits :class:`CIRDocument`."""

    def __init__(self, parsers: Optional[list[DocumentParser]] = None) -> None:
        """Initialise with a parser registry.

        Args:
            parsers: Optional explicit parser list; defaults to the MVP set
                (PDF, DOCX, email, text).
        """
        self._parsers = parsers or [PdfParser(), DocxParser(), EmailParser(), TextParser()]

    def _parser_for(self, filename: str) -> DocumentParser:
        """Return the parser whose extension matches ``filename``.

        Raises:
            ValueError: If no registered parser handles the extension.
        """
        ext = Path(filename).suffix.lower().lstrip(".")
        for parser in self._parsers:
            if ext in parser.extensions:
                return parser
        raise ValueError(f"No parser registered for '.{ext}' files")

    def ingest_bytes(
        self,
        data: bytes,
        filename: str,
        role: DocRole,
        progress_callback=None,
    ) -> CIRDocument:
        """Ingest in-memory bytes into a :class:`CIRDocument`.

        Email attachments are recursively ingested and their blocks appended,
        with each attachment's blocks re-id'd to stay unique within the document.

        Args:
            data: Raw file bytes.
            filename: Original filename (drives parser selection).
            role: The :class:`DocRole` for this document.
            progress_callback: Optional ``(current, total) -> None`` forwarded
                to the format parser for page/section-level progress reporting.
        """
        with log_stage("ingest", doc_id=None, filename=filename, role=role.value):
            parser = self._parser_for(filename)
            blocks, metadata, pages = parser.parse(data, filename, progress_callback)

            # Recursively fold in email attachments.
            for att in metadata.pop("attachments", []) if isinstance(metadata, dict) else []:
                try:
                    child_parser = self._parser_for(att["filename"])
                except ValueError:
                    log.warning("skip_unknown_attachment", extra={"filename": att["filename"]})
                    continue
                child_blocks, _child_meta, _ = child_parser.parse(att["data"], att["filename"])
                offset = len(blocks)
                for j, blk in enumerate(child_blocks):
                    blk.block_id = f"b-{offset + j + 1:03d}"
                    blocks.append(blk)

            meta = metadata if isinstance(metadata, dict) else {}
            meta.setdefault("filename", filename)  # always available for viewers
            doc = CIRDocument(
                role=role,
                format=parser.format,
                sha256=sha256_bytes(data),
                pages=pages,
                blocks=blocks,
                metadata=meta,
            )
            log.info("ingested", extra={"doc_id": doc.doc_id, "format": doc.format,
                                        "blocks": len(doc.blocks)})
            return doc

    def ingest_file(self, path: str | Path, role: DocRole) -> CIRDocument:
        """Read ``path`` from disk and ingest it.

        Args:
            path: Filesystem path to the document.
            role: The :class:`DocRole` for this document.

        Raises:
            FileNotFoundError: If the file does not exist.
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(p)
        return self.ingest_bytes(p.read_bytes(), p.name, role)
