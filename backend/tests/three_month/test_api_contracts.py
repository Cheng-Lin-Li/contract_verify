"""TDD spec: contract upload / verify / report endpoints."""

from __future__ import annotations

import io

import pytest

pytest.importorskip("fastapi")

from tests.three_month._spec import skip_until_implemented


@skip_until_implemented
def test_upload_creates_job(api_client, auth_headers):
    files = {"contract": ("contract.txt", io.BytesIO(b"net-45 payment"), "text/plain")}
    resp = api_client.post("/api/contracts?contract_type=services",
                           files=files, headers=auth_headers)
    assert resp.status_code in (200, 201)
    assert resp.json()["job_id"]


@skip_until_implemented
def test_report_endpoint_returns_scores(api_client, auth_headers):
    resp = api_client.get("/api/contracts/known-id/report", headers=auth_headers)
    assert resp.status_code == 200
    body = resp.json()
    assert "scores" in body and "rows" in body
    assert 0.0 <= body["scores"]["coverage_score"] <= 100.0


@skip_until_implemented
def test_deployment_endpoint_mirrors_doctor(api_client, auth_headers):
    body = api_client.get("/api/deployment", headers=auth_headers).json()
    assert set(body["residency"]) == {"llm", "ocr", "database", "blobs", "audit"}
