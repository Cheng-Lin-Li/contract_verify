"""Tests for report assembly (TDD §10) and the audit trail (TDD §13)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.audit.audit_log import AuditLog
from app.core.enums import DocRole, Layer, Priority
from app.core.models import CIRBlock, CIRDocument, ReferenceItem, VerificationResult
from app.report.report_builder import build_report
from app.scoring.coverage import coverage_score
from app.scoring.gate import evaluate_gate
from app.scoring.risk import playbook_compliance, risk_score, standard_terms_completeness


def _bundle():
    contract = CIRDocument(role=DocRole.CONTRACT, format="txt", blocks=[CIRBlock(block_id="b-001", type="paragraph",
                                                          page=1, text="clause")])
    items = [
        ReferenceItem(item_id="r-1", layer=Layer.REQUIREMENTS, text="x", priority=Priority.HIGH),
        ReferenceItem(item_id="pb-1", layer=Layer.PLAYBOOK, text="y", type="liability"),
        ReferenceItem(item_id="st-1", layer=Layer.STANDARD_TERMS, text="z", type="liability"),
    ]
    results = [
        VerificationResult(item_id="r-1", layer=Layer.REQUIREMENTS, status="Covered", confidence=0.9),
        VerificationResult(item_id="pb-1", layer=Layer.PLAYBOOK, status="Compliant", confidence=0.9),
        VerificationResult(item_id="st-1", layer=Layer.STANDARD_TERMS, status="Present", confidence=0.9),
    ]
    return contract, items, results


def test_report_has_one_row_per_item():
    contract, items, results = _bundle()
    cov = coverage_score(items, results)
    risk = risk_score(results)
    gate = evaluate_gate(items, results, risk)
    report = build_report(contract, items, results, cov,
                          playbook_compliance(results),
                          standard_terms_completeness(results), risk, gate)
    d = report.to_dict()
    assert len(d["rows"]) == len(items)
    assert d["coverage_score"] == 100.0
    assert "auto_confirm" in d


def test_report_serialises_to_json():
    contract, items, results = _bundle()
    cov = coverage_score(items, results)
    risk = risk_score(results)
    gate = evaluate_gate(items, results, risk)
    report = build_report(contract, items, results, cov,
                          playbook_compliance(results),
                          standard_terms_completeness(results), risk, gate)
    js = report.to_json()
    assert '"coverage_score"' in js


def test_audit_log_appends_and_reads_back():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "audit.jsonl"
        log = AuditLog(path)
        log.record("ingest", doc_id="d1", details={"role": "contract"})
        log.record("match", doc_id="d1", item_id="r-1", layer=1, status="Covered", confidence=0.9)
        events = list(log.read_all())
        assert len(events) == 2
        assert events[0]["event_type"] == "ingest"
        assert all("event_id" in e and "occurred_at" in e for e in events)


def test_audit_events_for_filters_by_doc():
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "audit.jsonl"
        log = AuditLog(path)
        log.record("ingest", doc_id="d1")
        log.record("ingest", doc_id="d2")
        assert len(log.events_for("d1")) == 1
