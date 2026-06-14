"""Shared helpers for the test suite (no pytest fixtures, so the bundled
stdlib runner and pytest both work).

These helpers resolve sample-data paths relative to the repo root and build the
deterministic :class:`FakeProvider` so tests never reach a real model.
"""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SAMPLES = REPO_ROOT / "samples"
PLAYBOOK_DIR = SAMPLES / "playbook"
STDTERMS_DIR = SAMPLES / "standard_terms"
DEAL_DIR = SAMPLES / "deal"
CONTRACT = SAMPLES / "contract" / "contract.txt"
TERM_SHEET = DEAL_DIR / "term_sheet.txt"
FOLLOWUP = DEAL_DIR / "followup.eml"


def fake_provider():
    """Return a fresh deterministic FakeProvider."""
    from app.llm.fake_provider import FakeProvider

    return FakeProvider()


def approx(a: float, b: float, tol: float = 1e-6) -> bool:
    """Return True if two floats are within ``tol``."""
    return abs(a - b) <= tol


class FakeS3Client:
    """Minimal in-memory stand-in for a boto3 S3 client (tests only).

    Implements just the surface ``S3BlobStore`` uses: ``head_bucket``,
    ``create_bucket``, ``put_object`` and ``get_object``. Objects live in a
    dict keyed by ``(bucket, key)`` so tests need neither boto3 nor a network.
    """

    class _NoSuchBucket(Exception):
        pass

    def __init__(self) -> None:
        self.buckets: set[str] = set()
        self.objects: dict[tuple[str, str], bytes] = {}

    def head_bucket(self, Bucket: str):  # noqa: N803 - boto3 kwarg casing
        if Bucket not in self.buckets:
            raise self._NoSuchBucket(Bucket)
        return {}

    def create_bucket(self, Bucket: str):  # noqa: N803
        self.buckets.add(Bucket)
        return {}

    def put_object(self, Bucket: str, Key: str, Body: bytes):  # noqa: N803
        self.objects[(Bucket, Key)] = bytes(Body)
        return {}

    def get_object(self, Bucket: str, Key: str):  # noqa: N803
        return {"Body": _Body(self.objects[(Bucket, Key)])}


class _Body:
    """A boto3-like streaming body wrapper exposing ``read()``."""

    def __init__(self, data: bytes) -> None:
        self._data = data

    def read(self) -> bytes:
        return self._data
