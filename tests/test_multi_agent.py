"""
Test script for multi-agent system

Validates that all agents work correctly and produce expected outputs.
"""

import json
from pathlib import Path
from typing import Any
import pytest

from peer_review_skills.agents.specialized_agents import (
    ReviewerUnderstandingAgent,
    TacitConcernInterpreterAgent,
    InstitutionalSignalInterpreterAgent,
    EvidenceActionPlannerAgent,
    AuthorPositioningAgent,
    ToneCommitmentCalibratorAgent,
)
from peer_review_skills.agents.specialized_agents_part2 import (
    ActorNetworkMapperAgent,
    CrossDisciplinaryLensInterpreterAgent,
    IntegrityAdequacyCheckerAgent,
    create_all_specialized_agents,
)
from peer_review_skills.agents.multi_agent_orchestrator import MultiAgentOrchestrator
from peer_review_skills.agents.workflow_integration import (
    _create_model_client,
    _load_interaction_units,
    _load_retrieval_predictions,
    run_multi_agent_workflow,
)


class MockLLMClient:
    """Mock LLM client for testing"""

    def __init__(self):
        self.model_name = "mock-deepseek-v3"
        self.call_count = 0

    def create_chat_completion(
        self,
        messages: list[dict[str, str]],
        response_format: dict[str, str] | None = None,
        temperature: float = 0.0
    ) -> dict[str, Any]:
        """Mock LLM response"""
        self.call_count += 1

        # Extract agent type from system message
        system_msg = messages[0]["content"]

        if "cross-disciplinary" in system_msg.lower():
            return self._mock_lens_interpretation_response()
        elif "reviewer understanding" in system_msg.lower():
            return self._mock_reviewer_understanding_response()
        elif "tacit concern" in system_msg.lower():
            return self._mock_tacit_concern_response()
        elif "institutional signal" in system_msg.lower():
            return self._mock_institutional_signal_response()
        elif "evidence action" in system_msg.lower():
            return self._mock_evidence_action_response()
        elif "author positioning" in system_msg.lower():
            return self._mock_author_positioning_response()
        elif "tone" in system_msg.lower():
            return self._mock_tone_calibration_response()
        elif "actor network" in system_msg.lower():
            return self._mock_actor_network_response()
        elif "integrity" in system_msg.lower():
            return self._mock_integrity_check_response()
        else:
            return self._mock_generic_response()

    def _mock_reviewer_understanding_response(self) -> dict[str, Any]:
        return {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "concern_map": [{
                            "concern_type": "methodological_rigor",
                            "surface_request": "Please provide more details on the experimental setup",
                            "text_evidence": "The methods section lacks sufficient detail",
                            "confidence": "high"
                        }],
                        "reasoning": "Reviewer explicitly requests methodological details"
                    })
                }
            }],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50}
        }

    def _mock_tacit_concern_response(self) -> dict[str, Any]:
        return {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "risk_interpretation": [{
                            "risk_type": "reproducibility_risk",
                            "tacit_concern": "insufficient_methodological_transparency",
                            "observable_trace": "Reviewer questions experimental setup details",
                            "boundary": "Observable textual trace only; not a claim about reviewer psychology."
                        }],
                        "reasoning": "Methodological questions signal reproducibility concerns"
                    })
                }
            }],
            "usage": {"prompt_tokens": 120, "completion_tokens": 60}
        }

    def _mock_institutional_signal_response(self) -> dict[str, Any]:
        return {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "institutional_signal_note": [{
                            "institutional_signal": "transparency_norm",
                            "action_link": "Provide detailed methods to meet transparency standards",
                            "boundary": "Not an acceptance prediction; author judgment required."
                        }],
                        "reasoning": "Journal emphasizes methodological transparency"
                    })
                }
            }],
            "usage": {"prompt_tokens": 110, "completion_tokens": 55}
        }

    def _mock_evidence_action_response(self) -> dict[str, Any]:
        return {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "evidence_action_plan": [{
                            "action_type": "clarify_existing_method",
                            "required_artifact": "Detailed methods description",
                            "supporting_case_ids": ["case_001", "case_002"],
                            "requires_author_confirmation": True
                        }],
                        "author_confirmation_questions": [
                            "Can you provide more details on the experimental setup?"
                        ],
                        "reasoning": "Clarification needed for existing methods"
                    })
                }
            }],
            "usage": {"prompt_tokens": 150, "completion_tokens": 70}
        }

    def _mock_author_positioning_response(self) -> dict[str, Any]:
        return {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "author_positioning": [{
                            "position": "acknowledge_and_clarify",
                            "stance_boundary": "Offer options for author judgment; do not force concession.",
                            "alternative_positions": ["defend_with_evidence", "acknowledge_and_revise"]
                        }],
                        "reasoning": "Author can clarify without major revision"
                    })
                }
            }],
            "usage": {"prompt_tokens": 130, "completion_tokens": 60}
        }

    def _mock_tone_calibration_response(self) -> dict[str, Any]:
        return {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "tone_commitment_warnings": [{
                            "tone": "neutral_professional",
                            "commitment_level": "appropriate",
                            "risk_flags": [],
                            "boundary": "Not a psychological diagnosis; observable text only."
                        }],
                        "reasoning": "Tone and commitments are appropriate"
                    })
                }
            }],
            "usage": {"prompt_tokens": 140, "completion_tokens": 65}
        }

    def _mock_actor_network_response(self) -> dict[str, Any]:
        return {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "actor_network_note": [{
                            "actor_type": "figure",
                            "actor_id": "Figure 2",
                            "role": "Carries methodological evidence",
                            "evidence_link": "Links to clarify_existing_method action"
                        }],
                        "retrieved_case_ids": ["case_001", "case_002"],
                        "boundary": "Observable alignment only; not causal claims.",
                        "reasoning": "Figure 2 provides methodological details"
                    })
                }
            }],
            "usage": {"prompt_tokens": 135, "completion_tokens": 70}
        }

    def _mock_lens_interpretation_response(self) -> dict[str, Any]:
        return {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "lens_interpretations": {
                            "tacit_knowledge_boundary": {
                                "observable_trace": "Methodological transparency request",
                                "system_action": "Convert to verifiable evidence requirement",
                                "boundary": "Not inferring true psychology"
                            },
                            "institutional_dependence": {
                                "observable_trace": "Journal transparency norms",
                                "system_action": "Identify institutional context",
                                "boundary": "Not predicting acceptance"
                            },
                            "actor_network_alignment": {
                                "observable_trace": "Figure 2 carries evidence",
                                "system_action": "Map evidence carriers",
                                "boundary": "Observable alignment only"
                            },
                            "fast_slow_cognitive_correction": {
                                "observable_trace": "Plan-first workflow",
                                "system_action": "Evidence check before output",
                                "boundary": "Not generating final text"
                            },
                            "emotion_tone_commitment_calibration": {
                                "observable_trace": "Neutral professional tone",
                                "system_action": "Calibrate commitment strength",
                                "boundary": "Not diagnosing emotions"
                            },
                            "author_agency_gate": {
                                "observable_trace": "Author confirmation required",
                                "system_action": "Gate all commitments",
                                "boundary": "Author judgment preserved"
                            }
                        },
                        "reasoning": "All 6 lenses applied successfully"
                    })
                }
            }],
            "usage": {"prompt_tokens": 200, "completion_tokens": 150}
        }

    def _mock_integrity_check_response(self) -> dict[str, Any]:
        return {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "adequacy_report": [
                            "All outputs are traceable to source text",
                            "Evidence plan is sufficient",
                            "No unsupported commitments found"
                        ],
                        "response_adequacy": {
                            "is_adequate": True,
                            "missing_elements": [],
                            "strengths": ["Clear evidence plan", "Appropriate tone"]
                        },
                        "provenance_checks": [{
                            "claim": "Methodological details needed",
                            "source": "Review text",
                            "traceable": True
                        }],
                        "responsible_use_warnings": [
                            "assistant_only",
                            "author_must_verify_all_claims",
                            "not_final_rebuttal_text",
                            "no_acceptance_prediction"
                        ],
                        "issues": [],
                        "reasoning": "All integrity checks passed"
                    })
                }
            }],
            "usage": {"prompt_tokens": 250, "completion_tokens": 100}
        }

    def _mock_generic_response(self) -> dict[str, Any]:
        return {
            "choices": [{
                "message": {
                    "content": json.dumps({
                        "output": "Generic mock response",
                        "reasoning": "Mock LLM response"
                    })
                }
            }],
            "usage": {"prompt_tokens": 100, "completion_tokens": 50}
        }


class ParsedJsonMockLLMClient(MockLLMClient):
    """Mock the repo's OpenAICompatibleChatClient, which returns parsed JSON dicts."""

    def create_chat_completion(
        self,
        messages: list[dict[str, str]],
        response_format: dict[str, str] | None = None,
        temperature: float = 0.0
    ) -> dict[str, Any]:
        raw = super().create_chat_completion(messages, response_format, temperature)
        return json.loads(raw["choices"][0]["message"]["content"])


def test_individual_agents():
    """Test each agent individually"""
    print("Testing individual agents...")

    client = MockLLMClient()
    taxonomies = {
        "concern_taxonomy": {},
        "risk_type": {},
        "tacit_concern": {},
        "institutional_signal": {},
        "evidence_action": {},
        "author_positioning": {},
        "tone_commitment": {}
    }

    # Test ReviewerUnderstandingAgent
    agent = ReviewerUnderstandingAgent("test_agent", client)
    inputs = {
        "review_text": "The methods section lacks sufficient detail.",
        "taxonomies": taxonomies
    }
    message = agent.execute(inputs)
    assert message.message_type == "output"
    assert "concern_map" in message.content
    print("OK ReviewerUnderstandingAgent works")

    # Test TacitConcernInterpreterAgent
    agent = TacitConcernInterpreterAgent("test_agent", client)
    inputs["concern_map"] = message.content
    message = agent.execute(inputs)
    assert "risk_interpretation" in message.content
    print("OK TacitConcernInterpreterAgent works")

    print("\nAll individual agent tests passed!")


def test_orchestrator():
    """Test full orchestrator workflow"""
    print("\nTesting orchestrator...")

    client = MockLLMClient()
    agents = create_all_specialized_agents(client)
    orchestrator = MultiAgentOrchestrator(agents)

    # Mock data
    unit = {
        "unit_id": "test_001",
        "review_text": "The methods section lacks sufficient detail.",
        "response_text": "We will provide more details in the revised manuscript.",
        "provenance": {"source": "test"}
    }

    retrieval = {
        "top_k": [
            {"unit_id": "case_001", "score": 0.9},
            {"unit_id": "case_002", "score": 0.8}
        ]
    }

    taxonomies = {
        "concern_taxonomy": {},
        "risk_type": {},
        "tacit_concern": {},
        "institutional_signal": {},
        "evidence_action": {},
        "author_positioning": {},
        "tone_commitment": {}
    }

    # Execute workflow
    trace = orchestrator.execute_workflow(unit, retrieval, taxonomies)

    # Validate output
    assert trace["trace_id"] == "workflow_v3_test_001"
    assert trace["query_unit_id"] == "test_001"
    assert len(trace["agent_intermediate_outputs"]) == 9
    assert len(trace["message_bus"]) == 9
    assert trace["execution_metadata"]["total_llm_calls"] == 9
    assert trace["execution_metadata"]["layers_executed"] == len(trace["execution_trace"])
    assert trace["execution_metadata"]["layers_executed"] == 8

    print(f"OK Orchestrator executed {len(trace['message_bus'])} agent calls")
    print("OK All 9 agents produced outputs")
    print(f"OK Execution trace has {len(trace['execution_trace'])} layers")

    # Check each agent output
    required_agents = [
        "reviewer_understanding_agent",
        "tacit_concern_interpreter",
        "institutional_signal_interpreter",
        "evidence_action_planner",
        "author_positioning_agent",
        "tone_commitment_calibrator",
        "actor_network_mapper",
        "cross_disciplinary_lens_interpreter",
        "integrity_adequacy_checker"
    ]

    for agent_id in required_agents:
        assert agent_id in trace["agent_intermediate_outputs"]
        print(f"OK {agent_id} output present")

    print("\nOrchestrator test passed!")


def test_message_bus():
    """Test message bus functionality"""
    print("\nTesting message bus...")

    client = MockLLMClient()
    agents = create_all_specialized_agents(client)
    orchestrator = MultiAgentOrchestrator(agents)

    unit = {"unit_id": "test_002", "review_text": "Test", "response_text": "Test"}
    retrieval = {"top_k": []}
    taxonomies = {}

    trace = orchestrator.execute_workflow(unit, retrieval, taxonomies)

    # Check message bus
    assert len(trace["message_bus"]) > 0
    for msg in trace["message_bus"]:
        assert "agent_id" in msg
        assert "timestamp" in msg
        assert "message_type" in msg
        assert "content" in msg
        assert "metadata" in msg
        print(f"OK Message from {msg['agent_id']}: {msg['message_type']}")

    print("\nMessage bus test passed!")


def test_reviewer_understanding_agent_accepts_missing_taxonomies():
    """Single-agent public use should tolerate omitted taxonomy context."""
    agent = ReviewerUnderstandingAgent("reviewer_understanding_agent", MockLLMClient())

    message = agent.execute({
        "review_text": "The methods section lacks sufficient detail."
    })

    assert message.message_type == "output"
    assert "concern_map" in message.content


@pytest.mark.parametrize(
    ("agent_cls", "expected_field", "inputs"),
    [
        (
            ReviewerUnderstandingAgent,
            "concern_map",
            {"review_text": "The methods section lacks sufficient detail."},
        ),
        (
            TacitConcernInterpreterAgent,
            "risk_interpretation",
            {
                "review_text": "The methods section lacks sufficient detail.",
                "concern_map": {"concern_map": []},
            },
        ),
        (
            InstitutionalSignalInterpreterAgent,
            "institutional_signal_note",
            {
                "review_text": "The methods section lacks sufficient detail.",
                "concern_map": {"concern_map": []},
            },
        ),
        (
            EvidenceActionPlannerAgent,
            "evidence_action_plan",
            {
                "concern_map": {"concern_map": []},
                "risk_interpretation": {"risk_interpretation": []},
                "retrieved_cases": [],
            },
        ),
        (
            AuthorPositioningAgent,
            "author_positioning",
            {
                "response_text": "We will clarify the method.",
                "evidence_plan": {"evidence_action_plan": []},
            },
        ),
        (
            ToneCommitmentCalibratorAgent,
            "tone_commitment_warnings",
            {
                "response_text": "We will clarify the method.",
                "evidence_plan": {"evidence_action_plan": []},
                "author_positioning": {"author_positioning": []},
            },
        ),
    ],
)
def test_taxonomy_aware_agents_accept_none_taxonomies(agent_cls, expected_field, inputs):
    """External callers may pass taxonomies=None; agents should use empty taxonomy context."""
    agent = agent_cls(agent_cls.__name__, MockLLMClient())

    message = agent.execute({**inputs, "taxonomies": None})

    assert message.message_type == "output"
    assert expected_field in message.content


def test_orchestrator_accepts_repo_parsed_json_client():
    """The real OpenAICompatibleChatClient returns parsed JSON, not raw choices."""
    client = ParsedJsonMockLLMClient()
    agents = create_all_specialized_agents(client)
    orchestrator = MultiAgentOrchestrator(agents)

    trace = orchestrator.execute_workflow(
        {
            "unit_id": "parsed_json_001",
            "review_text": "The methods section lacks sufficient detail.",
            "response_text": "We will add precise methodological details.",
            "provenance": {"source": "test"},
        },
        {"top_k": [{"unit_id": "case_001", "score": 0.9}]},
        {
            "concern_taxonomy": {},
            "risk_type": {},
            "tacit_concern": {},
            "institutional_signal": {},
            "evidence_action": {},
            "author_positioning": {},
            "tone_commitment": {},
        },
    )

    assert trace["execution_metadata"]["total_llm_calls"] == 9
    assert trace["agent_intermediate_outputs"]["integrity_adequacy_checker"]["responsible_use_warnings"]


def test_create_model_client_uses_existing_openai_compatible_signature():
    client = _create_model_client(
        {
            "api_base": "https://xh.v1api.cc",
            "api_key": "test-key",
            "model": "deepseek-v3",
        }
    )

    assert client.base_url == "https://xh.v1api.cc"
    assert client.model == "deepseek-v3"


def test_loads_official_naturereview_v01_paths():
    project_root = Path.cwd()

    units = _load_interaction_units(project_root)
    predictions = _load_retrieval_predictions(project_root)

    assert len(units) == 245
    assert len(predictions) == 100
    assert units[0]["unit_id"].startswith("riu_v1_")
    assert predictions[0]["top_k"]


def test_taxonomy_loader_exposes_agent_aliases():
    from peer_review_skills.agents.workflow_integration import _load_taxonomies

    taxonomies = _load_taxonomies(Path.cwd())

    assert "concern_taxonomy" in taxonomies
    assert "tacit_concern" in taxonomies
    assert "evidence_action" in taxonomies
    assert "institutional_signal" in taxonomies
    assert "author_positioning" in taxonomies
    assert "tone_commitment" in taxonomies
    assert "clarity_presentation" in json.dumps(taxonomies["concern_taxonomy"])
    assert "figure_table_revision" in json.dumps(taxonomies["evidence_action"])


def test_cross_disciplinary_lens_receives_prior_agent_outputs():
    captured_inputs: list[dict[str, Any]] = []

    class CapturingLensClient(ParsedJsonMockLLMClient):
        def create_chat_completion(
            self,
            messages: list[dict[str, str]],
            response_format: dict[str, str] | None = None,
            temperature: float = 0.0,
        ) -> dict[str, Any]:
            if "cross-disciplinary" in messages[0]["content"].lower():
                captured_inputs.append(json.loads(messages[1]["content"]))
            return super().create_chat_completion(messages, response_format, temperature)

    orchestrator = MultiAgentOrchestrator(create_all_specialized_agents(CapturingLensClient()))
    orchestrator.execute_workflow(
        {
            "unit_id": "lens_context_001",
            "review_text": "The methods section lacks sufficient detail.",
            "response_text": "We will add precise methodological details.",
            "provenance": {"source": "test"},
        },
        {"top_k": [{"unit_id": "case_001", "score": 0.9}]},
        {
            "concern_taxonomy": {},
            "risk_type": {},
            "tacit_concern": {},
            "institutional_signal": {},
            "evidence_action": {},
            "author_positioning": {},
            "tone_commitment": {},
        },
    )

    assert captured_inputs
    payload = captured_inputs[0]
    prior_outputs = payload["all_agent_outputs"]
    assert "reviewer_understanding_agent" in prior_outputs
    assert "evidence_action_planner" in prior_outputs
    assert "actor_network_mapper" in prior_outputs
    assert payload["unit"]["unit_id"] == "lens_context_001"
    assert payload["retrieved_case_ids"] == ["case_001"]


def test_dependency_order_passes_prior_outputs_to_dependent_agents():
    captured_inputs: dict[str, dict[str, Any]] = {}

    class CapturingDependencyClient(ParsedJsonMockLLMClient):
        def create_chat_completion(
            self,
            messages: list[dict[str, str]],
            response_format: dict[str, str] | None = None,
            temperature: float = 0.0,
        ) -> dict[str, Any]:
            system = messages[0]["content"].lower()
            payload = json.loads(messages[1]["content"])
            if "tacit concern" in system:
                captured_inputs["tacit"] = payload
            if "tone and commitment" in system:
                captured_inputs["tone"] = payload
            return super().create_chat_completion(messages, response_format, temperature)

    orchestrator = MultiAgentOrchestrator(create_all_specialized_agents(CapturingDependencyClient()))
    orchestrator.execute_workflow(
        {
            "unit_id": "dependency_001",
            "review_text": "The methods section lacks sufficient detail.",
            "response_text": "We will add precise methodological details.",
            "provenance": {"source": "test"},
        },
        {"top_k": [{"unit_id": "case_001", "score": 0.9}]},
        {
            "concern_taxonomy": {},
            "risk_type": {},
            "tacit_concern": {},
            "institutional_signal": {},
            "evidence_action": {},
            "author_positioning": {},
            "tone_commitment": {},
        },
    )

    assert captured_inputs["tacit"]["concern_map"]["concern_map"]
    assert captured_inputs["tone"]["author_positioning"]["author_positioning"]


def test_cross_disciplinary_prompt_forbids_private_intent_and_manipulation():
    agent = CrossDisciplinaryLensInterpreterAgent(
        "cross_disciplinary_lens_interpreter",
        ParsedJsonMockLLMClient(),
    )
    prompt = agent.build_prompt(
        {
            "all_agent_outputs": {},
            "unit": {"unit_id": "u1"},
            "retrieval": {"top_k": [{"unit_id": "case_001"}]},
        }
    )
    system_prompt = prompt[0]["content"]

    assert "Do NOT infer private reviewer psychology" in system_prompt
    assert "Do NOT suggest manipulating reviewer motivations" in system_prompt
    assert "Frame each lens as support for author reflection" in system_prompt


def test_cross_disciplinary_prompt_contains_readable_chinese_lens_names():
    agent = CrossDisciplinaryLensInterpreterAgent(
        "cross_disciplinary_lens_interpreter",
        ParsedJsonMockLLMClient(),
    )
    prompt = agent.build_prompt(
        {
            "all_agent_outputs": {},
            "unit": {"unit_id": "u1"},
            "retrieval": {"top_k": [{"unit_id": "case_001"}]},
        }
    )
    system_prompt = prompt[0]["content"]

    for phrase in [
        "默会知识边界",
        "制度依赖",
        "行动者网络对齐",
        "快慢思维校正",
        "情绪-语气-承诺校准",
        "作者主体性门控",
    ]:
        assert phrase in system_prompt
    for marker in [
        "".join(chr(code) for code in [0x699B, 0x6A39, 0x7D30]),
        "".join(chr(code) for code in [0x934F, 0x8DFA, 0x5BB3]),
        "".join(chr(code) for code in [0x7403, 0x5C70, 0x59E9]),
        chr(0x93AF),
        chr(0x6D63),
    ]:
        assert marker not in system_prompt

def test_cross_disciplinary_lens_rejects_private_psychology_language():
    agent = CrossDisciplinaryLensInterpreterAgent(
        "cross_disciplinary_lens_interpreter",
        ParsedJsonMockLLMClient(),
    )
    output = {
        "lens_interpretations": {
            "tacit_knowledge_boundary": {"observable_trace": "x", "system_action": "x", "boundary": "x"},
            "institutional_dependence": {"observable_trace": "x", "system_action": "x", "boundary": "x"},
            "actor_network_alignment": {"observable_trace": "x", "system_action": "x", "boundary": "x"},
            "fast_slow_cognitive_correction": {
                "observable_trace": "Reviewer fast thinking indicates perceptual biases",
                "system_action": "counter reviewer bias",
                "boundary": "x",
            },
            "emotion_tone_commitment_calibration": {"observable_trace": "x", "system_action": "x", "boundary": "x"},
            "author_agency_gate": {"observable_trace": "x", "system_action": "x", "boundary": "x"},
        }
    }

    valid, error = agent.validate_output(output)

    assert not valid
    assert "private psychology" in str(error)


def test_cross_disciplinary_lens_allows_fast_slow_lens_without_private_psychology():
    agent = CrossDisciplinaryLensInterpreterAgent(
        "cross_disciplinary_lens_interpreter",
        ParsedJsonMockLLMClient(),
    )
    output = {
        "lens_interpretations": {
            "tacit_knowledge_boundary": {"observable_trace": "x", "system_action": "x", "boundary": "x"},
            "institutional_dependence": {"observable_trace": "x", "system_action": "x", "boundary": "x"},
            "actor_network_alignment": {"observable_trace": "x", "system_action": "x", "boundary": "x"},
            "fast_slow_cognitive_correction": {
                "observable_trace": "Fast thinking / slow thinking lens used as an evidence-check label only.",
                "system_action": "Slow down response planning by requiring evidence anchors.",
                "boundary": "No private reviewer psychology or hidden motive claim.",
            },
            "emotion_tone_commitment_calibration": {"observable_trace": "x", "system_action": "x", "boundary": "x"},
            "author_agency_gate": {"observable_trace": "x", "system_action": "x", "boundary": "x"},
        }
    }

    valid, error = agent.validate_output(output)

    assert valid
    assert error is None


@pytest.mark.parametrize("alias_field", ["cross_disciplinary_lens_map", "lens_map"])
def test_cross_disciplinary_lens_normalizes_deepseek_lens_map_alias(alias_field):
    agent = CrossDisciplinaryLensInterpreterAgent(
        "cross_disciplinary_lens_interpreter",
        ParsedJsonMockLLMClient(),
    )
    lens_map = {
        "tacit_knowledge_boundary": {"observable_trace": "reviewer asks for explicit evidence"},
        "institutional_dependence": {"observable_trace": "editorial reproducibility norm"},
        "actor_network_alignment": {"observable_trace": "dataset split carries validity"},
        "fast_slow_cognitive_correction": {"observable_trace": "slow down claim checking"},
        "emotion_tone_commitment_calibration": {"observable_trace": "avoid over-promising"},
        "author_agency_gate": {"observable_trace": "author confirmation remains required"},
    }
    response = {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        {
                            alias_field: lens_map,
                            "reasoning": "Provider used a semantically equivalent lens map field.",
                        }
                    )
                }
            }
        ]
    }

    output = agent.parse_response(response)
    valid, error = agent.validate_output(output)

    assert output["lens_interpretations"] == lens_map
    assert valid
    assert error is None


def test_refinement_rechecks_integrity_and_preserves_original_agent_context():
    captured_evidence_inputs: list[dict[str, Any]] = []

    class RefinementClient(ParsedJsonMockLLMClient):
        def __init__(self):
            super().__init__()
            self.integrity_call_count = 0

        def create_chat_completion(
            self,
            messages: list[dict[str, str]],
            response_format: dict[str, str] | None = None,
            temperature: float = 0.0,
        ) -> dict[str, Any]:
            system = messages[0]["content"].lower()
            if "evidence action" in system:
                captured_evidence_inputs.append(json.loads(messages[1]["content"]))
            if "integrity and adequacy checker" in system:
                self.integrity_call_count += 1
                if self.integrity_call_count == 1:
                    return {
                        "adequacy_report": ["Evidence plan needs revision."],
                        "response_adequacy": {
                            "is_adequate": False,
                            "missing_elements": ["evidence plan revision"],
                            "strengths": [],
                        },
                        "provenance_checks": [],
                        "responsible_use_warnings": [
                            "assistant_only",
                            "author_must_verify_all_claims",
                            "not_final_rebuttal_text",
                            "no_acceptance_prediction",
                        ],
                        "issues": [
                            {
                                "severity": "critical",
                                "agent_id": "evidence_action_planner",
                                "description": "Evidence plan is not sufficiently grounded.",
                            }
                        ],
                        "reasoning": "Critical issue found.",
                    }
            return super().create_chat_completion(messages, response_format, temperature)

    client = RefinementClient()
    orchestrator = MultiAgentOrchestrator(
        create_all_specialized_agents(client),
        enable_refinement=True,
        max_refinement_iterations=2,
    )

    trace = orchestrator.execute_workflow(
        {
            "unit_id": "refine_001",
            "review_text": "The methods section lacks sufficient detail.",
            "response_text": "We will add precise methodological details.",
            "provenance": {"source": "test"},
        },
        {"top_k": [{"unit_id": "case_001", "score": 0.9}]},
        {
            "concern_taxonomy": {},
            "risk_type": {},
            "tacit_concern": {},
            "institutional_signal": {},
            "evidence_action": {},
            "author_positioning": {},
            "tone_commitment": {},
        },
    )

    assert len(captured_evidence_inputs) == 2
    assert captured_evidence_inputs[-1]["concern_map"]["concern_map"]
    assert captured_evidence_inputs[-1]["retrieved_cases"]
    assert (
        captured_evidence_inputs[-1]["refinement_context"]["feedback"]
        == "Evidence plan is not sufficiently grounded."
    )
    assert captured_evidence_inputs[-1]["refinement_context"]["previous_output"]["evidence_action_plan"]
    assert client.integrity_call_count == 2
    assert any(
        item.get("layer") == "Layer 5: Integrity Recheck 1"
        for item in trace["execution_trace"]
    )
    assert trace["execution_metadata"]["refinement_iterations"] == 1
    assert trace["agent_intermediate_outputs"]["integrity_adequacy_checker"]["issues"] == []


def test_refinement_of_upstream_agent_refreshes_dependent_agents():
    captured_tone_inputs: list[dict[str, Any]] = []

    class UpstreamRefinementClient(ParsedJsonMockLLMClient):
        def __init__(self):
            super().__init__()
            self.integrity_call_count = 0
            self.evidence_call_count = 0

        def create_chat_completion(
            self,
            messages: list[dict[str, str]],
            response_format: dict[str, str] | None = None,
            temperature: float = 0.0,
        ) -> dict[str, Any]:
            system = messages[0]["content"].lower()
            if "evidence action" in system:
                self.evidence_call_count += 1
                if self.evidence_call_count == 2:
                    return {
                        "evidence_action_plan": [{
                            "action_type": "add_sensitivity_analysis",
                            "required_artifact": "Sensitivity analysis table",
                            "supporting_case_ids": ["case_001"],
                            "requires_author_confirmation": True,
                        }],
                        "author_confirmation_questions": [
                            "Can the authors run and verify a sensitivity analysis?"
                        ],
                        "reasoning": "Refined after integrity feedback.",
                    }
            if "tone and commitment" in system:
                captured_tone_inputs.append(json.loads(messages[1]["content"]))
            if "integrity and adequacy checker" in system:
                self.integrity_call_count += 1
                if self.integrity_call_count == 1:
                    return {
                        "adequacy_report": ["Evidence plan needs stronger action."],
                        "response_adequacy": {
                            "is_adequate": False,
                            "missing_elements": ["sensitivity analysis"],
                            "strengths": [],
                        },
                        "provenance_checks": [],
                        "responsible_use_warnings": [
                            "assistant_only",
                            "author_must_verify_all_claims",
                            "not_final_rebuttal_text",
                            "no_acceptance_prediction",
                        ],
                        "issues": [
                            {
                                "severity": "critical",
                                "agent_id": "evidence_action_planner",
                                "description": "Evidence action must be strengthened.",
                            }
                        ],
                        "reasoning": "Critical issue found.",
                    }
            return super().create_chat_completion(messages, response_format, temperature)

    client = UpstreamRefinementClient()
    orchestrator = MultiAgentOrchestrator(
        create_all_specialized_agents(client),
        enable_refinement=True,
        max_refinement_iterations=2,
    )
    trace = orchestrator.execute_workflow(
        {
            "unit_id": "refresh_001",
            "review_text": "The methods section lacks sufficient detail.",
            "response_text": "We will add precise methodological details.",
            "provenance": {"source": "test"},
        },
        {"top_k": [{"unit_id": "case_001", "score": 0.9}]},
        {
            "concern_taxonomy": {},
            "risk_type": {},
            "tacit_concern": {},
            "institutional_signal": {},
            "evidence_action": {},
            "author_positioning": {},
            "tone_commitment": {},
        },
    )

    assert len(captured_tone_inputs) == 2
    refreshed_plan = captured_tone_inputs[-1]["evidence_plan"]["evidence_action_plan"][0]
    assert refreshed_plan["action_type"] == "add_sensitivity_analysis"
    assert any(
        item.get("layer") == "Refinement Propagation 1"
        for item in trace["execution_trace"]
    )


def test_refinement_fails_fast_for_unknown_agent_issue():
    class UnknownIssueClient(ParsedJsonMockLLMClient):
        def create_chat_completion(
            self,
            messages: list[dict[str, str]],
            response_format: dict[str, str] | None = None,
            temperature: float = 0.0,
        ) -> dict[str, Any]:
            if "integrity and adequacy checker" in messages[0]["content"].lower():
                return {
                    "adequacy_report": ["Unknown agent issue."],
                    "response_adequacy": {
                        "is_adequate": False,
                        "missing_elements": ["unknown"],
                        "strengths": [],
                    },
                    "provenance_checks": [],
                    "responsible_use_warnings": [
                        "assistant_only",
                        "author_must_verify_all_claims",
                        "not_final_rebuttal_text",
                        "no_acceptance_prediction",
                    ],
                    "issues": [
                        {
                            "severity": "critical",
                            "agent_id": "missing_agent",
                            "description": "Critical issue points to a missing agent.",
                        }
                    ],
                    "reasoning": "Critical issue found.",
                }
            return super().create_chat_completion(messages, response_format, temperature)

    orchestrator = MultiAgentOrchestrator(
        create_all_specialized_agents(UnknownIssueClient()),
        enable_refinement=True,
        max_refinement_iterations=2,
    )

    with pytest.raises(RuntimeError, match="unrefinable critical integrity issues"):
        orchestrator.execute_workflow(
            {
                "unit_id": "unknown_issue_001",
                "review_text": "The methods section lacks sufficient detail.",
                "response_text": "We will add precise methodological details.",
                "provenance": {"source": "test"},
            },
            {"top_k": [{"unit_id": "case_001", "score": 0.9}]},
            {
                "concern_taxonomy": {},
                "risk_type": {},
                "tacit_concern": {},
                "institutional_signal": {},
                "evidence_action": {},
                "author_positioning": {},
                "tone_commitment": {},
            },
        )


def test_multi_agent_workflow_fails_fast_without_retrieval(tmp_path):
    unit_dir = tmp_path / "data/processed/review_interaction_kb/v1"
    unit_dir.mkdir(parents=True)
    (unit_dir / "interaction_units.jsonl").write_text(
        json.dumps({"unit_id": "u1", "review_text": "x", "response_text": "y"}) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(FileNotFoundError, match="retrieval"):
        _load_retrieval_predictions(tmp_path)


def test_v3_loader_does_not_fall_back_to_legacy_paths(tmp_path):
    legacy_dir = tmp_path / "data/processed/interaction_units"
    legacy_dir.mkdir(parents=True)
    (legacy_dir / "interaction_units.jsonl").write_text(
        json.dumps({"unit_id": "legacy_001"}) + "\n",
        encoding="utf-8",
    )

    with pytest.raises(FileNotFoundError, match="interaction units"):
        _load_interaction_units(tmp_path)


def test_run_multi_agent_workflow_with_mock_client_writes_nonempty_traces(tmp_path):
    project_root = Path.cwd()
    summary = run_multi_agent_workflow(
        project_root,
        scope="mvp",
        config={"limit": 2, "output_dir": tmp_path},
        model_client=ParsedJsonMockLLMClient(),
    )

    output_path = tmp_path / "workflow_traces.jsonl"
    traces = [json.loads(line) for line in output_path.read_text(encoding="utf-8").splitlines()]

    assert summary["total_traces"] == 2
    assert summary["total_llm_calls"] == 18
    assert len(traces) == 2
    assert traces[0]["execution_metadata"]["total_llm_calls"] == 9
    assert traces[0]["agent_intermediate_outputs"]["cross_disciplinary_lens_interpreter"]


def test_workflow_summary_redacts_secret_config_values(tmp_path):
    secret = "test-secret-value-that-must-not-be-written"
    token = "Bearer nested-token-that-must-not-be-written"
    misplaced_token = "Bearer misplaced-token-that-must-not-be-written"

    summary = run_multi_agent_workflow(
        Path.cwd(),
        scope="mvp",
        config={
            "limit": 1,
            "output_dir": tmp_path,
            "api_key": secret,
            "headers": {
                "Authorization": token,
            },
            "notes": misplaced_token,
        },
        model_client=ParsedJsonMockLLMClient(),
    )

    summary_text = json.dumps(summary, ensure_ascii=False)
    summary_file_text = (tmp_path / "workflow_summary.json").read_text(encoding="utf-8")

    assert secret not in summary_text
    assert token not in summary_text
    assert misplaced_token not in summary_text
    assert secret not in summary_file_text
    assert token not in summary_file_text
    assert misplaced_token not in summary_file_text
    assert summary["config"]["api_key"] == "<redacted>"
    assert summary["config"]["headers"]["Authorization"] == "<redacted>"
    assert summary["config"]["notes"] == "<redacted>"


def main():
    """Run smoke tests when executed directly."""
    print("=" * 60)
    print("Multi-Agent System Tests")
    print("=" * 60)

    test_individual_agents()
    test_orchestrator()
    test_message_bus()

    print("\n" + "=" * 60)
    print("ALL TESTS PASSED")
    print("=" * 60)


if __name__ == "__main__":
    main()
