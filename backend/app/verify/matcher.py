"""Verification matching (TDD §8).

For each :class:`ReferenceItem`, the matcher (1) retrieves candidate contract
clauses, (2) asks the LLM verifier for a per-layer status with cited clause ids
and an LLM confidence, and (3) computes the blended per-determination
:class:`ConfidenceScore`. The verifier prompt is layer-specific (Layer 1 uses
``verify_requirement``, Layer 2 ``verify_playbook``, Layer 3
``verify_standard_term``), but the result shape is uniform.
"""

from __future__ import annotations

from typing import Optional

from app.core.enums import Layer
from app.core.models import CIRDocument, ReferenceItem, VerificationResult
from app.llm.base import LLMProvider
from app.logging_setup import get_logger, log_stage
from app.prompts.loader import PromptCatalog, load_catalog
from app.references.reconcile import ReconcileResult
from app.references.entities import value_conflict
from app.retrieval.retriever import Candidate, DirectRetriever, Retriever
from app.scoring.confidence import ConfidenceInputs, confidence_score

log = get_logger("verify.matcher")

_PROMPT_BY_LAYER = {
    Layer.REQUIREMENTS: "verify_requirement",
    Layer.PLAYBOOK: "verify_playbook",
    Layer.STANDARD_TERMS: "verify_standard_term",
}


class VerificationMatcher:
    """Matches reference items against the contract and assigns statuses."""

    def __init__(
        self,
        provider: LLMProvider,
        retriever: Optional[Retriever] = None,
        catalog: Optional[PromptCatalog] = None,
        top_k: int = 5,
    ) -> None:
        """Initialise the matcher.

        Args:
            provider: LLM provider for the verifier calls.
            retriever: Clause retriever; defaults to :class:`DirectRetriever`.
            catalog: Prompt catalog; defaults to the configured locale's catalog.
            top_k: Number of candidate clauses to send to the verifier.
        """
        self.provider = provider
        self.retriever = retriever or DirectRetriever()
        self.catalog = catalog or load_catalog()
        self.top_k = top_k

    def _render_clauses(self, candidates: list[Candidate]) -> str:
        """Render candidate clauses as ``[block_id] text`` lines for the prompt."""
        return "\n".join(f"[{c.block.block_id}] {c.block.text}" for c in candidates) or "(none)"

    def verify_item(
        self,
        item: ReferenceItem,
        contract: CIRDocument,
        reconcile: Optional[ReconcileResult] = None,
    ) -> VerificationResult:
        """Verify a single reference item against the contract.

        If ``reconcile`` marks the item as superseded, it is short-circuited to a
        ``Superseded`` result without an LLM call.

        Returns:
            A :class:`VerificationResult` with status, cited clauses and confidence.
        """
        if reconcile and item.item_id in reconcile.superseded:
            return VerificationResult(
                item_id=item.item_id,
                layer=item.layer,
                status="Superseded",
                matched_clause_ids=[],
                confidence=1.0,
                evidence={"superseded_by": reconcile.superseded[item.item_id]},
                notes="Overridden by a later source during reconciliation.",
            )

        candidates = self.retriever.retrieve(item.text, contract, top_k=self.top_k)
        prompt_key = _PROMPT_BY_LAYER[item.layer]
        render_kwargs = {"requirement_text": item.text, "clauses": self._render_clauses(candidates)}
        if item.layer is Layer.PLAYBOOK:
            render_kwargs["rule"] = item.rule.value if item.rule else "must_have"
        prompt = self.catalog.render(prompt_key, **render_kwargs)
        system_key = "system_verify"

        try:
            obj = self.provider.complete_json(prompt, system=self.catalog.get(system_key))
        except (ValueError, KeyError) as exc:
            log.error("verify_failed", extra={"item_id": item.item_id, "error": str(exc)})
            obj = {"status": "Missing", "matched_clause_ids": [], "llm_confidence": 0.3,
                   "notes": "verifier error"}

        # The verifier may not echo clause ids; fall back to retrieved candidates.
        matched = obj.get("matched_clause_ids") or [c.block.block_id for c in candidates[:1]]
        status = obj.get("status", "Missing")
        notes = obj.get("notes", "")

        # Value grounding: if Layer-1 reads Covered but the requirement and the
        # matched clause name different same-kind values (e.g. a different cap or
        # net-term), the key detail differs -> downgrade to Partial. This is a
        # deterministic, cited check on top of the LLM's judgement.
        if status == "Covered" and item.layer is Layer.REQUIREMENTS:
            matched_set = set(matched)
            clause_text = " ".join(
                c.block.text for c in candidates if c.block.block_id in matched_set
            ) or " ".join(c.block.text for c in candidates)
            conflict = value_conflict(item.text, clause_text)
            if conflict:
                status = "Partial"
                notes = (notes + " " if notes else "") + f"Value check: {conflict}."
                log.info("value_downgrade", extra={"item_id": item.item_id, "reason": conflict})

        conf = confidence_score(
            ConfidenceInputs(
                extract=1.0 if item.source_ref or item.layer is not Layer.REQUIREMENTS else 0.6,
                match=candidates[0].score if candidates else 0.0,
                contradiction=1.0 if status == "Contradicted" else 0.0,
                llm=float(obj.get("llm_confidence", 0.5)),
                source=1.0 if item.binding else 0.5,
            )
        )

        evidence = {
            "source_ref": item.source_ref.to_dict() if item.source_ref else None,
            "contract_ref": matched,
        }
        return VerificationResult(
            item_id=item.item_id,
            layer=item.layer,
            status=status,
            matched_clause_ids=matched,
            confidence=conf,
            evidence=evidence,
            notes=notes,
        )

    def verify_all(
        self,
        items: list[ReferenceItem],
        contract: CIRDocument,
        reconcile: Optional[ReconcileResult] = None,
    ) -> list[VerificationResult]:
        """Verify every reference item across all three layers in one pass."""
        with log_stage("match", doc_id=contract.doc_id, items=len(items)):
            return [self.verify_item(item, contract, reconcile) for item in items]
