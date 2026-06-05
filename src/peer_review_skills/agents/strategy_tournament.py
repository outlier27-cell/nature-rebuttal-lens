"""Strategy tournament agents for Nature RebuttalLens."""

from __future__ import annotations

import json
from typing import Any, Optional

from peer_review_skills.agents.base import (
    BaseAgent,
    parse_agent_json_response,
    require_bool_in_list_items,
    require_field,
    require_list_item_fields,
)


class StrategyTournamentAgent(BaseAgent):
    """Generates competing response strategies with rubric scores."""

    def build_prompt(self, inputs: dict[str, Any]) -> list[dict[str, str]]:
        return [
            {
                "role": "system",
                "content": (
                    "You are the Nature RebuttalLens strategy tournament agent. Generate "
                    "2-3 competing author response strategies. Score each strategy with "
                    "concern_coverage, evidence_grounding, feasibility, overclaim_risk, "
                    "tone_risk, and provenance_strength. Do not write final rebuttal text. "
                    "Do not invent completed experiments. Use the strategy library as "
                    "labels only: Accept means the reviewer is right and a concrete "
                    "change is supported; Defend means the current design is justified "
                    "by supplied facts; Clarify means the concern is addressed by "
                    "existing manuscript evidence but presentation needs clarification; "
                    "Experiment means additional analysis or experiment is needed and "
                    "must be marked planned or author_input_required unless supplied. "
                    "Every strategy must include an evidence anchor, a feasibility note, "
                    "and an overclaim gate. Optional candidate fields may include "
                    "strategy_family, evidence_anchor, and overclaim_gate. Return only valid JSON with "
                    "strategy_candidates[] and reasoning."
                ),
            },
            {"role": "user", "content": json.dumps(inputs, ensure_ascii=False, indent=2)},
        ]

    def parse_response(self, response: dict[str, Any]) -> dict[str, Any]:
        output = parse_agent_json_response(response)
        candidates = output.get("strategy_candidates")
        if isinstance(candidates, list):
            for index, candidate in enumerate(candidates, start=1):
                if isinstance(candidate, dict):
                    _normalize_strategy_candidate(candidate, index)
        return output

    def validate_output(self, output: dict[str, Any]) -> tuple[bool, Optional[str]]:
        for field, expected in [("strategy_candidates", list), ("reasoning", str)]:
            error = require_field(output, field, expected)
            if error:
                return False, error
        error = require_list_item_fields(
            output["strategy_candidates"],
            "strategy_candidates",
            {
                "strategy_id": str,
                "name": str,
                "response_position": str,
                "required_actions": list,
                "rubric_scores": dict,
                "author_confirmation_required": bool,
            },
        )
        if error:
            return False, error
        error = require_bool_in_list_items(
            output["strategy_candidates"],
            "strategy_candidates",
            "author_confirmation_required",
        )
        if error:
            return False, error
        return True, None


def _normalize_strategy_candidate(candidate: dict[str, Any], index: int) -> None:
    if not str(candidate.get("strategy_id", "")).strip():
        candidate["strategy_id"] = f"strategy_{index:03d}"
    strategy_family = str(candidate.get("strategy_family", "")).strip()
    if "name" not in candidate and strategy_family:
        candidate["name"] = strategy_family
    if "response_position" not in candidate and strategy_family:
        candidate["response_position"] = strategy_family.lower().replace(" ", "_")
    if "required_actions" not in candidate:
        action = str(candidate.get("overclaim_gate") or candidate.get("feasibility_note") or "").strip()
        candidate["required_actions"] = [action] if action else []
    if "rubric_scores" not in candidate:
        candidate["rubric_scores"] = {
            key: candidate[key]
            for key in [
                "concern_coverage",
                "evidence_grounding",
                "feasibility",
                "overclaim_risk",
                "tone_risk",
                "provenance_strength",
            ]
            if key in candidate
        }
    if "author_confirmation_required" not in candidate:
        text = " ".join(
            str(candidate.get(key, ""))
            for key in ["strategy_family", "response_position", "feasibility", "overclaim_risk", "overclaim_gate"]
        ).lower()
        candidate["author_confirmation_required"] = any(
            token in text
            for token in [
                "experiment",
                "new analysis",
                "requires new",
                "planned",
                "author_input",
                "pending",
                "high",
            ]
        )


class StrategyMetaPlannerAgent(BaseAgent):
    """Selects or merges the safest strategy candidate."""

    def build_prompt(self, inputs: dict[str, Any]) -> list[dict[str, str]]:
        return [
            {
                "role": "system",
                "content": (
                    "You are the Nature RebuttalLens strategy meta-planner. Select or merge "
                    "the safest strategy candidate. Prioritize evidence grounding, concern "
                    "coverage, author feasibility, and overclaim prevention. Do not predict "
                    "acceptance. Return only valid JSON with selected_strategy_id, merged_plan, "
                    "rejection_reasons, author_confirmation_questions, reasoning."
                ),
            },
            {"role": "user", "content": json.dumps(inputs, ensure_ascii=False, indent=2)},
        ]

    def parse_response(self, response: dict[str, Any]) -> dict[str, Any]:
        output = parse_agent_json_response(response)
        _normalize_meta_planner_output(output)
        return output

    def validate_output(self, output: dict[str, Any]) -> tuple[bool, Optional[str]]:
        for field, expected in [
            ("selected_strategy_id", str),
            ("merged_plan", dict),
            ("rejection_reasons", list),
            ("author_confirmation_questions", list),
            ("reasoning", str),
        ]:
            error = require_field(output, field, expected)
            if error:
                return False, error
        return True, None


def _normalize_meta_planner_output(output: dict[str, Any]) -> None:
    rejection_reasons = output.get("rejection_reasons")
    if isinstance(rejection_reasons, dict):
        output["rejection_reasons"] = [
            {"strategy_id": str(strategy_id), "reason": str(reason)}
            for strategy_id, reason in rejection_reasons.items()
        ]
    questions = output.get("author_confirmation_questions")
    if isinstance(questions, list):
        output["author_confirmation_questions"] = [
            _normalize_confirmation_question(question)
            for question in questions
            if _normalize_confirmation_question(question)
        ]


def _normalize_confirmation_question(question: Any) -> str:
    if isinstance(question, dict):
        return str(question.get("question") or question.get("text") or "").strip()
    return str(question).strip()
