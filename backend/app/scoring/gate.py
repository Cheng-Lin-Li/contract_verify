"""Combined auto-confirmation gate and attorney-routing logic (TDD §9, §11).

A contract is **never** auto-confirmed while any of these is open:

* a Critical Layer-1 requirement is Missing or Contradicted,
* a Layer-2 playbook Violation,
* a core Layer-3 standard protection Missing, or
* any determination with confidence < the human-review threshold.

The same triggers, plus a risk-score threshold, decide what routes to the
attorney queue.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.enums import Layer, Priority
from app.core.models import ReferenceItem, VerificationResult


@dataclass
class GateDecision:
    """The outcome of evaluating the combined auto-confirmation gate.

    Attributes:
        auto_confirm: Whether the contract may be auto-confirmed.
        blocking_reasons: Human-readable reasons the gate is closed (if any).
        attorney_items: Item ids that must go to the attorney queue.
    """

    auto_confirm: bool
    blocking_reasons: list[str] = field(default_factory=list)
    attorney_items: list[str] = field(default_factory=list)


# Standard-term types treated as "core protections" for the gate.
CORE_STANDARD_TYPES = {"liability", "governing_law", "indemnity", "confidentiality"}


def evaluate_gate(
    items: list[ReferenceItem],
    results: list[VerificationResult],
    risk: int,
    *,
    cs_human_review_threshold: float = 0.70,
    risk_attorney_threshold: int = 60,
) -> GateDecision:
    """Evaluate the combined gate and collect attorney-routing items.

    Args:
        items: All reference items (for priority/type lookup).
        results: All verification results.
        risk: The aggregate risk score (0-100).
        cs_human_review_threshold: Confidence below which a result blocks auto-confirm.
        risk_attorney_threshold: Risk at/above which the contract routes to an attorney.

    Returns:
        A :class:`GateDecision`.
    """
    item_by_id = {it.item_id: it for it in items}
    reasons: list[str] = []
    attorney: list[str] = []

    for res in results:
        item = item_by_id.get(res.item_id)

        # L1: Critical requirement Missing/Contradicted.
        if res.layer is Layer.REQUIREMENTS and res.status in ("Missing", "Contradicted"):
            if item and item.priority is Priority.CRITICAL:
                reasons.append(f"Critical requirement {res.item_id} is {res.status}")
                attorney.append(res.item_id)
            if res.status == "Contradicted":
                attorney.append(res.item_id)

        # L2: any Violation.
        if res.layer is Layer.PLAYBOOK and res.status == "Violation":
            reasons.append(f"Playbook violation on {res.item_id}")
            attorney.append(res.item_id)

        # L3: core protection Missing.
        if res.layer is Layer.STANDARD_TERMS and res.status == "Missing":
            if item and item.type in CORE_STANDARD_TYPES:
                reasons.append(f"Core standard protection {res.item_id} ({item.type}) is Missing")
                attorney.append(res.item_id)

        # Confidence floor applies to every layer.
        if res.confidence < cs_human_review_threshold:
            reasons.append(f"Low confidence ({res.confidence:.2f}) on {res.item_id}")
            attorney.append(res.item_id)

    if risk >= risk_attorney_threshold:
        reasons.append(f"Risk score {risk} >= attorney threshold {risk_attorney_threshold}")

    # De-duplicate the attorney queue while preserving order.
    seen: set[str] = set()
    attorney_unique = [i for i in attorney if not (i in seen or seen.add(i))]

    return GateDecision(
        auto_confirm=len(reasons) == 0,
        blocking_reasons=reasons,
        attorney_items=attorney_unique,
    )
