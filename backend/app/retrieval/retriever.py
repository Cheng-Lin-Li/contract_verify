"""Clause retrieval over the contract CIR (TDD §7, §2 scope table).

The matcher needs the candidate contract clauses most likely to satisfy a given
reference item. The MVP uses :class:`DirectRetriever` -- a dependency-free
lexical scorer over the (small) contract blocks -- behind the
:class:`Retriever` interface. The 3-month build swaps in a Qdrant hybrid
dense+sparse retriever implementing the same interface, so callers do not change.
"""

from __future__ import annotations

import abc
import re
from dataclasses import dataclass

from app.core.models import CIRBlock, CIRDocument


@dataclass
class Candidate:
    """A retrieved contract clause candidate with a relevance score."""

    block: CIRBlock
    score: float


def _tokens(text: str) -> set[str]:
    """Tokenise to a set of lowercase alphanumeric terms of length >= 3."""
    return {t for t in re.findall(r"[a-z0-9\-]{3,}", text.lower())}


class Retriever(abc.ABC):
    """Abstract clause retriever."""

    @abc.abstractmethod
    def retrieve(self, query: str, contract: CIRDocument, top_k: int = 5) -> list[Candidate]:
        """Return the ``top_k`` most relevant contract blocks for ``query``."""
        raise NotImplementedError


class DirectRetriever(Retriever):
    """Lexical Jaccard-overlap retriever for small documents (MVP default)."""

    def retrieve(self, query: str, contract: CIRDocument, top_k: int = 5) -> list[Candidate]:
        """Score every contract block by token overlap with ``query``.

        Args:
            query: The reference-item text to find clauses for.
            contract: The contract :class:`CIRDocument`.
            top_k: Maximum number of candidates to return.

        Returns:
            Candidates sorted by descending score (ties broken by block order).
        """
        q = _tokens(query)
        if not q:
            return []
        scored: list[Candidate] = []
        for block in contract.blocks:
            b = _tokens(block.text)
            if not b:
                continue
            overlap = len(q & b)
            if overlap == 0:
                continue
            score = overlap / len(q | b)  # Jaccard
            scored.append(Candidate(block=block, score=round(score, 4)))
        scored.sort(key=lambda c: c.score, reverse=True)
        return scored[:top_k]


def get_retriever(settings: object | None = None) -> Retriever:
    """Select the retriever from settings (``RETRIEVER=direct|qdrant``).

    ``direct`` (default) is the dependency-free lexical retriever; ``qdrant`` is
    the dense Qdrant retriever (3-month), constructed with the configured
    embedder. Both implement :class:`Retriever`, so callers don't change.
    """
    if settings is None:
        from app.config import get_settings
        settings = get_settings()
    if getattr(settings, "retriever", "qdrant").lower() != "qdrant":
        # `direct` (and any non-qdrant value): dependency-free lexical retriever.
        return DirectRetriever()

    from app.knowledge.embeddings import get_embedder
    from app.knowledge.qdrant_store import QdrantRetriever
    base: Retriever = QdrantRetriever(
        url=getattr(settings, "qdrant_url", "http://localhost:6333"),
        embedder=get_embedder(settings),
        collection=getattr(settings, "qdrant_collection", "clauses"),
        hybrid=getattr(settings, "retriever_hybrid", False),
        sparse_model=getattr(settings, "sparse_model", "Qdrant/bm25"),
    )
    # Optional cross-encoder reranker on top of the dense/hybrid candidates.
    from app.knowledge.reranker import RerankingRetriever, get_reranker
    reranker = get_reranker(settings)
    if reranker is not None:
        return RerankingRetriever(
            base, reranker, candidates=getattr(settings, "rerank_candidates", 20))
    return base
