"""SQLAlchemy ORM models (3-month scope · SKELETON).

Defines the persistent tables (users, contracts, jobs, reference items,
verification results, queue items, playbook versions) behind the storage
interface. Bodies/columns are to be filled in with the Alembic migration that
makes the schema reviewable evidence. Requires ``sqlalchemy>=2``.
"""

from __future__ import annotations


class Base:
    """Declarative base placeholder (replace with ``DeclarativeBase``)."""


class User:
    """users: id, username, password_hash, role, created_at."""


class Contract:
    """contracts: id, sha256, contract_type, uploaded_by, created_at."""


class Job:
    """jobs: id, contract_id, status, progress, error, timestamps."""


class ReferenceItemRow:
    """reference_items: item_id, contract_id, layer, text, type, priority, ..."""


class VerificationResultRow:
    """verification_results: item_id, layer, status, confidence, evidence JSONB."""


class QueueItem:
    """queue_items: queue_id, contract_id, item_id, reason, sla_due_at, state."""


class PlaybookVersion:
    """playbook_versions: item_id, version, text, rule, type, embedded_at."""
