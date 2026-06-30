"""The Japanese prompt catalog must stay structurally in sync with English.

The instruction prose is translated, but the prompt *keys*, the ``{placeholder}``
fields filled at render time, and the ``[TASK:...]`` markers the offline
provider parses must be identical across locales — otherwise a JA run would
render the wrong fields or fail to parse. These tests guard that contract.
"""

from __future__ import annotations

import re

from app.prompts.loader import load_catalog

_PLACEHOLDER = re.compile(r"\{([a-zA-Z0-9_]+)\}")
_TASK = re.compile(r"\[TASK:[A-Z_]+\]")


def _placeholders(template: str) -> set[str]:
    return set(_PLACEHOLDER.findall(template))


def test_ja_catalog_has_same_keys_as_en():
    en = load_catalog("en")
    ja = load_catalog("ja")
    assert ja.keys == en.keys


def test_ja_placeholders_match_en_per_prompt():
    en = load_catalog("en")
    ja = load_catalog("ja")
    for key in en.keys:
        assert _placeholders(en.get(key)) == _placeholders(ja.get(key)), key


def test_ja_preserves_task_markers():
    en = load_catalog("en")
    ja = load_catalog("ja")
    for key in en.keys:
        assert _TASK.findall(en.get(key)) == _TASK.findall(ja.get(key)), key


def test_unknown_locale_falls_back_to_default():
    # A locale with no catalog on disk degrades to the default (English) catalog.
    cat = load_catalog("zz")
    assert cat.locale == "en"
