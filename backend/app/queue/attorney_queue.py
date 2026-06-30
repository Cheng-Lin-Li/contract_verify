"""Attorney review queue store (3-month scope).

Persists items routed for attorney review, builds the context packet (sources,
report, scores, matched clauses) and records decisions to the immutable audit
trail. Backed by a ``store`` that provides the demo state-store surface
(``load_queue_items``/``save_queue_items``/``update_queue_item`` plus
``load_report``/``load_cir``/``load_contract_sources``); ``app.api.state_store``
satisfies it directly, and a Postgres-backed store can be swapped in later.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.audit.audit_log import AuditLog
from app.config import get_settings
from app.queue import sla as sla_mod


def _queue_id(contract_id: str, item_id: str) -> str:
    """Deterministic queue id so re-running a contract updates, not duplicates."""
    return f"{contract_id}:{item_id}"


def _as_dt(value: Any) -> datetime | None:
    """Parse an ISO string / datetime into a tz-aware datetime (UTC)."""
    if isinstance(value, datetime):
        dt = value
    elif isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value)
        except ValueError:
            return None
    else:
        return None
    return dt.replace(tzinfo=timezone.utc) if dt.tzinfo is None else dt


class AttorneyQueue:
    """CRUD + decisioning over queue items."""

    def __init__(self, store: Any) -> None:
        self._store = store

    # -- creation ------------------------------------------------------------

    def enqueue(self, contract_id: str, item_id: str, *, reason: str,
                risk_score: int, sla_due_at: Any) -> str:
        """Create (or refresh) a queue item; return its queue_id.

        Layer/status are read from the contract's persisted report row so the
        queue carries the verification verdict without the caller repeating it.
        """
        queue_id = _queue_id(contract_id, item_id)
        due = sla_due_at.isoformat() if isinstance(sla_due_at, datetime) else sla_due_at
        row = self._report_row(contract_id, item_id)
        item = {
            "queue_id": queue_id,
            "contract_id": contract_id,
            "item_id": item_id,
            "layer": row.get("layer", 0),
            "status": row.get("status", ""),
            "reason": reason,
            "risk_score": risk_score,
            "sla_due_at": due,
            "sla_state": "ok",
            "assigned_to": None,
            "attorney_action": None,
            "resolved": False,
        }
        self._store.save_queue_items([item])
        return queue_id

    def _report_row(self, contract_id: str, item_id: str) -> dict[str, Any]:
        """Return the report row for ``item_id`` (empty dict if not found)."""
        payload = self._store.load_report(contract_id) or {}
        rows = payload.get("report", {}).get("rows", [])
        return next((r for r in rows if r.get("item_id") == item_id), {})

    # -- reads ---------------------------------------------------------------

    def _live_sla_state(self, item: dict[str, Any], now: datetime) -> str:
        due = _as_dt(item.get("sla_due_at"))
        return sla_mod.sla_state(now, due) if due else "ok"

    def list(self, *, assigned_to: str | None = None,
             sla_state: str | None = None) -> list[Any]:
        """Return unresolved queue items, with live SLA state, optionally filtered."""
        now = datetime.now(tz=timezone.utc)
        out: list[dict[str, Any]] = []
        for raw in self._store.load_queue_items():
            if raw.get("resolved"):
                continue
            state = self._live_sla_state(raw, now)
            if assigned_to is not None and raw.get("assigned_to") != assigned_to:
                continue
            if sla_state is not None and state != sla_state:
                continue
            out.append({**raw, "sla_state": state})
        return out

    def _find(self, queue_id: str) -> dict[str, Any] | None:
        return next((it for it in self._store.load_queue_items()
                     if it.get("queue_id") == queue_id), None)

    def context_packet(self, queue_id: str) -> dict[str, Any]:
        """Assemble the full review packet for one item (report row + clauses)."""
        item = self._find(queue_id)
        if item is None:
            return {}
        contract_id = item.get("contract_id", "")
        payload = self._store.load_report(contract_id) or {}
        report = payload.get("report", {})
        row = next((r for r in report.get("rows", [])
                    if r.get("item_id") == item.get("item_id")), {})

        cir = self._store.load_cir(contract_id) or {}
        block_map = {b["block_id"]: b for b in cir.get("blocks", [])}
        matched = [block_map[b] for b in row.get("matched_clause_ids", []) if b in block_map]

        sources = (self._store.load_contract_sources(contract_id)
                   if hasattr(self._store, "load_contract_sources") else [])
        return {
            "item": item,
            "requirement_text": row.get("requirement_text", ""),
            "status": row.get("status", item.get("status", "")),
            "matched_clauses": matched,
            "scores": {k: report.get(k) for k in
                       ("coverage_score", "risk_score", "auto_confirm")},
            "sources": sources,
        }

    # -- decisioning ---------------------------------------------------------

    def apply_action(self, queue_id: str, action: str, *, actor: str,
                     comment: str | None = None) -> Any:
        """Apply an attorney decision, audit it, and resolve the item."""
        updated = self._store.update_queue_item(
            queue_id, resolved=True, assigned_to=actor,
            attorney_action=action, comment=comment,
        )
        if updated is None:
            return None
        try:
            AuditLog(get_settings().audit_log_path).record(
                f"attorney_{action}",
                doc_id=updated.get("contract_id"),
                item_id=updated.get("item_id"),
                layer=updated.get("layer"),
                status=updated.get("status"),
                actor_role="attorney",
                details={"actor": actor, "comment": comment or ""},
            )
        except Exception:  # noqa: BLE001 - audit must not break the decision path
            pass
        return updated
