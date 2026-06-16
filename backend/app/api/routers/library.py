"""Library router: upload playbook and standard-terms files (PDF/DOCX/YAML).

Each upload job ingests the files page-by-page (with OCR when needed), then
uses the configured LLM to extract structured items (type, priority, rule /
contract_type) from the ingested text. The job record is updated at every
stage so the frontend can show per-page and per-document progress.

Progress fields on the job:
  stage       : "ingest" | "extract" | "done"
  current_page: page being parsed (ingest) or doc index (extract)
  total_pages : total pages / total docs for the current stage
  stage_file  : filename currently being processed
"""

from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

import yaml
from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile

from app.api import state_store
from app.api.deps import get_current_user
from app.api.schemas import JobOut
from app.config import get_settings
from app.core.enums import DocRole
from app.ingestion.ingest_service import IngestService
from app.llm.factory import get_provider
from app.logging_setup import get_logger
from app.references.extractor import LibraryExtractor

router = APIRouter()
log = get_logger("api.library")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _update_job(job_id: str, **kwargs) -> None:
    job = state_store.load_job(job_id) or {}
    job.update(kwargs)
    state_store.save_job(job)


def _run_library_ingest(
    job_id: str,
    layer: str,
    uploads: list[tuple[str, bytes]],
    output_dir: str,
) -> None:
    """Background task: ingest → LLM extract → write YAML.

    Args:
        job_id:     State-store key updated with progress as work proceeds.
        layer:      ``"playbook"`` or ``"standard_terms"``.
        uploads:    ``[(filename, raw_bytes), ...]`` pairs from the multipart upload.
        output_dir: Directory where the resulting YAML is written.
    """
    total_files = len(uploads)
    ingest_svc = IngestService()
    role = DocRole.PLAYBOOK if layer == "playbook" else DocRole.STANDARD_TERMS
    all_docs = []

    try:
        # ---- Stage 1: ingest (page-level progress per file) ---------------
        _update_job(job_id, status="running", stage="ingest", progress=0.0,
                    current_page=0, total_pages=0, stage_file="")

        for file_idx, (filename, data) in enumerate(uploads):

            def _make_cb(fname: str, fidx: int):
                def _cb(current: int, total: int) -> None:
                    file_done = fidx / total_files
                    within = (current / total / total_files) if total > 0 else 0.0
                    _update_job(
                        job_id,
                        stage="ingest",
                        current_page=current,
                        total_pages=total,
                        stage_file=fname,
                        progress=round(file_done + within, 3),
                    )
                return _cb

            doc = ingest_svc.ingest_bytes(
                data, filename, role,
                progress_callback=_make_cb(filename, file_idx),
            )
            all_docs.append(doc)
            log.info("library_file_ingested",
                     extra={"job_id": job_id, "filename": filename,
                            "blocks": len(doc.blocks)})

        # ---- Stage 2: LLM extraction (per-document progress) --------------
        _update_job(job_id, stage="extract", progress=0.85,
                    current_page=0, total_pages=total_files, stage_file="")

        settings = get_settings()
        extractor = LibraryExtractor(get_provider(settings))
        all_items: list[dict] = []

        for doc_idx, doc in enumerate(all_docs):
            fname = (doc.metadata or {}).get("filename", f"doc-{doc_idx + 1}")
            _update_job(job_id, current_page=doc_idx + 1,
                        total_pages=total_files, stage_file=fname,
                        progress=round(0.85 + 0.12 * (doc_idx / total_files), 3))

            if layer == "playbook":
                items = extractor.extract_playbook(doc, start_index=len(all_items))
            else:
                items = extractor.extract_standard_terms(doc, start_index=len(all_items))
            # Tag every item with the source document so we can group and delete later.
            for item in items:
                item["source_doc_id"] = doc.doc_id
            all_items.extend(items)
            log.info("library_doc_extracted",
                     extra={"job_id": job_id, "filename": fname, "items": len(items)})

        # ---- Stage 3: write YAML + persist CIRs for viewer ------------------
        out_path = Path(output_dir)
        out_path.mkdir(parents=True, exist_ok=True)
        yaml_path = out_path / f"uploaded_{job_id[:8]}.yaml"
        yaml_path.write_text(
            yaml.dump(all_items, allow_unicode=True, sort_keys=False),
            encoding="utf-8",
        )
        log.info("library_saved",
                 extra={"job_id": job_id, "layer": layer,
                        "items": len(all_items), "path": str(yaml_path)})

        doc_infos = []
        for doc in all_docs:
            state_store.save_cir(doc.doc_id, doc.to_dict())
            doc_infos.append({
                "doc_id": doc.doc_id,
                "filename": (doc.metadata or {}).get("filename", doc.doc_id[:8]),
                "format": doc.format,
                "role": doc.role.value if hasattr(doc.role, "value") else str(doc.role),
                "yaml_file": str(yaml_path),
            })
        state_store.append_library_docs(layer, doc_infos)

        _update_job(job_id, status="completed", stage="done", progress=1.0,
                    error=None, current_page=len(all_items), total_pages=len(all_items))

    except Exception as exc:  # noqa: BLE001
        log.error("library_ingest_failed", extra={"job_id": job_id, "error": str(exc)})
        _update_job(job_id, status="failed", error=str(exc))


def _start_library_job(
    layer: str,
    files: list[UploadFile],
    output_dir: str,
    background_tasks: BackgroundTasks,
) -> JobOut:
    """Read uploads, create the initial job record, enqueue the background task."""
    uploads = [(f.filename or f"file_{i}", f.file.read()) for i, f in enumerate(files)]
    job_id = uuid.uuid4().hex
    job: dict = {
        "job_id": job_id,
        "contract_id": "",
        "status": "queued",
        "progress": 0.0,
        "error": None,
        "stage": "queued",
        "current_page": 0,
        "total_pages": 0,
        "stage_file": uploads[0][0] if uploads else "",
    }
    state_store.save_job(job)
    background_tasks.add_task(_run_library_ingest, job_id, layer, uploads, output_dir)
    return JobOut(**job)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/playbook", response_model=JobOut)
def upload_playbook(
    files: list[UploadFile] = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user=Depends(get_current_user),
) -> JobOut:
    """Upload one or more playbook files (PDF / DOCX).

    Returns 409 if any filename was already uploaded — delete the existing
    version first. Poll ``GET /api/contracts/jobs/{job_id}`` for progress.
    """
    s = get_settings()
    filenames = [f.filename or f"file_{i}" for i, f in enumerate(files)]
    dupes = state_store.find_library_duplicate_filenames("playbook", filenames)
    if dupes:
        raise HTTPException(
            status_code=409,
            detail={"type": "duplicate", "filenames": dupes},
        )
    return _start_library_job("playbook", files, s.library_playbook_dir, background_tasks)


@router.post("/standard-terms", response_model=JobOut)
def upload_standard_terms(
    files: list[UploadFile] = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    user=Depends(get_current_user),
) -> JobOut:
    """Upload one or more standard-terms files (PDF / DOCX).

    Returns 409 if any filename was already uploaded. Same flow as
    ``/library/playbook`` but items carry ``contract_type`` instead of ``rule``.
    """
    s = get_settings()
    filenames = [f.filename or f"file_{i}" for i, f in enumerate(files)]
    dupes = state_store.find_library_duplicate_filenames("standard_terms", filenames)
    if dupes:
        raise HTTPException(
            status_code=409,
            detail={"type": "duplicate", "filenames": dupes},
        )
    return _start_library_job(
        "standard_terms", files, s.library_standard_terms_dir, background_tasks
    )


@router.get("/playbook", response_model=list[dict])
def list_playbook(user=Depends(get_current_user)) -> list[dict]:
    """List all playbook items currently in the library (demo + uploaded).

    Demo items have ``source_doc_id=null``; uploaded items carry the doc_id of
    the source document they were extracted from.
    """
    from app.references.loaders import load_playbook
    s = get_settings()
    items: list[dict] = []

    # Demo items — loaded via the structured loader (no source_doc_id).
    try:
        for it in load_playbook(s.demo_playbook_dir):
            items.append({
                "item_id": it.item_id, "text": it.text, "type": it.type,
                "priority": getattr(it.priority, "value", str(it.priority)),
                "rule": getattr(it, "rule", None),
                "source_doc_id": None,
            })
    except FileNotFoundError:
        pass

    # Uploaded items — read raw YAML to preserve source_doc_id.
    lib_dir = Path(s.library_playbook_dir)
    if lib_dir.exists():
        for yaml_file in sorted(lib_dir.glob("*.y*ml")):
            try:
                raw = yaml.safe_load(yaml_file.read_text(encoding="utf-8")) or []
                for it_dict in raw if isinstance(raw, list) else []:
                    items.append({
                        "item_id": it_dict.get("id") or it_dict.get("item_id", ""),
                        "text": it_dict.get("text", ""),
                        "type": it_dict.get("type", ""),
                        "priority": it_dict.get("priority", ""),
                        "rule": it_dict.get("rule"),
                        "source_doc_id": it_dict.get("source_doc_id"),
                    })
            except Exception:  # noqa: BLE001
                pass

    return items


@router.get("/standard-terms", response_model=list[dict])
def list_standard_terms(
    contract_type: Optional[str] = None,
    user=Depends(get_current_user),
) -> list[dict]:
    """List all standard-terms items currently in the library (demo + uploaded).

    Demo items have ``source_doc_id=null``; uploaded items carry the doc_id.
    """
    from app.references.loaders import load_standard_terms
    s = get_settings()
    items: list[dict] = []

    # Demo items.
    try:
        for it in load_standard_terms(s.demo_standard_terms_dir, contract_type=contract_type):
            items.append({
                "item_id": it.item_id, "text": it.text, "type": it.type,
                "priority": getattr(it.priority, "value", str(it.priority)),
                "source_doc_id": None,
            })
    except FileNotFoundError:
        pass

    # Uploaded items — read raw YAML.
    lib_dir = Path(s.library_standard_terms_dir)
    if lib_dir.exists():
        for yaml_file in sorted(lib_dir.glob("*.y*ml")):
            try:
                raw = yaml.safe_load(yaml_file.read_text(encoding="utf-8")) or []
                for it_dict in raw if isinstance(raw, list) else []:
                    ct = it_dict.get("contract_type")
                    if contract_type and ct not in (None, contract_type):
                        continue
                    items.append({
                        "item_id": it_dict.get("id") or it_dict.get("item_id", ""),
                        "text": it_dict.get("text", ""),
                        "type": it_dict.get("type", ""),
                        "priority": it_dict.get("priority", ""),
                        "source_doc_id": it_dict.get("source_doc_id"),
                    })
            except Exception:  # noqa: BLE001
                pass

    return items


@router.get("/playbook/documents", response_model=list[dict])
def list_playbook_documents(user=Depends(get_current_user)) -> list[dict]:
    """List uploaded playbook source documents (with doc_id for the viewer)."""
    return state_store.load_library_docs("playbook")


@router.get("/standard-terms/documents", response_model=list[dict])
def list_standard_terms_documents(user=Depends(get_current_user)) -> list[dict]:
    """List uploaded standard-terms source documents (with doc_id for the viewer)."""
    return state_store.load_library_docs("standard_terms")


# ---------------------------------------------------------------------------
# Delete document endpoints
# ---------------------------------------------------------------------------

def _delete_library_document(layer: str, doc_id: str, lib_dir: str) -> dict:
    """Core delete logic shared by both layer endpoints."""
    docs = state_store.load_library_docs(layer)
    doc_info = next((d for d in docs if d.get("doc_id") == doc_id), None)
    if not doc_info:
        raise HTTPException(status_code=404, detail="Document not found")

    # Collect item IDs that belong to this document by scanning the YAML.
    yaml_file_path = doc_info.get("yaml_file")
    item_ids_in_doc: list[str] = []
    if yaml_file_path:
        try:
            raw = yaml.safe_load(Path(yaml_file_path).read_text(encoding="utf-8")) or []
            for it in raw if isinstance(raw, list) else []:
                if it.get("source_doc_id") == doc_id:
                    item_ids_in_doc.append(it.get("id") or it.get("item_id", ""))
        except Exception:  # noqa: BLE001
            pass

    # Block deletion if any items are referenced in existing reports.
    if item_ids_in_doc:
        used = state_store.get_used_item_ids()
        referenced = [iid for iid in item_ids_in_doc if iid in used]
        if referenced:
            raise HTTPException(
                status_code=409,
                detail={
                    "type": "referenced",
                    "count": len(referenced),
                    "item_ids": referenced[:10],
                },
            )

    # Remove items from YAML (or delete the file if it becomes empty).
    if yaml_file_path:
        try:
            p = Path(yaml_file_path)
            raw = yaml.safe_load(p.read_text(encoding="utf-8")) or []
            remaining = [it for it in (raw if isinstance(raw, list) else [])
                         if it.get("source_doc_id") != doc_id]
            if remaining:
                p.write_text(
                    yaml.dump(remaining, allow_unicode=True, sort_keys=False),
                    encoding="utf-8",
                )
            elif p.exists():
                p.unlink()
        except Exception:  # noqa: BLE001
            pass

    state_store.delete_library_doc_entry(layer, doc_id)
    log.info("library_doc_deleted",
             extra={"layer": layer, "doc_id": doc_id, "items_removed": len(item_ids_in_doc)})
    return {"deleted": True, "items_removed": len(item_ids_in_doc)}


@router.delete("/playbook/documents/{doc_id}")
def delete_playbook_document(
    doc_id: str,
    user=Depends(get_current_user),
) -> dict:
    """Delete an uploaded playbook document and all items extracted from it.

    Returns 409 if any of its items are referenced in an existing verification
    report — resolve or delete those reports first.
    """
    s = get_settings()
    return _delete_library_document("playbook", doc_id, s.library_playbook_dir)


@router.delete("/standard-terms/documents/{doc_id}")
def delete_standard_terms_document(
    doc_id: str,
    user=Depends(get_current_user),
) -> dict:
    """Delete an uploaded standard-terms document and all items extracted from it.

    Returns 409 if any of its items are referenced in an existing verification
    report — resolve or delete those reports first.
    """
    s = get_settings()
    return _delete_library_document("standard_terms", doc_id, s.library_standard_terms_dir)
