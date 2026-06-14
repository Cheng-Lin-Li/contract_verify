"""Prompt catalog loader (Foundation Rule i; TDD §8, §10).

All LLM prompt text lives in Markdown catalogs at
``backend/prompts/<locale>/PROMPTS.md`` -- never hardcoded in source. Each
prompt is a level-3 heading (``### key``) followed by a fenced code block
containing the template. Templates use ``{placeholder}`` fields filled at render
time via :meth:`PromptCatalog.render`.

Example catalog entry::

    ### extract_requirements
    ```
    [TASK:EXTRACT]
    Extract business requirements from the following source.
    [SOURCE]
    {source_text}
    [/SOURCE]
    ```
"""

from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path
from typing import Optional

from app.config import get_settings

_HEADING_RE = re.compile(r"^###\s+(?P<key>[A-Za-z0-9_]+)\s*$")
_FENCE_RE = re.compile(r"```[a-zA-Z0-9]*\n(?P<body>.*?)```", re.DOTALL)


class PromptCatalog:
    """A parsed collection of named prompt templates for one locale."""

    def __init__(self, prompts: dict[str, str], locale: str) -> None:
        """Initialise from a ``{key: template}`` mapping."""
        self._prompts = prompts
        self.locale = locale

    @property
    def keys(self) -> list[str]:
        """Return the available prompt keys."""
        return sorted(self._prompts)

    def get(self, key: str) -> str:
        """Return the raw template for ``key``.

        Raises:
            KeyError: If the prompt key is not present in the catalog.
        """
        if key not in self._prompts:
            raise KeyError(f"Prompt '{key}' not found in {self.locale} catalog "
                           f"(have: {', '.join(self.keys)})")
        return self._prompts[key]

    def render(self, key: str, **variables: object) -> str:
        """Return the template for ``key`` with ``{placeholders}`` substituted.

        Args:
            key: Prompt key to render.
            **variables: Values for the template placeholders.

        Raises:
            KeyError: If a required placeholder has no provided value.
        """
        template = self.get(key)
        try:
            return template.format(**variables)
        except KeyError as exc:
            raise KeyError(f"Missing variable {exc} for prompt '{key}'") from exc


def parse_catalog(text: str, locale: str = "en") -> PromptCatalog:
    """Parse the Markdown body of a PROMPTS catalog into a :class:`PromptCatalog`.

    Args:
        text: Raw Markdown content.
        locale: Locale tag the catalog belongs to.
    """
    prompts: dict[str, str] = {}
    # Split on level-3 headings, keeping the key with the following body.
    lines = text.splitlines()
    current_key: Optional[str] = None
    buffer: list[str] = []

    def flush() -> None:
        if current_key is None:
            return
        body_md = "\n".join(buffer)
        fence = _FENCE_RE.search(body_md)
        prompts[current_key] = (fence.group("body") if fence else body_md).rstrip("\n")

    for line in lines:
        m = _HEADING_RE.match(line)
        if m:
            flush()
            current_key = m.group("key")
            buffer = []
        elif current_key is not None:
            buffer.append(line)
    flush()
    return PromptCatalog(prompts, locale)


@lru_cache(maxsize=4)
def load_catalog(locale: Optional[str] = None) -> PromptCatalog:
    """Load and cache the prompt catalog for ``locale`` (default: configured).

    Args:
        locale: Locale tag; falls back to ``DEFAULT_LOCALE`` from settings.

    Raises:
        FileNotFoundError: If the catalog file does not exist.
    """
    settings = get_settings()
    locale = locale or settings.default_locale
    path = Path(settings.prompts_dir) / locale / "PROMPTS.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt catalog not found: {path}")
    return parse_catalog(path.read_text(encoding="utf-8"), locale)
