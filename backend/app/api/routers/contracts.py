"""Contracts router: upload, verify, status, report (3-month · SKELETON)."""
from __future__ import annotations
from typing import Any


def create_contract(files: Any = None, contract_type: str | None = None) -> Any:
    """POST /api/contracts -> ContractCreateResponse.

    Accept the contract plus deal sources (multipart), persist blobs, create a
    verification job and enqueue it as a background task.
    """
    raise NotImplementedError


def get_job(job_id: str) -> Any:
    """GET /api/contracts/jobs/{job_id} -> JobOut (status/progress)."""
    raise NotImplementedError


def get_report(contract_id: str) -> Any:
    """GET /api/contracts/{contract_id}/report -> ReportOut (unified report)."""
    raise NotImplementedError


def reverify(contract_id: str) -> Any:
    """POST /api/contracts/{contract_id}/verify -> JobOut. Re-run verification."""
    raise NotImplementedError


def get_deployment() -> Any:
    """GET /api/deployment -> DeploymentOut (mode + residency, like CLI doctor)."""
    raise NotImplementedError
