"""Qdrant dense (and optional hybrid dense+sparse) retrieval (3-month scope).

Implements the MVP ``Retriever`` interface (app/retrieval/retriever.py) with a
Qdrant backend: payload-scoped points (``doc_id``, ``layer``, ``type``,
``contract_type``) so a query only matches the intended scope. A drop-in
replacement for the lexical ``DirectRetriever`` — the matcher does not change.
When the matcher queries a contract it has not indexed yet, the contract's
blocks are embedded and upserted on demand, so it works without pipeline changes.

Two modes:

* **dense** (default) — a single dense vector (e.g. bge-m3). Best for paraphrase.
* **hybrid** (``RETRIEVER_HYBRID=1``) — dense + a sparse lexical vector
  (BM25/SPLADE via ``fastembed``), fused server-side with Reciprocal Rank
  Fusion. Recovers exact terms, numbers and defined-term names that pure dense
  misses. Falls back to dense-only if no sparse encoder is available.

Requires ``qdrant-client`` (and ``fastembed`` for hybrid).
"""

from __future__ import annotations

import uuid
from typing import Any

from app.core.models import CIRBlock
from app.retrieval.retriever import Candidate

_DENSE = "dense"
_SPARSE = "sparse"


class QdrantRetriever:
    """Dense (optionally hybrid) retriever over Qdrant, with on-demand indexing."""

    def __init__(self, url: str, embedder: Any, collection: str = "clauses",
                 *, hybrid: bool = False, sparse_model: str = "Qdrant/bm25") -> None:
        self.url = url
        self.embedder = embedder
        self.collection = collection
        self.hybrid = hybrid
        self.sparse_model = sparse_model
        self._client: Any = None
        self._sparse: Any = None
        self._dim: int | None = None
        self._indexed: set[str] = set()

    # -- client / encoders ---------------------------------------------------

    def _get_client(self) -> Any:
        if self._client is None:
            from qdrant_client import QdrantClient  # noqa: PLC0415
            self._client = QdrantClient(url=self.url)
        return self._client

    def _vector_dim(self) -> int:
        if self._dim is None:
            self._dim = len(self.embedder.embed(["dimension probe"])[0])
        return self._dim

    def _sparse_encoder(self):
        """Lazily build the sparse encoder (fastembed); ``None`` disables hybrid."""
        if not self.hybrid:
            return None
        if self._sparse is None:
            try:
                from fastembed import SparseTextEmbedding  # noqa: PLC0415
            except ImportError as exc:  # pragma: no cover - depends on env
                raise RuntimeError(
                    "Hybrid retrieval needs fastembed (RETRIEVER_HYBRID=1). Install it "
                    "from backend/requirements-3month.txt, or set RETRIEVER_HYBRID=0."
                ) from exc
            self._sparse = SparseTextEmbedding(model_name=self.sparse_model)
        return self._sparse

    def _sparse_vectors(self, texts: list[str]) -> list[Any]:
        """Return one Qdrant SparseVector per text."""
        from qdrant_client import models  # noqa: PLC0415
        out = []
        for emb in self._sparse_encoder().embed(texts):
            out.append(models.SparseVector(
                indices=emb.indices.tolist(), values=emb.values.tolist()))
        return out

    # -- collection ----------------------------------------------------------

    def ensure_collection(self) -> None:
        """Create the collection + payload indexes if absent."""
        from qdrant_client import models  # noqa: PLC0415

        client = self._get_client()
        if not client.collection_exists(self.collection):
            dense = models.VectorParams(size=self._vector_dim(),
                                        distance=models.Distance.COSINE)
            if self.hybrid:
                client.create_collection(
                    self.collection,
                    vectors_config={_DENSE: dense},
                    sparse_vectors_config={_SPARSE: models.SparseVectorParams()},
                )
            else:
                client.create_collection(self.collection, vectors_config=dense)
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
        doc_id = getattr(doc, "doc_id", "")
        if not blocks:
            self._indexed.add(doc_id)
            return

        texts = [b.text for b in blocks]
        dense_vecs = self.embedder.embed(texts)
        sparse_vecs = self._sparse_vectors(texts) if self.hybrid else [None] * len(blocks)

        points = []
        for b, dvec, svec in zip(blocks, dense_vecs, sparse_vecs):
            vector: Any = {_DENSE: dvec, _SPARSE: svec} if self.hybrid else dvec
            points.append(models.PointStruct(
                id=str(uuid.uuid4()),
                vector=vector,
                payload={
                    "doc_id": doc_id, "block_id": b.block_id, "type": b.type,
                    "page": b.page, "text": b.text, "layer": layer,
                    "contract_type": contract_type or "",
                },
            ))
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

        flt = models.Filter(must=[models.FieldCondition(
            key="doc_id", match=models.MatchValue(value=doc_id))]) if doc_id else None
        dense_vec = self.embedder.embed([query])[0]

        if self.hybrid:
            sparse_vec = self._sparse_vectors([query])[0]
            response = self._get_client().query_points(
                collection_name=self.collection,
                prefetch=[
                    models.Prefetch(query=dense_vec, using=_DENSE, limit=top_k * 4),
                    models.Prefetch(query=sparse_vec, using=_SPARSE, limit=top_k * 4),
                ],
                query=models.FusionQuery(fusion=models.Fusion.RRF),
                query_filter=flt, limit=top_k, with_payload=True,
            )
        else:
            response = self._get_client().query_points(
                collection_name=self.collection,
                query=dense_vec, query_filter=flt, limit=top_k, with_payload=True,
            )

        candidates: list[Candidate] = []
        for h in response.points:
            p = h.payload or {}
            block = CIRBlock(block_id=p.get("block_id", ""), type=p.get("type", "paragraph"),
                             page=p.get("page", 1), text=p.get("text", ""))
            candidates.append(Candidate(block=block, score=round(float(h.score), 4)))
        return candidates
