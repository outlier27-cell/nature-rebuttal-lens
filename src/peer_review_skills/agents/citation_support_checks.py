"""Conservative citation and retrieved-case support checks."""

from __future__ import annotations

from typing import Any


def grade_citation_support(card: dict[str, Any]) -> dict[str, Any]:
    text = " ".join(
        str(card.get(key, ""))
        for key in [
            "category",
            "surface_request",
            "recommended_action",
            "action_type",
        ]
    ).lower()
    applies = "citation" in text or card.get("category") == "citation_positioning"
    if not applies:
        return {
            "applies": False,
            "support_grade": "not_applicable",
            "can_be_used_as_evidence": False,
        }
    supplied_refs = card.get("evidence_refs") or []
    has_verified_ref = any(
        str(ref).startswith(("doi:", "pmid:", "section:", "citation:"))
        for ref in supplied_refs
    )
    if has_verified_ref:
        return {
            "applies": True,
            "support_grade": "supplied_anchor",
            "can_be_used_as_evidence": True,
            "required_verification": "",
        }
    return {
        "applies": True,
        "support_grade": "needs_verification",
        "can_be_used_as_evidence": False,
        "required_verification": (
            "Need verified bibliographic detail, DOI/PMID/publisher page, "
            "and claim-level support check."
        ),
    }
