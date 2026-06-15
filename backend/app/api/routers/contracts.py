"""Contracts router: upload, verify (synchronous for the demo), report."""

from __future__ import annotations

import tempfile
import uuid
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status

from app.api.deps import get_current_user
from app.api import state_store
from app.api.schemas import (
    DeploymentOut, JobOut, ReportOut, ReportRowOut, ScoreSummary,
)
from app.config import get_settings
from app.pipeline import VerificationPipeline

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


@router.post("/contracts", response_model=JobOut)
def create_contract(
    contract: UploadFile = File(...),
    sources: list[UploadFile] = File(default=[]),
    contract_type: Optional[str] = None,
    user=Depends(get_current_user),
) -> JobOut:
    """Accept a contract + deal sources, run verification, store the report.

    The demo runs the pipeline synchronously and returns a completed job; the
    SPA polls ``/contracts/jobs/{id}`` and then loads the report.
    """
    s = get_settings()
    cpath, spaths = _save_uploads(contract, sources)
    result = VerificationPipeline().run(
        contract_path=cpath, deal_source_paths=spaths,
        playbook_dir=s.demo_playbook_dir, standard_terms_dir=s.demo_standard_terms_dir,
        contract_type=contract_type,
    )
    contract_id = result.contract.doc_id
    entities = (result.contract.metadata or {}).get("entities", {})
    state_store.save_report(contract_id, {"report": result.report.to_dict(), "entities": entities})

    # Build attorney-queue items from the flagged rows.
    rep = result.report
    row_by_id = {r.item_id: r for r in rep.rows}
    q_items = []
    for item_id in rep.attorney_queue:
        row = row_by_id.get(item_id)
        q_items.append({
            "queue_id": f"{contract_id}:{item_id}", "contract_id": contract_id,
            "item_id": item_id, "layer": row.layer if row else 0,
            "status": row.status if row else "", "reason": (row.notes if row else "") or "flagged",
            "risk_score": rep.risk_score, "sla_due_at": None, "sla_state": "ok",
            "assigned_to": None, "resolved": False,
        })
    if q_items:
        state_store.save_queue_items(q_items)

    job = {"job_id": uuid.uuid4().hex, "contract_id": contract_id,
           "status": "completed", "progress": 1.0, "error": None}
    state_store.save_job(job)
    return JobOut(**job)


@router.get("/contracts/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: str, user=Depends(get_current_user)) -> JobOut:
    job = state_store.load_job(job_id)
    if job is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown job")
    return JobOut(**job)


@router.get("/contracts/{contract_id}/report", response_model=ReportOut)
def get_report(contract_id: str, user=Depends(get_current_user)) -> ReportOut:
    payload = state_store.load_report(contract_id)
    if payload is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Unknown contract")
    return _payload_to_report_out(contract_id, payload)


@router.get("/deployment", response_model=DeploymentOut)
def get_deployment(user=Depends(get_current_user)) -> DeploymentOut:
    s = get_settings()
    return DeploymentOut(
        mode=s.deployment_mode, residency=s.component_residency(),
        warnings=s.validate_deployment(),
    )
