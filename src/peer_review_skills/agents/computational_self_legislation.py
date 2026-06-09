"""Computational self-legislation for Kant Machine Phase 2."""

from __future__ import annotations

from typing import Any


def build_self_legislation(trace: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Build maxims that constrain what RebuttalLens may do in its own domain."""
    enabled = bool(config.get("enable_self_legislation") or config.get("enable_kant_phase2"))
    if not enabled:
        return {
            "enabled": False,
            "maxims": [],
            "system_may_commit_for_author": False,
            "author_confirmation_required_for": [],
        }

    return {
        "enabled": True,
        "maxims": [
            {
                "maxim_id": "evidence_before_persuasion",
                "maxim_zh": "回应辅助必须先尊重证据边界，再追求说服效果。",
                "forbidden": "把缺失证据包装成已经完成的修订。",
            },
            {
                "maxim_id": "author_decision_boundary",
                "maxim_zh": "系统不能替作者承诺实验、引用、修改或最终立场。",
                "forbidden": "把作者尚未确认的行动写成既成事实。",
            },
            {
                "maxim_id": "category_generation_humility",
                "maxim_zh": "新范畴只能作为未验证雏形出现，必须等待独立确认。",
                "forbidden": "把一次运行生成的范畴立即当作普遍规则。",
            },
            {
                "maxim_id": "forgetting_preserves_agency",
                "maxim_zh": "遗忘不是能力损失，而是防止旧承诺支配新判断。",
                "forbidden": "把历史偏好、旧策略或旧作者决定自动带入新运行。",
            },
        ],
        "system_may_commit_for_author": False,
        "author_confirmation_required_for": _author_confirmation_required_for(trace),
    }


def _author_confirmation_required_for(trace: dict[str, Any]) -> list[str]:
    outputs = trace.get("agent_intermediate_outputs", {})
    if not isinstance(outputs, dict):
        return []

    planner = outputs.get("evidence_action_planner") or outputs.get("evidence_action") or {}
    if not isinstance(planner, dict):
        return []

    required: list[str] = []
    for action in planner.get("evidence_action_plan", []):
        if not isinstance(action, dict):
            continue
        if bool(action.get("requires_author_confirmation", True)):
            artifact = str(action.get("required_artifact", "")).strip()
            if artifact and artifact not in required:
                required.append(artifact)
    return required
