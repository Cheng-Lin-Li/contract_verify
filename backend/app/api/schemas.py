"""API request/response schemas (3-month scope).

Pydantic v2 models that define the HTTP contract between the React frontend
(`frontend/src/api`) and the FastAPI service (`app/api/routers`). These are the
*data shapes* and are defined concretely (no business logic); the endpoint
handlers that produce/consume them are skeletons raising ``NotImplementedError``.

Requires ``pydantic>=2`` (a 3-month dependency, see requirements-3month.txt).
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

Role = Literal["operator", "gc_team", "attorney", "admin", "auditor"]
JobStatus = Literal["queued", "running", "completed", "failed"]
LayerStatus = str  # Covered/Partial/Missing/... | Compliant/... | Present/...


# --- auth ------------------------------------------------------------------

class LoginRequest(BaseModel):
    """Credentials posted to ``POST /api/auth/login``."""
    username: str
    password: str


class TokenResponse(BaseModel):
    """JWT returned on successful login."""
    access_token: str
    token_type: str = "bearer"
    role: Role


class UserOut(BaseModel):
    """The authenticated user (``GET /api/auth/me``)."""
    id: str
    username: str
    role: Role


# --- contracts / verification ---------------------------------------------

class ContractCreateResponse(BaseModel):
    """Returned when a contract + deal sources are uploaded for verification."""
    contract_id: str
    job_id: str
    status: JobStatus


class JobOut(BaseModel):
    """Status of a verification job."""
    job_id: str
    contract_id: str
    status: JobStatus
    progress: float = Field(0.0, ge=0.0, le=1.0)
    error: Optional[str] = None


class ScoreSummary(BaseModel):
    """The five headline scores plus the gate decision."""
    coverage_score: float
    risk_score: int
    playbook_compliance: dict[str, int]
    standard_terms_completeness: dict[str, int]
    auto_confirm: bool
    blocking_reasons: list[str]


class ReportRowOut(BaseModel):
    """One reference item across any of the three layers, with citations."""
    item_id: str
    layer: int
    type: str
    priority: Optional[str] = None
    status: LayerStatus
    confidence: float
    requirement_text: str
    source_citation: Optional[dict] = None
    source_label: Optional[str] = None
    matched_clause_ids: list[str] = []
    superseded_by: Optional[str] = None
    notes: str = ""


class EntityOut(BaseModel):
    """A contract entity (party/date/amount/...) cited to a block."""
    value: str
    block_id: str


class ReportOut(BaseModel):
    """The full unified verification report for a contract."""
    contract_id: str
    scores: ScoreSummary
    rows: list[ReportRowOut]
    entities: dict[str, list[EntityOut] | Optional[str]] = {}
    attorney_queue: list[str] = []


# --- attorney queue --------------------------------------------------------

class QueueItemOut(BaseModel):
    """An item routed to the supervising attorney."""
    queue_id: str
    contract_id: str
    item_id: str
    layer: int
    status: LayerStatus
    reason: str
    risk_score: int
    sla_due_at: Optional[datetime] = None
    sla_state: Literal["ok", "warn", "breach"] = "ok"
    assigned_to: Optional[str] = None


class QueueActionRequest(BaseModel):
    """An attorney decision on a queue item."""
    action: Literal["approve", "approve_with_edits", "request_clarification",
                    "reject", "escalate", "add_to_playbook"]
    comment: Optional[str] = None
    edited_text: Optional[str] = None


# --- playbook --------------------------------------------------------------

class PlaybookPositionIn(BaseModel):
    """A new or updated company playbook position (Layer 2)."""
    text: str
    type: str
    priority: str = "High"
    rule: Literal["must_have", "must_not_have", "preferred"] = "must_have"


class PlaybookPositionOut(PlaybookPositionIn):
    """A stored playbook position."""
    item_id: str
    version: int


# --- audit / deployment ----------------------------------------------------

class AuditEventOut(BaseModel):
    """A single immutable audit event."""
    event_id: str
    occurred_at: datetime
    actor_role: Optional[str] = None
    event_type: str
    layer: Optional[int] = None
    doc_id: Optional[str] = None
    item_id: Optional[str] = None
    status: Optional[str] = None
    confidence: Optional[float] = None


class DeploymentOut(BaseModel):
    """Deployment mode + per-component residency (mirrors the CLI ``doctor``)."""
    mode: str
    residency: dict[str, str]
    warnings: list[str] = []
