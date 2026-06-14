"""Layer-2 compliance, Layer-3 completeness, and the supporting risk score.

These mirror TDD §9 / PRD §6.2-6.5. Compliance and completeness summarise the
per-item statuses for their layer; the Risk Score is a 0-100 aggregate of
playbook Violations and missing/non-standard core terms that contributes to
attorney routing.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.enums import Layer
from app.core.models import VerificationResult


@dataclass
class LayerSummary:
    """A per-status count summary for a single layer."""

    counts: dict[str, int] = field(default_factory=dict)

    def total(self) -> int:
        """Return the number of items summarised."""
        return sum(self.counts.values())

    def get(self, status: str) -> int:
        """Return the count for ``status`` (0 if absent)."""
        return self.counts.get(status, 0)


def _summarise(results: list[VerificationResult], layer: Layer) -> LayerSummary:
    counts: dict[str, int] = {}
    for res in results:
        if res.layer is layer:
            counts[res.status] = counts.get(res.status, 0) + 1
    return LayerSummary(counts=counts)


def playbook_compliance(results: list[VerificationResult]) -> LayerSummary:
    """Summarise Layer-2 results into Compliant/Deviation/Violation counts."""
    return _summarise(results, Layer.PLAYBOOK)


def standard_terms_completeness(results: list[VerificationResult]) -> LayerSummary:
    """Summarise Layer-3 results into Present/Missing/Non-standard counts."""
    return _summarise(results, Layer.STANDARD_TERMS)


def risk_score(results: list[VerificationResult]) -> int:
    """Aggregate playbook Violations and missing/non-standard core terms to 0-100.

    The score rises with each policy violation and each missing or non-standard
    standard term, capped at 100. It is intentionally simple and transparent;
    the weighting is a baseline tunable per deployment.

    Args:
        results: All verification results.

    Returns:
        An integer risk score in ``[0, 100]``.
    """
    violations = sum(1 for r in results if r.layer is Layer.PLAYBOOK and r.status == "Violation")
    missing_terms = sum(
        1 for r in results if r.layer is Layer.STANDARD_TERMS and r.status in ("Missing", "Non-standard")
    )
    contradicted = sum(
        1 for r in results if r.layer is Layer.REQUIREMENTS and r.status == "Contradicted"
    )
    raw = violations * 30 + missing_terms * 15 + contradicted * 25
    return min(100, raw)
