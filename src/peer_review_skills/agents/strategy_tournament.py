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
        return parse_agent_json_response(response)

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
        return parse_agent_json_response(response)

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
