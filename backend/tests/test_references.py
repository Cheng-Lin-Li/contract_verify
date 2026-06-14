"""Tests for reference reconciliation and library loaders (TDD §6, §8).

Covers Layer-1 dedupe + payment supersession, and the Layer-2/3 loaders
(including the Layer-3 contract-type scoping that stands in for retrieval).
"""

from __future__ import annotations

from app.core.enums import Layer, PlaybookRule
from app.core.models import ReferenceItem
from app.references.loaders import load_playbook, load_standard_terms
from app.references.reconcile import reconcile_requirements, superseded_status_for

from tests.helpers import PLAYBOOK_DIR, STDTERMS_DIR


def _req(item_id, text, type_="general"):
    return ReferenceItem(item_id=item_id, layer=Layer.REQUIREMENTS, text=text, type=type_)


def test_reconcile_dedupes_identical_text():
    items = [_req("r-1", "Net-30 payment terms."), _req("r-2", "Net-30 payment terms.")]
    result = reconcile_requirements(items)
    assert len(result.items) == 1


def test_reconcile_supersedes_conflicting_payment_terms():
    items = [
        _req("r-1", "Payment terms shall be net-30 days.", "payment"),
        _req("r-2", "Payment terms shall be net-45 days.", "payment"),
    ]
    result = reconcile_requirements(items)
    # Later net-45 supersedes earlier net-30.
    assert result.superseded.get("r-1") == "r-2"
    assert superseded_status_for("r-1", result) is not None
    assert superseded_status_for("r-2", result) is None


def test_reconcile_keeps_non_conflicting_terms():
    items = [
        _req("r-1", "Payment net-30.", "payment"),
        _req("r-2", "Mutual confidentiality.", "confidentiality"),
    ]
    result = reconcile_requirements(items)
    assert result.superseded == {}
    assert len(result.items) == 2


def test_load_playbook_assigns_rules():
    items = load_playbook(PLAYBOOK_DIR)
    assert items and all(i.layer is Layer.PLAYBOOK for i in items)
    assert any(i.rule is PlaybookRule.MUST_NOT_HAVE for i in items)
    assert any(i.rule is PlaybookRule.MUST_HAVE for i in items)


def test_load_standard_terms_scopes_by_contract_type():
    services = load_standard_terms(STDTERMS_DIR, contract_type="services")
    assert services and all(i.layer is Layer.STANDARD_TERMS for i in services)
    # An unrelated contract type should keep only globally-scoped (untyped) items.
    other = load_standard_terms(STDTERMS_DIR, contract_type="nda")
    assert len(other) <= len(services)
