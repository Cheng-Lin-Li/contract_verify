"""TDD spec: attorney queue endpoints (app/api/routers/queue.py)."""

from __future__ import annotations

import pytest

pytest.importorskip("fastapi")

from tests.three_month._spec import skip_until_implemented


@skip_until_implemented
def test_list_queue_requires_attorney_role(api_client):
    # No auth -> 401; operator role -> 403 (RBAC).
    assert api_client.get("/api/queue").status_code == 401


@skip_until_implemented
def test_act_on_item_records_decision(api_client, auth_headers):
    resp = api_client.post("/api/queue/q-1/action",
                           json={"action": "approve", "comment": "ok"},
                           headers=auth_headers)
    assert resp.status_code == 200
    assert resp.json()["queue_id"] == "q-1"


@skip_until_implemented
def test_add_to_playbook_versions_position(api_client, auth_headers):
    resp = api_client.post("/api/queue/q-2/action",
                           json={"action": "add_to_playbook",
                                 "edited_text": "Cap liability at fees paid."},
                           headers=auth_headers)
    assert resp.status_code == 200
