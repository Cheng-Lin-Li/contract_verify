"""Tests for the ingestion pipeline (TDD §5): parsers and the ingest service.

Only stdlib-parseable formats (text/markdown/email) are exercised so the suite
runs without the optional pdfminer/python-docx native dependencies.
"""

from __future__ import annotations

from app.core.enums import DocRole
from app.core.models import sha256_bytes
from app.ingestion.email_parser import EmailParser
from app.ingestion.ingest_service import IngestService
from app.ingestion.text_parser import TextParser

from tests.helpers import TERM_SHEET, FOLLOWUP


def test_text_parser_splits_blocks():
    blocks, meta, pages = TextParser().parse(b"Para one.\n\nPara two.", "x.txt")
    assert len(blocks) == 2
    assert blocks[0].block_id.startswith("b-")
    assert blocks[0].type == "paragraph"


def test_email_parser_extracts_body_and_headers():
    data = FOLLOWUP.read_bytes()
    blocks, meta, pages = EmailParser().parse(data, "followup.eml")
    text = " ".join(b.text for b in blocks).lower()
    assert "net-45" in text
    assert meta.get("subject")  # headers captured


def test_email_parser_unpacks_attachments_into_metadata():
    # Build a tiny multipart email with one text attachment.
    raw = (
        "From: a@x\r\nTo: b@y\r\nSubject: t\r\n"
        'Content-Type: multipart/mixed; boundary="B"\r\n\r\n'
        "--B\r\nContent-Type: text/plain\r\n\r\nbody text\r\n"
        "--B\r\nContent-Type: text/plain\r\n"
        'Content-Disposition: attachment; filename="a.txt"\r\n\r\n'
        "attached net-30 payment\r\n--B--\r\n"
    ).encode()
    blocks, meta, pages = EmailParser().parse(raw, "m.eml")
    assert "attachments" in meta and len(meta["attachments"]) == 1
    assert meta["attachments"][0]["filename"] == "a.txt"


def test_ingest_service_routes_by_extension_and_hashes():
    svc = IngestService()
    doc = svc.ingest_file(TERM_SHEET, DocRole.DEAL_SOURCE)
    assert doc.format == "txt"
    assert doc.role == DocRole.DEAL_SOURCE
    assert doc.sha256 == sha256_bytes(TERM_SHEET.read_bytes())
    assert doc.blocks


def test_ingest_email_folds_attachment_text_into_blocks():
    raw = (
        "From: a@x\r\nTo: b@y\r\nSubject: t\r\n"
        'Content-Type: multipart/mixed; boundary="B"\r\n\r\n'
        "--B\r\nContent-Type: text/plain\r\n\r\nmain body\r\n"
        "--B\r\nContent-Type: text/plain\r\n"
        'Content-Disposition: attachment; filename="a.txt"\r\n\r\n'
        "liability cap required\r\n--B--\r\n"
    )
    svc = IngestService()
    doc = svc.ingest_bytes(raw.encode(), "m.eml", DocRole.DEAL_SOURCE)
    joined = doc.full_text().lower()
    assert "main body" in joined
    assert "liability cap required" in joined  # attachment recursively folded in
