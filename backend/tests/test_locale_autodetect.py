"""Language auto-detection: the detector heuristic and pipeline wiring."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path

from app.config import reset_settings_cache
from app.i18n.lang_detect import detect_locale
from app.llm.fake_provider import FakeProvider
from app.pipeline import VerificationPipeline

from tests.helpers import PLAYBOOK_DIR, STDTERMS_DIR

_JA_TEXT = "本契約は、支払条件をネット30日と定め、秘密保持義務および責任の上限を含む。"
_EN_TEXT = "This Agreement sets payment on net-30 terms and includes confidentiality."


# --- detector unit tests ---------------------------------------------------

def test_detects_japanese():
    assert detect_locale(_JA_TEXT, supported=["en", "ja"]) == "ja"


def test_detects_english():
    assert detect_locale(_EN_TEXT, supported=["en", "ja"]) == "en"


def test_empty_text_returns_default():
    assert detect_locale("", supported=["en", "ja"], default="en") == "en"


def test_unsupported_detected_locale_falls_back():
    # Japanese detected, but ja not permitted -> default.
    assert detect_locale(_JA_TEXT, supported=["en"], default="en") == "en"


def test_mixed_mostly_english_stays_english():
    # A stray kanji in an otherwise English sentence must not flip to ja.
    assert detect_locale("Governing law clause 第 present here.",
                         supported=["en", "ja"]) == "en"


# --- pipeline integration --------------------------------------------------

def _run_pipeline_on(text: str):
    """Run the pipeline on a temp contract and return its resolved locale."""
    prev = {k: os.environ.get(k) for k in ("SUPPORTED_LOCALES", "AUTO_DETECT_LOCALE")}
    os.environ["SUPPORTED_LOCALES"] = "en,ja"
    os.environ["AUTO_DETECT_LOCALE"] = "true"
    reset_settings_cache()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            contract = Path(tmp) / "contract.txt"
            contract.write_text(text, encoding="utf-8")
            pipe = VerificationPipeline(provider=FakeProvider())
            pipe.run(str(contract), [], PLAYBOOK_DIR, STDTERMS_DIR, contract_type="services")
            return pipe.locale
    finally:
        for k, v in prev.items():
            if v is None:
                os.environ.pop(k, None)
            else:
                os.environ[k] = v
        reset_settings_cache()


def test_pipeline_auto_detects_japanese_contract():
    assert _run_pipeline_on(_JA_TEXT) == "ja"


def test_pipeline_keeps_english_for_english_contract():
    assert _run_pipeline_on(_EN_TEXT) == "en"


def test_explicit_locale_overrides_detection():
    prev = os.environ.get("SUPPORTED_LOCALES")
    os.environ["SUPPORTED_LOCALES"] = "en,ja"
    reset_settings_cache()
    try:
        with tempfile.TemporaryDirectory() as tmp:
            contract = Path(tmp) / "contract.txt"
            contract.write_text(_JA_TEXT, encoding="utf-8")
            # Forcing en must skip detection even though the doc is Japanese.
            pipe = VerificationPipeline(provider=FakeProvider(), locale="en")
            pipe.run(str(contract), [], PLAYBOOK_DIR, STDTERMS_DIR, contract_type="services")
            assert pipe.locale == "en"
    finally:
        if prev is None:
            os.environ.pop("SUPPORTED_LOCALES", None)
        else:
            os.environ["SUPPORTED_LOCALES"] = prev
        reset_settings_cache()
