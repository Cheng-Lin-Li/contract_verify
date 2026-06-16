"""Routing rules: which results go to the attorney queue (3-month · SKELETON).

Wraps the MVP gate (app/scoring/gate.py) to decide routing and assignment.
"""

from __future__ import annotations

from typing import Any


def route_results(items: list[Any], results: list[Any], *, risk: int,
                  settings: Any) -> list[dict[str, Any]]:
    """Return the set of results to route to the attorney queue, with reasons.

    Triggers (mirrors the gate): Critical L1 Missing/Contradicted, L2 Violation,
    core L3 Missing, Risk >= threshold, or any determination below the
    confidence threshold.
    """
    raise NotImplementedError


def assign(queue_item: Any, attorneys: list[Any]) -> str:
    """Pick an assignee (load-balanced / round-robin). Return a user id."""
    raise NotImplementedError
