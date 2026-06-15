"""Background verification jobs (3-month scope · SKELETON).

Runs the existing pipeline (app/pipeline.py) off the request thread via
FastAPI BackgroundTasks (Celery+Redis at scale is backlog), updating job
status/progress and persisting the report.
"""

from __future__ import annotations

from typing import Any


def create_job(contract_id: str, source_ids: list[str], *,
               contract_type: str | None) -> str:
    """Create a queued job row; return its job_id."""
    raise NotImplementedError


def run_job(job_id: str) -> None:
    """Execute the verification pipeline for a job, updating progress/status."""
    raise NotImplementedError


def get_job_status(job_id: str) -> Any:
    """Return the current status/progress for a job."""
    raise NotImplementedError
