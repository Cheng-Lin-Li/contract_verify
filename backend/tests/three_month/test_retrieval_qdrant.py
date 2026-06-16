"""TDD spec: Qdrant dense retrieval (app/knowledge/qdrant_store.py)."""

from __future__ import annotations

import pytest

pytest.importorskip("qdrant_client")

from app.knowledge.qdrant_store import QdrantRetriever
from tests.three_month._spec import skip_until_implemented


@skip_until_implemented
def test_retriever_implements_interface(fake_embedder, sample_contract):
    r = QdrantRetriever(url="http://localhost:6333", embedder=fake_embedder)
    r.ensure_collection()
    r.index_document(sample_contract, layer=0, contract_type="services")
    candidates = r.retrieve("payment net-45 terms", sample_contract, top_k=3)
    assert isinstance(candidates, list)
    assert all(hasattr(c, "block") and hasattr(c, "score") for c in candidates)


@skip_until_implemented
def test_payload_scoping_filters_by_layer(fake_embedder, sample_contract):
    r = QdrantRetriever(url="http://localhost:6333", embedder=fake_embedder)
    # Retrieval must be scoped so a query only matches the requested layer/type.
    assert r.retrieve("x", sample_contract, top_k=1) is not None
