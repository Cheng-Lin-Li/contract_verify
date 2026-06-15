"""Attorney queue router: list + act on flagged items."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import require_role
from app.api import state_store
from app.api.schemas import QueueActionRequest, QueueItemOut

router = APIRouter()

# Only legal roles may see or action the queue.
_REVIEWERS = ("attorney", "gc_team", "admin")


@router.get("", response_model=list[QueueItemOut])
def list_queue(user=Depends(require_role(*_REVIEWERS))) -> list[QueueItemOut]:
    items = [it for it in state_store.load_queue_items() if not it.get("resolved")]
    return [QueueItemOut(**{k: it.get(k) for k in QueueItemOut.model_fields}) for it in items]


@router.post("/{queue_id}/action", response_model=QueueItemOut)
def act_on_item(
    queue_id: str, payload: QueueActionRequest,
    user=Depends(require_role(*_REVIEWERS)),
) -> QueueItemOut:
    updated = state_store.update_queue_item(
        queue_id, resolved=True, assigned_to=user.username,
    )
    if updated is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown queue item")
    return QueueItemOut(**{k: updated.get(k) for k in QueueItemOut.model_fields})
