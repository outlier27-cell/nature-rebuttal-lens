"""Build a compact ethics audit chain for RebuttalLens outputs."""

from __future__ import annotations

from typing import Any

from peer_review_skills.agents.memory_ethics import build_memory_ethics_runtime
from peer_review_skills.agents.universalization_gate import check_universalization


def build_ethics_audit_chain(
    *,
    response_cards: list[dict[str, Any]] | tuple[dict[str, Any], ...] | None = None,
    trace: dict[str, Any] | None = None,
    report: dict[str, Any] | None = None,
    memory_runtime: dict[str, Any] | None = None,
    reset_memory: bool = False,
    memory_policy: str = "default",
    forget_scope: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    trace = trace or {}
    report = report or {}
    cards = [
        dict(card or {})
        for card in (
            response_cards
            if response_cards is not None
            else report.get("comment_cards", [])
        )
    ]
    runtime = memory_runtime or build_memory_ethics_runtime(
        reset_memory=reset_memory,
        memory_policy=memory_policy,
        forget_scope=forget_scope,
    )
    if trace.get("forgetting_ledger"):
        runtime = {**runtime, "forgetting_ledger": trace.get("forgetting_ledger", [])}
    universalization_checks = list(
        report.get("universalization_checks") or [check_universalization(card) for card in cards]
    )
    ethical_blocks = [
        _attach_card_context(check, cards)
        for check in universalization_checks
        if check["decision"] == "block"
    ]
    deferred_author_decisions = [
        _attach_card_context(check, cards)
        for check in universalization_checks
        if check["decision"] == "defer"
    ]

    return {
        "mechanical_execution_events": _mechanical_execution_events(
            cards,
            trace.get("execution_trace", []),
        ),
        "organic_generation_events": _organic_generation_events(
            cards,
            report.get("reflective_judgment", {}),
            report.get("regenerated_category_candidates", []),
        ),
        "active_forgetting_events": list(runtime.get("forgetting_ledger", [])),
        "deferred_author_decisions": deferred_author_decisions,
        "universalization_checks": universalization_checks,
        "ethical_blocks": ethical_blocks,
        "heteronomy_transparency_statement": _heteronomy_transparency_statement(),
    }


def _mechanical_execution_events(
    cards: list[dict[str, Any]],
    execution_trace: list[Any],
) -> list[dict[str, Any]]:
    events = [
        {
            "event_type": "audit_chain_started",
            "response_card_count": len(cards),
            "system_role": "mechanical_executor",
        },
        {
            "event_type": "universalization_gate_applied",
            "response_card_count": len(cards),
            "system_role": "mechanical_executor",
        },
    ]
    for item in execution_trace:
        if not isinstance(item, dict):
            continue
        events.append({
            "event_type": "dag_rule_execution",
            "node_id": item.get("node_id"),
            "agent_id": item.get("agent_id"),
            "description": "Executed a configured workflow node under the DAG contract.",
            "system_role": "mechanical_executor",
        })
    return events


def _organic_generation_events(
    cards: list[dict[str, Any]],
    reflective_judgment: dict[str, Any],
    regenerated_candidates: list[Any],
) -> list[dict[str, Any]]:
    events = []
    if isinstance(reflective_judgment, dict) and reflective_judgment.get("mode") == "reflective_judgment":
        events.append({
            "event_type": "category_invention_draft",
            "description": "Entered reflective judgment mode because existing categories did not cover the concern.",
            "draft": reflective_judgment.get("category_invention_draft"),
            "system_role": "organic_generator",
        })
    for candidate in regenerated_candidates:
        if isinstance(candidate, dict):
            events.append({
                "event_type": "forgetting_regeneration",
                "category_id": candidate.get("category_id") or candidate.get("name"),
                "description": "Generated a forgettable derived category from repeated forgotten structure.",
                "system_role": "organic_generator",
            })
    for card in cards:
        events.append(
            {
                "event_type": "response_suggestion_generated",
                "comment_id": str(card.get("comment_id") or card.get("concern_id") or ""),
                "proposed_action": str(card.get("proposed_action") or ""),
                "readiness": str(card.get("readiness") or ""),
                "system_role": "organic_generator",
            }
        )
    if not events:
        events.append(
            {
                "event_type": "no_response_suggestions_generated",
                "system_role": "organic_generator",
            }
        )
    return events


def _attach_card_context(
    check: dict[str, Any],
    cards: list[dict[str, Any]],
) -> dict[str, Any]:
    comment_id = check.get("comment_id")
    source_card = next(
        (
            card
            for card in cards
            if str(card.get("comment_id") or card.get("concern_id") or "") == comment_id
        ),
        {},
    )
    return {
        "comment_id": comment_id,
        "proposed_action": check.get("proposed_action"),
        "readiness": check.get("readiness"),
        "risk_level": check.get("risk_level"),
        "decision": check.get("decision"),
        "reason": check.get("reason"),
        "missing_author_input": list(source_card.get("missing_author_input", [])),
    }


def _heteronomy_transparency_statement() -> str:
    return (
        "This audit chain is a heteronomous assistance layer: it does not make final author decisions, "
        "does not convert memory into author commitments, and blocks or defers suggestions that would "
        "depend on deception, concealed limitations, or unconfirmed high-risk author input."
    )
