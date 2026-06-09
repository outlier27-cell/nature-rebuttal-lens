"""Reflective and determining judgment helpers for reviewer concerns."""

from __future__ import annotations

import re
from typing import Any

from peer_review_skills.agents.kantian_categories import (
    CategoryRegistry,
    CategoryStatus,
)


def judge_reviewer_concern(
    concern_text: str,
    registry: CategoryRegistry,
    *,
    run_id: str,
    similarity_threshold: float = 0.35,
) -> dict[str, Any]:
    """Classify a reviewer concern or defer while drafting a new category."""
    match = registry.match(concern_text, threshold=similarity_threshold)
    if match is not None:
        return {
            "judgment_type": "determining_judgment",
            "readiness": "ready_for_category_application",
            "matched_category": {
                "name": match.category.name,
                "status": match.category.status.value,
                "similarity": match.similarity,
            },
            "category_invention_draft": None,
        }

    draft = registry.upsert(
        _draft_name(concern_text),
        description=str(concern_text),
        status=CategoryStatus.DRAFT,
        run_id=run_id,
        metadata={"verification_status": "unverified"},
    )
    return {
        "judgment_type": "reflective_judgment",
        "readiness": "decision_deferred",
        "matched_category": None,
        "category_invention_draft": {
            "name": draft.name,
            "status": draft.status.value,
            "verification_status": "unverified",
            "requires_independent_confirmation": True,
        },
    }


def build_reflective_judgment(
    *,
    concern_text: str,
    registry: CategoryRegistry,
    min_similarity: float = 0.25,
    run_id: str = "current_run",
) -> dict[str, Any]:
    """Return a report-friendly reflective/determining judgment payload."""
    judgment = judge_reviewer_concern(
        concern_text,
        registry,
        run_id=run_id,
        similarity_threshold=min_similarity,
    )
    if judgment["judgment_type"] == "determining_judgment":
        matched = judgment.get("matched_category") or {}
        return {
            "mode": "determining_judgment",
            "readiness": "needs_author_input",
            "matched_category": {
                "category_id": matched.get("name", ""),
                "name": matched.get("name", ""),
                "status": matched.get("status", ""),
                "similarity": matched.get("similarity", 0.0),
            },
            "category_invention_draft": None,
            "system_may_commit_for_author": False,
        }
    draft = dict(judgment.get("category_invention_draft") or {})
    return {
        "mode": "reflective_judgment",
        "readiness": "decision_deferred",
        "matched_category": None,
        "category_invention_draft": {
            "draft_id": draft.get("name", "category_draft"),
            "name": draft.get("name", ""),
            "status": "unverified_strategy_prototype",
            "registry_status": draft.get("status", "draft"),
            "verification_status": draft.get("verification_status", "unverified"),
            "requires_independent_confirmation": True,
            "author_instruction": (
                "请作者判断该新策略雏形是否可用；若确认有效并在多次独立运行中成功使用，"
                "再触发范畴生成流程。"
            ),
        },
        "system_may_commit_for_author": False,
        "author_confirmation_required": True,
    }


def _draft_name(text: str) -> str:
    tokens = [
        token
        for token in re.findall(r"[a-z0-9]+", str(text).lower())
        if len(token) > 3
    ]
    return "draft_" + "_".join(tokens[:5] or ["reviewer_concern"])
