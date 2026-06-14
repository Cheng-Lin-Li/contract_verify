"""Append-only audit trail (TDD §13; MVP tier).

Every reference-to-clause link and model action is recorded. The MVP writes
newline-delimited JSON (JSONL) -- append-only by construction (the writer only
ever opens in append mode and never rewrites prior lines). The 3-month build
moves this to PostgreSQL with a ``BEFORE UPDATE/DELETE`` immutability trigger;
the :class:`AuditLog` interface is identical so callers do not change.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator, Optional


def _now_iso() -> str:
    """Return the current UTC time as an ISO-8601 string."""
    return datetime.now(timezone.utc).isoformat()


class AuditLog:
    """An append-only JSONL audit log."""

    def __init__(self, path: str | Path) -> None:
        """Open (creating parent dirs) the audit log at ``path``."""
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def record(
        self,
        event_type: str,
        *,
        doc_id: Optional[str] = None,
        item_id: Optional[str] = None,
        layer: Optional[int] = None,
        contract_clause_id: Optional[str] = None,
        status: Optional[str] = None,
        confidence: Optional[float] = None,
        risk_score: Optional[int] = None,
        model_name: Optional[str] = None,
        actor_role: str = "system",
        details: Optional[dict[str, Any]] = None,
    ) -> dict[str, Any]:
        """Append one immutable audit event and return it.

        Args:
            event_type: The action (``ingest``/``extract``/``match``/``score``/
                ``route``/``approve`` ...), mirroring the audit schema.
            doc_id, item_id, layer, contract_clause_id, status, confidence,
            risk_score, model_name, actor_role, details: Structured fields from
                the audit schema (TDD §13).

        Returns:
            The event dict that was written.
        """
        event = {
            "event_id": str(uuid.uuid4()),
            "occurred_at": _now_iso(),
            "actor_role": actor_role,
            "event_type": event_type,
            "layer": layer,
            "doc_id": doc_id,
            "item_id": item_id,
            "contract_clause_id": contract_clause_id,
            "status": status,
            "confidence": confidence,
            "risk_score": risk_score,
            "model_name": model_name,
            "details": details or {},
        }
        with self.path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(event, default=str) + "\n")
        return event

    def read_all(self) -> Iterator[dict[str, Any]]:
        """Yield every recorded event in write order.

        Yields nothing if the log does not yet exist.
        """
        if not self.path.exists():
            return
        with self.path.open("r", encoding="utf-8") as fh:
            for line in fh:
                line = line.strip()
                if line:
                    yield json.loads(line)

    def events_for(self, doc_id: str) -> list[dict[str, Any]]:
        """Return all events whose ``doc_id`` matches (the contract's run)."""
        return [e for e in self.read_all() if e.get("doc_id") == doc_id]
