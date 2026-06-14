"""LLM provider factory -- selects a provider from configuration (TDD §3).

``get_provider()`` reads ``LLM_PROVIDER`` and returns a ready provider. Adding a
new provider is a single registry entry; the rest of the system depends only on
the :class:`LLMProvider` interface.
"""

from __future__ import annotations

from typing import Optional

from app.config import Settings, get_settings
from app.llm.base import LLMProvider
from app.llm.fake_provider import FakeProvider
from app.logging_setup import get_logger

log = get_logger("llm.factory")


def get_provider(settings: Optional[Settings] = None) -> LLMProvider:
    """Return the configured :class:`LLMProvider`.

    Args:
        settings: Optional settings override (defaults to :func:`get_settings`).

    Returns:
        A provider instance for ``settings.llm_provider``.

    Raises:
        ValueError: If the configured provider name is unknown.
    """
    settings = settings or get_settings()
    provider = settings.llm_provider.lower()
    log.info("select_llm_provider", extra={"provider": provider})

    if provider == "fake":
        return FakeProvider()
    if provider == "ollama":
        from app.llm.ollama_provider import OllamaProvider

        return OllamaProvider(settings.llm_base_url, settings.llm_extraction_model)
    if provider == "anthropic":
        from app.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider(settings.anthropic_api_key, settings.llm_extraction_model)
    if provider in ("openai", "azure_openai"):
        # Backlog (TDD §20): OpenAI / Azure OpenAI adapters slot in here.
        raise ValueError(f"Provider '{provider}' is on the backlog and not yet implemented")
    raise ValueError(f"Unknown LLM_PROVIDER: {provider!r}")
