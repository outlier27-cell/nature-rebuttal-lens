"""Organic quality checks for Kant Machine category generation."""

from __future__ import annotations

from typing import Any


def build_organic_quality(
    *,
    runtime: dict[str, Any],
    report: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    """Evaluate whether generated categories are grounded and forgetting-safe."""
    enabled = bool(
        config.get("enable_organic_quality")
        or config.get("enable_kant_phase2")
    )
    if not enabled:
        return {"enabled": False, "score": 0.0, "checks": []}

    reflective = runtime.get("reflective_judgment", {})
    draft = reflective.get("category_invention_draft") or {}
    heteronomy = runtime.get("heteronomy_boundary", {})
    cards = [card for card in report.get("comment_cards", []) if isinstance(card, dict)]
    universalization = [
        item
        for item in report.get("universalization_checks", [])
        if isinstance(item, dict)
    ]

    checks = [
        {
            "check_id": "grounded_in_evidence_gap",
            "passed": bool(cards and any(str(card.get("evidence_gap", "")).strip() for card in cards)),
            "reason_zh": "新范畴必须来自真实 evidence gap，而不是凭空发明。",
        },
        {
            "check_id": "author_confirmable",
            "passed": bool(draft.get("requires_independent_confirmation", True))
            and bool(heteronomy.get("category_generation_requires_author_confirmation", False)),
            "reason_zh": "新范畴必须等待作者或独立运行确认。",
        },
        {
            "check_id": "forgetting_safe",
            "passed": bool(heteronomy.get("derived_categories_are_forgetting_eligible", False)),
            "reason_zh": "派生范畴必须允许遗忘，避免一次运行支配后续判断。",
        },
        {
            "check_id": "non_deceptive_universalization",
            "passed": bool(universalization)
            and all(str(item.get("decision")) != "block" for item in universalization),
            "reason_zh": "有机生成不能以削弱真实性为代价。",
        },
        {
            "check_id": "deferred_until_validated",
            "passed": str(reflective.get("readiness", "")) in {
                "decision_deferred",
                "needs_author_input",
                "ready_for_category_application",
                "",
            },
            "reason_zh": "未验证范畴不能直接变成最终回应承诺。",
        },
    ]
    score = sum(1 for check in checks if check["passed"]) / len(checks)
    return {
        "enabled": True,
        "score": round(score, 3),
        "checks": checks,
    }
