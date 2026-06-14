"""Enumerations shared across the three-layer verification engine.

These enums define the controlled vocabularies used throughout the pipeline:
document roles, reference layers, requirement priorities, playbook rule kinds,
and the per-layer verification status taxonomies described in the TDD (§6).

Keeping these as ``str``-valued enums means they serialise cleanly to JSON for
the report and the audit trail while still giving callers type-safe constants.
"""

from __future__ import annotations

from enum import Enum


class DocRole(str, Enum):
    """The role a document plays in a verification run.

    ``DEAL_SOURCE`` documents feed Layer-1 requirement extraction; ``CONTRACT``
    is the single target every layer is matched against; ``PLAYBOOK`` and
    ``STANDARD_TERMS`` are the pre-loaded reference libraries for Layers 2 and 3.
    """

    DEAL_SOURCE = "deal_source"
    CONTRACT = "contract"
    PLAYBOOK = "playbook"
    STANDARD_TERMS = "standard_terms"


class Layer(int, Enum):
    """The reference layer a :class:`ReferenceItem` belongs to.

    1 = business requirements, 2 = internal playbook, 3 = standard contract terms.
    """

    REQUIREMENTS = 1
    PLAYBOOK = 2
    STANDARD_TERMS = 3


class Priority(str, Enum):
    """Business priority of a requirement, driving the coverage weighting."""

    CRITICAL = "Critical"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"


class PlaybookRule(str, Enum):
    """The kind of position a Layer-2 playbook item expresses."""

    MUST_HAVE = "must_have"
    MUST_NOT_HAVE = "must_not_have"
    PREFERRED = "preferred"


class L1Status(str, Enum):
    """Layer-1 (requirements) coverage status taxonomy (PRD §5)."""

    COVERED = "Covered"
    PARTIAL = "Partial"
    MISSING = "Missing"
    CONTRADICTED = "Contradicted"
    SUPERSEDED = "Superseded"


class L2Status(str, Enum):
    """Layer-2 (playbook) compliance status taxonomy."""

    COMPLIANT = "Compliant"
    DEVIATION = "Deviation"
    VIOLATION = "Violation"


class L3Status(str, Enum):
    """Layer-3 (standard terms) completeness status taxonomy."""

    PRESENT = "Present"
    MISSING = "Missing"
    NON_STANDARD = "Non-standard"


# Mapping of a layer to its valid status enum, used by validators/tests.
LAYER_STATUS = {
    Layer.REQUIREMENTS: L1Status,
    Layer.PLAYBOOK: L2Status,
    Layer.STANDARD_TERMS: L3Status,
}

# Priority -> weight, per the Coverage Score formula (PRD/TDD §9).
PRIORITY_WEIGHT = {
    Priority.CRITICAL: 4,
    Priority.HIGH: 3,
    Priority.MEDIUM: 2,
    Priority.LOW: 1,
}

# Layer-1 status -> coverage credit, per the Coverage Score formula.
COVERAGE_CREDIT = {
    L1Status.COVERED: 1.0,
    L1Status.PARTIAL: 0.5,
    L1Status.SUPERSEDED: 1.0,  # credited only when the superseding ask is covered
    L1Status.MISSING: 0.0,
    L1Status.CONTRADICTED: 0.0,
}
