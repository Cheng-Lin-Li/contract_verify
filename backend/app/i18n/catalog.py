"""Server-side message catalog (3-month scope).

Resolves API/report strings by locale (en, ja) from ``backend/locales/<lang>.json``,
mirroring the externalized-prompt approach so adding a language is additive — drop
in a ``<lang>.json`` and it is picked up automatically.

Lookup is by dot-path (``"gate.violation"``) into the nested JSON. Missing keys
fall back to the default locale, then to the key itself, so a missing string is
visible but never raises. Interpolation uses ``str.format`` (``{name}``).
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

#: backend/locales — sibling of the ``app`` package (catalog.py is app/i18n/).
_LOCALES_DIR = Path(__file__).resolve().parents[2] / "locales"


@lru_cache(maxsize=None)
def _catalog(locale: str) -> dict[str, Any]:
    """Load and cache one locale's JSON catalog (empty dict if absent)."""
    path = _LOCALES_DIR / f"{locale}.json"
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}


def _lookup(catalog: dict[str, Any], key: str) -> str | None:
    """Resolve a dot-path ``key`` into ``catalog``; ``None`` if not a string."""
    node: Any = catalog
    for part in key.split("."):
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node if isinstance(node, str) else None


def translate(key: str, locale: str = "en", **kwargs: object) -> str:
    """Return the localized string for ``key`` in ``locale`` (with interpolation).

    Falls back to the deployment default locale, then to ``key`` itself.
    """
    from app.config import get_settings

    default = get_settings().default_locale
    template = (_lookup(_catalog(locale), key)
                or _lookup(_catalog(default), key)
                or key)
    if not kwargs:
        return template
    try:
        return template.format(**kwargs)
    except (KeyError, IndexError, ValueError):
        return template


def available_locales() -> list[str]:
    """Return the locales that have a (loadable, non-empty) catalog on disk."""
    if not _LOCALES_DIR.is_dir():
        return []
    return sorted(p.stem for p in _LOCALES_DIR.glob("*.json") if _catalog(p.stem))
