"""Contracts router: upload, verify (background task), poll job, report."""

from __future__ import annotations

import tempfile
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile, status

from app.api.deps import get_current_user
from app.api import state_store
from app.api.schemas import (
    CIRBlockOut, CIRDocumentOut, ContractSourceInfo, ContractSummaryOut,
    DeploymentOut, JobOut, ReportOut, ReportRowOut, ScoreSummary,
)
from app.config import get_settings
from app.core.enums import DocRole
from app.ingestion.ingest_service import IngestService
from app.pipeline import VerificationPipeline
from app.references.loaders import load_playbook, load_standard_terms

router = APIRouter()


def _save_uploads(contract: UploadFile, sources: list[UploadFile]) -> tuple[str, list[str]]:
    base = Path(tempfile.mkdtemp(prefix="cv_upload_", dir=_ensure(get_settings().uploads_dir)))
    cpath = base / (contract.filename or "contract")
    cpath.write_bytes(contract.file.read())
    spaths = []
    for s in sources:
        sp = base / (s.filename or f"source_{uuid.uuid4().hex}")
        sp.write_bytes(s.file.read())
        spaths.append(str(sp))
    return str(cpath), spaths


def _ensure(d: str) -> str:
    Path(d).mkdir(parents=True, exist_ok=True)
    return d


def _load_merged(loader_fn, *dirs, **kwargs):
    """Load and merge reference items from multiple directories, skipping missing ones."""
    items = []
    for d in dirs:
        try:
            items.extend(loader_fn(d, **kwargs))
        except FileNotFoundError:
            pass
    return items


def _payload_to_report_out(contract_id: str, payload: dict) -> ReportOut:
    rep = payload["report"]
    scores = ScoreSummary(
        coverage_score=rep["coverage_score"],
        risk_score=rep["risk_score"],
        playbook_compliance=rep["playbook_compliance"],
        standard_terms_completeness=rep["standard_terms_completeness"],
        auto_confirm=rep["auto_confirm"],
        blocking_reasons=rep["blocking_reasons"],
    )
    rows = [ReportRowOut(**{k: r.get(k) for k in ReportRowOut.model_fields}) for r in rep["rows"]]
    return ReportOut(
        contract_id=contract_id, scores=scores, rows=rows,
        entities=payload.get("entities", {}), attorney_queue=rep.get("attorney_queue", []),
    )


# ---------------------------------------------------------------------------
# Background pipeline task
# ---------------------------------------------------------------------------

def _run_pipeline_task(
    job_id: str,
    cpath: str,
    spaths: list[str],
    contract_type: Optional[str],
    playbook_items: list,
    std_items: list,
) -> None:
    """Run the full verification pipeline and persist results to the state store."""

    def _upd(stage: str, progress: float, stage_file: str = "") -> None:
        job = state_store.load_job(job_id) or {}
        job.update(status="running", stage=stage,
                   progress=round(progress, 3), stage_file=stage_file or "")
        state_store.save_job(job)

    _upd("ingest_contract", 0.0, Path(cpath).name)
    try:
        s = get_settings()
        result = VerificationPipeline().run(
            contract_path=cpath,
            deal_source_paths=spaths,
            playbook_dir=s.demo_playbook_dir,
            standard_terms_dir=s.demo_standard_terms_dir,
            contract_type=contract_type,
            preloaded_playbook=playbook_items,
            preloaded_std_terms=std_items,
            progress_fn=_upd,
        )
        contract_id = result.contract.doc_id
        entities = (result.contract.metadata or {}).get("entities", {})
        state_store.save_report(
            contract_id, {"report": result.report.to_dict(), "entities": entities}
        )

        rep = result.report
        row_by_id = {r.item_id: r for r in rep.rows}
        sla_due = datetime.now(tz=timezone.utc) + timedelta(days=3)
        q_items = []
        for item_id in rep.attorney_queue:
            row = row_by_id.get(item_id)
            q_items.append({
                "queue_id": f"{contract_id}:{item_id}",
                "contract_id": contract_id,
                "item_id": item_id,
                "layer": row.layer if row else 0,
                "status": row.status if row else "",
                "reason": (row.notes if row else "") or "flagged",
                "risk_score": rep.risk_score,
                "sla_due_at": sla_due.isoformat(),
                "sla_state": "ok",
                "assigned_to": None,
                "resolved": False,
            })
        if q_items:
            state_store.save_queue_items(q_items)

        # Persist CIR documents so the viewer can display block-level content.
        state_store.save_cir(contract_id, result.contract.to_dict())
        sources_info = []
        for doc in result.deal_docs:
            state_store.save_cir(doc.doc_id, doc.to_dict())
            sources_info.append({
                "doc_id": doc.doc_id,
                "filename": (doc.metadata or {}).get("filename", doc.doc_id[:8]),
                "format": doc.format,
                "role": doc.role.value if hasattr(doc.role, "value") else str(doc.role),
            })
        state_store.save_contract_sources(contract_id, sources_info)

        job = state_store.load_job(job_id) or {}
        job.update(status="completed", stage="done", progress=1.0,
                   contract_id=contract_id, error=None, stage_file="")
        state_store.save_job(job)

    except Exception as exc:  # noqa: BLE001
        job = state_store.load_job(job_id) or {}
        job.update(status="failed", stage="failed", error=str(exc))
        state_store.save_job(job)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/contracts", response_model=list[ContractSummaryOut])
def list_contracts(user=Depends(get_current_user)) -> list[ContractSummaryOut]:
    """Return all contracts with summary scores, newest first."""
    return [ContractSummaryOut(**c) for c in state_store.list_contracts()]


@router.post("/contracts", response_model=JobOut)
def create_contract(
    background_tasks: BackgroundTasks,
    contract: UploadFile = File(...),
    sources: list[UploadFile] = File(default=[]),
    contract_type: Optional[str] = None,
    user=Depends(get_current_user),
) -> JobOut:
    """Accept a contract + deal sources, enqueue verification, return a job to poll.

    The pipeline runs in a FastAPI background task. The SPA polls
    ``GET /api/contracts/jobs/{job_id}`` for stage/progress updates, then loads
    the report once status reaches ``completed``.
    """
    s = get_settings()
    cpath, spaths = _save_uploads(contract, sources)
    playbook_items = _load_merged(load_playbook, s.demo_playbook_dir, s.library_playbook_dir)
    std_items = _load_merged(
        load_standard_terms, s.demo_standard_terms_dir, s.library_standard_terms_dir,
        contract_type=contract_type,
    )

    job_id = uuid.uuid4().hex
    job: dict = {
        "job_id": job_id,
        "contract_id": "",
        "status": "queued",
        "progress": 0.0,
        "error": None,
        "stage": "queued",
        "current_page": None,
        "total_pages": None,
        "stage_file": contract.filename or "",
        "contract_filename": contract.filename or "",
    }
    state_store.save_job(job)
    background_tasks.add_task(
        _run_pipeline_task, job_id, cpath, spaths, contract_type, playbook_items, std_items
    )
    return JobOut(**job)


@router.get("/contracts/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: str, user=Depends(get_current_user)) -> JobOut:
    job = state_store.load_job(job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown job")
    return JobOut(**job)


def _check_library_overlap(contract_id: str) -> list[str]:
    """Return warnings if any uploaded document matches a library reference document.

    Compares SHA-256 hashes (exact duplicate) and filenames (same-name heuristic)
    of the contract and its deal sources against every document in the playbook
    and standard-terms libraries.
    """
    warnings: list[str] = []

    # Build library index: sha256 → human label, and lowercase filename set.
    lib_sha256: dict[str, str] = {}
    lib_filenames: set[str] = set()
    for layer in ("playbook", "standard_terms"):
        layer_label = "Playbook" if layer == "playbook" else "Standard Terms"
        for info in state_store.load_library_docs(layer):
            fname = info.get("filename") or ""
            lib_filenames.add(fname.lower())
            cir = state_store.load_cir(info["doc_id"])
            if cir and cir.get("sha256"):
                lib_sha256[cir["sha256"]] = f"{layer_label}: {fname}"

    if not lib_sha256 and not lib_filenames:
        return []

    def _check(sha256: str, filename: str, label: str) -> None:
        if sha256 and sha256 in lib_sha256:
            warnings.append(
                f"{label} '{filename}' is identical to library document "
                f"{lib_sha256[sha256]}. Verify the correct file was uploaded."
            )
        elif filename.lower() in lib_filenames:
            warnings.append(
                f"{label} '{filename}' has the same name as a library reference document. "
                f"Verify the correct file was uploaded."
            )

    # Check the contract CIR.
    contract_cir = state_store.load_cir(contract_id)
    if contract_cir:
        sha = contract_cir.get("sha256", "")
        fname = (contract_cir.get("metadata") or {}).get("filename", "")
        _check(sha, fname, "Contract")

    # Check each deal source CIR.
    for info in state_store.load_contract_sources(contract_id):
        doc_cir = state_store.load_cir(info["doc_id"])
        if not doc_cir:
            continue
        sha = doc_cir.get("sha256", "")
        fname = info.get("filename") or (doc_cir.get("metadata") or {}).get("filename", "")
        _check(sha, fname, "Deal source")

    return warnings


def _build_queue_decisions(contract_id: str) -> dict[str, str]:
    """Return item_id → attorney_action for all resolved queue items of this contract."""
    decisions: dict[str, str] = {}
    for it in state_store.load_queue_items():
        if (it.get("contract_id") == contract_id
                and it.get("resolved")
                and it.get("attorney_action")):
            decisions[it["item_id"]] = it["attorney_action"]
    return decisions


@router.get("/contracts/{contract_id}/report", response_model=ReportOut)
def get_report(contract_id: str, user=Depends(get_current_user)) -> ReportOut:
    payload = state_store.load_report(contract_id)
    if payload is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown contract")
    report_out = _payload_to_report_out(contract_id, payload)
    report_out.library_warnings = _check_library_overlap(contract_id)
    report_out.queue_decisions = _build_queue_decisions(contract_id)
    return report_out


@router.delete("/contracts/{contract_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_contract(contract_id: str, user=Depends(get_current_user)) -> None:
    """Delete a contract report and all associated state (CIRs, sources, job, queue items)."""
    if state_store.load_report(contract_id) is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown contract")
    state_store.delete_contract(contract_id)


@router.get("/contracts/{contract_id}/sources", response_model=list[ContractSourceInfo])
def get_contract_sources(contract_id: str, user=Depends(get_current_user)) -> list[ContractSourceInfo]:
    """Return the deal-source documents that were verified with this contract."""
    return [ContractSourceInfo(**s) for s in state_store.load_contract_sources(contract_id)]


def _regenerate_cir_from_blob(doc_id: str) -> Optional[dict]:
    """Re-ingest a document from its stored blob to recover a missing CIR.

    Used for contracts created before CIR persistence was implemented. Returns
    None (graceful no-op) if the blob store is S3 or the blob dir is missing.
    Also caches the recovered CIR so subsequent requests are fast.
    """
    s = get_settings()
    if s.blob_dir.lower().startswith("s3://"):
        return None

    blob_dir = Path(s.blob_dir) / doc_id
    if not blob_dir.is_dir():
        return None

    files = [f for f in blob_dir.iterdir() if f.is_file()]
    if not files:
        return None

    # Contracts have a matching report; everything else is a deal source.
    role = DocRole.CONTRACT if state_store.load_report(doc_id) is not None else DocRole.DEAL_SOURCE

    try:
        doc = IngestService().ingest_file(files[0], role)
        doc.doc_id = doc_id  # Restore original ID so matched_clause_ids remain valid.
        cir = doc.to_dict()
        state_store.save_cir(doc_id, cir)
        return cir
    except Exception:
        return None


@router.get("/documents/{doc_id}", response_model=CIRDocumentOut)
def get_document(doc_id: str, user=Depends(get_current_user)) -> CIRDocumentOut:
    """Return the parsed CIR (blocks with IDs) for any ingested document."""
    cir = state_store.load_cir(doc_id)
    if cir is None:
        cir = _regenerate_cir_from_blob(doc_id)
    if cir is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Document not found")
    blocks = [CIRBlockOut(**b) for b in cir.get("blocks", [])]
    return CIRDocumentOut(
        doc_id=cir["doc_id"],
        role=cir.get("role", ""),
        format=cir.get("format", ""),
        filename=(cir.get("metadata") or {}).get("filename", cir["doc_id"][:8]),
        pages=cir.get("pages", 1),
        blocks=blocks,
        metadata={k: str(v) for k, v in (cir.get("metadata") or {}).items()
                  if k not in ("filename",) and not isinstance(v, (dict, list))},
    )


@router.get("/deployment", response_model=DeploymentOut)
def get_deployment(user=Depends(get_current_user)) -> DeploymentOut:
    s = get_settings()
    return DeploymentOut(
        mode=s.deployment_mode, residency=s.component_residency(),
        warnings=s.validate_deployment(),
    )
