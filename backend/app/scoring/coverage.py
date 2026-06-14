"""Coverage Score -- the Layer-1 headline metric (TDD §9 / PRD §6.1).

    CVS = Σ(priority_weight · coverage_credit) / Σ priority_weight × 100

``priority_weight`` and ``coverage_credit`` come from
:mod:`app.core.enums`. A ``Contradicted`` item scores zero credit *and* forces an
attorney flag (handled by the routing layer, not here).
"""

from __future__ import annotations

from dataclasses import dataclass

from app.core.enums import COVERAGE_CREDIT, PRIORITY_WEIGHT, L1Status, Layer, Priority
from app.core.models import ReferenceItem, VerificationResult


@dataclass
class CoverageBreakdown:
    """Coverage score plus the per-status counts that produced it."""

    score: float
    counts: dict[str, int]
    weighted_total: float
    weighted_covered: float


def _credit_for(status: str) -> float:
    """Return the coverage credit for a Layer-1 status string (0.0 if unknown)."""
    try:
        return COVERAGE_CREDIT[L1Status(status)]
    except (ValueError, KeyError):
        return 0.0


def coverage_score(
    items: list[ReferenceItem],
    results: list[VerificationResult],
) -> CoverageBreakdown:
    """Compute the priority-weighted Coverage Score over Layer-1 items.

    Args:
        items: All reference items (used to look up each item's priority).
        results: Verification results; only Layer-1 results are scored.

    Returns:
        A :class:`CoverageBreakdown`. ``score`` is 0.0 when there are no
        Layer-1 items.
    """
    priority_by_id: dict[str, Priority] = {
        it.item_id: it.priority for it in items if it.layer is Layer.REQUIREMENTS
    }
    counts: dict[str, int] = {}
    weighted_total = 0.0
    weighted_covered = 0.0

    for res in results:
        if res.layer is not Layer.REQUIREMENTS:
            continue
        counts[res.status] = counts.get(res.status, 0) + 1
        weight = PRIORITY_WEIGHT.get(priority_by_id.get(res.item_id, Priority.MEDIUM), 2)
        weighted_total += weight
        weighted_covered += weight * _credit_for(res.status)

    score = round((weighted_covered / weighted_total) * 100, 2) if weighted_total else 0.0
    return CoverageBreakdown(
        score=score,
        counts=counts,
        weighted_total=weighted_total,
        weighted_covered=round(weighted_covered, 4),
    )
