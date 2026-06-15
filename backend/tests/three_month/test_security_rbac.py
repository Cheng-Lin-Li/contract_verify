"""TDD spec: authentication, password hashing and RBAC (app/core/security.py)."""

from __future__ import annotations

import pytest

pytest.importorskip("jose")
pytest.importorskip("passlib")

from app.core import security
from tests.three_month._spec import skip_until_implemented


@skip_until_implemented
def test_password_hash_roundtrip():
    h = security.hash_password("s3cret")
    assert h != "s3cret"
    assert security.verify_password("s3cret", h) is True
    assert security.verify_password("wrong", h) is False


@skip_until_implemented
def test_access_token_roundtrip_carries_role():
    token = security.create_access_token("user-1", "attorney")
    claims = security.decode_access_token(token)
    assert claims["sub"] == "user-1"
    assert claims["role"] == "attorney"


@skip_until_implemented
def test_decode_rejects_tampered_token():
    token = security.create_access_token("user-1", "operator")
    with pytest.raises(Exception):
        security.decode_access_token(token + "tamper")


@skip_until_implemented
def test_role_allowed():
    assert security.role_allowed("attorney", ("attorney", "admin")) is True
    assert security.role_allowed("operator", ("attorney", "admin")) is False
