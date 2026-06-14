"""Tests for the scoring engines (TDD §9): confidence, coverage, risk, gate.

These pin the exact documented formulas so a refactor cannot silently change a
score the business and attorney workflows depend on.
"""

from __future__ import annotations

from app.core.enums import Layer, Priority
from app.core.models import ReferenceItem, VerificationResult
from app.scoring.confidence import (
    ConfidenceInputs,
    confidence_score,
    eligible_for_auto_confirm,
    needs_human_review,
)
from app.scoring.coverage import coverage_score
from app.scoring.gate import CORE_STANDARD_TYPES, evaluate_gate
from app.scoring.risk import (
    playbook_compliance,
    risk_score,
    standard_terms_completeness,
)


def _req(item_id, priority=Priority.MEDIUM):
    return ReferenceItem(item_id=item_id, layer=Layer.REQUIREMENTS, text="x", priority=priority)


def _res(item_id, layer, status, confidence=0.9):
    return VerificationResult(item_id=item_id, layer=layer, status=status, confidence=confidence)


# --- confidence -----------------------------------------------------------

def test_confidence_formula_exact():
    # CS = .30*1 + .30*1 + .20*(1-0) + .15*1 + .05*1 = 1.0
    assert confidence_score(ConfidenceInputs(1, 1, 0, 1, 1)) == 1.0


def test_confidence_weights_sum_to_one():
    # All-1 inputs with no contradiction must total exactly 1.0 (weights sum=1).
    cs = confidence_score(ConfidenceInputs(extract=1, match=1, contradiction=0, llm=1, source=1))
    assert abs(cs - 1.0) < 1e-9


def test_confidence_contradiction_penalty():
    # Full contradiction zeroes the 0.20 contradiction term only.
    cs = confidence_score(ConfidenceInputs(1, 1, 1, 1, 1))
    assert abs(cs - 0.80) < 1e-9


def test_confidence_clamps_out_of_range():
    cs = confidence_score(ConfidenceInputs(5, -3, 0, 2, 1))  # clamps to (1,0,0,1,1)
    # .30*1 + .30*0 + .20*1 + .15*1 + .05*1 = 0.70
    assert abs(cs - 0.70) < 1e-9


def test_confidence_thresholds():
    assert needs_human_review(0.69, 0.70) is True
    assert needs_human_review(0.70, 0.70) is False
    assert eligible_for_auto_confirm(0.85, 0.85) is True
    assert eligible_for_auto_confirm(0.84, 0.85) is False


# --- coverage -------------------------------------------------------------

def test_coverage_all_covered_is_100():
    items = [_req("r-1", Priority.CRITICAL), _req("r-2", Priority.LOW)]
    results = [_res("r-1", Layer.REQUIREMENTS, "Covered"),
               _res("r-2", Layer.REQUIREMENTS, "Covered")]
    assert coverage_score(items, results).score == 100.0


def test_coverage_priority_weighting():
    # Critical(4) Covered=1.0, Low(1) Missing=0.0 -> 4 / 5 * 100 = 80.0
    items = [_req("r-1", Priority.CRITICAL), _req("r-2", Priority.LOW)]
    results = [_res("r-1", Layer.REQUIREMENTS, "Covered"),
               _res("r-2", Layer.REQUIREMENTS, "Missing")]
    assert coverage_score(items, results).score == 80.0


def test_coverage_partial_credit_and_superseded():
    # High(3) Partial=0.5 -> 1.5 ; Medium(2) Superseded=1.0 -> 2.0
    # (1.5 + 2.0) / (3 + 2) * 100 = 70.0
    items = [_req("r-1", Priority.HIGH), _req("r-2", Priority.MEDIUM)]
    results = [_res("r-1", Layer.REQUIREMENTS, "Partial"),
               _res("r-2", Layer.REQUIREMENTS, "Superseded")]
    assert coverage_score(items, results).score == 70.0


def test_coverage_ignores_other_layers():
    items = [_req("r-1", Priority.HIGH)]
    results = [_res("r-1", Layer.REQUIREMENTS, "Covered"),
               _res("pb-1", Layer.PLAYBOOK, "Violation")]
    assert coverage_score(items, results).score == 100.0


def test_coverage_empty_is_zero():
    assert coverage_score([], []).score == 0.0


# --- risk / compliance / completeness ------------------------------------

def test_risk_aggregates_violations_and_missing_terms():
    results = [
        _res("pb-1", Layer.PLAYBOOK, "Violation"),       # 30
        _res("st-1", Layer.STANDARD_TERMS, "Missing"),    # 15
        _res("r-1", Layer.REQUIREMENTS, "Contradicted"),  # 25
    ]
    assert risk_score(results) == 70


def test_risk_capped_at_100():
    results = [_res(f"pb-{i}", Layer.PLAYBOOK, "Violation") for i in range(5)]  # 150 -> cap
    assert risk_score(results) == 100


def test_compliance_and_completeness_summaries():
    results = [
        _res("pb-1", Layer.PLAYBOOK, "Compliant"),
        _res("pb-2", Layer.PLAYBOOK, "Violation"),
        _res("st-1", Layer.STANDARD_TERMS, "Present"),
        _res("st-2", Layer.STANDARD_TERMS, "Missing"),
    ]
    comp = playbook_compliance(results)
    assert comp.get("Compliant") == 1 and comp.get("Violation") == 1
    cmpl = standard_terms_completeness(results)
    assert cmpl.get("Present") == 1 and cmpl.get("Missing") == 1


# --- gate -----------------------------------------------------------------

def test_gate_blocks_on_critical_missing():
    items = [_req("r-1", Priority.CRITICAL)]
    results = [_res("r-1", Layer.REQUIREMENTS, "Missing", confidence=0.99)]
    decision = evaluate_gate(items, results, risk=0)
    assert decision.auto_confirm is False
    assert "r-1" in decision.attorney_items


def test_gate_blocks_on_playbook_violation():
    items = [ReferenceItem(item_id="pb-1", layer=Layer.PLAYBOOK, text="x")]
    results = [_res("pb-1", Layer.PLAYBOOK, "Violation", confidence=0.99)]
    decision = evaluate_gate(items, results, risk=0)
    assert decision.auto_confirm is False
    assert "pb-1" in decision.attorney_items


def test_gate_blocks_on_core_standard_missing():
    items = [ReferenceItem(item_id="st-1", layer=Layer.STANDARD_TERMS, text="x", type="liability")]
    results = [_res("st-1", Layer.STANDARD_TERMS, "Missing", confidence=0.99)]
    decision = evaluate_gate(items, results, risk=0)
    assert decision.auto_confirm is False
    assert "liability" in CORE_STANDARD_TYPES


def test_gate_non_core_missing_does_not_block():
    items = [ReferenceItem(item_id="st-9", layer=Layer.STANDARD_TERMS, text="x", type="notices")]
    results = [_res("st-9", Layer.STANDARD_TERMS, "Missing", confidence=0.99)]
    decision = evaluate_gate(items, results, risk=0)
    assert decision.auto_confirm is True


def test_gate_blocks_on_low_confidence():
    items = [_req("r-1", Priority.LOW)]
    results = [_res("r-1", Layer.REQUIREMENTS, "Covered", confidence=0.50)]
    decision = evaluate_gate(items, results, risk=0, cs_human_review_threshold=0.70)
    assert decision.auto_confirm is False


def test_gate_auto_confirms_clean_run():
    items = [_req("r-1", Priority.HIGH)]
    results = [_res("r-1", Layer.REQUIREMENTS, "Covered", confidence=0.95)]
    decision = evaluate_gate(items, results, risk=10, risk_attorney_threshold=60)
    assert decision.auto_confirm is True
    assert decision.attorney_items == []


def test_gate_blocks_on_high_risk():
    items = [_req("r-1", Priority.HIGH)]
    results = [_res("r-1", Layer.REQUIREMENTS, "Covered", confidence=0.95)]
    decision = evaluate_gate(items, results, risk=80, risk_attorney_threshold=60)
    assert decision.auto_confirm is False
