"""Playbook router: list + add company positions (3-month · SKELETON)."""
from __future__ import annotations
from typing import Any


def list_positions(contract_type: str | None = None) -> Any:
    """GET /api/playbook -> list[PlaybookPositionOut]."""
    raise NotImplementedError


def add_position(payload: Any) -> Any:
    """POST /api/playbook -> PlaybookPositionOut.

    Add/version a Layer-2 position and embed it into the vector store.
    """
    raise NotImplementedError
