"""Anthropic Claude provider -- the opt-in cloud path (TDD §4.4).

Selected with ``LLM_PROVIDER=anthropic``; used only when a customer accepts
cloud processing and wants peak accuracy. The SDK is imported lazily so the
dependency is never required for local/air-gapped deployments.
"""

from __future__ import annotations

from typing import Optional

from app.llm.base import LLMProvider


class AnthropicProvider(LLMProvider):
    """Chat-completion provider backed by the Anthropic Messages API."""

    name = "anthropic"

    def __init__(self, api_key: Optional[str], default_model: str) -> None:
        """Initialise the provider.

        Args:
            api_key: Anthropic API key (from ``ANTHROPIC_API_KEY``).
            default_model: Model id, e.g. ``claude-sonnet-4-6``.

        Raises:
            ValueError: If no API key is configured.
        """
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY is required for the anthropic provider")
        self.api_key = api_key
        self.default_model = default_model

    def complete(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        """Call the Anthropic Messages API and return the text content.

        Raises:
            RuntimeError: If the SDK is unavailable or the request fails.
        """
        try:  # pragma: no cover - cloud path
            import anthropic  # type: ignore
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "The 'anthropic' package is required for LLM_PROVIDER=anthropic"
            ) from exc

        client = anthropic.Anthropic(api_key=self.api_key)
        kwargs = {
            "model": model or self.default_model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": [{"role": "user", "content": prompt}],
        }
        if system:
            kwargs["system"] = system
        msg = client.messages.create(**kwargs)  # type: ignore[arg-type]
        return "".join(block.text for block in msg.content if getattr(block, "type", "") == "text")
