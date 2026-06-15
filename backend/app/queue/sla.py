"""SLA countdown for queued items (3-month scope · SKELETON)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal


def due_at(created_at: datetime, sla_hours: int) -> datetime:
    """Return the SLA deadline for an item created at ``created_at``."""
    raise NotImplementedError


def sla_state(now: datetime, due: datetime) -> Literal["ok", "warn", "breach"]:
    """Classify SLA health: warn at 80% elapsed, breach past the deadline."""
    raise NotImplementedError


def reminders_due(now: datetime, due: datetime) -> list[str]:
    """Return which reminders (50%/80%/breach) are now due for an item."""
    raise NotImplementedError
