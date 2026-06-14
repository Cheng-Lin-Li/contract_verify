"""Canonical data models for the verification pipeline.

These are implemented as stdlib :mod:`dataclasses` so the MVP runs with no
third-party validation dependency (and therefore air-gapped / on a minimal
host). The 3-month build introduces Pydantic v2 at the API boundary (TDD §4.1);
the field shapes here intentionally mirror the schemas in TDD §5 and §6 so that
migration is a swap, not a redesign.

Models
------
* :class:`CIRBlock` / :class:`CIRDocument` -- the Canonical Internal
  Representation every input normalises into (TDD §5).
* :class:`ReferenceItem` -- the common shape extracted from all three layers
  (TDD §6).
* :class:`VerificationResult` -- the per-item verification outcome (TDD §6).
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import asdict, dataclass, field
from typing import Any, Optional

from app.core.enums import DocRole, Layer, PlaybookRule, Priority


def new_uuid() -> str:
    """Return a fresh random UUID4 string (used for ``doc_id`` defaults)."""
    return str(uuid.uuid4())


def sha256_bytes(data: bytes) -> str:
    """Return the hex SHA-256 digest of ``data``.

    Used to fingerprint ingested blobs for the CIR and the audit trail.
    """
    return hashlib.sha256(data).hexdigest()


@dataclass
class CIRBlock:
    """A single normalised content block within a document.

    Attributes:
        block_id: Stable identifier, unique within the document (e.g. ``b-001``).
        type: One of ``paragraph``, ``table`` or ``image``.
        page: 1-based page number the block was found on.
        text: Plain-text content (empty string for pure-image blocks).
        bbox: Optional bounding box ``{x0, y0, x1, y1}`` for precise citation.
        ocr_conf: OCR confidence in ``[0, 1]`` when produced by OCR, else ``None``.
        table: For ``table`` blocks, a row/column matrix of cell strings.
    """

    block_id: str
    type: str
    page: int = 1
    text: str = ""
    bbox: Optional[dict[str, float]] = None
    ocr_conf: Optional[float] = None
    table: Optional[list[list[str]]] = None

    def to_dict(self) -> dict[str, Any]:
        """Serialise the block to a plain dict for JSON output."""
        return asdict(self)


@dataclass
class CIRDocument:
    """The Canonical Internal Representation of one ingested document.

    Every parser (PDF, DOCX, email, text) emits this shape so downstream
    extraction, matching and citation logic is format-agnostic (TDD §5).

    Attributes:
        doc_id: UUID identifying this document instance.
        role: The :class:`DocRole` this document plays in the run.
        format: Source format, e.g. ``pdf``/``docx``/``eml``/``txt``.
        sha256: SHA-256 of the original bytes, for audit fingerprinting.
        pages: Page count (1 for formats without pages).
        blocks: Ordered list of :class:`CIRBlock`.
        metadata: Free-form source metadata (email ``from``/``subject``/``date``).
    """

    role: DocRole
    format: str
    doc_id: str = field(default_factory=new_uuid)
    sha256: str = ""
    pages: int = 1
    blocks: list[CIRBlock] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def full_text(self) -> str:
        """Return all block text concatenated, one block per line."""
        return "\n".join(b.text for b in self.blocks if b.text)

    def to_dict(self) -> dict[str, Any]:
        """Serialise the document (and its blocks) to a JSON-ready dict."""
        d = asdict(self)
        d["role"] = self.role.value if isinstance(self.role, DocRole) else self.role
        return d


@dataclass
class SourceRef:
    """A pointer back to where a reference item was found (Layer 1 only)."""

    doc_id: str
    block_id: str
    page: int = 1
    line: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ReferenceItem:
    """A single extracted reference, common to all three layers (TDD §6).

    Attributes:
        item_id: Stable id, prefixed by layer (``r-007``/``pb-012``/``st-003``).
        layer: The :class:`Layer` this item belongs to.
        text: The natural-language statement of the requirement/rule/term.
        type: Coarse category (``payment``, ``data``, ``SLA``, ``IP`` ...).
        priority: Business :class:`Priority` (drives coverage weighting).
        source_ref: Where it came from (Layer-1 deal sources only).
        rule: ``must_have``/``must_not_have``/``preferred`` (Layer-2 only).
        binding: Whether it derives from a binding source (signed term sheet)
            versus a casual email (Layer-1 only).
    """

    item_id: str
    layer: Layer
    text: str
    type: str = "general"
    priority: Priority = Priority.MEDIUM
    source_ref: Optional[SourceRef] = None
    rule: Optional[PlaybookRule] = None
    binding: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "layer": int(self.layer),
            "text": self.text,
            "type": self.type,
            "priority": self.priority.value,
            "source_ref": self.source_ref.to_dict() if self.source_ref else None,
            "rule": self.rule.value if self.rule else None,
            "binding": self.binding,
        }


@dataclass
class VerificationResult:
    """The outcome of matching one :class:`ReferenceItem` against the contract.

    Attributes:
        item_id: The reference item this result is for.
        layer: Its layer (selects which status enum ``status`` belongs to).
        status: The per-layer status string (e.g. ``Covered``/``Violation``).
        matched_clause_ids: Contract ``block_id``\\ s that satisfy/relate to it.
        confidence: Per-determination confidence in ``[0, 1]`` (TDD §9).
        evidence: ``{"source_ref": ..., "contract_ref": ...}`` citation payload.
        notes: Free-form rationale from the verifier.
    """

    item_id: str
    layer: Layer
    status: str
    matched_clause_ids: list[str] = field(default_factory=list)
    confidence: float = 0.0
    evidence: dict[str, Any] = field(default_factory=dict)
    notes: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "layer": int(self.layer),
            "status": self.status,
            "matched_clause_ids": self.matched_clause_ids,
            "confidence": round(self.confidence, 4),
            "evidence": self.evidence,
            "notes": self.notes,
        }
