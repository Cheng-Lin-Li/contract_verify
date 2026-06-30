"""Tests for settings loading (Foundation Rule i/l: nothing hardcoded).

Verifies defaults, ``.env``/environment overrides, threshold parsing, and the
prompt-catalog path helper.
"""

from __future__ import annotations

import os

from app.config import get_settings, reset_settings_cache


def _reload():
    reset_settings_cache()
    return get_settings()


def test_defaults_present():
    s = _reload()
    assert s.app_version == "1.0.0"
    assert s.ocr_engine  # has a default
    assert 0.0 < s.cs_human_review_threshold < s.cs_auto_confirm_threshold <= 1.0


def test_env_override_provider(monkeypatch_env=None):
    os.environ["LLM_PROVIDER"] = "anthropic"
    try:
        s = _reload()
        assert s.llm_provider == "anthropic"
    finally:
        os.environ["LLM_PROVIDER"] = "fake"
        _reload()


def test_threshold_parsing_from_env():
    os.environ["CS_HUMAN_REVIEW_THRESHOLD"] = "0.55"
    os.environ["RISK_ATTORNEY_THRESHOLD"] = "42"
    try:
        s = _reload()
        assert abs(s.cs_human_review_threshold - 0.55) < 1e-9
        assert s.risk_attorney_threshold == 42
    finally:
        del os.environ["CS_HUMAN_REVIEW_THRESHOLD"]
        del os.environ["RISK_ATTORNEY_THRESHOLD"]
        _reload()


def test_prompt_catalog_path_uses_locale():
    s = _reload()
    p = s.prompt_catalog_path()
    assert p.name == "PROMPTS.md"
    assert s.default_locale in str(p)


# --- deployment model -----------------------------------------------------

def test_default_deployment_is_on_prem_and_local():
    os.environ["LLM_PROVIDER"] = "ollama"
    try:
        s = _reload()
        assert s.deployment_mode == "on_prem"
        residency = s.component_residency()
        assert residency["llm"] == "local"
        assert residency["database"] == "local"
        assert s.validate_deployment() == []  # consistent
    finally:
        os.environ["LLM_PROVIDER"] = "fake"
        _reload()


def test_on_prem_with_cloud_llm_warns():
    os.environ["LLM_PROVIDER"] = "anthropic"
    os.environ["DEPLOYMENT_MODE"] = "on_prem"
    try:
        s = _reload()
        assert s.component_residency()["llm"] == "cloud"
        warnings = s.validate_deployment()
        assert any("leave the host" in w for w in warnings)
    finally:
        os.environ["LLM_PROVIDER"] = "fake"
        del os.environ["DEPLOYMENT_MODE"]
        _reload()


def test_hybrid_cloud_llm_local_data_is_consistent():
    os.environ["LLM_PROVIDER"] = "anthropic"
    os.environ["DEPLOYMENT_MODE"] = "hybrid"
    try:
        s = _reload()
        res = s.component_residency()
        assert res["llm"] == "cloud" and res["database"] == "local"
        assert s.validate_deployment() == []  # proper split, no warning
    finally:
        os.environ["LLM_PROVIDER"] = "fake"
        del os.environ["DEPLOYMENT_MODE"]
        _reload()


def test_cloud_mode_with_local_data_store_warns():
    os.environ["DEPLOYMENT_MODE"] = "cloud"
    try:
        s = _reload()  # default sqlite/local stores
        warnings = s.validate_deployment()
        assert any("data stores are still local" in w for w in warnings)
    finally:
        del os.environ["DEPLOYMENT_MODE"]
        _reload()


def test_cloud_stores_detected_as_cloud():
    os.environ["DATABASE_URL"] = "postgresql://db.example.com:5432/cv"
    os.environ["BLOB_DIR"] = "s3://bucket/blobs"
    try:
        s = _reload()
        res = s.component_residency()
        assert res["database"] == "cloud"
        assert res["blobs"] == "cloud"
    finally:
        del os.environ["DATABASE_URL"]
        del os.environ["BLOB_DIR"]
        _reload()


def test_unknown_deployment_mode_warns():
    os.environ["DEPLOYMENT_MODE"] = "spaceship"
    try:
        s = _reload()
        assert any("Unknown DEPLOYMENT_MODE" in w for w in s.validate_deployment())
    finally:
        del os.environ["DEPLOYMENT_MODE"]
        _reload()
