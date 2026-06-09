"""Unknowability ledger for Kant Machine Phase 2."""

from __future__ import annotations

import re
from typing import Any


BOUNDARY_SPECS = [
    {
        "boundary_type": "future_editorial_outcome",
        "description_zh": "系统不能预测接收、拒稿、编辑态度或审稿人最终满意度。",
        "patterns": [
            r"\bguarantee(?:d)?\s+acceptance\b",
            r"\bwill\s+be\s+accepted\b",
            r"\bsatisfy\s+the\s+reviewer\b",
            r"确保接收",
            r"保证接收",
        ],
        "author_question_zh": "系统不能预测接收结果；请作者只确认可执行修改和真实证据。",
    },
    {
        "boundary_type": "reviewer_inner_motive",
        "description_zh": "系统不能知道 reviewer 的真实心理动机，只能处理文本中可见的 concern。",
        "patterns": [
            r"\breviewer\s+(?:wants|wanted|intends|intended)\b",
            r"\breviewer\s+probably\b",
            r"审稿人.*真实动机",
        ],
        "author_question_zh": "请确认回应是否只针对文本 concern，而不是猜测 reviewer 动机。",
    },
    {
        "boundary_type": "unperformed_analysis",
        "description_zh": "系统不能把尚未完成的实验、分析或引用验证写成已经完成。",
        "patterns": [
            r"\bwe\s+have\s+completed\b",
            r"\bcompleted\s+the\s+analysis\b",
            r"已经完成.*实验",
            r"已经完成.*分析",
        ],
        "author_question_zh": "请作者确认相关分析是否真实完成；否则只能写成计划或条件性承诺。",
    },
    {
        "boundary_type": "author_capacity",
        "description_zh": "系统不能判断作者是否一定有时间、数据或权限完成某项补充工作。",
        "patterns": [
            r"\bauthors?\s+can\s+definitely\b",
            r"作者一定可以",
        ],
        "author_question_zh": "请作者确认是否具备完成该补充工作的时间、数据和权限。",
    },
    {
        "boundary_type": "confidential_or_private_fact",
        "description_zh": "系统不能臆测未提供的私密审稿材料、编辑通信或保密数据。",
        "patterns": [
            r"\bconfidential\b.*\bprobably\b",
            r"未公开.*可以推断",
        ],
        "author_question_zh": "请不要上传或要求系统推断未授权的保密审稿材料。",
    },
]


def build_unknowability_ledger(trace: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Build a ledger of things the assistant must not pretend to know."""
    enabled = bool(config.get("enable_unknowability_ledger") or config.get("enable_kant_phase2"))
    if not enabled:
        return {
            "enabled": False,
            "boundaries": [],
            "blocked_inferences": [],
            "author_questions": [],
        }

    text = _trace_text(trace)
    boundaries = []
    blocked = []
    questions = []
    for spec in BOUNDARY_SPECS:
        matches = [
            pattern
            for pattern in spec["patterns"]
            if re.search(pattern, text, flags=re.IGNORECASE)
        ]
        status = "triggered" if matches else "standing_boundary"
        boundaries.append(
            {
                "boundary_type": spec["boundary_type"],
                "description_zh": spec["description_zh"],
                "status": status,
            }
        )
        if matches:
            blocked.append(
                {
                    "boundary_type": spec["boundary_type"],
                    "matched_patterns": matches,
                    "reason_zh": spec["description_zh"],
                }
            )
            questions.append(spec["author_question_zh"])

    if not questions:
        questions.append(
            "请作者确认所有承诺均来自已提供材料，而不是系统对未来结果或他人心理的推断。"
        )

    return {
        "enabled": True,
        "boundaries": boundaries,
        "blocked_inferences": blocked,
        "author_questions": _dedupe(questions),
    }


def _trace_text(trace: dict[str, Any]) -> str:
    return _flatten(trace.get("agent_intermediate_outputs", {}))


def _flatten(value: Any) -> str:
    if isinstance(value, dict):
        return " ".join(_flatten(item) for item in value.values())
    if isinstance(value, list):
        return " ".join(_flatten(item) for item in value)
    return str(value)


def _dedupe(values: list[str]) -> list[str]:
    seen = set()
    result = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result
