"""Routing rules: which results go to the attorney queue (3-month scope).

Wraps the MVP gate (app/scoring/gate.py) so routing and the auto-confirm gate
share one source of truth. :func:`route_results` turns the gate's flagged
item ids into queue-ready records (item, layer, status, reason, risk);
:func:`assign` picks the least-loaded attorney for an item.
"""

from __future__ import annotations

from typing import Any

from app.scoring.gate import evaluate_gate


def _layer_value(layer: Any) -> int:
    """Return a layer as a plain int (``Layer`` is an int enum)."""
    return int(getattr(layer, "value", layer) or 0)


def route_results(items: list[Any], results: list[Any], *, risk: int,
                  settings: Any) -> list[dict[str, Any]]:
    """Return the set of results to route to the attorney queue, with reasons.

    Triggers (mirrors the gate): Critical L1 Missing/Contradicted, L2 Violation,
    core L3 Missing, Risk >= threshold, or any determination below the
    confidence threshold.
    """
    decision = evaluate_gate(
        items, results, risk,
        cs_human_review_threshold=settings.cs_human_review_threshold,
        risk_attorney_threshold=settings.risk_attorney_threshold,
    )
    result_by_id = {r.item_id: r for r in results}

    routed: list[dict[str, Any]] = []
    for item_id in decision.attorney_items:
        res = result_by_id.get(item_id)
        # Attach the gate's own reasons that name this item; fall back generically.
        reasons = [r for r in decision.blocking_reasons if item_id in r]
        routed.append({
            "item_id": item_id,
            "layer": _layer_value(res.layer) if res else 0,
            "status": getattr(res, "status", "") if res else "",
            "reason": "; ".join(reasons) if reasons else "Flagged for attorney review",
            "risk_score": risk,
        })
    return routed


def assign(queue_item: Any, attorneys: list[Any]) -> str:
    """Pick an assignee (least-loaded, ties broken by order). Return a user id.

    Accepts attorneys as bare id strings or objects exposing ``id``/``username``
    and an optional ``load`` (current open-item count); the lowest load wins.
    """
    if not attorneys:
        return ""

    def _id(a: Any) -> str:
        return a if isinstance(a, str) else (getattr(a, "id", None)
                                             or getattr(a, "username", "") or "")

    def _load(a: Any) -> int:
        return 0 if isinstance(a, str) else int(getattr(a, "load", 0) or 0)

    return _id(min(attorneys, key=_load))
