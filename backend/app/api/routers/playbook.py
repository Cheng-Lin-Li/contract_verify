"""Playbook router: list company positions (demo: read the seeded library)."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends

from app.api.deps import get_current_user
from app.config import get_settings
from app.references.loaders import load_playbook

router = APIRouter()


@router.get("")
def list_positions(contract_type: Optional[str] = None, user=Depends(get_current_user)) -> list[dict]:
    """Return the Layer-2 playbook positions currently loaded."""
    try:
        items = load_playbook(get_settings().demo_playbook_dir)
    except Exception:
        return []
    return [
        {"item_id": it.item_id, "text": it.text, "type": it.type,
         "priority": getattr(it.priority, "value", str(it.priority)),
         "rule": getattr(it, "rule", None)}
        for it in items
    ]
