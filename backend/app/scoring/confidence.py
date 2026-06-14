"""Confidence Score (TDD §9 / PRD §6.4).

Per-determination confidence that gates all three layers::

    CS = 0.30·extract + 0.30·match + 0.20·(1 - contradiction)
         + 0.15·llm + 0.05·source

    CS < 0.70  -> route to human confirmation (even if status reads positive)
    CS >= 0.85 -> eligible for auto-confirmation

The weights are the design baseline; they are read as named constants here so a
deployment can override them without touching the formula's structure.
"""

from __future__ import annotations

from dataclasses import dataclass

# Component weights (sum to 1.0). Centralised so they are auditable in one place.
W_EXTRACT = 0.30
W_MATCH = 0.30
W_CONTRADICTION = 0.20
W_LLM = 0.15
W_SOURCE = 0.05


@dataclass
class ConfidenceInputs:
    """The five signals that feed the confidence score, each in ``[0, 1]``.

    Attributes:
        extract: Quality/grounding of the requirement extraction.
        match: Retrieval/match strength for the best candidate clause.
        contradiction: Likelihood the determination is contradicted (penalised).
        llm: The verifier model's self-reported confidence.
        source: Strength of the source (binding term sheet vs casual email).
    """

    extract: float
    match: float
    contradiction: float
    llm: float
    source: float

    def clamped(self) -> "ConfidenceInputs":
        """Return a copy with every field clamped to ``[0, 1]``."""
        c = lambda v: max(0.0, min(1.0, float(v)))  # noqa: E731
        return ConfidenceInputs(c(self.extract), c(self.match), c(self.contradiction),
                                c(self.llm), c(self.source))


def confidence_score(inputs: ConfidenceInputs) -> float:
    """Compute the blended confidence score in ``[0, 1]``.

    Args:
        inputs: The five component signals.

    Returns:
        The weighted confidence, rounded to 4 decimals.
    """
    i = inputs.clamped()
    cs = (
        W_EXTRACT * i.extract
        + W_MATCH * i.match
        + W_CONTRADICTION * (1.0 - i.contradiction)
        + W_LLM * i.llm
        + W_SOURCE * i.source
    )
    return round(cs, 4)


def needs_human_review(cs: float, threshold: float = 0.70) -> bool:
    """Return ``True`` if ``cs`` is below the human-review threshold."""
    return cs < threshold


def eligible_for_auto_confirm(cs: float, threshold: float = 0.85) -> bool:
    """Return ``True`` if ``cs`` meets the auto-confirmation threshold."""
    return cs >= threshold
