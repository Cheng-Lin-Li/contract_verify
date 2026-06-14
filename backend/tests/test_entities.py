"""Tests for contract-entity extraction and value-conflict grounding."""

from __future__ import annotations

from app.core.enums import DocRole, Layer
from app.core.models import CIRBlock, CIRDocument
from app.references.entities import (
    extract_contract_entities,
    salient_values,
    value_conflict,
)


def _doc(*texts: str) -> CIRDocument:
    blocks = [CIRBlock(block_id=f"b-{i:03d}", type="paragraph", page=1, text=t)
              for i, t in enumerate(texts, start=1)]
    return CIRDocument(role=DocRole.CONTRACT, format="txt", blocks=blocks)


# --- salient_values -------------------------------------------------------

def test_salient_values_amounts_and_multipliers():
    v = salient_values("The cap is $500,000 and the bonus is $1.5m.")
    assert 500000.0 in v["amounts"]
    assert 1500000.0 in v["amounts"]


def test_salient_values_net_terms_and_percent():
    v = salient_values("Payment net-45; uptime 99.9%.")
    assert 45 in v["net_terms"]
    assert 99.9 in v["percentages"]


# --- value_conflict -------------------------------------------------------

def test_value_conflict_detects_differing_amount():
    reason = value_conflict("cap limited to $500,000", "aggregate liability capped at $250,000")
    assert reason and "amount" in reason


def test_value_conflict_detects_differing_net_term():
    reason = value_conflict("payment net-30", "payment on net-45 terms")
    assert reason and "net-term" in reason


def test_value_conflict_none_when_values_match():
    assert value_conflict("payment net-45", "net-45 from invoice date") is None


def test_value_conflict_none_when_clause_has_no_value():
    # Absence in the clause is not a conflict (the LLM decides coverage).
    assert value_conflict("cap at $500,000", "liability is capped at fees paid") is None


# --- entity extraction ----------------------------------------------------

def test_extract_entities_party_law_and_values():
    doc = _doc(
        "MASTER SERVICES AGREEMENT between Acme Corp and the Customer.",
        "Payment net-45; fees of $250,000; uptime 99.9%.",
        "This agreement is governed by the laws of the State of California.",
    )
    e = extract_contract_entities(doc)
    party_values = {p["value"] for p in e["parties"]}
    assert "Acme Corp" in party_values
    assert "Customer" in party_values
    assert e["governing_law"] == "California"
    assert any(a["value"].replace(" ", "") == "$250,000" for a in e["amounts"])
    assert e["net_terms"] and e["net_terms"][0]["value"] == "net-45"


def test_extract_entities_each_cites_a_block():
    doc = _doc("Fees of $1,000 due on net-30 terms.")
    e = extract_contract_entities(doc)
    assert all("block_id" in a for a in e["amounts"])
    assert e["amounts"][0]["block_id"] == "b-001"


def test_extract_entities_empty_contract():
    e = extract_contract_entities(_doc("Hello world."))
    assert e["parties"] == [] and e["amounts"] == [] and e["governing_law"] is None
