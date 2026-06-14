"""End-to-end pipeline test (TDD §1) over the bundled sample data.

Runs the full six-stage pipeline with the deterministic FakeProvider, so it is
hermetic (no GPU, no network) yet exercises ingest -> extract -> reconcile ->
verify -> score -> report across all three layers.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from app.audit.audit_log import AuditLog
from app.core.enums import Layer
from app.llm.fake_provider import FakeProvider
from app.pipeline import VerificationPipeline

from tests.helpers import CONTRACT, DEAL_DIR, PLAYBOOK_DIR, STDTERMS_DIR


def _run():
    sources = [str(p) for p in sorted(DEAL_DIR.glob("*")) if p.is_file()]
    with tempfile.TemporaryDirectory() as tmp:
        audit = AuditLog(Path(tmp) / "audit.jsonl")
        pipe = VerificationPipeline(provider=FakeProvider(), audit=audit)
        result = pipe.run(CONTRACT, sources, PLAYBOOK_DIR, STDTERMS_DIR, contract_type="services")
        events = list(audit.read_all())
    return result, events


def test_pipeline_runs_all_three_layers():
    result, _ = _run()
    layers = {int(r.layer) for r in result.results}
    assert layers == {1, 2, 3}


def test_pipeline_extracts_and_covers_requirements():
    result, _ = _run()
    l1 = [r for r in result.results if r.layer is Layer.REQUIREMENTS]
    assert l1, "expected Layer-1 requirements to be extracted"
    assert result.report.to_dict()["coverage_score"] > 0.0


def test_pipeline_applies_supersession():
    result, _ = _run()
    statuses = {r.item_id: r.status for r in result.results if r.layer is Layer.REQUIREMENTS}
    # net-30 in the signed term sheet is superseded by net-45 in the follow-up email.
    assert "Superseded" in statuses.values()


def test_pipeline_report_row_per_item():
    result, _ = _run()
    assert len(result.report.to_dict()["rows"]) == len(result.items)


def test_pipeline_writes_audit_trail():
    _, events = _run()
    types = {e["event_type"] for e in events}
    # Every major stage leaves a trace.
    assert {"ingest", "extract", "match", "score"} <= types


def test_pipeline_gate_routes_to_attorney():
    result, _ = _run()
    d = result.report.to_dict()
    # The sample contract omits indemnity (a core term) and clusters low-confidence
    # items, so it must not auto-confirm and must route items to the attorney queue.
    assert d["auto_confirm"] is False
    assert d["attorney_queue"]


def test_pipeline_attaches_contract_entities():
    result, events = _run()
    entities = result.contract.metadata.get("entities")
    assert entities is not None
    assert entities["governing_law"] == "California"
    assert any(n["value"] == "net-45" for n in entities["net_terms"])
    assert any(e["event_type"] == "entities" for e in events)


def test_pipeline_supersession_is_order_independent():
    """The net-45 email must supersede the net-30 term sheet regardless of input order."""
    sources = [str(p) for p in sorted(DEAL_DIR.glob("*")) if p.is_file()]
    for ordering in (sources, list(reversed(sources))):
        with tempfile.TemporaryDirectory() as tmp:
            audit = AuditLog(Path(tmp) / "audit.jsonl")
            pipe = VerificationPipeline(provider=FakeProvider(), audit=audit)
            result = pipe.run(CONTRACT, ordering, PLAYBOOK_DIR, STDTERMS_DIR,
                              contract_type="services")
        l1 = [r for r in result.results if r.layer is Layer.REQUIREMENTS]
        superseded = [r for r in l1 if r.status == "Superseded"]
        assert len(superseded) == 1
        # The surviving net-45 must not be downgraded by a payment value conflict.
        assert not any("net-term differs" in (r.notes or "") for r in l1)


def test_pipeline_hybrid_pushes_blobs_to_s3_keeps_audit_local():
    """Hybrid: blobs physically go to (fake) S3 while the audit log stays local."""
    from app.storage.store import S3BlobStore
    from tests.helpers import FakeS3Client

    fake = FakeS3Client()
    s3 = S3BlobStore("cv-bucket", "blobs", client=fake)
    sources = [str(p) for p in sorted(DEAL_DIR.glob("*")) if p.is_file()]
    with tempfile.TemporaryDirectory() as tmp:
        audit_path = Path(tmp) / "audit.jsonl"
        audit = AuditLog(audit_path)
        pipe = VerificationPipeline(provider=FakeProvider(), audit=audit, blob_store=s3)
        pipe.run(CONTRACT, sources, PLAYBOOK_DIR, STDTERMS_DIR, contract_type="services")
        events = list(audit.read_all())
        # The audit log itself stayed on the local filesystem.
        assert audit_path.exists()

    # Every source blob landed in the object store, under the bucket/prefix.
    assert len(fake.objects) == 1 + len(sources)  # contract + deal sources
    assert all(b == "cv-bucket" and key.startswith("blobs/") for (b, key) in fake.objects)
    # The audit trail (local file) recorded the s3:// locations.
    blob_uris = [e["details"].get("blob") for e in events
                 if e["event_type"] == "ingest" and isinstance(e.get("details"), dict)]
    assert blob_uris and all(uri.startswith("s3://cv-bucket/blobs/") for uri in blob_uris)
