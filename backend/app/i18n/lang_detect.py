"""Lightweight, dependency-free document language detection (EN/JA).

Air-gap friendly: no model download, no network. Distinguishes Japanese from
Latin-script text by script ratio — Japanese legal text is dense with kana, so a
modest kana/CJK share is a strong signal, while English contracts contain none.
Used to auto-select the prompt-catalog locale when the caller doesn't force one.
"""

from __future__ import annotations

import re
from typing import Iterable, Optional

# Hiragana, Katakana, CJK Unified Ideographs, half-width katakana.
_JA = re.compile(r"[぀-ヿ一-鿿ｦ-ﾟ]")
_LATIN = re.compile(r"[A-Za-z]")

#: Minimum share of Japanese script (vs. JA+Latin chars) to classify as ``ja``.
_JA_RATIO = 0.20


def detect_locale(text: str, *, supported: Optional[Iterable[str]] = None,
                  default: str = "en") -> str:
    """Return the best-guess locale for ``text``.

    Args:
        text: The document text to inspect.
        supported: Allowed locales; a detected locale not in this set falls back
            to ``default``. ``None`` means "no restriction".
        default: Locale to return when the language is Latin-script/undetermined.

    Returns:
        ``"ja"`` when Japanese script dominates (and is permitted), else ``default``.
    """
    if not text:
        return default
    ja = len(_JA.findall(text))
    if ja == 0:
        return default
    latin = len(_LATIN.findall(text))
    total = ja + latin
    detected = "ja" if total and (ja / total) >= _JA_RATIO else default
    if supported is not None and detected not in set(supported):
        return default
    return detected
