"""Layer-2 (playbook) and Layer-3 (standard-terms) reference loaders.

Unlike Layer 1, these are *pre-loaded* libraries, not per-deal extraction. The
MVP loads them from small YAML/Markdown files on disk into
:class:`ReferenceItem`\\ s; the 3-month build versions them and embeds them into
Qdrant (TDD §5, §7). Each loader yields items in the common reference shape so
one matcher and one scorer serve all three layers.

YAML schema (per item)::

    - id: pb-001
      text: "Liability is capped at 12 months of fees."
      type: liability
      priority: Critical
      rule: must_have          # Layer 2 only
      contract_type: msa       # optional retrieval scope
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

from app.core.enums import Layer, PlaybookRule, Priority
from app.core.models import ReferenceItem
from app.logging_setup import get_logger

log = get_logger("references.loader")


def _load_yaml_items(directory: str | Path) -> list[dict]:
    """Load and concatenate the item lists from every YAML file in ``directory``.

    Raises:
        RuntimeError: If PyYAML is not installed.
        FileNotFoundError: If the directory does not exist.
    """
    try:
        import yaml
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("PyYAML is required to load reference libraries") from exc

    path = Path(directory)
    if not path.exists():
        raise FileNotFoundError(path)
    items: list[dict] = []
    for fp in sorted(path.glob("*.y*ml")):
        data = yaml.safe_load(fp.read_text(encoding="utf-8")) or []
        if isinstance(data, list):
            items.extend(data)
    return items


def _priority(value: str) -> Priority:
    try:
        return Priority(str(value).capitalize())
    except ValueError:
        return Priority.MEDIUM


def load_playbook(directory: str | Path) -> list[ReferenceItem]:
    """Load the Layer-2 company playbook into reference items.

    Args:
        directory: Directory of YAML playbook files.

    Returns:
        Layer-2 :class:`ReferenceItem`\\ s, each carrying a ``rule``.
    """
    items: list[ReferenceItem] = []
    for i, obj in enumerate(_load_yaml_items(directory), start=1):
        rule_val = obj.get("rule", "must_have")
        try:
            rule = PlaybookRule(rule_val)
        except ValueError:
            rule = PlaybookRule.PREFERRED
        items.append(
            ReferenceItem(
                item_id=obj.get("id", f"pb-{i:03d}"),
                layer=Layer.PLAYBOOK,
                text=obj["text"],
                type=obj.get("type", "general"),
                priority=_priority(obj.get("priority", "High")),
                rule=rule,
            )
        )
    log.info("playbook_loaded", extra={"count": len(items)})
    return items


def load_standard_terms(directory: str | Path, contract_type: Optional[str] = None) -> list[ReferenceItem]:
    """Load the Layer-3 standard-terms library into reference items.

    Args:
        directory: Directory of YAML standard-term files.
        contract_type: If given, keep only items whose ``contract_type`` matches
            or is unset (acts as the retrieval scope of TDD §7).

    Returns:
        Layer-3 :class:`ReferenceItem`\\ s.
    """
    items: list[ReferenceItem] = []
    for i, obj in enumerate(_load_yaml_items(directory), start=1):
        if contract_type and obj.get("contract_type") not in (None, contract_type):
            continue
        items.append(
            ReferenceItem(
                item_id=obj.get("id", f"st-{i:03d}"),
                layer=Layer.STANDARD_TERMS,
                text=obj["text"],
                type=obj.get("type", "general"),
                priority=_priority(obj.get("priority", "High")),
            )
        )
    log.info("standard_terms_loaded", extra={"count": len(items), "contract_type": contract_type})
    return items
