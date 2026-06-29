"""Qdrant dense-vector retrieval (3-month scope).

Implements the MVP ``Retriever`` interface (app/retrieval/retriever.py) with a
Qdrant backend: payload-scoped points (``doc_id``, ``layer``, ``type``,
``contract_type``) so a query only matches the intended scope. It is a drop-in
replacement for the MVP ``DirectRetriever`` — the matcher does not change. When
the matcher calls :meth:`retrieve` for a contract it has not indexed yet, the
contract's blocks are embedded and upserted on demand, so it works without any
pipeline changes. Requires ``qdrant-client``.
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.models import CIRBlock
from app.retrieval.retriever import Candidate

_DISTANCE = "Cosine"


class QdrantRetriever:
    """Dense retriever over Qdrant, scoped by payload, with on-demand indexing."""

    def __init__(self, url: str, embedder: Any, collection: str = "clauses") -> None:
        self.url = url
        self.embedder = embedder
        self.collection = collection
        self._client: Any = None
        self._dim: int | None = None
        self._indexed: set[str] = set()

    # -- client / collection -------------------------------------------------

    def _get_client(self) -> Any:
        """Lazily create the Qdrant client (import only when used)."""
        if self._client is None:
            from qdrant_client import QdrantClient  # noqa: PLC0415
            self._client = QdrantClient(url=self.url)
        return self._client

    def _vector_dim(self) -> int:
        """Detect the embedding dimension from a probe (cached)."""
        if self._dim is None:
            self._dim = len(self.embedder.embed(["dimension probe"])[0])
        return self._dim

    def ensure_collection(self) -> None:
        """Create the collection + payload indexes if absent."""
        from qdrant_client import models  # noqa: PLC0415

        client = self._get_client()
        if client.collection_exists(self.collection):
            return
        client.create_collection(
            collection_name=self.collection,
            vectors_config=models.VectorParams(
                size=self._vector_dim(), distance=models.Distance.COSINE),
        )
        for field_name in ("doc_id", "layer", "type", "contract_type"):
            schema = (models.PayloadSchemaType.INTEGER if field_name == "layer"
                      else models.PayloadSchemaType.KEYWORD)
            client.create_payload_index(self.collection, field_name, field_schema=schema)

    # -- indexing ------------------------------------------------------------

    def index_document(self, doc: Any, *, layer: int,
                       contract_type: str | None) -> None:
        """Embed and upsert a document's blocks with payload scoping."""
        from qdrant_client import models  # noqa: PLC0415

        self.ensure_collection()
        blocks = [b for b in doc.blocks if b.text]
        if not blocks:
            self._indexed.add(getattr(doc, "doc_id", ""))
            return

        vectors = self.embedder.embed([b.text for b in blocks])
        doc_id = getattr(doc, "doc_id", "")
        points = [
            models.PointStruct(
                id=str(uuid.uuid4()),
                vector=vec,
                payload={
                    "doc_id": doc_id,
                    "block_id": b.block_id,
                    "type": b.type,
                    "page": b.page,
                    "text": b.text,
                    "layer": layer,
                    "contract_type": contract_type or "",
                },
            )
            for b, vec in zip(blocks, vectors)
        ]
        self._get_client().upsert(self.collection, points=points)
        self._indexed.add(doc_id)

    # -- retrieval -----------------------------------------------------------

    def retrieve(self, query: str, contract: Any, top_k: int = 5) -> list[Candidate]:
        """Return candidate clauses for ``query``, scoped to ``contract``."""
        from qdrant_client import models  # noqa: PLC0415

        self.ensure_collection()
        doc_id = getattr(contract, "doc_id", "")
        if doc_id and doc_id not in self._indexed:
            # Drop-in behaviour: index the contract the first time it's queried.
            self.index_document(contract, layer=1, contract_type=None)

        query_vec = self.embedder.embed([query])[0]
        flt = models.Filter(must=[models.FieldCondition(
            key="doc_id", match=models.MatchValue(value=doc_id))]) if doc_id else None
        hits = self._get_client().query_points(
            collection_name=self.collection,
            query=query_vec,
            query_filter=flt,
            limit=top_k,
        ).points
        candidates: list[Candidate] = []
        for h in hits:
            p = h.payload or {}
            block = CIRBlock(block_id=p.get("block_id", ""), type=p.get("type", "paragraph"),
                             page=p.get("page", 1), text=p.get("text", ""))
            candidates.append(Candidate(block=block, score=round(float(h.score), 4)))
        return candidates
