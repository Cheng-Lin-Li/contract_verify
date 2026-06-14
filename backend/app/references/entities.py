"""Contract-entity extraction & value comparison (grounding enrichment).

A light, dependency-free pass over the *contract* CIR that pulls the concrete
data points coverage decisions hinge on — **parties, dates, monetary amounts,
percentages, payment (net-N) terms, and governing law** — each cited back to the
block it came from. This is intentionally an *internal enrichment*, not a
standalone "structured data extraction" feature: its purpose is to sharpen the
verification decision (e.g. distinguish "cap at $500k" from "cap at $250k") and
to make citations richer, not to compete with generic CLM metadata export.

The same regexes power :func:`value_conflict`, which the matcher uses to
downgrade a clean *Covered* to *Partial* when a requirement and the matched
clause both state a value of the same kind but the values differ.

Rule-based on purpose: it runs fully offline/local with no NER model, matching
the on-prem-first posture. A learned NER pass can later sit behind the same
function signature.
"""

from __future__ import annotations

import re
from typing import Any, Optional

from app.core.models import CIRDocument

# --- regexes ---------------------------------------------------------------

# Monetary amounts: a currency marker plus a number, optional k/m/bn multiplier.
_CURRENCY = r"(?:USD|US\$|\$|EUR|€|GBP|£|JPY|¥)"
_AMOUNT_RE = re.compile(
    rf"{_CURRENCY}\s?\d[\d,]*(?:\.\d+)?\s?(?:k|m|bn|million|billion|thousand)?",
    re.IGNORECASE,
)
_AMOUNT_TRAILING_RE = re.compile(
    r"\b\d[\d,]*(?:\.\d+)?\s?(?:USD|EUR|GBP|JPY|dollars|euros)\b",
    re.IGNORECASE,
)
_NET_TERM_RE = re.compile(r"net[\s\-]?(\d{1,3})", re.IGNORECASE)
_PERCENT_RE = re.compile(r"(\d{1,3}(?:\.\d+)?)\s?%")
_DATE_RES = [
    re.compile(r"\b\d{4}-\d{2}-\d{2}\b"),
    re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"),
    re.compile(
        r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\.?\s+\d{1,2},?\s+\d{4}\b"
    ),
]
_ORG_RE = re.compile(
    r"\b([A-Z][A-Za-z0-9&.\-]*(?:\s+[A-Z][A-Za-z0-9&.\-]*)*\s+"
    r"(?:Inc|LLC|L\.L\.C\.|Corp|Corporation|Ltd|Limited|GmbH|Co|Company|LP|LLP|PLC)\.?)\b"
)
_ROLE_RE = re.compile(
    r"\b(Customer|Vendor|Supplier|Provider|Client|Licensor|Licensee|"
    r"Buyer|Seller|Contractor|Disclosing Party|Receiving Party)\b"
)
_GOV_LAW_RES = [
    re.compile(r"govern(?:ed|ing)\s+(?:by\s+)?(?:the\s+)?laws?\s+of\s+(?:the\s+)?"
               r"(?:State\s+of\s+)?([A-Z][A-Za-z ]+?)(?:[,.;]|\s+without|\s*$)"),
    re.compile(r"\bState\s+of\s+([A-Z][A-Za-z]+)\b"),
]

_MULTIPLIER = {"k": 1_000, "thousand": 1_000, "m": 1_000_000, "million": 1_000_000,
               "bn": 1_000_000_000, "billion": 1_000_000_000}


def _normalize_amount(raw: str) -> Optional[float]:
    """Normalize a raw currency string to a numeric magnitude (rounded to cents)."""
    low = raw.lower()
    mult = 1
    for token, factor in _MULTIPLIER.items():
        if re.search(rf"\b{token}\b|\d\s*{token}\b|{token}$", low):
            mult = factor
            break
    digits = re.sub(r"[^\d.]", "", low)
    if not digits or digits == ".":
        return None
    try:
        return round(float(digits) * mult, 2)
    except ValueError:
        return None


# --- salient values & conflict --------------------------------------------

def salient_values(text: str) -> dict[str, set]:
    """Extract comparable numeric values from a piece of text.

    Returns a dict with sets of:
        * ``amounts``     — normalized monetary magnitudes (floats),
        * ``net_terms``   — payment net-N day counts (ints),
        * ``percentages`` — percentage values (floats).
    """
    amounts: set = set()
    for m in list(_AMOUNT_RE.finditer(text)) + list(_AMOUNT_TRAILING_RE.finditer(text)):
        val = _normalize_amount(m.group(0))
        if val is not None:
            amounts.add(val)
    net_terms = {int(m.group(1)) for m in _NET_TERM_RE.finditer(text)}
    percentages = {round(float(m.group(1)), 2) for m in _PERCENT_RE.finditer(text)}
    return {"amounts": amounts, "net_terms": net_terms, "percentages": percentages}


def value_conflict(requirement_text: str, clause_text: str) -> Optional[str]:
    """Return a reason string if a same-kind value differs between the two texts.

    A conflict is reported only when **both** texts contain a value of the same
    kind (amount / net-term / percentage) and the sets are disjoint — i.e. the
    requirement and the clause each name a value but they are not the same one.
    Mere absence in the clause is *not* a conflict (that is the LLM's call), so
    this never invents a downgrade.
    """
    r = salient_values(requirement_text)
    c = salient_values(clause_text)
    labels = {"amounts": "amount", "net_terms": "net-term", "percentages": "percent"}
    for kind, label in labels.items():
        if r[kind] and c[kind] and r[kind].isdisjoint(c[kind]):
            return (f"{label} differs: requirement {sorted(r[kind])} "
                    f"vs clause {sorted(c[kind])}")
    return None


# --- contract entity extraction --------------------------------------------

def _dedupe_keep_order(items: list[dict]) -> list[dict]:
    """Drop duplicate ``value`` entries, keeping first occurrence (with its block)."""
    seen: set = set()
    out: list[dict] = []
    for it in items:
        key = it["value"].lower()
        if key not in seen:
            seen.add(key)
            out.append(it)
    return out


def extract_contract_entities(doc: CIRDocument) -> dict[str, Any]:
    """Extract key entities from a contract CIR, each cited to its block.

    Args:
        doc: The contract :class:`CIRDocument`.

    Returns:
        A dict with ``parties``, ``dates``, ``amounts``, ``percentages``,
        ``net_terms`` and ``governing_law`` — each a list of
        ``{"value": str, "block_id": str}`` (governing_law is a single string or
        ``None``). This is attached to ``doc.metadata['entities']`` so it travels
        with the CIR and lands in the audit trail.
    """
    parties: list[dict] = []
    dates: list[dict] = []
    amounts: list[dict] = []
    percentages: list[dict] = []
    net_terms: list[dict] = []
    governing_law: Optional[str] = None

    for block in doc.blocks:
        text = block.text
        bid = block.block_id
        for m in _ORG_RE.finditer(text):
            parties.append({"value": m.group(1).strip(), "block_id": bid})
        for m in _ROLE_RE.finditer(text):
            parties.append({"value": m.group(1).strip(), "block_id": bid})
        for date_re in _DATE_RES:
            for m in date_re.finditer(text):
                dates.append({"value": m.group(0).strip(), "block_id": bid})
        for m in list(_AMOUNT_RE.finditer(text)) + list(_AMOUNT_TRAILING_RE.finditer(text)):
            amounts.append({"value": m.group(0).strip(), "block_id": bid})
        for m in _PERCENT_RE.finditer(text):
            percentages.append({"value": m.group(0).strip(), "block_id": bid})
        for m in _NET_TERM_RE.finditer(text):
            net_terms.append({"value": f"net-{m.group(1)}", "block_id": bid})
        if governing_law is None:
            for gov_re in _GOV_LAW_RES:
                gm = gov_re.search(text)
                if gm:
                    governing_law = gm.group(1).strip()
                    break

    return {
        "parties": _dedupe_keep_order(parties),
        "dates": _dedupe_keep_order(dates),
        "amounts": _dedupe_keep_order(amounts),
        "percentages": _dedupe_keep_order(percentages),
        "net_terms": _dedupe_keep_order(net_terms),
        "governing_law": governing_law,
    }


def entity_summary(entities: dict[str, Any]) -> dict[str, Any]:
    """Compact count summary of extracted entities for logs/audit."""
    return {
        "parties": len(entities.get("parties", [])),
        "dates": len(entities.get("dates", [])),
        "amounts": len(entities.get("amounts", [])),
        "percentages": len(entities.get("percentages", [])),
        "net_terms": len(entities.get("net_terms", [])),
        "governing_law": entities.get("governing_law"),
    }
