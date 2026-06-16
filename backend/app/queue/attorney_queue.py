"""Attorney review queue store (3-month scope · SKELETON).

Persists items routed for attorney review, builds the context packet (sources,
report, scores, proposed redline, audit snapshot) and records decisions.
"""

from __future__ import annotations

from typing import Any


class AttorneyQueue:
    """CRUD + decisioning over queue items (SKELETON)."""

    def __init__(self, store: Any) -> None:
        raise NotImplementedError

    def enqueue(self, contract_id: str, item_id: str, *, reason: str,
                risk_score: int, sla_due_at: Any) -> str:
        """Create a queue item; return its queue_id."""
        raise NotImplementedError

    def list(self, *, assigned_to: str | None = None,
             sla_state: str | None = None) -> list[Any]:
        """Return queue items, optionally filtered."""
        raise NotImplementedError

    def context_packet(self, queue_id: str) -> dict[str, Any]:
        """Assemble the full review packet for one item."""
        raise NotImplementedError

    def apply_action(self, queue_id: str, action: str, *, actor: str,
                     comment: str | None = None) -> Any:
        """Apply an attorney decision, audit it, and resolve the item."""
        raise NotImplementedError
