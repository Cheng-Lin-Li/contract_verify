"""Email parser using the stdlib :mod:`email` package (TDD §4.3).

Parses EML/MIME into the message body plus recursively-unpacked attachments.
The body becomes paragraph blocks; each attachment is returned as a raw
``(filename, bytes)`` pair so the :class:`IngestService` can re-dispatch it to
the correct format parser (PDF/DOCX/text). Outlook ``.msg`` support via
``extract-msg`` is a lazy, optional path.
"""

from __future__ import annotations

from email import message_from_bytes
from email.message import Message

from app.core.models import CIRBlock
from app.ingestion.base import DocumentParser, block_id
from app.logging_setup import get_logger

log = get_logger("ingestion.email")


class EmailParser(DocumentParser):
    """Parse an ``.eml`` message into body blocks; expose attachments."""

    extensions = ("eml",)
    format = "eml"

    def parse(self, data: bytes, filename: str) -> tuple[list[CIRBlock], dict, int]:
        """Parse the email body and collect attachments.

        Returns:
            ``(blocks, metadata, 1)`` where ``metadata['attachments']`` is a list
            of ``{"filename": str, "data": bytes}`` for recursive ingestion.
        """
        msg: Message = message_from_bytes(data)
        body_text = self._extract_body(msg)
        attachments = self._extract_attachments(msg)

        chunks = [c.strip() for c in body_text.split("\n\n") if c.strip()]
        blocks = [
            CIRBlock(block_id=block_id(i), type="paragraph", page=1, text=chunk)
            for i, chunk in enumerate(chunks)
        ]
        meta = {
            "filename": filename,
            "from": msg.get("From", ""),
            "to": msg.get("To", ""),
            "subject": msg.get("Subject", ""),
            "date": msg.get("Date", ""),
            "attachments": attachments,
        }
        log.info("email_parsed", extra={"filename": filename, "blocks": len(blocks),
                                        "attachments": len(attachments)})
        return blocks, meta, 1

    @staticmethod
    def _extract_body(msg: Message) -> str:
        """Return the best-effort plain-text body of the message."""
        if not msg.is_multipart():
            payload = msg.get_payload(decode=True) or b""
            return payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
        parts: list[str] = []
        for part in msg.walk():
            if part.get_content_type() == "text/plain" and "attachment" not in str(
                part.get("Content-Disposition", "")
            ):
                payload = part.get_payload(decode=True) or b""
                parts.append(payload.decode(part.get_content_charset() or "utf-8", errors="replace"))
        return "\n\n".join(parts)

    @staticmethod
    def _extract_attachments(msg: Message) -> list[dict]:
        """Recursively collect attachment ``{filename, data}`` pairs."""
        attachments: list[dict] = []
        if not msg.is_multipart():
            return attachments
        for part in msg.walk():
            disp = str(part.get("Content-Disposition", ""))
            if "attachment" in disp:
                fname = part.get_filename() or "attachment.bin"
                payload = part.get_payload(decode=True) or b""
                attachments.append({"filename": fname, "data": payload})
        return attachments
