"""Author-facing final report composer for Nature RebuttalLens."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from peer_review_skills.agents.evidence_ledger import (
    build_evidence_ledger,
    validate_evidence_ledger,
)


def compose_final_user_report(trace: dict[str, Any]) -> dict[str, Any]:
    """Build a stable user-facing report from a RebuttalLens trace."""
    outputs = trace.get("agent_intermediate_outputs", {})
    reviewer = _output_for(outputs, "reviewer_understanding_agent", "reviewer_understanding")
    evidence = _output_for(outputs, "manuscript_evidence_locator", "manuscript_evidence")
    actions = _output_for(outputs, "evidence_action_planner", "evidence_action")
    tone = _output_for(outputs, "tone_commitment_calibrator", "tone_commitment")
    integrity = _output_for(outputs, "integrity_adequacy_checker", "integrity")
    strategy = _output_for(outputs, "strategy_meta_planner", "meta_synthesis")
    committee = _output_for(outputs, "committee_meta_reviewer", "committee_meta_review")

    concern_map = _dict_items(reviewer.get("concern_map", []))
    evidence_map = _as_list(evidence.get("manuscript_evidence_map", []))
    action_plan = _as_list(actions.get("evidence_action_plan", []))
    tone_warnings = _as_list(tone.get("tone_commitment_warnings", []))
    provenance_checks = _as_list(integrity.get("provenance_checks", []))
    evidence_ledger = build_evidence_ledger(
        concerns=concern_map,
        evidence_items=evidence_map,
        action_items=action_plan,
        manuscript_context=_as_dict(trace.get("manuscript_context")),
        select_item=_select_for_concern,
    )

    comment_cards = []
    for index, concern in enumerate(concern_map, start=1):
        linked_evidence = _select_for_concern(
            evidence_map,
            index - 1,
            concern,
        )
        linked_action = _select_for_concern(
            action_plan,
            index - 1,
            concern,
        )
        card = {
            "comment_id": f"comment_{index:03d}",
            "concern_type": str(concern.get("concern_type", "unknown")),
            "surface_request": str(concern.get("surface_request", "")),
            "implicit_risk": str(concern.get("text_evidence", "")),
            "confidence": str(concern.get("confidence", "unknown")),
            "evidence_status": str(linked_evidence.get("status", "uncertain")),
            "manuscript_section": str(linked_evidence.get("section_id", "none")),
            "evidence_gap": str(linked_evidence.get("gap", "")),
            "recommended_action": str(linked_action.get("required_artifact", "")),
            "action_type": str(linked_action.get("action_type", "")),
            "supporting_case_ids": _as_string_list(
                linked_action.get("supporting_case_ids")
            ),
            "author_input_required": bool(
                linked_action.get("requires_author_confirmation", True)
            ),
            "safe_response_language": _safe_language_for(linked_action, linked_evidence),
            "unsafe_language_to_avoid": _unsafe_language_for(linked_evidence),
        }
        ledger_entry = evidence_ledger[index - 1] if index - 1 < len(evidence_ledger) else {}
        if ledger_entry:
            card["ledger_id"] = ledger_entry["ledger_id"]
            card["provenance"] = {
                "ledger_id": ledger_entry["ledger_id"],
                "concern_id": ledger_entry["concern_id"],
                "manuscript_span_id": ledger_entry["manuscript_span"]["span_id"],
                "case_ids": ledger_entry["case_ids"],
            }
        comment_cards.append(card)

    unsafe_claims = [
        check
        for check in provenance_checks
        if isinstance(check, dict) and check.get("traceable") is False
    ]
    confirmation_questions = _dedupe_strings(
        _as_list(evidence.get("author_confirmation_questions", []))
        + _as_list(actions.get("author_confirmation_questions", []))
        + _as_list(committee.get("author_confirmation_questions", []))
        + _as_list(strategy.get("author_confirmation_questions", []))
        + [
            card["recommended_action"]
            for card in comment_cards
            if card["author_input_required"] and card["recommended_action"]
        ]
    )
    recommended_outline = _build_outline(comment_cards, integrity, strategy)

    return {
        "report_type": "author_rebuttal_assistant_report",
        "workflow_version": trace.get("workflow_version", "rebuttal_lens_v1"),
        "query_unit_id": trace.get("query_unit_id", "unknown"),
        "executive_summary": _build_executive_summary(comment_cards, unsafe_claims),
        "evidence_ledger": evidence_ledger,
        "comment_cards": comment_cards,
        "recommended_rebuttal_outline": recommended_outline,
        "author_confirmation_questions": confirmation_questions,
        "tone_and_commitment_warnings": tone_warnings,
        "committee_synthesis": committee.get("committee_synthesis", {}),
        "strategy_plan": strategy.get("merged_plan", {}),
        "unsafe_claims": unsafe_claims,
        "provenance_checks": provenance_checks,
        "responsible_use_warnings": _responsible_use_warnings(trace, integrity),
        "integrity_issues": _as_list(integrity.get("issues", [])),
        "not_final_submission_text": True,
    }


def validate_final_user_report(report: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate the stable final report contract used by downstream UIs."""
    errors: list[str] = []
    required = [
        "report_type",
        "workflow_version",
        "query_unit_id",
        "executive_summary",
        "evidence_ledger",
        "comment_cards",
        "recommended_rebuttal_outline",
        "author_confirmation_questions",
        "responsible_use_warnings",
        "not_final_submission_text",
    ]
    for key in required:
        if key not in report:
            errors.append(f"missing required final report field: {key}")
    if report.get("report_type") != "author_rebuttal_assistant_report":
        errors.append("report_type must be author_rebuttal_assistant_report")
    if report.get("not_final_submission_text") is not True:
        errors.append("not_final_submission_text must be true")
    ledger_valid, ledger_errors = validate_evidence_ledger(report)
    errors.extend(ledger_errors)
    return not errors and ledger_valid, errors


def render_final_user_report_markdown(report: dict[str, Any]) -> str:
    """Render the final report as a concise Chinese Markdown artifact."""
    lines = [
        "# Nature RebuttalLens 最终作者回应辅助报告",
        "",
        "本报告是 assistant 输出，不是可直接提交的最终 rebuttal。所有实验、证据、引用和承诺都必须由作者确认。",
        "",
        "## 1. 核心判断",
        "",
        str(report.get("executive_summary", "")),
        "",
        "## 2. Reviewer Concern Cards",
        "",
    ]
    for card in report.get("comment_cards", []):
        lines.extend(
            [
                f"### {card.get('comment_id')} - {card.get('concern_type')}",
                "",
                f"- 表层要求：{card.get('surface_request')}",
                f"- 深层风险：{card.get('implicit_risk')}",
                f"- 证据状态：{card.get('evidence_status')} / {card.get('manuscript_section')}",
                f"- 证据缺口：{card.get('evidence_gap')}",
                f"- 建议动作：{card.get('recommended_action')}",
                f"- 作者确认必需：{card.get('author_input_required')}",
                f"- 安全表达：{card.get('safe_response_language')}",
                f"- 避免表达：{card.get('unsafe_language_to_avoid')}",
                "",
            ]
        )
    if report.get("committee_synthesis"):
        lines.extend(
            [
                "## 3. Reviewer Committee 综合",
                "",
                "```json",
                json.dumps(report["committee_synthesis"], ensure_ascii=False, indent=2),
                "```",
                "",
            ]
        )
    if report.get("strategy_plan"):
        lines.extend(
            [
                "## 4. 选择后的回应策略",
                "",
                "```json",
                json.dumps(report["strategy_plan"], ensure_ascii=False, indent=2),
                "```",
                "",
            ]
        )
    lines.extend(["## 5. 推荐回应结构", ""])
    for item in report.get("recommended_rebuttal_outline", []):
        lines.append(f"- {item}")
    lines.extend(["", "## 6. 作者必须确认的问题", ""])
    for question in report.get("author_confirmation_questions", []):
        lines.append(f"- {question}")
    lines.extend(["", "## 7. 不安全或不可追溯的 claim", ""])
    unsafe_claims = report.get("unsafe_claims", [])
    if unsafe_claims:
        for claim in unsafe_claims:
            lines.append(f"- {claim.get('claim')}（source: {claim.get('source')}）")
    else:
        lines.append("- 暂无由 integrity checker 标记的不可追溯 claim。")
    lines.extend(["", "## 8. Responsible Use", ""])
    for warning in report.get("responsible_use_warnings", []):
        lines.append(f"- {warning}")
    return "\n".join(lines).rstrip() + "\n"


def write_final_user_report(report: dict[str, Any], output_dir: Path) -> dict[str, str]:
    """Write JSON and Markdown final report files."""
    is_valid, errors = validate_final_user_report(report)
    if not is_valid:
        raise ValueError(
            "final user report contract validation failed: " + "; ".join(errors)
        )
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / "final_user_report.json"
    md_path = output_dir / "final_user_report.md"
    json_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    md_path.write_text(
        render_final_user_report_markdown(report),
        encoding="utf-8",
        newline="\n",
    )
    return {
        "final_user_report_json": str(json_path),
        "final_user_report_markdown": str(md_path),
    }


def _output_for(outputs: dict[str, Any], *keys: str) -> dict[str, Any]:
    for key in keys:
        value = outputs.get(key)
        if isinstance(value, dict):
            return value
    return {}


def _as_list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _dict_items(value: Any) -> list[dict[str, Any]]:
    return [item for item in _as_list(value) if isinstance(item, dict)]


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _as_string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return _dedupe_strings(value)
    if isinstance(value, (str, int, float, bool)):
        return _dedupe_strings([value])
    return []


def _select_for_concern(
    items: list[Any],
    index: int,
    concern: dict[str, Any],
) -> dict[str, Any]:
    dict_items = [item for item in items if isinstance(item, dict)]
    concern_id = _clean_match_value(concern.get("concern_id"))
    concern_type = _clean_match_value(concern.get("concern_type"))
    if concern_id:
        matched = _find_exact_match(
            dict_items,
            concern_id,
            ("concern_id", "reviewer_concern_id", "source_concern_id", "comment_id"),
        )
        if matched:
            return matched
    if concern_type:
        matched = _find_exact_match(
            dict_items,
            concern_type,
            (
                "concern_type",
                "risk_type",
                "type",
                "concern_id",
                "reviewer_concern_id",
                "source_concern_id",
            ),
        )
        if matched:
            return matched
    for item in dict_items:
        item_text = json.dumps(item, ensure_ascii=False)
        if concern_type and concern_type in item_text:
            return item
    if index < len(dict_items):
        return dict_items[index]
    return {}


def _find_exact_match(
    items: list[dict[str, Any]],
    expected: str,
    keys: tuple[str, ...],
) -> dict[str, Any]:
    for item in items:
        for key in keys:
            if _clean_match_value(item.get(key)) == expected:
                return item
    return {}


def _clean_match_value(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


def _safe_language_for(action: dict[str, Any], evidence: dict[str, Any]) -> str:
    if action.get("requires_author_confirmation", True):
        return (
            "We will report this analysis if completed, or narrow the claim if it "
            "cannot be supported."
        )
    if evidence.get("status") == "supported":
        return (
            "We have clarified the existing manuscript evidence and point to the "
            "relevant section."
        )
    return "We acknowledge the concern and will align the claim with available evidence."


def _unsafe_language_for(evidence: dict[str, Any]) -> str:
    if evidence.get("status") in {"missing", "partially_supported", "uncertain", ""}:
        return (
            "Avoid claiming that the concern is fully resolved before evidence is "
            "available."
        )
    return "Avoid overstating implications beyond the supplied manuscript evidence."


def _build_outline(
    comment_cards: list[dict[str, Any]],
    integrity: dict[str, Any],
    strategy: dict[str, Any],
) -> list[str]:
    outline = [
        "Thank the reviewer and restate the concern as an evidence/validity issue.",
    ]
    merged_plan = _as_dict(strategy.get("merged_plan"))
    if isinstance(merged_plan, dict):
        position = merged_plan.get("response_position")
        if position:
            outline.append(f"Use response position: {position}.")
        for action in _as_list(merged_plan.get("required_actions", [])):
            outline.append(f"Complete or explicitly qualify this planned action: {action}.")
        for adjustment in _as_list(merged_plan.get("claim_adjustments", [])):
            outline.append(f"Adjust claim scope: {adjustment}.")
    for card in comment_cards:
        action = card.get("recommended_action")
        if action:
            outline.append(f"Address {card.get('comment_id')} by explaining: {action}.")
    missing = _as_dict(integrity.get("response_adequacy")).get("missing_elements", [])
    for item in _as_list(missing):
        outline.append(f"Do not overclaim until this missing element is resolved: {item}.")
    outline.append(
        "Close by distinguishing completed revisions from analyses that require "
        "author confirmation."
    )
    return outline


def _build_executive_summary(
    comment_cards: list[dict[str, Any]],
    unsafe_claims: list[dict[str, Any]],
) -> str:
    concern_count = len(comment_cards)
    unsafe_count = len(unsafe_claims)
    return (
        f"系统识别出 {concern_count} 个 reviewer concern。"
        f"其中 {unsafe_count} 个 claim 暂时不可追溯或证据不足。"
        "建议先补证据和缩窄承诺，再组织 rebuttal 草稿。"
    )


def _responsible_use_warnings(
    trace: dict[str, Any],
    integrity: dict[str, Any],
) -> list[str]:
    warnings = _as_list(integrity.get("responsible_use_warnings", []))
    boundary = trace.get("responsible_use_boundary", {})
    if isinstance(boundary, dict):
        warnings.extend(key for key, value in boundary.items() if value is True)
    return _dedupe_strings(warnings)


def _dedupe_strings(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value).strip()
        if text and text not in seen:
            seen.add(text)
            result.append(text)
    return result
