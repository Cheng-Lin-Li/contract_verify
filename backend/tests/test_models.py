"""Tests for the core data model (TDD §4-5): serialization and hashing."""

from __future__ import annotations

from app.core.enums import DocRole, Layer, PlaybookRule, Priority
from app.core.models import (
    CIRBlock,
    CIRDocument,
    ReferenceItem,
    SourceRef,
    VerificationResult,
    new_uuid,
    sha256_bytes,
)


def test_new_uuid_is_unique():
    assert new_uuid() != new_uuid()


def test_sha256_is_stable():
    assert sha256_bytes(b"abc") == sha256_bytes(b"abc")
    assert sha256_bytes(b"abc") != sha256_bytes(b"abd")


def test_cir_document_full_text_joins_blocks():
    doc = CIRDocument(
        role=DocRole.CONTRACT, format="txt",
        blocks=[CIRBlock(block_id="b-001", type="paragraph", page=1, text="one"),
                CIRBlock(block_id="b-002", type="paragraph", page=1, text="two")],
    )
    assert "one" in doc.full_text() and "two" in doc.full_text()


def test_reference_item_to_dict_serialises_enums():
    item = ReferenceItem(
        item_id="pb-1", layer=Layer.PLAYBOOK, text="x", type="liability",
        priority=Priority.CRITICAL, rule=PlaybookRule.MUST_HAVE,
        source_ref=SourceRef(doc_id="d", block_id="b-001", page=1),
    )
    d = item.to_dict()
    assert d["layer"] == 2
    assert d["priority"] == "Critical"
    assert d["rule"] == "must_have"
    assert d["source_ref"]["block_id"] == "b-001"


def test_verification_result_rounds_confidence():
    res = VerificationResult(item_id="r-1", layer=Layer.REQUIREMENTS, status="Covered",
                             confidence=0.123456)
    assert res.to_dict()["confidence"] == 0.1235
