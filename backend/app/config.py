"""Application configuration, loaded from the environment / ``.env`` file.

Per Foundation Rule (i): no constant value or LLM prompt is hardcoded in source
-- OCR engine, LLM provider/model, thresholds, log paths and locale all resolve
from environment variables (TDD Appendix). The production build uses
``pydantic-settings``; to keep the MVP runnable on a minimal/air-gapped host we
implement a dependency-light ``Settings`` dataclass that reads ``os.environ``
after best-effort loading of a ``.env`` file via ``python-dotenv``.

Usage::

    from app.config import get_settings
    settings = get_settings()
    print(settings.llm_provider)
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Optional

try:  # python-dotenv is available in the MVP image; degrade gracefully if not.
    from dotenv import load_dotenv  # type: ignore
except Exception:  # pragma: no cover - trivial fallback
    def load_dotenv(*_args, **_kwargs):  # type: ignore
        return False


def _env(key: str, default: str) -> str:
    """Return ``os.environ[key]`` or ``default`` if unset/empty."""
    val = os.environ.get(key)
    return val if val not in (None, "") else default


def _env_float(key: str, default: float) -> float:
    """Return a float environment variable, falling back to ``default``."""
    try:
        return float(os.environ.get(key, ""))
    except (TypeError, ValueError):
        return default


def _env_int(key: str, default: int) -> int:
    """Return an int environment variable, falling back to ``default``."""
    try:
        return int(os.environ.get(key, ""))
    except (TypeError, ValueError):
        return default


@dataclass
class Settings:
    """Resolved runtime configuration for one process.

    Field defaults mirror ``.env.example`` so the system has sane behaviour even
    with an empty environment (local Ollama, Tesseract OCR, English locale).
    """

    app_version: str = field(default_factory=lambda: _env("APP_VERSION", "0.9.0"))

    # --- Deployment model (on_prem | cloud | hybrid) ---
    # The product supports three deployment models. ``on_prem`` keeps every
    # component on customer-controlled infrastructure (air-gap capable);
    # ``cloud`` runs every component in a cloud tenant; ``hybrid`` splits them so
    # sensitive data (documents, DB, audit) can stay on-prem while compute or
    # public-facing pieces run in the cloud. The mode is declarative: it drives
    # the data-residency report and a guardrail that warns when a component's
    # actual placement contradicts the declared mode (see ``validate_deployment``).
    deployment_mode: str = field(default_factory=lambda: _env("DEPLOYMENT_MODE", "on_prem"))

    # --- LLM provider ---
    llm_provider: str = field(default_factory=lambda: _env("LLM_PROVIDER", "ollama"))
    llm_base_url: str = field(default_factory=lambda: _env("LLM_BASE_URL", "http://localhost:11434"))
    llm_extraction_model: str = field(
        default_factory=lambda: _env("LLM_EXTRACTION_MODEL", "qwen3:14b")
    )
    llm_verify_model: str = field(
        default_factory=lambda: _env("LLM_VERIFY_MODEL", "qwen3:14b")
    )
    embedding_model: str = field(default_factory=lambda: _env("EMBEDDING_MODEL", "bge-m3"))
    anthropic_api_key: Optional[str] = field(default_factory=lambda: os.environ.get("ANTHROPIC_API_KEY"))
    llm_temperature: float = field(default_factory=lambda: _env_float("LLM_TEMPERATURE", 0.1))

    # --- OCR ---
    ocr_engine: str = field(default_factory=lambda: _env("OCR_ENGINE", "tesseract"))

    # --- Storage (MVP: sqlite + filesystem) ---
    database_url: str = field(default_factory=lambda: _env("DATABASE_URL", "sqlite:///./contract_verify.db"))
    blob_dir: str = field(default_factory=lambda: _env("BLOB_DIR", "./var/blobs"))
    audit_log_path: str = field(default_factory=lambda: _env("AUDIT_LOG_PATH", "./var/audit.jsonl"))

    # --- S3 / MinIO (only used when BLOB_DIR is an s3:// URL) ---
    # Lets a hybrid deployment ship blobs to an S3-compatible object store
    # (MinIO on-prem, or AWS S3 in the cloud) while the DB stays local.
    s3_endpoint_url: str = field(default_factory=lambda: _env("S3_ENDPOINT_URL", ""))
    s3_access_key: str = field(default_factory=lambda: _env("S3_ACCESS_KEY", ""))
    s3_secret_key: str = field(default_factory=lambda: _env("S3_SECRET_KEY", ""))
    s3_region: str = field(default_factory=lambda: _env("S3_REGION", "us-east-1"))

    # --- Scoring thresholds (configurable per deployment, PRD Appendix) ---
    cs_human_review_threshold: float = field(
        default_factory=lambda: _env_float("CS_HUMAN_REVIEW_THRESHOLD", 0.70)
    )
    cs_auto_confirm_threshold: float = field(
        default_factory=lambda: _env_float("CS_AUTO_CONFIRM_THRESHOLD", 0.85)
    )
    risk_attorney_threshold: int = field(
        default_factory=lambda: _env_int("RISK_ATTORNEY_THRESHOLD", 60)
    )

    # --- Localization ---
    default_locale: str = field(default_factory=lambda: _env("DEFAULT_LOCALE", "en"))
    supported_locales: str = field(default_factory=lambda: _env("SUPPORTED_LOCALES", "en"))

    # --- Prompts ---
    prompts_dir: str = field(default_factory=lambda: _env("PROMPTS_DIR", "backend/prompts"))

    # --- API / auth (demo server) ---
    # Secret used to sign JWTs. MUST be overridden in production via SECRET_KEY.
    secret_key: str = field(default_factory=lambda: _env("SECRET_KEY", "dev-insecure-change-me"))
    jwt_algorithm: str = field(default_factory=lambda: _env("JWT_ALGORITHM", "HS256"))
    jwt_expire_minutes: int = field(default_factory=lambda: _env_int("JWT_EXPIRE_MINUTES", 480))
    # Comma-separated list of allowed browser origins for the SPA (CORS).
    cors_origins: str = field(
        default_factory=lambda: _env("CORS_ORIGINS", "http://localhost:5173")
    )
    # Where the demo user store, generated reports, and uploads live.
    users_db_path: str = field(default_factory=lambda: _env("USERS_DB_PATH", "./var/users.json"))
    reports_dir: str = field(default_factory=lambda: _env("REPORTS_DIR", "./var/reports"))
    uploads_dir: str = field(default_factory=lambda: _env("UPLOADS_DIR", "./var/uploads"))
    # Layer-2 / Layer-3 libraries the API verifies uploads against (the SPA only
    # uploads the contract + deal sources; these supply the playbook/standard terms).
    demo_playbook_dir: str = field(default_factory=lambda: _env("DEMO_PLAYBOOK_DIR", "samples/playbook"))
    demo_standard_terms_dir: str = field(
        default_factory=lambda: _env("DEMO_STANDARD_TERMS_DIR", "samples/standard_terms")
    )

    def cors_origin_list(self) -> list[str]:
        """Return ``CORS_ORIGINS`` parsed into a list."""
        return [s.strip() for s in self.cors_origins.split(",") if s.strip()]

    # --- Logging ---
    log_level: str = field(default_factory=lambda: _env("LOG_LEVEL", "INFO"))
    log_file: str = field(default_factory=lambda: _env("LOG_FILE", ""))
    log_format: str = field(default_factory=lambda: _env("LOG_FORMAT", "json"))

    def prompt_catalog_path(self) -> Path:
        """Return the path to the prompt catalog for the default locale."""
        return Path(self.prompts_dir) / self.default_locale / "PROMPTS.md"

    def supported_locale_list(self) -> list[str]:
        """Return ``SUPPORTED_LOCALES`` parsed into a list."""
        return [s.strip() for s in self.supported_locales.split(",") if s.strip()]

    # --- Deployment / data-residency helpers ---------------------------------

    def _is_local_endpoint(self, value: str) -> bool:
        """Heuristic: does a URL/path point at the local host rather than cloud?"""
        v = (value or "").lower()
        if v.startswith(("sqlite://", "file:", "./", "/", "../")) or not v:
            return True
        if "://" not in v:  # bare filesystem path
            return True
        return any(h in v for h in ("localhost", "127.0.0.1", "host.docker.internal", "::1"))

    def component_residency(self) -> dict[str, str]:
        """Report where each major component runs: ``local`` vs ``cloud``.

        Inferred from the actual configured providers/endpoints so the report
        reflects reality rather than the declared :attr:`deployment_mode`.
        """
        cloud_llm = {"anthropic", "openai", "azure_openai"}
        cloud_ocr = {"google_vision", "azure_vision"}
        return {
            "llm": "cloud" if self.llm_provider.lower() in cloud_llm else "local",
            "ocr": "cloud" if self.ocr_engine.lower() in cloud_ocr else "local",
            "database": "local" if self._is_local_endpoint(self.database_url) else "cloud",
            "blobs": "local" if self._is_local_endpoint(self.blob_dir) else "cloud",
            "audit": "local" if self._is_local_endpoint(self.audit_log_path) else "cloud",
        }

    def validate_deployment(self) -> list[str]:
        """Guardrail: warn when actual component placement contradicts the mode.

        Returns a list of human-readable warnings (empty when consistent).

        The check distinguishes two kinds of component:

        * **Compute** (``llm``, ``ocr``) runs wherever the app runs. A *cloud*
          LLM/OCR is an external API call, so it sends document content off the
          host; a *local* engine simply runs in-process.
        * **Data stores** (``database``, ``blobs``, ``audit``) have a true
          residency: where the data physically lives.

        This protects the on-prem promise (it flags any cloud component that
        would move data off the host) and confirms a ``hybrid`` deployment keeps
        sensitive data local while using cloud compute/stores elsewhere.
        """
        residency = self.component_residency()
        data_components = ("database", "blobs", "audit")
        cloud = [c for c, loc in residency.items() if loc == "cloud"]
        local_data = [c for c in data_components if residency[c] == "local"]
        mode = self.deployment_mode.lower()

        if mode not in ("on_prem", "cloud", "hybrid"):
            return [f"Unknown DEPLOYMENT_MODE='{self.deployment_mode}' (expected on_prem|cloud|hybrid)."]

        warnings: list[str] = []
        if mode == "on_prem" and cloud:
            warnings.append(
                "DEPLOYMENT_MODE=on_prem but these components are cloud-bound: "
                f"{', '.join(sorted(cloud))}. Data will leave the host. "
                "Set them to local providers, or switch to hybrid/cloud."
            )
        elif mode == "cloud" and local_data:
            warnings.append(
                "DEPLOYMENT_MODE=cloud but these data stores are still local: "
                f"{', '.join(sorted(local_data))}. They will not persist or be reachable "
                "from a cloud tenant; point them at managed cloud stores."
            )
        elif mode == "hybrid" and (not cloud or not local_data):
            warnings.append(
                "DEPLOYMENT_MODE=hybrid but the split is degenerate "
                f"(cloud={sorted(cloud)}, local-data={sorted(local_data)}). "
                "A hybrid deployment should keep sensitive data local while running "
                "other components in the cloud."
            )
        return warnings


@lru_cache(maxsize=1)
def get_settings(env_file: Optional[str] = ".env") -> Settings:
    """Load and cache :class:`Settings`.

    The ``.env`` file (if present) is loaded into ``os.environ`` first, then a
    :class:`Settings` instance is built from the environment. Cached so repeated
    calls are cheap; pass a different ``env_file`` and call
    :func:`reset_settings_cache` in tests to reload.

    Args:
        env_file: Path to a dotenv file to load before reading the environment.

    Returns:
        A populated :class:`Settings` instance.
    """
    if env_file and Path(env_file).exists():
        load_dotenv(env_file, override=False)
    return Settings()


def reset_settings_cache() -> None:
    """Clear the cached settings (used by tests after mutating the environment)."""
    get_settings.cache_clear()
