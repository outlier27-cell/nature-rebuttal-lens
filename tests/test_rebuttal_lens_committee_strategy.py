import json
from typing import Any

from peer_review_skills.agents.committee_agents import (
    CommitteeMetaReviewerAgent,
    CommitteeReviewerAgent,
)
from peer_review_skills.agents.strategy_tournament import (
    StrategyMetaPlannerAgent,
    StrategyTournamentAgent,
)


class CommitteeMockClient:
    model = "mock-deepseek-v3"
    model_name = "mock-deepseek-v3"

    def __init__(self):
        self.call_count = 0

    def create_chat_completion(
        self,
        messages: list[dict[str, str]],
        response_format: dict[str, str] | None = None,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        self.call_count += 1
        system = messages[0]["content"].lower()
        if "meta-reviewer" in system:
            payload = {
                "committee_synthesis": {
                    "highest_priority_risks": ["temporal leakage"],
                    "agreement": ["methodology and claim reviewers agree"],
                    "disagreement": [],
                    "recommended_focus": "add temporal split or narrow claim",
                },
                "author_confirmation_questions": ["Can the temporal split be completed?"],
                "reasoning": "Meta review merges committee findings.",
            }
        elif "strategy meta-planner" in system:
            payload = {
                "selected_strategy_id": "strategy_a",
                "merged_plan": {
                    "response_position": "accept_and_revise",
                    "required_actions": ["temporal split"],
                    "claim_adjustments": ["narrow generalization"],
                },
                "rejection_reasons": [{"strategy_id": "strategy_b", "reason": "overclaim risk"}],
                "author_confirmation_questions": ["Can temporal split be completed?"],
                "reasoning": "Strategy A is safest.",
            }
        elif "strategy tournament" in system:
            payload = {
                "strategy_candidates": [
                    {
                        "strategy_id": "strategy_a",
                        "name": "add temporal split and narrow claim",
                        "response_position": "accept_and_revise",
                        "required_actions": ["temporal split"],
                        "rubric_scores": {
                            "concern_coverage": 5,
                            "evidence_grounding": 4,
                            "feasibility": 3,
                            "overclaim_risk": 1,
                        },
                        "author_confirmation_required": True,
                    }
                ],
                "reasoning": "Candidate A is strongest.",
            }
        else:
            payload = {
                "reviewer_role": "methodology",
                "findings": [
                    {
                        "risk": "temporal leakage",
                        "severity": "high",
                        "evidence": "no temporal split",
                        "recommendation": "run temporal split",
                    }
                ],
                "author_confirmation_questions": ["Can the temporal split be completed?"],
                "reasoning": "Methodology risk is high.",
            }
        return {"choices": [{"message": {"content": json.dumps(payload)}}], "usage": {}}


def test_committee_reviewer_agent_returns_structured_findings():
    client = CommitteeMockClient()
    agent = CommitteeReviewerAgent(
        "methodology_committee_reviewer",
        client,
        reviewer_role="methodology",
    )

    message = agent.execute({"review_text": "split unclear", "all_agent_outputs": {}})

    assert message.content["reviewer_role"] == "methodology"
    assert message.content["findings"][0]["severity"] == "high"
    assert client.call_count == 1


def test_committee_meta_reviewer_synthesizes_committee_outputs():
    client = CommitteeMockClient()
    agent = CommitteeMetaReviewerAgent("committee_meta_reviewer", client)

    message = agent.execute({
        "committee_outputs": {
            "methodology_committee_reviewer": {"findings": [{"risk": "temporal leakage"}]}
        }
    })

    assert "committee_synthesis" in message.content
    assert "temporal leakage" in message.content["committee_synthesis"]["highest_priority_risks"]


def test_strategy_tournament_agent_outputs_candidates_with_scores():
    client = CommitteeMockClient()
    agent = StrategyTournamentAgent("strategy_tournament_agent", client)

    message = agent.execute({"all_agent_outputs": {}})

    assert message.content["strategy_candidates"][0]["strategy_id"] == "strategy_a"
    assert message.content["strategy_candidates"][0]["author_confirmation_required"] is True


def test_strategy_meta_planner_selects_safe_strategy():
    client = CommitteeMockClient()
    agent = StrategyMetaPlannerAgent("strategy_meta_planner", client)

    message = agent.execute({"strategy_candidates": []})

    assert message.content["selected_strategy_id"] == "strategy_a"
    assert "narrow generalization" in message.content["merged_plan"]["claim_adjustments"]
