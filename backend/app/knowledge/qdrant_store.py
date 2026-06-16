"""Qdrant dense-vector retrieval (3-month scope · SKELETON).

Implements the MVP ``Retriever`` interface (app/retrieval/retriever.py) with a
Qdrant backend: payload-scoped collections (``layer``, ``type``,
``contract_type``) and hybrid dense+sparse search. Drop-in replacement for the
MVP ``DirectRetriever`` — the matcher does not change. Requires
``qdrant-client``.
"""

from __future__ import annotations

from typing import Any


class QdrantRetriever:
    """Hybrid dense+sparse retriever over Qdrant (SKELETON)."""

    def __init__(self, url: str, embedder: Any, collection: str = "clauses") -> None:
        raise NotImplementedError

    def ensure_collection(self) -> None:
        """Create the collection + payload indexes if absent."""
        raise NotImplementedError

    def index_document(self, doc: Any, *, layer: int, contract_type: str | None) -> None:
        """Embed and upsert a document's blocks with payload scoping."""
        raise NotImplementedError

    def retrieve(self, query: str, contract: Any, top_k: int = 5) -> list[Any]:
        """Return candidate clauses for ``query`` (implements Retriever)."""
        raise NotImplementedError
