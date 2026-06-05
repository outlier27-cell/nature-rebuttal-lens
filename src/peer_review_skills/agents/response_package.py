"""Nature-response compatible package schema for RebuttalLens final reports."""

from __future__ import annotations

from typing import Any


NATURE_ACTION_LABELS = {
    "ACCEPT_TEXT",
    "ACCEPT_ANALYSIS",
    "ACCEPT_EXPERIMENT",
    "ACCEPT_FIGURE",
    "CLARIFY_EXISTING",
    "ADD_CITATION",
    "SOFTEN_CLAIM",
    "PARTIAL",
    "DISAGREE",
    "OUT_OF_SCOPE",
    "AUTHOR_INPUT_NEEDED",
    "BLOCKING",
}

READINESS_STATES = {
    "ready_to_submit",
    "draft_with_placeholders",
    "needs_author_input",
    "decision_deferred",
    "blocked",
}


def infer_nature_action(
    *,
    action_type: str,
    evidence_status: str,
    required_artifact: str,
    requires_author_confirmation: bool,
) -> str:
    """Map internal RebuttalLens action labels to Nature-response action labels."""
    action = str(action_type or "").strip()
    evidence = str(evidence_status or "").strip()
    artifact = str(required_artifact or "").strip()
    if requires_author_confirmation:
        return "AUTHOR_INPUT_NEEDED"
    if evidence == "missing" and action in {"claim_narrowing", "limitation_discussion"}:
        return "SOFTEN_CLAIM"
    if evidence == "missing" and action in {"code_data_availability"}:
        return "AUTHOR_INPUT_NEEDED"
    mapping = {
        "claim_narrowing": "SOFTEN_CLAIM",
        "code_data_availability": "ACCEPT_TEXT",
        "figure_table_revision": "ACCEPT_FIGURE",
        "future_work_commitment": "PARTIAL",
        "limitation_discussion": "PARTIAL",
        "literature_repositioning": "ADD_CITATION",
        "method_clarification": "CLARIFY_EXISTING",
        "new_analysis": "ACCEPT_ANALYSIS",
        "new_baseline_or_comparison": "ACCEPT_ANALYSIS",
        "new_experiment": "ACCEPT_EXPERIMENT",
        "no_new_evidence_explanation_only": "CLARIFY_EXISTING",
        "statistical_test_or_uncertainty": "ACCEPT_ANALYSIS",
        "supplementary_material_revision": "ACCEPT_TEXT",
    }
    if action in mapping:
        return mapping[action]
    if artifact:
        return "ACCEPT_TEXT"
    return "AUTHOR_INPUT_NEEDED"


def infer_category(concern_type: str, action_type: str) -> str:
    text = f"{concern_type} {action_type}".lower()
    if any(token in text for token in ["data", "code", "material", "availability", "repository"]):
        return "data_code_materials"
    if any(token in text for token in ["citation", "literature", "novelty", "prior"]):
        return "citation_positioning"
    if any(token in text for token in ["stat", "uncertainty", "sample", "replicate"]):
        return "statistical"
    if any(
        token in text
        for token in [
            "method",
            "reproduc",
            "baseline",
            "validation",
            "evaluation",
            "experiment",
            "design",
        ]
    ):
        return "methodological"
    if any(token in text for token in ["claim", "interpret", "evidence"]):
        return "evidence_interpretation"
    return "editorial_presentation"


def infer_severity(category: str, evidence_status: str, proposed_action: str) -> str:
    if proposed_action == "BLOCKING":
        return "blocking"
    if category == "data_code_materials" and evidence_status == "missing":
        return "blocking"
    if evidence_status in {"missing", "partially_supported", "uncertain"}:
        return "major"
    return "minor"


def infer_risk_level(severity: str, evidence_status: str, proposed_action: str) -> str:
    if severity == "blocking" or proposed_action == "BLOCKING":
        return "blocking"
    if severity == "major" or evidence_status in {"missing", "partially_supported", "uncertain"}:
        return "high"
    if proposed_action in {"ADD_CITATION", "ACCEPT_FIGURE", "ACCEPT_TEXT"}:
        return "medium"
    return "low"


def infer_readiness(
    *,
    proposed_action: str,
    evidence_status: str,
    author_input_required: bool,
    evidence_anchor: str,
    action_type: str = "",
    risk_level: str = "",
) -> str:
    if proposed_action == "BLOCKING":
        return "blocked"
    if (
        author_input_required
        and str(risk_level) in {"high", "blocking"}
        and _requires_author_decision(action_type)
    ):
        return "decision_deferred"
    if author_input_required or proposed_action == "AUTHOR_INPUT_NEEDED":
        return "needs_author_input"
    if evidence_status in {"missing", "uncertain"}:
        return "needs_author_input"
    if not evidence_anchor:
        return "draft_with_placeholders"
    return "ready_to_submit"


def build_response_package_cards(
    *,
    concern_map: list[dict[str, Any]],
    evidence_map: list[dict[str, Any]],
    action_plan: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    cards = []
    for index, concern in enumerate(concern_map, start=1):
        evidence = _select_for_concern(evidence_map, index - 1, concern)
        action = _select_for_concern(action_plan, index - 1, concern)
        comment_id = str(
            concern.get("comment_id")
            or concern.get("concern_id")
            or action.get("concern_id")
            or evidence.get("concern_id")
            or f"comment_{index:03d}"
        )
        evidence_status = str(evidence.get("status", "uncertain"))
        action_type = str(action.get("action_type", ""))
        required_artifact = str(action.get("required_artifact", ""))
        author_input_required = bool(action.get("requires_author_confirmation", True))
        category = infer_category(str(concern.get("concern_type", "")), action_type)
        proposed_action = infer_nature_action(
            action_type=action_type,
            evidence_status=evidence_status,
            required_artifact=required_artifact,
            requires_author_confirmation=author_input_required,
        )
        severity = infer_severity(category, evidence_status, proposed_action)
        risk_level = infer_risk_level(severity, evidence_status, proposed_action)
        evidence_anchor = str(
            evidence.get("evidence_anchor")
            or evidence.get("section_id")
            or evidence.get("evidence_ref")
            or action.get("evidence_anchor")
            or ""
        )
        readiness = infer_readiness(
            proposed_action=proposed_action,
            evidence_status=evidence_status,
            author_input_required=author_input_required,
            evidence_anchor=evidence_anchor,
            action_type=action_type,
            risk_level=risk_level,
        )
        missing_author_input = (
            [required_artifact] if author_input_required and required_artifact else []
        )
        cards.append({
            "comment_id": comment_id,
            "severity": severity,
            "category": category,
            "proposed_action": proposed_action,
            "readiness": readiness,
            "risk_level": risk_level,
            "missing_author_input": missing_author_input,
            "evidence_anchor": evidence_anchor,
            "memory_decision_boundary": build_memory_decision_boundary(
                action_type=action_type,
                author_input_required=author_input_required,
                risk_level=risk_level,
            ),
        })
    return cards


def validate_response_package_cards(cards: list[dict[str, Any]]) -> list[str]:
    issues = []
    for card in cards:
        comment_id = str(card.get("comment_id", "unknown"))
        if card.get("proposed_action") not in NATURE_ACTION_LABELS:
            issues.append(f"{comment_id}: invalid proposed_action {card.get('proposed_action')}")
        if card.get("readiness") not in READINESS_STATES:
            issues.append(f"{comment_id}: invalid readiness {card.get('readiness')}")
        if card.get("readiness") == "ready_to_submit" and (
            card.get("author_input_required") or card.get("missing_author_input")
        ):
            issues.append(f"{comment_id}: ready_to_submit conflicts with missing author input")
        if card.get("readiness") == "ready_to_submit" and not card.get("evidence_anchor"):
            issues.append(f"{comment_id}: ready_to_submit requires evidence_anchor")
    return issues


def build_memory_decision_boundary(
    *,
    action_type: str,
    author_input_required: bool,
    risk_level: str,
) -> dict[str, Any]:
    high_risk_decision = author_input_required and _requires_author_decision(action_type)
    return {
        "author_decision_required": bool(author_input_required),
        "system_may_commit_for_author": False,
        "cross_run_preference_used": False,
        "requires_independent_confirmation": bool(high_risk_decision or risk_level in {"high", "blocking"}),
        "decision_class": "high_risk_author_decision" if high_risk_decision else "bounded_assistance",
    }


def _requires_author_decision(action_type: str) -> bool:
    text = str(action_type or "").lower()
    return any(
        token in text
        for token in [
            "new_analysis",
            "new_experiment",
            "new_baseline",
            "claim_narrowing",
            "limitation_discussion",
            "future_work_commitment",
            "statistical_test",
        ]
    )


def _select_for_concern(
    items: list[dict[str, Any]],
    index: int,
    concern: dict[str, Any],
) -> dict[str, Any]:
    concern_id = str(concern.get("concern_id") or concern.get("comment_id") or "").strip()
    concern_type = str(concern.get("concern_type") or "").strip()
    for item in items:
        item_id = str(item.get("concern_id") or item.get("comment_id") or "").strip()
        if concern_id and item_id == concern_id:
            return item
    for item in items:
        if concern_type and concern_type in str(item):
            return item
    if 0 <= index < len(items):
        return items[index]
    return {}
