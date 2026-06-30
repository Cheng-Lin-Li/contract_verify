"""Sample demo data so the SPA (and the API specs) have something to show.

Seeds one verified contract (``known-id``) with a unified report and two
attorney-queue items (``q-1``, ``q-2``). Gated by ``SEED_DEMO_DATA`` and
idempotent — production deployments set ``SEED_DEMO_DATA=false``.
"""

from __future__ import annotations

from datetime import datetime, timezone

from app.config import get_settings
from app.queue import sla as sla_mod

KNOWN_CONTRACT_ID = "known-id"

_ROWS = [
    {"item_id": "r-1", "layer": 1, "type": "payment", "priority": "Critical",
     "status": "Missing", "confidence": 0.82,
     "requirement_text": "Payment due on net-30 terms.",
     "matched_clause_ids": [], "notes": "No matching payment-terms clause found."},
    {"item_id": "r-2", "layer": 1, "type": "term", "priority": "High",
     "status": "Covered", "confidence": 0.91,
     "requirement_text": "Initial term of 24 months.",
     "matched_clause_ids": ["b-002"], "notes": ""},
    {"item_id": "pb-1", "layer": 2, "type": "liability", "priority": "High",
     "status": "Violation", "confidence": 0.88,
     "requirement_text": "Liability must be capped at fees paid.",
     "matched_clause_ids": ["b-003"], "notes": "Liability is uncapped."},
    {"item_id": "std-1", "layer": 3, "type": "governing_law",
     "status": "Present", "confidence": 0.95,
     "requirement_text": "Governing-law clause present.",
     "matched_clause_ids": ["b-004"], "notes": ""},
]

_REPORT = {
    "coverage_score": 72.5,
    "risk_score": 55,
    "playbook_compliance": {"Compliant": 2, "Deviation": 0, "Violation": 1},
    "standard_terms_completeness": {"Present": 3, "Missing": 1, "Non-standard": 0},
    "auto_confirm": False,
    "blocking_reasons": ["Critical requirement r-1 is Missing",
                         "Playbook violation on pb-1"],
    "attorney_queue": ["r-1", "pb-1"],
    "rows": _ROWS,
}

_CIR = {
    "doc_id": KNOWN_CONTRACT_ID, "role": "contract", "format": "txt",
    "sha256": "", "pages": 1, "metadata": {"filename": "sample_msa.txt"},
    "blocks": [
        {"block_id": "b-002", "type": "paragraph", "page": 1,
         "text": "This Agreement has an initial term of twenty-four (24) months."},
        {"block_id": "b-003", "type": "paragraph", "page": 1,
         "text": "The Provider's liability under this Agreement shall be unlimited."},
        {"block_id": "b-004", "type": "paragraph", "page": 1,
         "text": "This Agreement is governed by the laws of the State of Delaware."},
    ],
}


def seed_demo_data(reset: bool = False) -> None:
    """Create the sample contract + queue items if absent (or with ``reset``)."""
    from app.api import state_store

    if not reset and state_store.load_report(KNOWN_CONTRACT_ID) is not None:
        return

    state_store.save_report(KNOWN_CONTRACT_ID, {"report": _REPORT, "entities": {}})
    state_store.save_cir(KNOWN_CONTRACT_ID, _CIR)

    now = datetime.now(tz=timezone.utc)
    due = sla_mod.due_at(now, get_settings().queue_sla_hours).isoformat()
    state_store.save_queue_items([
        {"queue_id": "q-1", "contract_id": KNOWN_CONTRACT_ID, "item_id": "r-1",
         "layer": 1, "status": "Missing", "reason": "Critical requirement r-1 is Missing",
         "risk_score": 55, "sla_due_at": due, "sla_state": "ok",
         "assigned_to": None, "attorney_action": None, "resolved": False},
        {"queue_id": "q-2", "contract_id": KNOWN_CONTRACT_ID, "item_id": "pb-1",
         "layer": 2, "status": "Violation", "reason": "Playbook violation on pb-1",
         "risk_score": 55, "sla_due_at": due, "sla_state": "ok",
         "assigned_to": None, "attorney_action": None, "resolved": False},
    ])
