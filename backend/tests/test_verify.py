"""Tests for the verification matcher (TDD §8) using the FakeProvider.

Confirms cross-layer verification, the superseded short-circuit (no model call),
and that every result carries a confidence and cited clause evidence.
"""

from __future__ import annotations

from app.core.enums import DocRole, Layer, PlaybookRule, Priority
from app.core.models import CIRBlock, CIRDocument, ReferenceItem
from app.references.reconcile import ReconcileResult
from app.verify.matcher import VerificationMatcher

from tests.helpers import fake_provider


def _contract():
    return CIRDocument(
        role=DocRole.CONTRACT,
        format="txt",
        blocks=[
            CIRBlock(block_id="b-001", type="paragraph", page=1,
                     text="Payment on net-45 day terms from the invoice date."),
            CIRBlock(block_id="b-002", type="paragraph", page=1,
                     text="Mutual confidentiality survives termination for three years."),
        ],
    )


def test_matcher_covers_present_requirement():
    item = ReferenceItem(item_id="r-1", layer=Layer.REQUIREMENTS,
                         text="payment net-45 invoice terms", type="payment",
                         priority=Priority.CRITICAL)
    res = VerificationMatcher(fake_provider()).verify_item(item, _contract())
    assert res.status == "Covered"
    assert 0.0 <= res.confidence <= 1.0
    assert res.matched_clause_ids  # cited a clause


def test_matcher_flags_missing_requirement():
    item = ReferenceItem(item_id="r-2", layer=Layer.REQUIREMENTS,
                         text="data deletion within thirty days of termination", type="data")
    res = VerificationMatcher(fake_provider()).verify_item(item, _contract())
    assert res.status in ("Missing", "Partial")


def test_matcher_short_circuits_superseded_without_model():
    item = ReferenceItem(item_id="r-1", layer=Layer.REQUIREMENTS, text="net-30", type="payment")
    rec = ReconcileResult(items=[item], superseded={"r-1": "r-9"})
    res = VerificationMatcher(fake_provider()).verify_item(item, _contract(), reconcile=rec)
    assert res.status == "Superseded"
    assert res.evidence.get("superseded_by") == "r-9"


def test_matcher_downgrades_covered_to_partial_on_value_conflict():
    # Requirement names a $500,000 cap; the matched clause names $250,000.
    contract = CIRDocument(
        role=DocRole.CONTRACT, format="txt",
        blocks=[CIRBlock(block_id="b-001", type="paragraph", page=1,
                         text="Aggregate liability is capped at $250,000 under this agreement.")],
    )
    item = ReferenceItem(item_id="r-cap", layer=Layer.REQUIREMENTS,
                         text="liability capped at $500,000", type="liability",
                         priority=Priority.CRITICAL)
    res = VerificationMatcher(fake_provider()).verify_item(item, contract)
    assert res.status == "Partial"
    assert "Value check" in res.notes


def test_matcher_keeps_covered_when_values_agree():
    contract = CIRDocument(
        role=DocRole.CONTRACT, format="txt",
        blocks=[CIRBlock(block_id="b-001", type="paragraph", page=1,
                         text="Payment on net-45 day terms from the invoice date.")],
    )
    item = ReferenceItem(item_id="r-pay", layer=Layer.REQUIREMENTS,
                         text="payment net-45 invoice terms", type="payment")
    res = VerificationMatcher(fake_provider()).verify_item(item, contract)
    assert res.status == "Covered"


def test_matcher_verify_all_spans_three_layers():
    items = [
        ReferenceItem(item_id="r-1", layer=Layer.REQUIREMENTS, text="net-45 payment", type="payment"),
        ReferenceItem(item_id="pb-1", layer=Layer.PLAYBOOK, text="confidentiality mutual",
                      type="confidentiality", rule=PlaybookRule.PREFERRED),
        ReferenceItem(item_id="st-1", layer=Layer.STANDARD_TERMS, text="indemnification clause",
                      type="indemnity"),
    ]
    results = VerificationMatcher(fake_provider()).verify_all(items, _contract())
    layers = {int(r.layer) for r in results}
    assert layers == {1, 2, 3}
    assert len(results) == 3
