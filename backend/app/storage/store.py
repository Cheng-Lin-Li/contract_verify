"""State & blob storage (TDD §2 scope table; §19 deployment models).

Two concerns live here, deliberately decoupled so a **hybrid** deployment can
place them differently:

* **DocumentStore** — structured JSON state (documents, results). MVP keeps this
  in local SQLite; it is the "data stays local" half of a hybrid split.
* **BlobStore** — the raw uploaded bytes (contracts, deal sources, attachments).
  Two interchangeable backends sit behind one interface:
    - :class:`LocalBlobStore` — the filesystem (on-prem default).
    - :class:`S3BlobStore` — any S3-compatible object store (MinIO on-prem, or
      AWS S3 / other cloud), selected when ``BLOB_DIR`` is an ``s3://`` URL.

The :func:`get_blob_store` factory picks the backend from settings, so call
sites never branch on deployment model. ``boto3`` is imported lazily and only
when an S3 backend actually performs I/O, so the local/offline path needs no
cloud dependency.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any, Optional, Tuple
from urllib.parse import urlparse

from app.logging_setup import get_logger

log = get_logger("storage")


# ---------------------------------------------------------------------------
# Blob storage
# ---------------------------------------------------------------------------

class BlobStore:
    """Abstract blob store interface.

    Implementations persist opaque ``bytes`` under a string ``name`` and return
    a backend-specific location reference (a filesystem path or an ``s3://``
    URI) that is safe to record in the audit trail.
    """

    #: ``local`` or ``cloud`` — used by the deployment residency report.
    residency: str = "local"

    def put(self, name: str, data: bytes) -> str:  # pragma: no cover - interface
        """Store ``data`` under ``name``; return its location reference."""
        raise NotImplementedError

    def get(self, name: str) -> bytes:  # pragma: no cover - interface
        """Return the bytes previously stored under ``name``."""
        raise NotImplementedError

    def location(self, name: str) -> str:  # pragma: no cover - interface
        """Return the location reference for ``name`` without reading it."""
        raise NotImplementedError


class LocalBlobStore(BlobStore):
    """Blob storage on the local filesystem (on-prem default)."""

    residency = "local"

    def __init__(self, root: str | Path) -> None:
        """Create the blob root directory if needed."""
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, name: str, data: bytes) -> str:
        """Write ``data`` under ``name`` and return the absolute path."""
        path = self.root / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        log.info("blob_put", extra={"backend": "local", "name": name, "bytes": len(data)})
        return str(path)

    def get(self, name: str) -> bytes:
        """Read and return the bytes stored under ``name``."""
        return (self.root / name).read_bytes()

    def location(self, name: str) -> str:
        """Return the filesystem path for ``name``."""
        return str(self.root / name)


def parse_s3_url(url: str) -> Tuple[str, str]:
    """Split an ``s3://bucket/optional/prefix`` URL into ``(bucket, prefix)``.

    Args:
        url: An ``s3://`` URL. The path component (if any) becomes the key
            prefix; a missing prefix yields an empty string.

    Returns:
        ``(bucket, prefix)`` with no leading/trailing slashes on the prefix.

    Raises:
        ValueError: If ``url`` is not a well-formed ``s3://`` URL with a bucket.
    """
    parsed = urlparse(url)
    if parsed.scheme != "s3" or not parsed.netloc:
        raise ValueError(f"Not an s3:// URL with a bucket: {url!r}")
    bucket = parsed.netloc
    prefix = parsed.path.strip("/")
    return bucket, prefix


class S3BlobStore(BlobStore):
    """Blob storage on any S3-compatible object store (MinIO or AWS S3).

    Works against MinIO (set ``endpoint_url`` to e.g. ``http://localhost:9000``)
    or AWS S3 (leave ``endpoint_url`` unset). The ``boto3`` client is created
    lazily on first I/O so that merely *selecting* this backend (e.g. for the
    residency report) does not require ``boto3`` to be installed.
    """

    residency = "cloud"

    def __init__(
        self,
        bucket: str,
        prefix: str = "",
        *,
        endpoint_url: Optional[str] = None,
        access_key: Optional[str] = None,
        secret_key: Optional[str] = None,
        region: str = "us-east-1",
        client: Any = None,
        ensure_bucket: bool = True,
    ) -> None:
        """Configure the store (no network call until first ``put``/``get``).

        Args:
            bucket: Target bucket name.
            prefix: Optional key prefix applied to every object.
            endpoint_url: S3 endpoint (set for MinIO; unset for AWS S3).
            access_key/secret_key: Credentials (fall back to the boto3 chain).
            region: AWS region (MinIO ignores it but boto3 wants one).
            client: Pre-built client to inject (used by tests; bypasses boto3).
            ensure_bucket: Create the bucket on first use if it is missing.
        """
        self.bucket = bucket
        self.prefix = prefix.strip("/")
        self._endpoint_url = endpoint_url or None
        self._access_key = access_key or None
        self._secret_key = secret_key or None
        self._region = region
        self._client = client
        self._ensure_bucket = ensure_bucket
        self._bucket_ready = False

    # -- client / key helpers ------------------------------------------------

    def _get_client(self) -> Any:
        """Return the (lazily created) S3 client, importing boto3 on demand."""
        if self._client is None:
            try:
                import boto3  # noqa: PLC0415 - lazy so the local path needs no boto3
            except ImportError as exc:  # pragma: no cover - depends on env
                raise RuntimeError(
                    "S3BlobStore requires boto3. Install it with "
                    "`pip install boto3` (or use a local BLOB_DIR)."
                ) from exc
            self._client = boto3.client(
                "s3",
                endpoint_url=self._endpoint_url,
                aws_access_key_id=self._access_key,
                aws_secret_access_key=self._secret_key,
                region_name=self._region,
            )
        return self._client

    def _key(self, name: str) -> str:
        """Return the full object key for ``name`` (prefix-joined)."""
        return f"{self.prefix}/{name}" if self.prefix else name

    def _ensure_bucket_exists(self) -> None:
        """Best-effort create the bucket if absent (convenient for MinIO)."""
        if self._bucket_ready or not self._ensure_bucket:
            return
        client = self._get_client()
        try:
            client.head_bucket(Bucket=self.bucket)
        except Exception:  # noqa: BLE001 - any miss -> try to create
            try:
                client.create_bucket(Bucket=self.bucket)
                log.info("s3_bucket_created", extra={"bucket": self.bucket})
            except Exception as exc:  # noqa: BLE001 - surface as a clear error
                log.warning("s3_bucket_create_failed",
                            extra={"bucket": self.bucket, "error": str(exc)})
        self._bucket_ready = True

    # -- interface -----------------------------------------------------------

    def put(self, name: str, data: bytes) -> str:
        """Upload ``data`` to ``s3://bucket/prefix/name`` and return that URI."""
        self._ensure_bucket_exists()
        key = self._key(name)
        self._get_client().put_object(Bucket=self.bucket, Key=key, Body=data)
        uri = f"s3://{self.bucket}/{key}"
        log.info("blob_put", extra={"backend": "s3", "uri": uri, "bytes": len(data)})
        return uri

    def get(self, name: str) -> bytes:
        """Download and return the bytes for ``name``."""
        obj = self._get_client().get_object(Bucket=self.bucket, Key=self._key(name))
        body = obj["Body"]
        return body.read() if hasattr(body, "read") else bytes(body)

    def location(self, name: str) -> str:
        """Return the ``s3://`` URI for ``name`` without downloading it."""
        return f"s3://{self.bucket}/{self._key(name)}"


def get_blob_store(settings: Any = None, *, client: Any = None) -> BlobStore:
    """Build the blob store for the active settings.

    An ``s3://`` ``BLOB_DIR`` selects :class:`S3BlobStore` (MinIO/S3); anything
    else (a filesystem path) selects :class:`LocalBlobStore`. This is the only
    place that branches on blob backend, so the rest of the app — and a hybrid
    deployment that keeps the DB local while shipping blobs to object storage —
    is backend-agnostic.

    Args:
        settings: A settings object; defaults to :func:`get_settings`.
        client: Optional pre-built S3 client to inject (tests).
    """
    if settings is None:
        from app.config import get_settings
        settings = get_settings()

    blob_dir = settings.blob_dir
    if blob_dir.lower().startswith("s3://"):
        bucket, prefix = parse_s3_url(blob_dir)
        return S3BlobStore(
            bucket,
            prefix,
            endpoint_url=getattr(settings, "s3_endpoint_url", "") or None,
            access_key=getattr(settings, "s3_access_key", "") or None,
            secret_key=getattr(settings, "s3_secret_key", "") or None,
            region=getattr(settings, "s3_region", "us-east-1"),
            client=client,
        )
    return LocalBlobStore(blob_dir)


# ---------------------------------------------------------------------------
# Document (structured state) storage — stays local in a hybrid deployment
# ---------------------------------------------------------------------------

class DocumentStore:
    """A tiny JSON key-value store over SQLite for documents and results."""

    def __init__(self, db_path: str | Path) -> None:
        """Open (creating) the SQLite database and ensure the schema exists."""
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.execute(
            "CREATE TABLE IF NOT EXISTS kv "
            "(collection TEXT, key TEXT, value TEXT, PRIMARY KEY (collection, key))"
        )
        self._conn.commit()

    def save(self, collection: str, key: str, value: dict[str, Any]) -> None:
        """Upsert a JSON ``value`` under ``(collection, key)``."""
        self._conn.execute(
            "INSERT INTO kv (collection, key, value) VALUES (?, ?, ?) "
            "ON CONFLICT(collection, key) DO UPDATE SET value=excluded.value",
            (collection, key, json.dumps(value, default=str)),
        )
        self._conn.commit()

    def load(self, collection: str, key: str) -> Optional[dict[str, Any]]:
        """Return the JSON value under ``(collection, key)`` or ``None``."""
        cur = self._conn.execute(
            "SELECT value FROM kv WHERE collection=? AND key=?", (collection, key)
        )
        row = cur.fetchone()
        return json.loads(row[0]) if row else None

    def close(self) -> None:
        """Close the underlying SQLite connection."""
        self._conn.close()
