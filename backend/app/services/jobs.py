"""Background verification jobs (3-month scope).

Runs the existing pipeline (app/pipeline.py) off the request thread via FastAPI
BackgroundTasks (Celery+Redis at scale is backlog), updating job status/progress,
persisting the report/CIRs, and routing flagged items to the attorney queue via
:mod:`app.queue` (routing + sla + AttorneyQueue).

Signature note: the original skeleton sketched ``create_job(contract_id,
source_ids, ...)`` assuming documents are pre-stored by id. The shipped pipeline
ingests from file paths and assigns its own ``doc_id`` (the contract's becomes
the contract_id), so this consolidates the demo router's proven, path-based
background task here and takes the upload paths instead — same three lifecycle
functions, wired to the real pipeline.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from app.config import get_settings
from app.logging_setup import get_logger
from app.pipeline import VerificationPipeline
from app.queue import sla as sla_mod
from app.queue.attorney_queue import AttorneyQueue
from app.references.loaders import load_playbook, load_standard_terms

log = get_logger("services.jobs")


def _store():
    """The demo state store (lazy import avoids an api<-service import cycle)."""
    from app.api import state_store
    return state_store


def _load_merged(loader_fn, *dirs, **kwargs) -> list:
    """Merge reference items from multiple dirs, skipping missing ones."""
    items: list = []
    for d in dirs:
        try:
            items.extend(loader_fn(d, **kwargs))
        except FileNotFoundError:
            pass
    return items


def create_job(contract_path: str, source_paths: list[str], *,
               contract_type: Optional[str] = None,
               contract_filename: Optional[str] = None,
               locale: Optional[str] = None) -> str:
    """Create a queued job row; return its job_id.

    ``contract_path``/``source_paths`` are the saved upload locations the job
    will verify; ``contract_id`` is assigned by the pipeline at run time.
    ``locale`` selects the prompt-catalog language for this run (e.g. ``ja``).
    """
    job_id = uuid.uuid4().hex
    _store().save_job({
        "job_id": job_id,
        "contract_id": "",
        "status": "queued",
        "progress": 0.0,
        "error": None,
        "stage": "queued",
        "current_page": None,
        "total_pages": None,
        "stage_file": contract_filename or "",
        "contract_filename": contract_filename or "",
        "contract_path": contract_path,
        "source_paths": list(source_paths),
        "contract_type": contract_type,
        "locale": locale,
    })
    return job_id


def _enqueue_flagged(report: Any, contract_id: str) -> None:
    """Route the report's flagged items to the attorney queue (sla + queue)."""
    s = get_settings()
    queue = AttorneyQueue(_store())
    due = sla_mod.due_at(datetime.now(tz=timezone.utc), s.queue_sla_hours)
    row_by_id = {r.item_id: r for r in report.rows}
    for item_id in report.attorney_queue:
        row = row_by_id.get(item_id)
        queue.enqueue(
            contract_id, item_id,
            reason=(getattr(row, "notes", "") or "Flagged for attorney review"),
            risk_score=report.risk_score,
            sla_due_at=due,
        )


def run_job(job_id: str) -> None:
    """Execute the verification pipeline for a job, updating progress/status."""
    store = _store()
    job = store.load_job(job_id)
    if job is None:
        log.warning("run_job_missing", extra={"job_id": job_id})
        return

    def _upd(stage: str, progress: float, stage_file: str = "") -> None:
        j = store.load_job(job_id) or {}
        j.update(status="running", stage=stage,
                 progress=round(progress, 3), stage_file=stage_file or "")
        store.save_job(j)

    cpath = job["contract_path"]
    spaths = job.get("source_paths", [])
    contract_type = job.get("contract_type")
    locale = job.get("locale")
    _upd("ingest_contract", 0.0, Path(cpath).name)

    try:
        s = get_settings()
        playbook_items = _load_merged(load_playbook, s.demo_playbook_dir, s.library_playbook_dir)
        std_items = _load_merged(
            load_standard_terms, s.demo_standard_terms_dir, s.library_standard_terms_dir,
            contract_type=contract_type,
        )
        result = VerificationPipeline(locale=locale).run(
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
        store.save_report(contract_id,
                          {"report": result.report.to_dict(), "entities": entities})

        _enqueue_flagged(result.report, contract_id)

        store.save_cir(contract_id, result.contract.to_dict())
        sources_info = []
        for doc in result.deal_docs:
            store.save_cir(doc.doc_id, doc.to_dict())
            sources_info.append({
                "doc_id": doc.doc_id,
                "filename": (doc.metadata or {}).get("filename", doc.doc_id[:8]),
                "format": doc.format,
                "role": doc.role.value if hasattr(doc.role, "value") else str(doc.role),
            })
        store.save_contract_sources(contract_id, sources_info)

        j = store.load_job(job_id) or {}
        j.update(status="completed", stage="done", progress=1.0,
                 contract_id=contract_id, error=None, stage_file="")
        store.save_job(j)

    except Exception as exc:  # noqa: BLE001 - surface failure on the job, never crash the worker
        log.warning("run_job_failed", extra={"job_id": job_id, "error": str(exc)})
        j = store.load_job(job_id) or {}
        j.update(status="failed", stage="failed", error=str(exc))
        store.save_job(j)


def get_job_status(job_id: str) -> Any:
    """Return the current status/progress for a job (or ``None`` if unknown)."""
    return _store().load_job(job_id)
