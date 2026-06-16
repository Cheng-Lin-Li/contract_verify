"""Ollama (local, llama.cpp) provider -- the on-prem default (TDD §4.4).

Targets the OpenAI-compatible / native Ollama HTTP endpoint exposed on the
customer's host (default ``http://localhost:11434``), so the same adapter shape
is reused by the cloud providers. Models (e.g. ``qwen3:14b``)
run on the RTX 4070 Ti; no data leaves the host.
"""

from __future__ import annotations

from typing import Optional

from app.llm.base import LLMProvider


class OllamaProvider(LLMProvider):
    """Chat-completion provider backed by a local Ollama server."""

    name = "ollama"

    def __init__(self, base_url: str, default_model: str, timeout: float = 600.0) -> None:
        """Initialise the provider.

        Args:
            base_url: Base URL of the Ollama server (no trailing ``/``).
            default_model: Model tag used when a call does not override it.
            timeout: Per-request timeout in seconds (large models are slow).
        """
        self.base_url = base_url.rstrip("/")
        self.default_model = default_model
        self.timeout = timeout

    def complete(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        """Call Ollama's ``/api/chat`` endpoint and return the text content.

        Imports ``requests`` lazily so importing this module never requires the
        dependency when a different provider is selected.

        Raises:
            RuntimeError: If the HTTP call fails or returns an error payload.
        """
        import requests  # lazy import

        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        model_name = model or self.default_model
        payload = {
            "model": model_name,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens},
        }
        try:
            resp = requests.post(f"{self.base_url}/api/chat", json=payload, timeout=self.timeout)
            if resp.status_code == 404:
                # Ollama returns 404 from /api/chat when the tag isn't pulled locally.
                raise RuntimeError(
                    f"Ollama has no local model '{model_name}'. Pull it with "
                    f"`ollama pull {model_name}`, or set LLM_EXTRACTION_MODEL / "
                    f"LLM_VERIFY_MODEL in .env to a tag shown by `ollama list`."
                )
            resp.raise_for_status()
        except RuntimeError:
            raise
        except Exception as exc:  # pragma: no cover - network path
            raise RuntimeError(f"Ollama request failed: {exc}") from exc

        data = resp.json()
        return (data.get("message") or {}).get("content", "")
