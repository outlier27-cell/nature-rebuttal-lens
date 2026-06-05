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


def test_committee_prompt_forbids_invented_reviewer_identity():
    agent = CommitteeReviewerAgent(
        "methodology_committee_reviewer",
        CommitteeMockClient(),
        reviewer_role="methodology",
    )
    prompt = agent.build_prompt({"review_text": "split unclear", "all_agent_outputs": {}})
    system_prompt = prompt[0]["content"].lower()

    assert "shared fact base" in system_prompt
    assert "emphasis" in system_prompt
    assert "do not invent reviewer identities" in system_prompt
    assert "do not invent specialties" in system_prompt


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


def test_committee_meta_reviewer_normalizes_structured_reasoning_from_provider():
    class StructuredReasoningClient:
        model = "mock-deepseek-v3"
        model_name = "mock-deepseek-v3"

        def create_chat_completion(
            self,
            messages: list[dict[str, str]],
            response_format: dict[str, str] | None = None,
            temperature: float = 0.0,
        ) -> dict[str, Any]:
            return {
                "committee_synthesis": {
                    "highest_priority_risks": ["temporal leakage"],
                    "agreement": ["methodology and claim reviewers agree"],
                    "disagreement": [],
                    "recommended_focus": "add temporal split or narrow claim",
                },
                "author_confirmation_questions": ["Can the temporal split be completed?"],
                "reasoning": {
                    "consensus": "committee findings agree on split validity",
                    "priority": ["temporal split", "claim narrowing"],
                },
            }

    agent = CommitteeMetaReviewerAgent("committee_meta_reviewer", StructuredReasoningClient())

    message = agent.execute({
        "committee_outputs": {
            "methodology_committee_reviewer": {"findings": [{"risk": "temporal leakage"}]}
        }
    })

    assert isinstance(message.content["reasoning"], str)
    assert "consensus" in message.content["reasoning"]


def test_strategy_tournament_agent_outputs_candidates_with_scores():
    client = CommitteeMockClient()
    agent = StrategyTournamentAgent("strategy_tournament_agent", client)

    message = agent.execute({"all_agent_outputs": {}})

    assert message.content["strategy_candidates"][0]["strategy_id"] == "strategy_a"
    assert message.content["strategy_candidates"][0]["author_confirmation_required"] is True


def test_strategy_tournament_agent_fills_missing_candidate_ids():
    class MissingStrategyIdClient:
        model = "mock-deepseek-v3"
        model_name = "mock-deepseek-v3"

        def create_chat_completion(
            self,
            messages: list[dict[str, str]],
            response_format: dict[str, str] | None = None,
            temperature: float = 0.0,
        ) -> dict[str, Any]:
            return {
                "strategy_candidates": [
                    {
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

    agent = StrategyTournamentAgent("strategy_tournament_agent", MissingStrategyIdClient())

    message = agent.execute({"all_agent_outputs": {}})

    assert message.content["strategy_candidates"][0]["strategy_id"] == "strategy_001"


def test_strategy_tournament_agent_normalizes_deepseek_flat_candidate_shape():
    class FlatCandidateClient:
        model = "mock-deepseek-v3"
        model_name = "mock-deepseek-v3"

        def create_chat_completion(
            self,
            messages: list[dict[str, str]],
            response_format: dict[str, str] | None = None,
            temperature: float = 0.0,
        ) -> dict[str, Any]:
            return {
                "strategy_candidates": [
                    {
                        "strategy_family": "Experiment",
                        "evidence_anchor": "section_008",
                        "concern_coverage": 0.9,
                        "evidence_grounding": 0.5,
                        "feasibility": "Medium - requires new analysis",
                        "overclaim_risk": "High - pending results",
                        "tone_risk": "Medium - avoid overpromising",
                        "provenance_strength": 0.6,
                        "overclaim_gate": "Mark new analyses as planned",
                    }
                ],
                "reasoning": "Experiment directly tackles reviewer requests.",
            }

    agent = StrategyTournamentAgent("strategy_tournament_agent", FlatCandidateClient())

    message = agent.execute({"all_agent_outputs": {}})
    candidate = message.content["strategy_candidates"][0]

    assert candidate["strategy_id"] == "strategy_001"
    assert candidate["name"] == "Experiment"
    assert candidate["response_position"] == "experiment"
    assert candidate["required_actions"] == ["Mark new analyses as planned"]
    assert candidate["rubric_scores"]["concern_coverage"] == 0.9
    assert candidate["author_confirmation_required"] is True


def test_strategy_tournament_agent_does_not_turn_numeric_scores_into_actions():
    class NumericScoreCandidateClient:
        model = "mock-deepseek-v3"
        model_name = "mock-deepseek-v3"

        def create_chat_completion(
            self,
            messages: list[dict[str, str]],
            response_format: dict[str, str] | None = None,
            temperature: float = 0.0,
        ) -> dict[str, Any]:
            return {
                "strategy_candidates": [
                    {
                        "strategy_family": "Clarify",
                        "evidence_anchor": "section_002",
                        "concern_coverage": 0.8,
                        "evidence_grounding": 0.7,
                        "feasibility": 0.9,
                        "overclaim_risk": 0.2,
                        "tone_risk": 0.1,
                        "provenance_strength": 0.8,
                    }
                ],
                "reasoning": "Clarification uses existing manuscript evidence.",
            }

    agent = StrategyTournamentAgent("strategy_tournament_agent", NumericScoreCandidateClient())

    message = agent.execute({"all_agent_outputs": {}})
    candidate = message.content["strategy_candidates"][0]

    assert candidate["required_actions"] == []
    assert candidate["rubric_scores"]["feasibility"] == 0.9


def test_strategy_tournament_prompt_includes_four_strategy_library_and_evidence_gate():
    agent = StrategyTournamentAgent("strategy_tournament_agent", CommitteeMockClient())
    prompt = agent.build_prompt({"all_agent_outputs": {}})
    system_prompt = prompt[0]["content"]

    for label in ["Accept", "Defend", "Clarify", "Experiment"]:
        assert label in system_prompt
    assert "evidence anchor" in system_prompt.lower()
    assert "Do not invent completed experiments" in system_prompt


def test_strategy_meta_planner_selects_safe_strategy():
    client = CommitteeMockClient()
    agent = StrategyMetaPlannerAgent("strategy_meta_planner", client)

    message = agent.execute({"strategy_candidates": []})

    assert message.content["selected_strategy_id"] == "strategy_a"
    assert "narrow generalization" in message.content["merged_plan"]["claim_adjustments"]


def test_strategy_meta_planner_normalizes_dict_rejection_reasons_and_question_objects():
    class MetaPlannerDriftClient:
        model = "mock-deepseek-v3"
        model_name = "mock-deepseek-v3"

        def create_chat_completion(
            self,
            messages: list[dict[str, str]],
            response_format: dict[str, str] | None = None,
            temperature: float = 0.0,
        ) -> dict[str, Any]:
            return {
                "selected_strategy_id": "strategy_002",
                "merged_plan": {
                    "core_strategy": "add_new_analysis",
                    "supporting_actions": [
                        {
                            "action_type": "new_analysis",
                            "description": "Run temporal split validation",
                        }
                    ],
                },
                "rejection_reasons": {
                    "strategy_001": "Insufficient direct response to temporal validation",
                    "strategy_003": "Does not address robustness checks",
                },
                "author_confirmation_questions": [
                    {
                        "question": "Can the temporal split analysis be completed?",
                        "urgency": "high",
                    }
                ],
                "reasoning": "Strategy 002 covers the core concern.",
            }

    agent = StrategyMetaPlannerAgent("strategy_meta_planner", MetaPlannerDriftClient())

    message = agent.execute({"strategy_candidates": []})

    assert message.content["rejection_reasons"] == [
        {
            "strategy_id": "strategy_001",
            "reason": "Insufficient direct response to temporal validation",
        },
        {
            "strategy_id": "strategy_003",
            "reason": "Does not address robustness checks",
        },
    ]
    assert message.content["author_confirmation_questions"] == [
        "Can the temporal split analysis be completed?"
    ]
