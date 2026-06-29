"""SLA countdown for queued items (3-month scope).

Every attorney-queue item carries a deadline (``due_at``) derived from when it
was created plus the configured SLA window. The queue UI and the reminder
service classify an item's health by how much of that window has elapsed:

* ``ok``     — comfortably inside the window,
* ``warn``   — at or past 80% elapsed (the final 20% before the deadline),
* ``breach`` — the deadline has passed.

The window is a single global value (``QUEUE_SLA_HOURS``); ``sla_state`` and
``reminders_due`` read it from settings so they need only ``now`` and ``due``.
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Literal

#: Fractions of the window elapsed at which a reminder fires (besides breach).
_REMINDER_MILESTONES = (("50", 0.50), ("80", 0.80))

#: Elapsed fraction at which an item moves from ``ok`` to ``warn``.
_WARN_AT = 0.80


def _window_hours() -> int:
    """Return the configured global SLA window in hours."""
    from app.config import get_settings
    return get_settings().queue_sla_hours


def due_at(created_at: datetime, sla_hours: int) -> datetime:
    """Return the SLA deadline for an item created at ``created_at``."""
    return created_at + timedelta(hours=sla_hours)


def sla_state(now: datetime, due: datetime) -> Literal["ok", "warn", "breach"]:
    """Classify SLA health: warn at 80% elapsed, breach past the deadline."""
    if now >= due:
        return "breach"
    window = timedelta(hours=_window_hours())
    warn_at = due - window * (1.0 - _WARN_AT)
    return "warn" if now >= warn_at else "ok"


def reminders_due(now: datetime, due: datetime) -> list[str]:
    """Return which reminders (50%/80%/breach) are now due for an item.

    Milestones are cumulative: an item past the deadline returns the earlier
    milestones too, so a late escalation still reflects every threshold crossed.
    """
    window = timedelta(hours=_window_hours())
    fired: list[str] = []
    for label, fraction in _REMINDER_MILESTONES:
        if now >= due - window * (1.0 - fraction):
            fired.append(label)
    if now >= due:
        fired.append("breach")
    return fired
