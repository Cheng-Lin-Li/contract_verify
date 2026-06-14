"""Layer-1 business-requirement extraction (TDD §8).

Runs the externalised extraction prompt over each deal-source CIR and parses the
model's JSON into :class:`ReferenceItem`\\ s, attaching a :class:`SourceRef` so
every requirement cites where it came from. A lightweight rule-based pass marks
items for re-extraction when the two disagree (the full second-LLM-pass on
disagreement is a 3-month refinement).
"""

from __future__ import annotations

from typing import Optional

from app.core.enums import Layer, Priority
from app.core.models import CIRDocument, ReferenceItem, SourceRef
from app.llm.base import LLMProvider
from app.logging_setup import get_logger, log_stage
from app.prompts.loader import PromptCatalog, load_catalog

log = get_logger("references.extractor")


def _coerce_priority(value: str) -> Priority:
    """Map a model-provided priority string to a :class:`Priority` (default Medium)."""
    try:
        return Priority(str(value).capitalize())
    except ValueError:
        return Priority.MEDIUM


class RequirementExtractor:
    """Extracts Layer-1 requirements from deal-source documents."""

    def __init__(self, provider: LLMProvider, catalog: Optional[PromptCatalog] = None) -> None:
        """Initialise with an LLM provider and a prompt catalog.

        Args:
            provider: The :class:`LLMProvider` to call.
            catalog: Prompt catalog; defaults to the configured locale's catalog.
        """
        self.provider = provider
        self.catalog = catalog or load_catalog()

    def extract(self, doc: CIRDocument, start_index: int = 0) -> list[ReferenceItem]:
        """Extract requirements from a single deal-source document.

        Args:
            doc: The deal-source :class:`CIRDocument`.
            start_index: Offset for item numbering when extracting across many
                documents, so ids stay globally unique.

        Returns:
            A list of Layer-1 :class:`ReferenceItem`.
        """
        with log_stage("extract", doc_id=doc.doc_id, layer=1):
            prompt = self.catalog.render("extract_requirements", source_text=doc.full_text())
            system = self.catalog.get("system_extract")
            try:
                raw = self.provider.complete_json(prompt, system=system)
            except ValueError as exc:
                log.error("extract_parse_failed", extra={"doc_id": doc.doc_id, "error": str(exc)})
                return []

            items: list[ReferenceItem] = []
            for offset, obj in enumerate(raw if isinstance(raw, list) else []):
                text = (obj.get("text") or "").strip()
                if not text:
                    continue
                # Cite the first block whose text contains the requirement, else block 0.
                source_block = next(
                    (b for b in doc.blocks if text[:30].lower() in b.text.lower()),
                    doc.blocks[0] if doc.blocks else None,
                )
                src = (
                    SourceRef(doc_id=doc.doc_id, block_id=source_block.block_id,
                              page=source_block.page)
                    if source_block
                    else None
                )
                items.append(
                    ReferenceItem(
                        item_id=f"r-{start_index + offset + 1:03d}",
                        layer=Layer.REQUIREMENTS,
                        text=text,
                        type=obj.get("type", "general"),
                        priority=_coerce_priority(obj.get("priority", "Medium")),
                        source_ref=src,
                        binding=bool(obj.get("binding", False)),
                    )
                )
            log.info("extracted_requirements", extra={"doc_id": doc.doc_id, "count": len(items)})
            return items

    def extract_many(self, docs: list[CIRDocument]) -> list[ReferenceItem]:
        """Extract across several deal-source documents, keeping ids unique."""
        all_items: list[ReferenceItem] = []
        for doc in docs:
            all_items.extend(self.extract(doc, start_index=len(all_items)))
        return all_items
