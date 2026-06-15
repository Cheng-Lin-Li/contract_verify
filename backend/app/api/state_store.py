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


# --- reports ---------------------------------------------------------------

def save_report(contract_id: str, payload: dict[str, Any]) -> None:
    _file("report", contract_id).write_text(json.dumps(payload), encoding="utf-8")


def load_report(contract_id: str) -> Optional[dict[str, Any]]:
    f = _file("report", contract_id)
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


# --- jobs ------------------------------------------------------------------

def save_job(job: dict[str, Any]) -> None:
    _file("job", job["job_id"]).write_text(json.dumps(job), encoding="utf-8")


def load_job(job_id: str) -> Optional[dict[str, Any]]:
    f = _file("job", job_id)
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


# --- attorney queue --------------------------------------------------------

def save_queue_items(items: list[dict[str, Any]]) -> None:
    existing = {it["queue_id"]: it for it in load_queue_items()}
    for it in items:
        existing[it["queue_id"]] = it
    (_root() / "queue.json").write_text(json.dumps(list(existing.values())), encoding="utf-8")


def load_queue_items() -> list[dict[str, Any]]:
    f = _root() / "queue.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []


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


# --- contracts list --------------------------------------------------------

# --- CIR documents --------------------------------------------------------

def save_cir(doc_id: str, cir_dict: dict[str, Any]) -> None:
    _file("cir", doc_id).write_text(json.dumps(cir_dict), encoding="utf-8")


def load_cir(doc_id: str) -> Optional[dict[str, Any]]:
    f = _file("cir", doc_id)
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else None


# --- contract → source document list -------------------------------------

def save_contract_sources(contract_id: str, sources: list[dict[str, Any]]) -> None:
    _file("sources", contract_id).write_text(json.dumps(sources), encoding="utf-8")


def load_contract_sources(contract_id: str) -> list[dict[str, Any]]:
    f = _file("sources", contract_id)
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []


# --- library document index -----------------------------------------------

def _library_docs_file(layer: str) -> Path:
    return _root() / f"library_docs_{layer}.json"


def append_library_docs(layer: str, new_docs: list[dict[str, Any]]) -> None:
    f = _library_docs_file(layer)
    existing: list[dict[str, Any]] = json.loads(f.read_text(encoding="utf-8")) if f.exists() else []
    ids = {d["doc_id"] for d in existing}
    for doc in new_docs:
        if doc["doc_id"] not in ids:
            existing.append(doc)
    f.write_text(json.dumps(existing), encoding="utf-8")


def load_library_docs(layer: str) -> list[dict[str, Any]]:
    f = _library_docs_file(layer)
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else []


# --- contracts list --------------------------------------------------------

def list_contracts() -> list[dict[str, Any]]:
    """Return a summary of every contract, newest-submitted first.

    Completed contracts come from their ``report_*.json`` file; contracts that
    are still running, queued, or failed (no report yet) come from the matching
    ``job_*.json`` file.
    """
    root = _root()
    completed: list[dict[str, Any]] = []

    for f in root.glob("report_*.json"):
        try:
            payload = json.loads(f.read_text(encoding="utf-8"))
            contract_id = f.stem.removeprefix("report_")
            rep = payload.get("report", {})
            completed.append({
                "contract_id": contract_id,
                "status": "completed",
                "coverage_score": rep.get("coverage_score"),
                "risk_score": rep.get("risk_score"),
                "auto_confirm": rep.get("auto_confirm"),
                "blocking_count": len(rep.get("blocking_reasons", [])),
                "submitted_at": f.stat().st_mtime,
                "contract_filename": None,
                "error": None,
                "stage": "done",
                "progress": 1.0,
            })
        except Exception:  # noqa: BLE001
            pass

    completed_ids = {c["contract_id"] for c in completed}
    pending: list[dict[str, Any]] = []

    for f in root.glob("job_*.json"):
        try:
            job = json.loads(f.read_text(encoding="utf-8"))
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
                    "submitted_at": f.stat().st_mtime,
                    "contract_filename": job.get("contract_filename"),
                    "error": job.get("error"),
                    "stage": job.get("stage"),
                    "progress": job.get("progress", 0.0),
                })
        except Exception:  # noqa: BLE001
            pass

    all_items = pending + completed
    return sorted(all_items, key=lambda x: x.get("submitted_at") or 0, reverse=True)
