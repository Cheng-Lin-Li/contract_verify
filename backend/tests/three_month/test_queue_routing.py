"""TDD spec: routing results to the attorney queue (app/queue/routing.py)."""

from __future__ import annotations

import pytest

from app.queue import routing
from tests.three_month._spec import skip_until_implemented


@skip_until_implemented
def test_routes_critical_missing_and_violations(make_items_and_results, settings):
    items, results = make_items_and_results(
        critical_missing=True, playbook_violation=True
    )
    routed = routing.route_results(items, results, risk=70, settings=settings)
    reasons = " ".join(r["reason"] for r in routed)
    assert routed and ("Critical" in reasons or "Violation" in reasons)


@skip_until_implemented
def test_clean_run_routes_nothing(make_items_and_results, settings):
    items, results = make_items_and_results(clean=True)
    assert routing.route_results(items, results, risk=0, settings=settings) == []
