"""Server-side message catalog (3-month scope · SKELETON).

Resolves API/report strings by locale (en, ja) from ``backend/locales/<lang>``,
mirroring the externalized-prompt approach so adding a language is additive.
"""

from __future__ import annotations


def translate(key: str, locale: str = "en", **kwargs: object) -> str:
    """Return the localized string for ``key`` in ``locale`` (with interpolation)."""
    raise NotImplementedError


def available_locales() -> list[str]:
    """Return the locales that have a message catalog on disk."""
    raise NotImplementedError
