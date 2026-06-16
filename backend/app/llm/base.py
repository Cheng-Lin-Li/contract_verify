"""LLM provider adapter interface (TDD §3, §4.4).

Every LLM call in the system goes through :class:`LLMProvider`, so the local
default (Ollama on an RTX 4070 Ti) and the cloud option (Anthropic) are swapped
via the ``LLM_PROVIDER`` environment variable with no application changes. A
deterministic :class:`FakeProvider` (see ``fake_provider.py``) implements the
same interface so the pipeline runs offline / in CI with no GPU.
"""

from __future__ import annotations

import abc
import json
import re
from typing import Any, Optional


class LLMProvider(abc.ABC):
    """Abstract base class for chat-completion providers.

    Concrete providers implement :meth:`complete`. The convenience method
    :meth:`complete_json` wraps it with robust JSON extraction for the
    structured-output prompts used by extraction and verification.
    """

    name: str = "base"

    @abc.abstractmethod
    def complete(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        """Return the model's text completion for ``prompt``.

        Args:
            prompt: The user prompt (already rendered from a template).
            system: Optional system instruction.
            model: Override the provider's default model.
            temperature: Sampling temperature; defaults to a low, deterministic value.
            max_tokens: Maximum tokens to generate.

        Returns:
            The raw text content of the completion.
        """
        raise NotImplementedError

    def complete_json(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> Any:
        """Call :meth:`complete` and parse the result as JSON.

        Strips Markdown code fences and extracts the first balanced JSON value,
        so models that wrap output in prose or ```json fences still parse.

        Raises:
            ValueError: If no JSON value can be recovered from the completion.
        """
        raw = self.complete(
            prompt, system=system, model=model, temperature=temperature, max_tokens=max_tokens
        )
        return self.parse_json(raw)

    @staticmethod
    def parse_json(raw: str) -> Any:
        """Best-effort extraction of a JSON value from a model completion."""
        text = raw.strip()
        # Strip <think>...</think> reasoning blocks (Qwen3, DeepSeek-R1, etc.)
        # before any other parsing so their stray [ { chars don't confuse the
        # bracket-search fallback below.
        text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL).strip()
        # Remove ```json ... ``` or ``` ... ``` fences.
        text = re.sub(r"^```(?:json)?\s*|\s*```$", "", text, flags=re.MULTILINE).strip()
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        # Fall back to the first balanced [...] or {...} span.
        for opener, closer in (("[", "]"), ("{", "}")):
            start = text.find(opener)
            end = text.rfind(closer)
            if start != -1 and end != -1 and end > start:
                try:
                    return json.loads(text[start : end + 1])
                except json.JSONDecodeError:
                    continue
        raise ValueError(f"Could not parse JSON from model output: {raw[:200]!r}")
