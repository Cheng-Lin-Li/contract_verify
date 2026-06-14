"""Tests for the deterministic FakeProvider (offline stand-in for a real model).

The fake provider underpins the whole offline test/demo path, so its contract
(JSON shape, layer-aware verify vocabulary) is pinned here.
"""

from __future__ import annotations

import json

from tests.helpers import fake_provider


EXTRACT_PROMPT = (
    "[TASK:EXTRACT]\n[SOURCE]\n"
    "Payment terms shall be net-30 from invoice date.\n"
    "Aggregate liability must be capped at fees paid.\n"
    "hi\n"  # too short -> ignored
    "[/SOURCE]\n"
)


def test_fake_extract_returns_requirement_items():
    out = json.loads(fake_provider().complete(EXTRACT_PROMPT))
    texts = " ".join(o["text"].lower() for o in out)
    assert "net-30" in texts
    assert "liability" in texts
    assert all("item_id" in o and "type" in o for o in out)


def test_fake_extract_marks_critical_terms():
    out = json.loads(fake_provider().complete(EXTRACT_PROMPT))
    crit = [o for o in out if o["priority"] == "Critical"]
    assert crit  # net-/liability lines are Critical


def _verify_prompt(layer_phrase, requirement, clauses):
    return (
        f"[TASK:VERIFY]\n{layer_phrase}\n"
        f"[REQUIREMENT]\n{requirement}\n[/REQUIREMENT]\n"
        f"[SOURCE]\n{clauses}\n[/SOURCE]\n"
    )


def test_fake_verify_requirement_vocab():
    p = _verify_prompt("", "mutual confidentiality survives termination",
                       "The parties agree to mutual confidentiality that survives termination.")
    out = json.loads(fake_provider().complete(p))
    assert out["status"] in ("Covered", "Partial", "Missing", "Contradicted")
    assert out["status"] == "Covered"


def test_fake_verify_playbook_vocab():
    p = _verify_prompt("The REQUIREMENT is a company playbook position with rule must_have.",
                       "liability capped at fees paid", "no relevant clause here")
    out = json.loads(fake_provider().complete(p))
    assert out["status"] in ("Compliant", "Deviation", "Violation")


def test_fake_verify_standard_term_vocab():
    p = _verify_prompt("The REQUIREMENT is a standard market term expected in this contract type.",
                       "indemnification clause for third-party claims", "unrelated text")
    out = json.loads(fake_provider().complete(p))
    assert out["status"] in ("Present", "Non-standard", "Missing")


def test_fake_unknown_task_returns_empty_object():
    assert fake_provider().complete("no markers here") == "{}"
