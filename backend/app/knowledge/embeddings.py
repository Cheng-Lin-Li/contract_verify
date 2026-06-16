"""Embedding backends (3-month scope · SKELETON).

Local (bge-m3 / nomic) and cloud (Voyage) embedders behind one interface, so
retrieval is provider-agnostic and multilingual (EN/JA cross-lingual).
"""

from __future__ import annotations

from typing import Protocol


class Embedder(Protocol):
    """Turns text into dense vectors."""

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return one embedding vector per input text."""
        ...


class LocalEmbedder:
    """bge-m3 / nomic-embed-text via the local runtime (SKELETON)."""

    def __init__(self, model: str) -> None:
        raise NotImplementedError

    def embed(self, texts: list[str]) -> list[list[float]]:
        raise NotImplementedError


def get_embedder(settings: object) -> Embedder:
    """Select the embedder from settings (local vs cloud). SKELETON."""
    raise NotImplementedError
