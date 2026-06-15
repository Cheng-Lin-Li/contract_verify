"""Deterministic, offline LLM provider for tests and air-gapped demos.

:class:`FakeProvider` satisfies the :class:`LLMProvider` contract without any
network or GPU. It uses simple, transparent heuristics so that:

* requirement extraction returns a small structured list derived from the input
  text, and
* verification returns a status by checking whether the requirement's key terms
  appear in the candidate contract clauses.

This makes the whole pipeline runnable end-to-end with ``LLM_PROVIDER=fake`` --
useful for CI, smoke tests and demos on machines without Ollama. It is **not** a
substitute for a real model; production runs use Ollama or Anthropic.
"""

from __future__ import annotations

import json
import re
from typing import Any, Optional

from app.llm.base import LLMProvider

_REQUIREMENT_HINTS = (
    "net-", "net ", "payment", "deliver", "sla", "credit", "data", "deletion",
    "liability", "cap", "terminate", "warranty", "indemnif", "confidential",
    "governing law", "renewal", "must", "shall", "require",
)


class FakeProvider(LLMProvider):
    """A rule-based stand-in for a real chat model (deterministic output)."""

    name = "fake"

    def complete(
        self,
        prompt: str,
        *,
        system: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048,
    ) -> str:
        """Return canned JSON appropriate to the prompt's task.

        The provider inspects the prompt for the task markers injected by the
        prompt templates (``[TASK:EXTRACT]`` / ``[TASK:VERIFY]``) and responds
        with deterministic structured JSON.
        """
        if "[TASK:VERIFY]" in prompt:
            return json.dumps(self._verify(prompt))
        if "[TASK:EXTRACT_PLAYBOOK]" in prompt:
            return json.dumps(self._extract_playbook(prompt))
        if "[TASK:EXTRACT_STANDARD_TERMS]" in prompt:
            return json.dumps(self._extract_standard_terms(prompt))
        if "[TASK:EXTRACT]" in prompt:
            return json.dumps(self._extract(prompt))
        return "{}"

    # -- task handlers -----------------------------------------------------

    @staticmethod
    def _candidate_lines(prompt: str) -> list[str]:
        """Split the SOURCE block out of a prompt into candidate lines."""
        m = re.search(r"\[SOURCE\](.*?)\[/SOURCE\]", prompt, flags=re.DOTALL)
        body = m.group(1) if m else prompt
        return [ln.strip() for ln in body.splitlines() if ln.strip()]

    def _extract(self, prompt: str) -> list[dict[str, Any]]:
        """Derive a small list of requirement items from the source text."""
        items: list[dict[str, Any]] = []
        for i, line in enumerate(self._candidate_lines(prompt), start=1):
            low = line.lower()
            if len(line) < 6:
                continue
            if any(h in low for h in _REQUIREMENT_HINTS):
                items.append(
                    {
                        "item_id": f"r-{i:03d}",
                        "text": line[:300],
                        "type": self._guess_type(low),
                        "priority": "Critical" if ("net-" in low or "liability" in low) else "Medium",
                        "binding": "term sheet" in low or "signed" in low,
                    }
                )
        return items[:25]

    def _verify(self, prompt: str) -> dict[str, Any]:
        """Decide a layer-appropriate status by term overlap with the clauses.

        The verify prompts differ per layer (requirement / playbook /
        standard-term) and name their own status vocabulary; this stand-in
        detects the layer from the prompt and maps a single overlap ratio onto
        that layer's enum so the deterministic offline path still exercises
        compliance, completeness and risk scoring.
        """
        # Detect the layer from distinctive phrasing in the verify templates.
        if "playbook position" in prompt:
            vocab = ("Compliant", "Deviation", "Violation")
        elif "standard market term" in prompt:
            vocab = ("Present", "Non-standard", "Missing")
        else:
            vocab = ("Covered", "Partial", "Missing")

        req = ""
        m = re.search(r"\[REQUIREMENT\](.*?)\[/REQUIREMENT\]", prompt, flags=re.DOTALL)
        if m:
            req = m.group(1).strip().lower()
        clauses = " ".join(self._candidate_lines(prompt)).lower()
        terms = [t for t in re.findall(r"[a-z0-9\-]{4,}", req) if t not in _STOP]
        if not terms:
            return {"status": vocab[2], "matched_clause_ids": [], "llm_confidence": 0.5,
                    "notes": "no salient terms"}
        hits = sum(1 for t in set(terms) if t in clauses)
        ratio = hits / len(set(terms))
        if ratio >= 0.6:
            status, conf = vocab[0], 0.9
        elif ratio > 0:
            status, conf = vocab[1], 0.7
        else:
            status, conf = vocab[2], 0.8
        return {
            "status": status,
            "matched_clause_ids": [],  # the matcher attaches real ids from retrieval
            "llm_confidence": conf,
            "notes": f"term overlap {hits}/{len(set(terms))}",
        }

    def _extract_playbook(self, prompt: str) -> list[dict]:
        """Return playbook positions derived from the source text."""
        items: list[dict] = []
        for line in self._candidate_lines(prompt):
            low = line.lower()
            if len(line) < 20:
                continue
            if not any(h in low for h in _REQUIREMENT_HINTS):
                continue
            if "must not" in low or "shall not" in low or "prohibited" in low:
                rule = "must_not_have"
            elif "should" in low or "prefer" in low or "recommended" in low:
                rule = "preferred"
            else:
                rule = "must_have"
            items.append({
                "text": line[:300],
                "type": self._guess_type(low),
                "priority": "Critical" if ("liability" in low or "net-" in low) else "High",
                "rule": rule,
            })
        return items[:25]

    def _extract_standard_terms(self, prompt: str) -> list[dict]:
        """Return standard-terms items derived from the source text."""
        items: list[dict] = []
        for line in self._candidate_lines(prompt):
            low = line.lower()
            if len(line) < 20:
                continue
            if not any(h in low for h in _REQUIREMENT_HINTS):
                continue
            items.append({
                "text": line[:300],
                "type": self._guess_type(low),
                "priority": "Critical" if "liability" in low else "High",
                "contract_type": "services",
            })
        return items[:25]

    @staticmethod
    def _guess_type(low: str) -> str:
        for key, typ in (
            ("payment", "payment"), ("net-", "payment"), ("data", "data"),
            ("deletion", "data"), ("sla", "SLA"), ("deliver", "delivery"),
            ("liability", "liability"), ("indemnif", "liability"),
            ("confidential", "confidentiality"), ("governing law", "governing_law"),
        ):
            if key in low:
                return typ
        return "general"


_STOP = {"the", "and", "for", "with", "that", "this", "shall", "must", "will",
         "from", "into", "have", "been", "their", "which", "within"}
