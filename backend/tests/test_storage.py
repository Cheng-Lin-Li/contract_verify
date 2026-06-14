"""Tests for the blob storage layer (TDD §19 hybrid deployment).

Covers the local filesystem backend, ``s3://`` URL parsing, the S3-compatible
backend driven by an in-memory fake client (no boto3, no network), and the
factory that selects a backend from settings.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.config import get_settings, reset_settings_cache
from app.storage.store import (
    LocalBlobStore,
    S3BlobStore,
    get_blob_store,
    parse_s3_url,
)

from tests.helpers import FakeS3Client


# --- local backend --------------------------------------------------------

def test_local_blob_store_round_trips():
    with tempfile.TemporaryDirectory() as tmp:
        store = LocalBlobStore(tmp)
        loc = store.put("doc-1/file.txt", b"hello")
        assert Path(loc).exists()
        assert store.get("doc-1/file.txt") == b"hello"
        assert store.residency == "local"


# --- s3 url parsing -------------------------------------------------------

def test_parse_s3_url_with_prefix():
    bucket, prefix = parse_s3_url("s3://my-bucket/contract_verify/blobs")
    assert bucket == "my-bucket"
    assert prefix == "contract_verify/blobs"


def test_parse_s3_url_without_prefix():
    bucket, prefix = parse_s3_url("s3://my-bucket")
    assert bucket == "my-bucket"
    assert prefix == ""


def test_parse_s3_url_rejects_non_s3():
    try:
        parse_s3_url("./var/blobs")
        assert False, "expected ValueError"
    except ValueError:
        pass


# --- s3 backend (fake client) --------------------------------------------

def test_s3_blob_store_put_get_with_fake_client():
    fake = FakeS3Client()
    store = S3BlobStore("cv-bucket", "blobs", client=fake)
    uri = store.put("doc-9/contract.pdf", b"%PDF-bytes")
    assert uri == "s3://cv-bucket/blobs/doc-9/contract.pdf"
    assert store.residency == "cloud"
    # Physically present in the (fake) object store under the prefixed key.
    assert ("cv-bucket", "blobs/doc-9/contract.pdf") in fake.objects
    assert store.get("doc-9/contract.pdf") == b"%PDF-bytes"


def test_s3_blob_store_creates_missing_bucket():
    fake = FakeS3Client()  # starts with no buckets
    store = S3BlobStore("new-bucket", client=fake)
    store.put("a.txt", b"x")
    assert "new-bucket" in fake.buckets


def test_s3_blob_store_no_prefix_key():
    fake = FakeS3Client()
    store = S3BlobStore("b", client=fake)
    store.put("k.txt", b"y")
    assert ("b", "k.txt") in fake.objects


# --- factory selection ----------------------------------------------------

def test_factory_returns_local_for_path():
    reset_settings_cache()
    s = get_settings()  # default BLOB_DIR is ./var/blobs
    assert isinstance(get_blob_store(s), LocalBlobStore)


def test_factory_returns_s3_for_s3_url():
    import os
    os.environ["BLOB_DIR"] = "s3://bucket/prefix"
    os.environ["S3_ENDPOINT_URL"] = "http://localhost:9000"
    try:
        reset_settings_cache()
        s = get_settings()
        store = get_blob_store(s, client=FakeS3Client())
        assert isinstance(store, S3BlobStore)
        assert store.bucket == "bucket" and store.prefix == "prefix"
    finally:
        del os.environ["BLOB_DIR"]
        del os.environ["S3_ENDPOINT_URL"]
        reset_settings_cache()
