"""End-to-end verification pipeline orchestrator.

Ties the six grounded stages (PRD §5 / TDD §1) into one callable:

1. ingest contract + deal sources, load playbook + standard terms,
2. extract Layer-1 requirements,
3. reconcile Layer-1 (dedupe + basic supersession),
4. verify all three layers against the contract,
5. score (coverage, compliance, completeness, risk, gate) and build the report,
6. record every step to the audit trail.

In the MVP this runs in-process (synchronous); the 3-month build moves the
stages onto FastAPI BackgroundTasks / Celery behind the same interface.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Optional

from app.audit.audit_log import AuditLog
from app.config import Settings, get_settings
from app.core.enums import DocRole, Layer
from app.core.models import CIRDocument, ReferenceItem, VerificationResult
from app.ingestion.ingest_service import IngestService
from app.llm.base import LLMProvider
from app.llm.factory import get_provider
from app.logging_setup import get_logger, log_stage
from app.references.extractor import RequirementExtractor
from app.references.entities import entity_summary, extract_contract_entities
from app.references.loaders import load_playbook, load_standard_terms
from app.references.reconcile import ReconcileResult, reconcile_requirements
from app.report.report_builder import VerificationReport, build_report
from app.scoring.coverage import coverage_score
from app.scoring.gate import evaluate_gate
from app.scoring.risk import playbook_compliance, risk_score, standard_terms_completeness
from app.storage.store import BlobStore, get_blob_store
from app.verify.matcher import VerificationMatcher

log = get_logger("pipeline")


_EPOCH = datetime.min.replace(tzinfo=timezone.utc)


def _deal_doc_recency_key(doc: CIRDocument) -> datetime:
    """Sort key placing undated sources first, then dated ones chronologically.

    Uses the email ``Date`` header when present; sources without a parseable
    date (e.g. a plain term sheet) are treated as the earliest, so a later email
    revision supersedes them. This makes supersession independent of the order
    files happen to be supplied or globbed.
    """
    raw = (doc.metadata or {}).get("date")
    if raw:
        try:
            dt = parsedate_to_datetime(raw)
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except (TypeError, ValueError):
            pass
    return _EPOCH


@dataclass
class PipelineResult:
    """Everything produced by one verification run."""

    contract: CIRDocument
    deal_docs: list[CIRDocument]
    items: list[ReferenceItem]
    results: list[VerificationResult]
    report: VerificationReport


class VerificationPipeline:
    """Coordinates the full three-layer verification of one contract."""

    def __init__(
        self,
        provider: Optional[LLMProvider] = None,
        settings: Optional[Settings] = None,
        audit: Optional[AuditLog] = None,
        blob_store: Optional[BlobStore] = None,
    ) -> None:
        """Initialise the pipeline.

        Args:
            provider: LLM provider; defaults to the configured one (factory).
            settings: Settings; defaults to :func:`get_settings`.
            audit: Audit log; defaults to one at ``settings.audit_log_path``.
            blob_store: Blob backend for raw uploads; defaults to the configured
                one (local filesystem, or S3/MinIO when ``BLOB_DIR`` is ``s3://``).
        """
        self.settings = settings or get_settings()
        self.provider = provider or get_provider(self.settings)
        self.audit = audit or AuditLog(self.settings.audit_log_path)
        self.blobs = blob_store or get_blob_store(self.settings)
        self.ingest = IngestService()
        self.extractor = RequirementExtractor(self.provider)
        self.matcher = VerificationMatcher(self.provider)

    def _persist_blob(self, doc_id: str, path: str | Path) -> str:
        """Store a source document's raw bytes in the blob store.

        Keeps a durable copy of every ingested file (contract, deal source)
        keyed by ``doc_id``. In a hybrid deployment this physically ships the
        bytes to the configured S3/MinIO bucket while structured state stays in
        the local DB. Returns the backend location reference (path or ``s3://``
        URI) for the audit trail; never fails the pipeline on a storage error.
        """
        try:
            data = Path(path).read_bytes()
            return self.blobs.put(f"{doc_id}/{Path(path).name}", data)
        except Exception as exc:  # noqa: BLE001 - storage must not break verification
            log.warning("blob_persist_failed", extra={"doc_id": doc_id, "error": str(exc)})
            return ""

    def run(
        self,
        contract_path: str | Path,
        deal_source_paths: list[str | Path],
        playbook_dir: str | Path,
        standard_terms_dir: str | Path,
        contract_type: Optional[str] = None,
        preloaded_playbook: Optional[list] = None,
        preloaded_std_terms: Optional[list] = None,
        progress_fn=None,
    ) -> PipelineResult:
        """Run the full pipeline and return its :class:`PipelineResult`.

        Args:
            contract_path: Path to the target contract (PDF/DOCX).
            deal_source_paths: Paths to deal sources (emails/PDFs/DOCX/text).
            playbook_dir: Directory of Layer-2 playbook YAML files.
            standard_terms_dir: Directory of Layer-3 standard-term YAML files.
            contract_type: Optional contract type to scope Layer-3 retrieval.
            preloaded_playbook: Pre-loaded Layer-2 items; takes precedence over
                ``playbook_dir`` when provided (used to merge multiple dirs).
            preloaded_std_terms: Pre-loaded Layer-3 items; same semantics.
        """
        def _prog(stage: str, frac: float, stage_file: str = "") -> None:
            if progress_fn:
                try:
                    progress_fn(stage, frac, stage_file)
                except Exception:  # noqa: BLE001 — never let progress reporting break verification
                    pass

        # 1. Ingest.
        residency = self.settings.component_residency()
        warnings = self.settings.validate_deployment()
        log.info("deployment", extra={"mode": self.settings.deployment_mode,
                                      "residency": residency})
        for w in warnings:
            log.warning("deployment_guardrail", extra={"warning": w})
        self.audit.record("deployment", doc_id=None,
                          details={"mode": self.settings.deployment_mode,
                                   "residency": residency, "warnings": warnings})

        _prog("ingest_contract", 0.05, Path(contract_path).name)
        contract = self.ingest.ingest_file(contract_path, DocRole.CONTRACT)
        contract_blob = self._persist_blob(contract.doc_id, contract_path)
        self.audit.record("ingest", doc_id=contract.doc_id,
                          details={"role": "contract", "blob": contract_blob})
        _prog("ingest_contract", 0.18)

        # doc_id -> original filename, used to render readable requirement provenance.
        doc_names: dict[str, str] = {contract.doc_id: Path(contract_path).name}
        deal_docs = []
        n_src = max(len(deal_source_paths), 1)
        for i, p in enumerate(deal_source_paths):
            _prog("ingest_sources", 0.20 + 0.22 * (i / n_src), Path(p).name)
            d = self.ingest.ingest_file(p, DocRole.DEAL_SOURCE)
            blob = self._persist_blob(d.doc_id, p)
            self.audit.record("ingest", doc_id=d.doc_id,
                              details={"role": "deal_source", "blob": blob})
            doc_names[d.doc_id] = Path(p).name
            deal_docs.append(d)
        _prog("ingest_sources", 0.44)

        # Order deal sources by recency (undated first, then chronological by the
        # email Date header) so reconciliation — which assumes earliest-first and
        # lets the later source win — supersedes correctly regardless of the
        # order files were supplied/globbed.
        deal_docs.sort(key=_deal_doc_recency_key)

        playbook_items = (
            preloaded_playbook if preloaded_playbook is not None
            else load_playbook(playbook_dir)
        )
        std_items = (
            preloaded_std_terms if preloaded_std_terms is not None
            else load_standard_terms(standard_terms_dir, contract_type=contract_type)
        )

        # 1b. Contract-entity enrichment: pull parties/dates/amounts/etc. into the
        # contract CIR so they ground citations and the value-aware verification.
        entities = extract_contract_entities(contract)
        contract.metadata["entities"] = entities
        summary = entity_summary(entities)
        log.info("contract_entities", extra={"doc_id": contract.doc_id, **summary})
        self.audit.record("entities", doc_id=contract.doc_id, details=summary)

        # 2. Extract Layer-1.
        _prog("extract", 0.50)
        req_items = self.extractor.extract_many(deal_docs)
        for it in req_items:
            self.audit.record("extract", doc_id=contract.doc_id, item_id=it.item_id, layer=1)

        # 3. Reconcile Layer-1.
        _prog("reconcile", 0.62)
        reconcile: ReconcileResult = reconcile_requirements(req_items)
        req_items = reconcile.items
        self.audit.record("reconcile", doc_id=contract.doc_id,
                          details={"superseded": reconcile.superseded})

        all_items = req_items + playbook_items + std_items

        # 4. Verify all three layers.
        _prog("match", 0.66)
        with log_stage("verify", doc_id=contract.doc_id, items=len(all_items)):
            results = self.matcher.verify_all(all_items, contract, reconcile)
        for res in results:
            self.audit.record(
                "match", doc_id=contract.doc_id, item_id=res.item_id, layer=int(res.layer),
                status=res.status, confidence=res.confidence,
                contract_clause_id=",".join(res.matched_clause_ids),
                model_name=self.provider.name,
            )
        _prog("match", 0.82)

        # 5. Score + report.
        _prog("score", 0.86)
        coverage = coverage_score(all_items, results)
        compliance = playbook_compliance(results)
        completeness = standard_terms_completeness(results)
        risk = risk_score(results)
        gate = evaluate_gate(
            all_items, results, risk,
            cs_human_review_threshold=self.settings.cs_human_review_threshold,
            risk_attorney_threshold=self.settings.risk_attorney_threshold,
        )
        self.audit.record("score", doc_id=contract.doc_id, status="coverage",
                          confidence=coverage.score / 100.0, risk_score=risk,
                          details={"auto_confirm": gate.auto_confirm})
        for item_id in gate.attorney_items:
            self.audit.record("route", doc_id=contract.doc_id, item_id=item_id,
                              details={"queue": "attorney"})

        _prog("report", 0.94)
        report = build_report(contract, all_items, results, coverage,
                              compliance, completeness, risk, gate, doc_names=doc_names)
        log.info("pipeline_complete", extra={"doc_id": contract.doc_id,
                                             "coverage": coverage.score, "risk": risk,
                                             "auto_confirm": gate.auto_confirm})
        return PipelineResult(contract=contract, deal_docs=deal_docs,
                              items=all_items, results=results, report=report)
