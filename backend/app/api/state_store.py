"""File-backed report / job / queue store for the demo server.

Persists verification reports, upload jobs, and attorney-queue items under
``REPORTS_DIR`` so the SPA flow (upload -> poll job -> report -> queue) works in
a single-process demo. Production replaces this with Postgres + a task queue.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

from app.config import get_settings


def _root() -> Path:
    p = Path(get_settings().reports_dir)
    p.mkdir(parents=True, exist_ok=True)
    return p


def _file(kind: str, key: str) -> Path:
    return _root() / f"{kind}_{key}.json"


def _load_json(f: Path, default: Any) -> Any:
    if not f.exists():
        return default
    try:
        text = f.read_text(encoding="utf-8")
        return json.loads(text) if text.strip() else default
    except json.JSONDecodeError:
        return default


# --- reports ---------------------------------------------------------------

def save_report(contract_id: str, payload: dict[str, Any]) -> None:
    _file("report", contract_id).write_text(json.dumps(payload), encoding="utf-8")


def load_report(contract_id: str) -> Optional[dict[str, Any]]:
    return _load_json(_file("report", contract_id), None)


# --- jobs ------------------------------------------------------------------

def save_job(job: dict[str, Any]) -> None:
    _file("job", job["job_id"]).write_text(json.dumps(job), encoding="utf-8")


def load_job(job_id: str) -> Optional[dict[str, Any]]:
    return _load_json(_file("job", job_id), None)


# --- attorney queue --------------------------------------------------------

def save_queue_items(items: list[dict[str, Any]]) -> None:
    existing = {it["queue_id"]: it for it in load_queue_items()}
    for it in items:
        existing[it["queue_id"]] = it
    (_root() / "queue.json").write_text(json.dumps(list(existing.values())), encoding="utf-8")


def load_queue_items() -> list[dict[str, Any]]:
    return _load_json(_root() / "queue.json", [])


def update_queue_item(queue_id: str, **changes: Any) -> Optional[dict[str, Any]]:
    items = load_queue_items()
    found = None
    for it in items:
        if it["queue_id"] == queue_id:
            it.update(changes)
            found = it
    if found is not None:
        (_root() / "queue.json").write_text(json.dumps(items), encoding="utf-8")
    return found


# --- CIR documents --------------------------------------------------------

def save_cir(doc_id: str, cir_dict: dict[str, Any]) -> None:
    _file("cir", doc_id).write_text(json.dumps(cir_dict), encoding="utf-8")


def load_cir(doc_id: str) -> Optional[dict[str, Any]]:
    return _load_json(_file("cir", doc_id), None)


# --- contract → source document list -------------------------------------

def save_contract_sources(contract_id: str, sources: list[dict[str, Any]]) -> None:
    _file("sources", contract_id).write_text(json.dumps(sources), encoding="utf-8")


def load_contract_sources(contract_id: str) -> list[dict[str, Any]]:
    return _load_json(_file("sources", contract_id), [])


def delete_contract(contract_id: str) -> None:
    """Remove all persisted state for a contract (report, CIRs, sources, job, queue items)."""
    root = _root()

    # Collect deal-source doc_ids before removing the sources file.
    source_doc_ids = [s.get("doc_id", "") for s in load_contract_sources(contract_id)]

    # Remove CIR files for the contract and each deal source.
    for doc_id in [contract_id] + source_doc_ids:
        if doc_id:
            f = _file("cir", doc_id)
            if f.exists():
                f.unlink()

    # Remove report and sources index files.
    for kind in ("report", "sources"):
        f = _file(kind, contract_id)
        if f.exists():
            f.unlink()

    # Remove job files that reference this contract.
    for job_file in root.glob("job_*.json"):
        try:
            job = json.loads(job_file.read_text(encoding="utf-8"))
            if job.get("contract_id") == contract_id:
                job_file.unlink()
        except Exception:  # noqa: BLE001
            pass

    # Remove queue items that belong to this contract.
    remaining = [it for it in load_queue_items() if it.get("contract_id") != contract_id]
    (root / "queue.json").write_text(json.dumps(remaining), encoding="utf-8")


# --- library document index -----------------------------------------------

def _library_docs_file(layer: str) -> Path:
    return _root() / f"library_docs_{layer}.json"


def append_library_docs(layer: str, new_docs: list[dict[str, Any]]) -> None:
    f = _library_docs_file(layer)
    existing: list[dict[str, Any]] = _load_json(f, [])
    ids = {d["doc_id"] for d in existing}
    for doc in new_docs:
        if doc["doc_id"] not in ids:
            existing.append(doc)
    f.write_text(json.dumps(existing), encoding="utf-8")


def load_library_docs(layer: str) -> list[dict[str, Any]]:
    return _load_json(_library_docs_file(layer), [])


def delete_library_doc_entry(layer: str, doc_id: str) -> None:
    """Remove one document record from the library docs index."""
    f = _library_docs_file(layer)
    if not f.exists():
        return
    docs = _load_json(f, [])
    docs = [d for d in docs if d.get("doc_id") != doc_id]
    f.write_text(json.dumps(docs), encoding="utf-8")


def find_library_duplicate_filenames(layer: str, filenames: list[str]) -> list[str]:
    """Return filenames that already exist in the library docs index."""
    existing = {d.get("filename") for d in load_library_docs(layer)}
    return [fn for fn in filenames if fn in existing]


def get_used_item_ids() -> set[str]:
    """Return all item_ids referenced in any completed verification report."""
    root = _root()
    used: set[str] = set()
    for f in root.glob("report_*.json"):
        try:
            payload = json.loads(f.read_text(encoding="utf-8"))
            for row in payload.get("report", {}).get("rows", []):
                if row.get("item_id"):
                    used.add(row["item_id"])
        except Exception:  # noqa: BLE001
            pass
    return used


# --- contracts list --------------------------------------------------------

def _queue_review_status(items: list[dict]) -> tuple[int, Optional[str]]:
    """Return (pending_count, review_status) for a contract's queue items.

    Priority: rejected > escalated > in_review > pending > cleared > None.
    """
    if not items:
        return 0, None
    pending_items = [it for it in items if not it.get("resolved")]
    resolved_items = [it for it in items if it.get("resolved")]
    actions = {it.get("attorney_action") for it in resolved_items}
    if "reject" in actions:
        rs = "rejected"
    elif "escalate" in actions:
        rs = "escalated"
    elif pending_items:
        rs = "pending" if not resolved_items else "in_review"
    else:
        rs = "cleared"
    return len(pending_items), rs


def list_contracts() -> list[dict[str, Any]]:
    """Return a summary of every contract, newest-submitted first.

    Completed contracts come from their ``report_*.json`` file; contracts that
    are still running, queued, or failed (no report yet) come from the matching
    ``job_*.json`` file.
    """
    root = _root()

    # Build queue index once: contract_id → list[queue_item]
    queue_by_contract: dict[str, list[dict]] = {}
    for it in load_queue_items():
        cid = it.get("contract_id", "")
        queue_by_contract.setdefault(cid, []).append(it)

    # Build filename/job index from job files (job dict always has contract_filename).
    filename_by_cid: dict[str, str] = {}
    # (contract_id or job_id) → (job_dict, file_mtime)
    jobs: list[tuple[dict, float]] = []
    for f in root.glob("job_*.json"):
        try:
            job = json.loads(f.read_text(encoding="utf-8"))
            mtime = f.stat().st_mtime
            jobs.append((job, mtime))
            cid = job.get("contract_id", "")
            fname = job.get("contract_filename") or ""
            if cid and fname:
                filename_by_cid[cid] = fname
        except Exception:  # noqa: BLE001
            pass

    completed: list[dict[str, Any]] = []

    for f in root.glob("report_*.json"):
        try:
            payload = json.loads(f.read_text(encoding="utf-8"))
            contract_id = f.stem.removeprefix("report_")
            rep = payload.get("report", {})
            q_pending, r_status = _queue_review_status(queue_by_contract.get(contract_id, []))
            # Try job file first; fall back to CIR metadata for legacy contracts.
            contract_filename = filename_by_cid.get(contract_id)
            if not contract_filename:
                cir = load_cir(contract_id)
                if cir:
                    contract_filename = (cir.get("metadata") or {}).get("filename")
            completed.append({
                "contract_id": contract_id,
                "status": "completed",
                "coverage_score": rep.get("coverage_score"),
                "risk_score": rep.get("risk_score"),
                "auto_confirm": rep.get("auto_confirm"),
                "blocking_count": len(rep.get("blocking_reasons", [])),
                "submitted_at": f.stat().st_mtime,
                "contract_filename": contract_filename,
                "error": None,
                "stage": "done",
                "progress": 1.0,
                "queue_pending": q_pending,
                "review_status": r_status,
            })
        except Exception:  # noqa: BLE001
            pass

    completed_ids = {c["contract_id"] for c in completed}
    pending: list[dict[str, Any]] = []

    for job, mtime in jobs:
        cid = job.get("contract_id", "")
        if cid and cid in completed_ids:
            continue  # already represented by its report
        if job.get("status") in ("running", "queued", "failed"):
            pending.append({
                "contract_id": cid or "",
                "job_id": job.get("job_id"),
                "status": job.get("status"),
                "coverage_score": None,
                "risk_score": None,
                "auto_confirm": None,
                "blocking_count": 0,
                "submitted_at": mtime,
                "contract_filename": job.get("contract_filename"),
                "error": job.get("error"),
                "stage": job.get("stage"),
                "progress": job.get("progress", 0.0),
                "queue_pending": 0,
                "review_status": None,
            })

    all_items = pending + completed
    return sorted(all_items, key=lambda x: x.get("submitted_at") or 0, reverse=True)
