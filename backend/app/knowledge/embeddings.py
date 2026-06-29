"""Embedding backends (3-month scope).

Local (bge-m3 / nomic) and cloud (Voyage) embedders behind one interface, so
retrieval is provider-agnostic and multilingual (EN/JA cross-lingual). The MVP
default is :class:`LocalEmbedder`, which calls the same local Ollama runtime
used for extraction/verification — air-gap friendly, no cloud dependency.
"""

from __future__ import annotations

from typing import Protocol

from app.logging_setup import get_logger

log = get_logger("knowledge.embeddings")


class Embedder(Protocol):
    """Turns text into dense vectors."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""
        ...


class LocalEmbedder:
    """bge-m3 / nomic-embed-text via the local Ollama runtime."""

    def __init__(self, model: str, base_url: str = "http://localhost:11434",
                 timeout: float = 60.0) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Embed each text via Ollama's ``/api/embeddings`` endpoint."""
        import requests  # noqa: PLC0415 - lazy so import works offline

        vectors: list[list[float]] = []
        for text in texts:
            resp = requests.post(
                f"{self.base_url}/api/embeddings",
                json={"model": self.model, "prompt": text},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            vectors.append(resp.json()["embedding"])
        return vectors


def get_embedder(settings: object) -> Embedder:
    """Select the embedder from settings.

    Local (Ollama) is the default and only built-in backend; a cloud embedder
    (Voyage) is a drop-in addition for hosted deployments (backlog) and would be
    selected here off an ``EMBEDDING_PROVIDER`` setting.
    """
    model = getattr(settings, "embedding_model", "bge-m3")
    base_url = getattr(settings, "llm_base_url", "http://localhost:11434")
    return LocalEmbedder(model, base_url=base_url)
