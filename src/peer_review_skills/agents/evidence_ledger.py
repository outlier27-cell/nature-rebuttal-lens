"""Evidence ledger construction for Nature RebuttalLens reports."""

from __future__ import annotations

import json
from typing import Any


def build_evidence_ledger(
    *,
    concerns: list[dict[str, Any]],
    evidence_items: list[Any],
    action_items: list[Any],
    manuscript_context: dict[str, Any],
    select_item,
) -> list[dict[str, Any]]:
    """Build machine-verifiable concern/evidence/action provenance rows."""
    sections = _sections_by_id(manuscript_context)
    ledger = []
    for index, concern in enumerate(concerns, start=1):
        evidence = select_item(evidence_items, index - 1, concern)
        action = select_item(action_items, index - 1, concern)
        section_id = str(evidence.get("section_id", "") or "")
        quote = _quote_for_evidence(evidence, sections.get(section_id, {}))
        ledger.append({
            "ledger_id": f"ledger_{index:03d}",
            "concern_id": _concern_id(concern, index),
            "concern_type": str(concern.get("concern_type", "unknown")),
            "support_status": str(evidence.get("status", "uncertain")),
            "manuscript_span": {
                "span_id": f"{section_id or 'none'}:{index:03d}",
                "section_id": section_id or "none",
                "heading": str(sections.get(section_id, {}).get("heading", "")),
                "quote": quote,
            },
            "case_ids": _string_list(action.get("supporting_case_ids")),
            "required_author_action": str(action.get("required_artifact", "")),
            "action_type": str(action.get("action_type", "")),
            "evidence_gap": str(evidence.get("gap", "")),
            "unsafe_claims": _unsafe_claims_for_evidence(evidence),
            "author_confirmation_required": bool(
                action.get("requires_author_confirmation", True)
            ),
        })
    return ledger


def validate_evidence_ledger(report: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate final report ledger/card referential integrity."""
    errors: list[str] = []
    ledger = report.get("evidence_ledger", [])
    if not isinstance(ledger, list):
        errors.append("evidence_ledger must be a list")
        ledger = []
    ledger_ids = {
        entry.get("ledger_id")
        for entry in ledger
        if isinstance(entry, dict) and entry.get("ledger_id")
    }
    for entry in ledger:
        if not isinstance(entry, dict):
            errors.append("evidence_ledger contains non-object entry")
            continue
        for key in [
            "ledger_id",
            "concern_id",
            "support_status",
            "manuscript_span",
            "required_author_action",
            "author_confirmation_required",
        ]:
            if key not in entry:
                errors.append(f"ledger entry missing {key}")
        manuscript_span = entry.get("manuscript_span")
        if not isinstance(manuscript_span, dict):
            errors.append(f"ledger entry {entry.get('ledger_id')} has invalid manuscript_span")
    for card in report.get("comment_cards", []):
        if not isinstance(card, dict):
            errors.append("comment_cards contains non-object entry")
            continue
        ledger_id = card.get("ledger_id")
        if ledger_id not in ledger_ids:
            errors.append(f"comment card {card.get('comment_id')} has orphan ledger_id {ledger_id}")
    return not errors, errors


def _sections_by_id(manuscript_context: dict[str, Any]) -> dict[str, dict[str, Any]]:
    sections = manuscript_context.get("sections", [])
    if not isinstance(sections, list):
        return {}
    return {
        str(section.get("section_id")): section
        for section in sections
        if isinstance(section, dict) and section.get("section_id")
    }


def _concern_id(concern: dict[str, Any], index: int) -> str:
    value = concern.get("concern_id") or concern.get("comment_id")
    return str(value).strip() if value else f"concern_{index:03d}"


def _quote_for_evidence(evidence: dict[str, Any], section: dict[str, Any]) -> str:
    explicit = str(evidence.get("text_evidence", "") or "").strip()
    if explicit:
        return explicit
    text = str(section.get("text", "") or "").strip()
    return text[:240]


def _unsafe_claims_for_evidence(evidence: dict[str, Any]) -> list[dict[str, str]]:
    status = str(evidence.get("status", "") or "").strip()
    if status in {"supported", "present"}:
        return []
    gap = str(evidence.get("gap", "") or "").strip()
    return [{
        "claim": "Concern is fully resolved",
        "reason": gap or f"evidence status is {status or 'uncertain'}",
    }]


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        value = [value]
    result = []
    seen = set()
    for item in value:
        text = str(item).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result


def canonical_report_json(report: dict[str, Any]) -> str:
    """Stable JSON form for snapshots or replay comparisons."""
    return json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2)
