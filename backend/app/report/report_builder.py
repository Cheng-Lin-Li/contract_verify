"""Explainable verification report (TDD §10).

Produces the unified report as a single per-item table across all three layers,
where each row carries the reference item (with source citation) and the matched
or missing contract clause (with clause citation). Two outputs are supported in
the MVP: JSON (for API/audit storage) and HTML (interactive, citation-linked).
Annotated DOCX redline is a 3-month deliverable.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from app.core.models import CIRDocument, ReferenceItem, VerificationResult
from app.scoring.coverage import CoverageBreakdown
from app.scoring.gate import GateDecision
from app.scoring.risk import LayerSummary


@dataclass
class ReportRow:
    """One row of the unified per-item table."""

    item_id: str
    layer: int
    type: str
    priority: str
    status: str
    confidence: float
    requirement_text: str
    source_citation: Optional[dict[str, Any]]
    matched_clause_ids: list[str]
    notes: str


@dataclass
class VerificationReport:
    """The full verification report payload."""

    contract_id: str
    coverage_score: float
    coverage_counts: dict[str, int]
    playbook_compliance: dict[str, int]
    standard_terms_completeness: dict[str, int]
    risk_score: int
    auto_confirm: bool
    blocking_reasons: list[str]
    attorney_queue: list[str]
    rows: list[ReportRow] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialise the report to a JSON-ready dict."""
        d = asdict(self)
        return d

    def to_json(self, indent: int = 2) -> str:
        """Serialise the report to a JSON string."""
        return json.dumps(self.to_dict(), indent=indent, default=str)


def build_report(
    contract: CIRDocument,
    items: list[ReferenceItem],
    results: list[VerificationResult],
    coverage: CoverageBreakdown,
    compliance: LayerSummary,
    completeness: LayerSummary,
    risk: int,
    gate: GateDecision,
) -> VerificationReport:
    """Assemble a :class:`VerificationReport` from the pipeline outputs.

    Args:
        contract: The verified contract CIR.
        items: All reference items across the three layers.
        results: All verification results.
        coverage: Layer-1 coverage breakdown.
        compliance: Layer-2 summary.
        completeness: Layer-3 summary.
        risk: Aggregate risk score.
        gate: Combined gate decision.
    """
    item_by_id = {it.item_id: it for it in items}
    rows: list[ReportRow] = []
    for res in results:
        item = item_by_id.get(res.item_id)
        rows.append(
            ReportRow(
                item_id=res.item_id,
                layer=int(res.layer),
                type=item.type if item else "general",
                priority=item.priority.value if item else "Medium",
                status=res.status,
                confidence=res.confidence,
                requirement_text=item.text if item else "",
                source_citation=(item.source_ref.to_dict() if item and item.source_ref else None),
                matched_clause_ids=res.matched_clause_ids,
                notes=res.notes,
            )
        )
    return VerificationReport(
        contract_id=contract.doc_id,
        coverage_score=coverage.score,
        coverage_counts=coverage.counts,
        playbook_compliance=compliance.counts,
        standard_terms_completeness=completeness.counts,
        risk_score=risk,
        auto_confirm=gate.auto_confirm,
        blocking_reasons=gate.blocking_reasons,
        attorney_queue=gate.attorney_items,
        rows=rows,
    )


def render_html(report: VerificationReport) -> str:
    """Render the report as a self-contained HTML page.

    Uses Jinja2 if available, else a minimal string-built fallback, so the
    function works on a minimal image. Clause ids are shown so the UI can
    deep-link to ``/docs/{doc_id}#block-{block_id}`` (TDD §7).
    """
    try:
        from jinja2 import Template
    except ImportError:  # pragma: no cover - fallback path
        return _render_html_fallback(report)

    template = Template(_HTML_TEMPLATE)
    return template.render(r=report)


def _status_class(status: str) -> str:
    """Return a CSS class name for a status (used for colour coding)."""
    return {
        "Covered": "ok", "Compliant": "ok", "Present": "ok", "Superseded": "ok",
        "Partial": "warn", "Deviation": "warn", "Non-standard": "warn",
        "Missing": "bad", "Violation": "bad", "Contradicted": "bad",
    }.get(status, "")


def _render_html_fallback(report: VerificationReport) -> str:
    """Build a minimal HTML report without Jinja2."""
    rows = "".join(
        f"<tr class='{_status_class(row.status)}'><td>{row.item_id}</td><td>L{row.layer}</td>"
        f"<td>{row.type}</td><td>{row.priority}</td><td>{row.status}</td>"
        f"<td>{row.confidence:.2f}</td><td>{row.requirement_text}</td>"
        f"<td>{', '.join(row.matched_clause_ids)}</td></tr>"
        for row in report.rows
    )
    return (
        f"<html><body><h1>Verification report — {report.contract_id}</h1>"
        f"<p>Coverage {report.coverage_score} · Risk {report.risk_score} · "
        f"Auto-confirm: {report.auto_confirm}</p>"
        f"<table border='1'><tr><th>Item</th><th>Layer</th><th>Type</th><th>Priority</th>"
        f"<th>Status</th><th>Conf.</th><th>Requirement</th><th>Clauses</th></tr>{rows}</table>"
        f"</body></html>"
    )


_HTML_TEMPLATE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>Verification report</title>
<style>
 body{font-family:system-ui,Arial,sans-serif;margin:2rem;color:#1a1a1a}
 .scores{display:flex;gap:1rem;margin:1rem 0}
 .card{border:1px solid #ddd;border-radius:8px;padding:.75rem 1rem}
 table{border-collapse:collapse;width:100%;font-size:.9rem}
 th,td{border:1px solid #e3e3e3;padding:.4rem .6rem;text-align:left;vertical-align:top}
 th{background:#fafafa}
 .ok{background:#eafaf0}.warn{background:#fff8e6}.bad{background:#fdecec}
 .gate-open{color:#137a3f}.gate-closed{color:#b4231f}
</style></head><body>
<h1>Verification report</h1>
<p>Contract <code>{{ r.contract_id }}</code></p>
<div class="scores">
 <div class="card"><strong>Coverage</strong><br>{{ r.coverage_score }}</div>
 <div class="card"><strong>Risk</strong><br>{{ r.risk_score }}</div>
 <div class="card"><strong>Auto-confirm</strong><br>
   <span class="{{ 'gate-open' if r.auto_confirm else 'gate-closed' }}">
   {{ 'YES' if r.auto_confirm else 'NO' }}</span></div>
</div>
{% if r.blocking_reasons %}<h3>Blocking reasons</h3><ul>
{% for reason in r.blocking_reasons %}<li>{{ reason }}</li>{% endfor %}</ul>{% endif %}
{% if r.attorney_queue %}<p><strong>Attorney queue:</strong> {{ r.attorney_queue|join(', ') }}</p>{% endif %}
<table>
 <tr><th>Item</th><th>Layer</th><th>Type</th><th>Priority</th><th>Status</th>
     <th>Conf.</th><th>Requirement</th><th>Cited clauses</th><th>Notes</th></tr>
 {% for row in r.rows %}
 <tr class="{{ {'Covered':'ok','Compliant':'ok','Present':'ok','Superseded':'ok',
                'Partial':'warn','Deviation':'warn','Non-standard':'warn',
                'Missing':'bad','Violation':'bad','Contradicted':'bad'}.get(row.status,'') }}">
   <td>{{ row.item_id }}</td><td>L{{ row.layer }}</td><td>{{ row.type }}</td>
   <td>{{ row.priority }}</td><td>{{ row.status }}</td><td>{{ '%.2f'|format(row.confidence) }}</td>
   <td>{{ row.requirement_text }}</td><td>{{ row.matched_clause_ids|join(', ') }}</td>
   <td>{{ row.notes }}</td></tr>
 {% endfor %}
</table></body></html>"""
