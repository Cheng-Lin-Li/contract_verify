"""Reconciliation of Layer-1 requirements (TDD §8).

The MVP performs *basic dedupe* and a simple, transparent supersession pass:
near-identical asks are collapsed, and when two requirements of the same ``type``
conflict, the later (or binding) one wins and the earlier is marked superseded.
Full timestamp-driven supersession, contradiction detection and cross-layer
conflict are 3-month / backlog items (TDD §2 scope table) and are stubbed behind
the same function signature so they slot in without changing callers.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

from app.core.enums import L1Status
from app.core.models import ReferenceItem
from app.logging_setup import get_logger

log = get_logger("references.reconcile")


@dataclass
class ReconcileResult:
    """Output of reconciliation.

    Attributes:
        items: The surviving (deduped) requirement items.
        superseded: ``{item_id: superseding_item_id}`` for items overridden.
        notes: Human-readable notes describing what was reconciled.
    """

    items: list[ReferenceItem]
    superseded: dict[str, str] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


def _normalise(text: str) -> str:
    """Lowercase, collapse whitespace and strip punctuation for comparison."""
    return re.sub(r"[^a-z0-9 ]", "", text.lower()).strip()


def _net_term(text: str) -> int | None:
    """Return the N from a 'net-N' / 'net N' payment term if present, else None."""
    m = re.search(r"net[\s\-]?(\d{1,3})", text.lower())
    return int(m.group(1)) if m else None


def reconcile_requirements(items: list[ReferenceItem]) -> ReconcileResult:
    """Deduplicate near-identical requirements and apply basic supersession.

    Args:
        items: Extracted Layer-1 requirements, assumed in source order (earlier
            first), which the supersession heuristic relies on.

    Returns:
        A :class:`ReconcileResult`.
    """
    deduped: list[ReferenceItem] = []
    seen: dict[str, ReferenceItem] = {}
    result = ReconcileResult(items=[])

    for item in items:
        key = _normalise(item.text)
        if key in seen:
            result.notes.append(f"deduped {item.item_id} (== {seen[key].item_id})")
            continue
        seen[key] = item
        deduped.append(item)

    # Basic supersession: conflicting payment 'net-N' terms -> later wins.
    by_net: dict[str, ReferenceItem] = {}
    for item in deduped:
        n = _net_term(item.text)
        if n is None or item.type != "payment":
            continue
        prior = by_net.get("payment")
        if prior is not None and _net_term(prior.text) != n:
            # Later item supersedes earlier conflicting payment term.
            result.superseded[prior.item_id] = item.item_id
            result.notes.append(
                f"{item.item_id} (net-{n}) supersedes {prior.item_id} "
                f"(net-{_net_term(prior.text)})"
            )
        by_net["payment"] = item

    result.items = deduped
    log.info("reconciled", extra={"in": len(items), "out": len(deduped),
                                  "superseded": len(result.superseded)})
    return result


def superseded_status_for(item_id: str, reconcile: ReconcileResult) -> L1Status | None:
    """Return :attr:`L1Status.SUPERSEDED` if ``item_id`` was overridden, else ``None``."""
    return L1Status.SUPERSEDED if item_id in reconcile.superseded else None
