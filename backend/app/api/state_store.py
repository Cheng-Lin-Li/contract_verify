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
