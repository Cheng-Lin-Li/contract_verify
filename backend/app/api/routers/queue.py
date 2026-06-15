"""Attorney queue router: list + act on flagged items (3-month · SKELETON)."""
from __future__ import annotations
from typing import Any


def list_queue(assigned_to: str | None = None,
               sla_state: str | None = None) -> Any:
    """GET /api/queue -> list[QueueItemOut]. Filter by assignee / SLA state."""
    raise NotImplementedError


def act_on_item(queue_id: str, payload: Any) -> Any:
    """POST /api/queue/{queue_id}/action -> QueueItemOut.

    Apply an attorney decision (approve/reject/escalate/add_to_playbook),
    record it to the audit trail, and stop the SLA clock.
    """
    raise NotImplementedError
