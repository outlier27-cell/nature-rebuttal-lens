"""Parallel reviewer committee agents for Nature RebuttalLens."""

from __future__ import annotations

import json
from typing import Any, Optional

from peer_review_skills.agents.base import (
    BaseAgent,
    parse_agent_json_response,
    require_field,
    require_list_item_fields,
    require_optional_field,
)


class CommitteeReviewerAgent(BaseAgent):
    """Independent reviewer-role critique for committee mode."""

    def __init__(
        self,
        agent_id: str,
        model_client: Any,
        *,
        reviewer_role: str,
        temperature: float = 0.0,
        max_retries: int = 3,
    ):
        super().__init__(agent_id, model_client, temperature=temperature, max_retries=max_retries)
        self.reviewer_role = reviewer_role

    def build_prompt(self, inputs: dict[str, Any]) -> list[dict[str, str]]:
        return [
            {
                "role": "system",
                "content": (
                    "You are one committee lens in Nature RebuttalLens. Use the same "
                    "shared fact base as the other reviewer committee lenses. Your difference is "
                    f"emphasis only: {self.reviewer_role}. Independently inspect the "
                    "reviewer concern, manuscript evidence, author draft, editor note, "
                    "retrieved cases, and prior agent outputs. Do not invent reviewer "
                    "identities, do not invent specialties, institutions, biographies, "
                    "or selection history. Do not write a final rebuttal. Do not invent "
                    "experiments, citations, manuscript locations, or editorial outcomes. "
                    "Return only valid "
                    "JSON with: reviewer_role, findings[], author_confirmation_questions[], "
                    "reasoning. Each finding must include risk, severity, evidence, recommendation."
                ),
            },
            {"role": "user", "content": json.dumps(inputs, ensure_ascii=False, indent=2)},
        ]

    def parse_response(self, response: dict[str, Any]) -> dict[str, Any]:
        return parse_agent_json_response(response)

    def validate_output(self, output: dict[str, Any]) -> tuple[bool, Optional[str]]:
        for field, expected in [
            ("reviewer_role", str),
            ("findings", list),
            ("reasoning", str),
        ]:
            error = require_field(output, field, expected)
            if error:
                return False, error
        error = require_list_item_fields(
            output["findings"],
            "findings",
            {"risk": str, "severity": str, "evidence": str, "recommendation": str},
        )
        if error:
            return False, error
        error = require_optional_field(output, "author_confirmation_questions", list)
        if error:
            return False, error
        return True, None


class CommitteeMetaReviewerAgent(BaseAgent):
    """Synthesizes independent committee outputs."""

    def build_prompt(self, inputs: dict[str, Any]) -> list[dict[str, str]]:
        return [
            {
                "role": "system",
                "content": (
                    "You are the Nature RebuttalLens committee meta-reviewer. Synthesize "
                    "independent committee outputs into a prioritized, non-duplicative plan. "
                    "Preserve consensus and emphasis differences separately. "
                    "Do not collapse all committee lenses into one invented reviewer persona. "
                    "Preserve disagreement. Do not predict acceptance. Do not write final "
                    "submission text. Preserve author confirmation gates. Return only valid "
                    "JSON with committee_synthesis, author_confirmation_questions, reasoning."
                ),
            },
            {"role": "user", "content": json.dumps(inputs, ensure_ascii=False, indent=2)},
        ]

    def parse_response(self, response: dict[str, Any]) -> dict[str, Any]:
        return parse_agent_json_response(response)

    def validate_output(self, output: dict[str, Any]) -> tuple[bool, Optional[str]]:
        for field, expected in [
            ("committee_synthesis", dict),
            ("author_confirmation_questions", list),
            ("reasoning", str),
        ]:
            error = require_field(output, field, expected)
            if error:
                return False, error
        return True, None
