"""
Specialized Agents - Part 2

Remaining agents: ActorNetworkMapper, CrossDisciplinaryLensInterpreter, IntegrityAdequacyChecker
"""

import json
from typing import Any, Optional

from peer_review_skills.agents.base import (
    BaseAgent,
    attach_refinement_context,
    parse_agent_json_response,
)
from peer_review_skills.agents.specialized_agents import (
    AuthorPositioningAgent,
    EvidenceActionPlannerAgent,
    InstitutionalSignalInterpreterAgent,
    ReviewerUnderstandingAgent,
    TacitConcernInterpreterAgent,
    ToneCommitmentCalibratorAgent,
)


class ActorNetworkMapperAgent(BaseAgent):
    """
    Layer 4: Maps actor networks (human and non-human actors).

    Identifies who/what carries evidence, signals, and commitments.
    """

    def build_prompt(self, inputs: dict[str, Any]) -> list[dict[str, str]]:
        review_text = inputs.get("review_text", "")
        response_text = inputs.get("response_text", "")
        evidence_plan = inputs.get("evidence_plan", {})
        retrieved_cases = inputs.get("retrieved_cases", [])

        return [
            {
                "role": "system",
                "content": (
                    "You are an actor network mapper for an author rebuttal assistant. "
                    "Your task is to identify human and non-human actors in the interaction. "
                    "Actors include: reviewers, authors, editors, figures, datasets, code, benchmarks, citations. "
                    "Map who/what carries evidence, signals, and commitments. "
                    "Do NOT reduce to simple social causality. "
                    "Do NOT replace author/reviewer/editor judgment. "
                    "Return only valid JSON with the following structure:\n"
                    "{\n"
                    "  \"actor_network_note\": [\n"
                    "    {\n"
                    "      \"actor_type\": \"<human|figure|dataset|code|benchmark|citation|other>\",\n"
                    "      \"actor_id\": \"<identifier>\",\n"
                    "      \"role\": \"<what this actor carries>\",\n"
                    "      \"evidence_link\": \"<how this relates to evidence plan>\"\n"
                    "    }\n"
                    "  ],\n"
                    "  \"retrieved_case_ids\": [\"<case IDs>\"],\n"
                    "  \"boundary\": \"Observable alignment only; not causal claims.\",\n"
                    "  \"reasoning\": \"<brief explanation>\"\n"
                    "}"
                )
            },
            {
                "role": "user",
                "content": json.dumps(attach_refinement_context({
                    "review_text": review_text,
                    "response_text": response_text,
                    "evidence_plan": evidence_plan,
                    "retrieved_cases": [c.get("unit_id") for c in retrieved_cases[:5]],
                    "task": "Map actor network"
                }, inputs), ensure_ascii=False, indent=2)
            }
        ]

    def parse_response(self, response: dict[str, Any]) -> dict[str, Any]:
        return parse_agent_json_response(response)

    def validate_output(self, output: dict[str, Any]) -> tuple[bool, Optional[str]]:
        if "actor_network_note" not in output:
            return False, "Missing 'actor_network_note' field"
        return True, None


class CrossDisciplinaryLensInterpreterAgent(BaseAgent):
    """
    Layer 4: Applies cross-disciplinary theoretical lenses.

    Interprets the interaction through 6 theoretical frameworks.
    """

    def build_prompt(self, inputs: dict[str, Any]) -> list[dict[str, str]]:
        all_outputs = inputs.get("all_agent_outputs", {})
        unit = inputs.get("unit", {})
        retrieval = inputs.get("retrieval", {})

        return [
            {
                "role": "system",
                "content": (
                    "You are a cross-disciplinary lens interpreter for an author rebuttal assistant. "
                    "Your task is to apply 6 theoretical lenses to the interaction:\n"
                    "1. Tacit Knowledge Boundary (默会知识边界)\n"
                    "2. Institutional Dependence (制度依赖)\n"
                    "3. Actor Network Alignment (行动者网络对齐)\n"
                    "4. Fast-Slow Cognitive Correction (快慢思维校正)\n"
                    "5. Emotion-Tone-Commitment Calibration (情绪-语气-承诺校准)\n"
                    "6. Author Agency Gate (作者主体性门控)\n\n"
                    "For each lens, explain:\n"
                    "- Observable trace in this interaction\n"
                    "- System action taken\n"
                    "- Boundary (what the system does NOT claim)\n"
                    "- Evaluation question\n\n"
                    "Use only the provided unit text, prior agent outputs, retrieved Nature cases, "
                    "and provenance. Do NOT infer private reviewer psychology, reviewer motives, "
                    "acceptance probability, or hidden institutional decisions. Do NOT suggest "
                    "manipulating reviewer motivations. Frame each lens as support for author "
                    "reflection, evidence planning, and integrity checking.\n\n"
                    "Return only valid JSON with the following structure:\n"
                    "{\n"
                    "  \"lens_interpretations\": {\n"
                    "    \"tacit_knowledge_boundary\": {...},\n"
                    "    \"institutional_dependence\": {...},\n"
                    "    \"actor_network_alignment\": {...},\n"
                    "    \"fast_slow_cognitive_correction\": {...},\n"
                    "    \"emotion_tone_commitment_calibration\": {...},\n"
                    "    \"author_agency_gate\": {...}\n"
                    "  },\n"
                    "  \"reasoning\": \"<brief explanation>\"\n"
                    "}"
                )
            },
            {
                "role": "user",
                "content": json.dumps(attach_refinement_context({
                    "all_agent_outputs": all_outputs,
                    "unit": {
                        "unit_id": unit.get("unit_id"),
                        "concern_type": unit.get("concern_type"),
                        "risk_type": unit.get("risk_type"),
                        "tacit_concern": unit.get("tacit_concern"),
                        "institutional_signal": unit.get("institutional_signal"),
                        "provenance": unit.get("provenance", {}),
                    },
                    "retrieved_case_ids": [
                        case.get("unit_id")
                        for case in (retrieval.get("top_k") or [])[:5]
                        if case.get("unit_id")
                    ],
                    "task": "Apply 6 cross-disciplinary lenses"
                }, inputs), ensure_ascii=False, indent=2)
            }
        ]

    def parse_response(self, response: dict[str, Any]) -> dict[str, Any]:
        return parse_agent_json_response(response)

    def validate_output(self, output: dict[str, Any]) -> tuple[bool, Optional[str]]:
        if "lens_interpretations" not in output:
            return False, "Missing 'lens_interpretations' field"

        required_lenses = [
            "tacit_knowledge_boundary",
            "institutional_dependence",
            "actor_network_alignment",
            "fast_slow_cognitive_correction",
            "emotion_tone_commitment_calibration",
            "author_agency_gate"
        ]

        lenses = output["lens_interpretations"]
        missing = [lens for lens in required_lenses if lens not in lenses]

        if missing:
            return False, f"Missing lenses: {missing}"

        disallowed_markers = [
            "private reviewer psychology",
            "reviewer motive",
            "reviewer motivation",
            "perceptual bias",
            "perceptual biases",
            "fast thinking",
            "cognitive error",
            "manipulate reviewer",
            "counter reviewer bias",
            "acceptance probability",
        ]
        serialized = json.dumps(lenses, ensure_ascii=False).lower()
        for marker in disallowed_markers:
            if marker in serialized:
                return False, (
                    "Cross-disciplinary lens output must avoid private psychology, "
                    f"manipulation, or acceptance-prediction language: {marker}"
                )

        return True, None


class IntegrityAdequacyCheckerAgent(BaseAgent):
    """
    Layer 5: Checks integrity and adequacy of the complete workflow.

    Final quality control and responsible use warnings.
    """

    def build_prompt(self, inputs: dict[str, Any]) -> list[dict[str, str]]:
        all_outputs = inputs.get("all_agent_outputs", {})
        unit = inputs.get("unit", {})

        return [
            {
                "role": "system",
                "content": (
                    "You are an integrity and adequacy checker for an author rebuttal assistant. "
                    "Your task is to perform final quality control on all agent outputs. "
                    "Check for:\n"
                    "- Provenance: Are all claims traceable to source text?\n"
                    "- Adequacy: Is the response plan sufficient?\n"
                    "- Safety: Are there unsupported commitments or overclaims?\n"
                    "- Boundaries: Are all responsible use warnings present?\n"
                    "- Author agency: Is author confirmation required?\n\n"
                    "CRITICAL BOUNDARIES:\n"
                    "- This is NOT final rebuttal text\n"
                    "- Do NOT predict acceptance probability\n"
                    "- Do NOT invent experiments, data, or citations\n"
                    "- Author must verify all claims\n\n"
                    "Return only valid JSON with the following structure:\n"
                    "{\n"
                    "  \"adequacy_report\": [\n"
                    "    \"<adequacy assessment>\"\n"
                    "  ],\n"
                    "  \"response_adequacy\": {\n"
                    "    \"is_adequate\": true|false,\n"
                    "    \"missing_elements\": [\"<what's missing>\"],\n"
                    "    \"strengths\": [\"<what's good>\"]\n"
                    "  },\n"
                    "  \"provenance_checks\": [\n"
                    "    {\n"
                    "      \"claim\": \"<claim made>\",\n"
                    "      \"source\": \"<source in unit>\",\n"
                    "      \"traceable\": true|false\n"
                    "    }\n"
                    "  ],\n"
                    "  \"responsible_use_warnings\": [\n"
                    "    \"assistant_only\",\n"
                    "    \"author_must_verify_all_claims\",\n"
                    "    \"not_final_rebuttal_text\",\n"
                    "    \"no_acceptance_prediction\"\n"
                    "  ],\n"
                    "  \"issues\": [\n"
                    "    {\n"
                    "      \"severity\": \"critical|warning|info\",\n"
                    "      \"agent_id\": \"<which agent>\",\n"
                    "      \"description\": \"<issue description>\"\n"
                    "    }\n"
                    "  ],\n"
                    "  \"reasoning\": \"<brief explanation>\"\n"
                    "}"
                )
            },
            {
                "role": "user",
                "content": json.dumps(attach_refinement_context({
                    "all_agent_outputs": all_outputs,
                    "unit": {
                        "unit_id": unit.get("unit_id"),
                        "review_text": unit.get("review_text", "")[:200],
                        "response_text": unit.get("response_text", "")[:200],
                        "provenance": unit.get("provenance", {}),
                        "manuscript_context": {
                            "mode": unit.get("manuscript_context", {}).get("mode"),
                            "section_count": unit.get("manuscript_context", {}).get("section_count"),
                            "evidence_boundary": unit.get("manuscript_context", {}).get(
                                "evidence_boundary", {}
                            ),
                        },
                    },
                    "task": "Check integrity and adequacy"
                }, inputs), ensure_ascii=False, indent=2)
            }
        ]

    def parse_response(self, response: dict[str, Any]) -> dict[str, Any]:
        return parse_agent_json_response(response)

    def validate_output(self, output: dict[str, Any]) -> tuple[bool, Optional[str]]:
        required_fields = [
            "adequacy_report",
            "response_adequacy",
            "provenance_checks",
            "responsible_use_warnings"
        ]

        missing = [field for field in required_fields if field not in output]
        if missing:
            return False, f"Missing required fields: {missing}"

        # Check responsible use warnings
        required_warnings = [
            "assistant_only",
            "author_must_verify_all_claims"
        ]
        warnings = output.get("responsible_use_warnings", [])
        missing_warnings = [w for w in required_warnings if w not in warnings]

        if missing_warnings:
            return False, f"Missing required warnings: {missing_warnings}"

        return True, None


# Agent factory function
def create_all_specialized_agents(model_client: Any) -> dict[str, BaseAgent]:
    """
    Create all 9 specialized agents.

    Args:
        model_client: OpenAI-compatible client

    Returns:
        Dictionary mapping agent_id to agent instance
    """
    return {
        "reviewer_understanding_agent": ReviewerUnderstandingAgent(
            "reviewer_understanding_agent",
            model_client,
            temperature=0.0
        ),
        "tacit_concern_interpreter": TacitConcernInterpreterAgent(
            "tacit_concern_interpreter",
            model_client,
            temperature=0.0
        ),
        "institutional_signal_interpreter": InstitutionalSignalInterpreterAgent(
            "institutional_signal_interpreter",
            model_client,
            temperature=0.0
        ),
        "evidence_action_planner": EvidenceActionPlannerAgent(
            "evidence_action_planner",
            model_client,
            temperature=0.0
        ),
        "author_positioning_agent": AuthorPositioningAgent(
            "author_positioning_agent",
            model_client,
            temperature=0.0
        ),
        "tone_commitment_calibrator": ToneCommitmentCalibratorAgent(
            "tone_commitment_calibrator",
            model_client,
            temperature=0.0
        ),
        "actor_network_mapper": ActorNetworkMapperAgent(
            "actor_network_mapper",
            model_client,
            temperature=0.0
        ),
        "cross_disciplinary_lens_interpreter": CrossDisciplinaryLensInterpreterAgent(
            "cross_disciplinary_lens_interpreter",
            model_client,
            temperature=0.0
        ),
        "integrity_adequacy_checker": IntegrityAdequacyCheckerAgent(
            "integrity_adequacy_checker",
            model_client,
            temperature=0.0
        ),
    }
