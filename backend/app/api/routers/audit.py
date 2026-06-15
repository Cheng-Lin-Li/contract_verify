"""Audit router: read the immutable trail for a document (demo: JSONL tail)."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends

from app.api.deps import require_role
from app.config import get_settings

router = APIRouter()


@router.get("/{doc_id}")
def get_audit(doc_id: str, user=Depends(require_role("attorney", "admin", "auditor"))) -> list[dict]:
    """Return audit events referencing ``doc_id`` from the JSONL log."""
    path = Path(get_settings().audit_log_path)
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            ev = json.loads(line)
        except json.JSONDecodeError:
            continue
        if ev.get("doc_id") == doc_id:
            out.append(ev)
    return out
