"""Audit router: read the immutable trail for a document (3-month · SKELETON)."""
from __future__ import annotations
from typing import Any


def get_audit(doc_id: str) -> Any:
    """GET /api/audit/{doc_id} -> list[AuditEventOut] (read-only)."""
    raise NotImplementedError
