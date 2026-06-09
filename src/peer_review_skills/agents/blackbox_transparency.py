"""Black-box transparency summaries for Kant Machine Phase 2."""

from __future__ import annotations

from typing import Any


def build_blackbox_transparency(
    *,
    trace: dict[str, Any],
    report: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Explain a bounded judgment without pretending full access to hidden states."""
    enabled = bool(
        config.get("enable_blackbox_transparency")
        or config.get("enable_kant_phase2")
    )
    if not enabled:
        return {
            "enabled": False,
            "summary_zh": "",
            "evidence_inputs": [],
            "deferred_decisions": [],
            "category_generation_events": [],
            "memory_boundary_events": [],
        }

    evidence_inputs = _evidence_inputs(trace)
    deferred_decisions = [
        str(card.get("comment_id"))
        for card in report.get("comment_cards", [])
        if isinstance(card, dict) and str(card.get("readiness")) == "decision_deferred"
    ]
    runtime = trace.get("kant_machine_runtime", {})
    reflective = runtime.get("reflective_judgment", {})
    draft = reflective.get("category_invention_draft") or {}
    category_generation_events = []
    if draft:
        category_generation_events.append({
            "draft_id": str(draft.get("draft_id") or draft.get("name", "")),
            "status": str(draft.get("status", "unverified_strategy_prototype")),
            "requires_independent_confirmation": bool(
                draft.get("requires_independent_confirmation", True)
            ),
        })

    memory_passport = (
        runtime.get("memory_passport")
        or trace.get("memory_passport")
        or report.get("memory_passport")
        or {}
    )
    memory_boundary_events = []
    if isinstance(memory_passport, dict) and memory_passport:
        memory_boundary_events.append({
            "retained": list(memory_passport.get("retained_memory_types", [])),
            "forgotten": list(memory_passport.get("forgotten_memory_types", [])),
        })

    summary = (
        "本次运行承认作者、reviewer 与 AI 都存在黑箱边界；系统只依据已提供文本、"
        "证据定位、committee 输出和审计 gate 生成辅助判断。对无法知道的未来结果、"
        "他人真实动机和作者未确认行动，系统以 defer 或 author input 形式显式保留。"
    )
    return {
        "enabled": True,
        "summary_zh": summary,
        "evidence_inputs": evidence_inputs,
        "deferred_decisions": deferred_decisions,
        "category_generation_events": category_generation_events,
        "memory_boundary_events": memory_boundary_events,
    }


def _evidence_inputs(trace: dict[str, Any]) -> list[str]:
    outputs = trace.get("agent_intermediate_outputs", {})
    preferred = [
        "reviewer_understanding_agent",
        "manuscript_evidence_locator",
        "evidence_action_planner",
        "committee_meta_reviewer",
        "strategy_meta_planner",
        "integrity_adequacy_checker",
    ]
    return [name for name in preferred if name in outputs]
