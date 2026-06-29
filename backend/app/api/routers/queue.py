"""Attorney queue router: list (grouped + enriched) + act on flagged items."""

from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_role
from app.api import state_store
from app.api.schemas import (
    ContractQueueGroupOut, QueueActionRequest, QueueClauseOut,
    QueueItemDetailOut, QueueItemOut,
)
from app.queue.attorney_queue import AttorneyQueue

router = APIRouter()

_REVIEWERS = ("attorney", "gc_team", "admin")


def _queue() -> AttorneyQueue:
    """The attorney queue backed by the demo state store."""
    return AttorneyQueue(state_store)


def _sla_state(sla_due_at: str | None) -> str:
    if not sla_due_at:
        return "ok"
    try:
        due = datetime.fromisoformat(sla_due_at)
        if due.tzinfo is None:
            due = due.replace(tzinfo=timezone.utc)
        now = datetime.now(tz=timezone.utc)
        if now > due:
            return "breach"
        if (due - now).total_seconds() < 86400:  # < 24h
            return "warn"
    except ValueError:
        pass
    return "ok"


def _enrich_and_group(raw_items: list[dict]) -> list[ContractQueueGroupOut]:
    """Enrich raw queue items with requirement text and contract clause text,
    then group them by contract.
    """
    # Group by contract_id, preserving insertion order.
    by_contract: dict[str, list[dict]] = {}
    for it in raw_items:
        cid = it.get("contract_id", "")
        by_contract.setdefault(cid, []).append(it)

    groups: list[ContractQueueGroupOut] = []
    for contract_id, items in by_contract.items():
        # Load the report to get requirement_text and matched_clause_ids.
        payload = state_store.load_report(contract_id)
        row_map: dict[str, dict] = {}
        if payload:
            for row in payload.get("report", {}).get("rows", []):
                row_map[row["item_id"]] = row

        # Load the contract CIR to resolve block text.
        cir = state_store.load_cir(contract_id)
        block_map: dict[str, dict] = {}
        contract_filename = contract_id[:8]
        if cir:
            for block in cir.get("blocks", []):
                block_map[block["block_id"]] = block
            contract_filename = (cir.get("metadata") or {}).get("filename", contract_id[:8])

        enriched: list[QueueItemDetailOut] = []
        for it in items:
            item_id = it.get("item_id", "")
            row = row_map.get(item_id, {})

            matched_clauses = [
                QueueClauseOut(
                    block_id=bid,
                    text=block_map[bid].get("text", ""),
                    page=block_map[bid].get("page", 1),
                )
                for bid in row.get("matched_clause_ids", [])
                if bid in block_map
            ]

            enriched.append(QueueItemDetailOut(
                queue_id=it.get("queue_id", ""),
                contract_id=contract_id,
                item_id=item_id,
                layer=it.get("layer", 0),
                status=it.get("status", ""),
                reason=it.get("reason", ""),
                risk_score=it.get("risk_score", 0),
                sla_due_at=it.get("sla_due_at"),
                sla_state=_sla_state(it.get("sla_due_at")),
                assigned_to=it.get("assigned_to"),
                requirement_text=row.get("requirement_text", ""),
                matched_clauses=matched_clauses,
            ))

        risk_score = max((it.get("risk_score", 0) for it in items), default=0)
        groups.append(ContractQueueGroupOut(
            contract_id=contract_id,
            contract_filename=contract_filename,
            risk_score=risk_score,
            items=enriched,
        ))

    return groups


@router.get("", response_model=list[ContractQueueGroupOut])
def list_queue(user=Depends(require_role(*_REVIEWERS))) -> list[ContractQueueGroupOut]:
    """Return unresolved queue items grouped by contract, enriched with clause text."""
    return _enrich_and_group(_queue().list())


@router.post("/{queue_id}/action", response_model=QueueItemOut)
def act_on_item(
    queue_id: str, payload: QueueActionRequest,
    user=Depends(require_role(*_REVIEWERS)),
) -> QueueItemOut:
    updated = _queue().apply_action(
        queue_id, payload.action, actor=user.username, comment=payload.comment,
    )
    if updated is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown queue item")
    return QueueItemOut(**{k: updated.get(k) for k in QueueItemOut.model_fields})
