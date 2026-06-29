"""TDD spec: attorney-queue SLA countdown (app/queue/sla.py)."""

from __future__ import annotations

from datetime import datetime, timedelta


from app.queue import sla
from tests.three_month._spec import skip_until_implemented


@skip_until_implemented
def test_due_at_adds_sla_window():
    created = datetime(2026, 6, 1, 9, 0, 0)
    assert sla.due_at(created, sla_hours=24) == created + timedelta(hours=24)


@skip_until_implemented
def test_sla_state_thresholds():
    created = datetime(2026, 6, 1, 9, 0, 0)
    due = sla.due_at(created, 10)
    assert sla.sla_state(created + timedelta(hours=1), due) == "ok"
    assert sla.sla_state(created + timedelta(hours=9), due) == "warn"   # >=80%
    assert sla.sla_state(created + timedelta(hours=11), due) == "breach"


@skip_until_implemented
def test_reminders_due_at_milestones():
    created = datetime(2026, 6, 1, 9, 0, 0)
    due = sla.due_at(created, 10)
    assert "breach" in sla.reminders_due(created + timedelta(hours=11), due)
