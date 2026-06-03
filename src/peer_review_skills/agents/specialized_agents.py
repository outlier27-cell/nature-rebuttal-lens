"""
Specialized Agents for Review Interaction Analysis

This module implements the 9 specialized agents for the multi-agent workflow.
Each agent is an independent LLM-based reasoning unit.
"""

from typing import Any, Optional

import json

from peer_review_skills.agents.base import (
    BaseAgent,
    attach_refinement_context,
    parse_agent_json_response,
    require_bool_in_list_items,
    require_field,
    require_list_item_fields,
    require_list_items,
    require_optional_field,
)


def _taxonomy_context(inputs: dict[str, Any]) -> dict[str, Any]:
    taxonomies = inputs.get("taxonomies") or {}
    if not isinstance(taxonomies, dict):
        return {}
    return taxonomies


class ReviewerUnderstandingAgent(BaseAgent):
    """
    Layer 1: Understands what the reviewer is asking for.

    Identifies concern types and maps them to taxonomy.
    """

    def build_prompt(self, inputs: dict[str, Any]) -> list[dict[str, str]]:
        review_text = inputs.get("review_text", "")
        taxonomies = _taxonomy_context(inputs)
        concern_taxonomy = taxonomies.get("concern_taxonomy", {})

        return [
            {
                "role": "system",
                "content": (
                    "You are a reviewer understanding agent for an author rebuttal assistant. "
                    "Your task is to identify what the reviewer is asking for. "
                    "Use the provided concern taxonomy when possible. "
                    "Ground your analysis in observable review text. "
                    "Do not infer private reviewer intent or psychology. "
                    "Return only valid JSON with the following structure:\n"
                    "{\n"
                    "  \"concern_map\": [\n"
                    "    {\n"
                    "      \"concern_id\": \"<stable id such as R1.1 or concern_001>\",\n"
                    "      \"severity\": \"minor|major|blocking|unclear\",\n"
                    "      \"category\": \"editorial_presentation|evidence_interpretation|methodological|statistical|data_code_materials|citation_positioning|scope_feasibility|ethics_compliance|unclear\",\n"
                    "      \"concern_type\": \"<taxonomy label>\",\n"
                    "      \"surface_request\": \"<what reviewer explicitly asks>\",\n"
                    "      \"text_evidence\": \"<quote from review>\",\n"
                    "      \"confidence\": \"high|medium|low\"\n"
                    "    }\n"
                    "  ],\n"
                    "  \"reasoning\": \"<brief explanation>\"\n"
                    "}"
                )
            },
            {
                "role": "user",
                "content": json.dumps(attach_refinement_context({
                    "review_text": review_text,
                    "concern_taxonomy": concern_taxonomy,
                    "task": "Identify reviewer concerns and map to taxonomy"
                }, inputs), ensure_ascii=False, indent=2)
            }
        ]

    def parse_response(self, response: dict[str, Any]) -> dict[str, Any]:
        return parse_agent_json_response(response)

    def validate_output(self, output: dict[str, Any]) -> tuple[bool, Optional[str]]:
        if "concern_map" not in output:
            return False, "Missing 'concern_map' field"
        if not isinstance(output["concern_map"], list):
            return False, "'concern_map' must be a list"
        return True, None


class TacitConcernInterpreterAgent(BaseAgent):
    """
    Layer 1: Interprets implicit risks and tacit concerns.

    Identifies what the reviewer might be worried about beyond explicit text.
    """

    def build_prompt(self, inputs: dict[str, Any]) -> list[dict[str, str]]:
        review_text = inputs.get("review_text", "")
        concern_map = inputs.get("concern_map", {})
        taxonomies = _taxonomy_context(inputs)
        risk_taxonomy = taxonomies.get("risk_type", {})
        tacit_taxonomy = taxonomies.get("tacit_concern", {})

        return [
            {
                "role": "system",
                "content": (
                    "You are a tacit concern interpreter for an author rebuttal assistant. "
                    "Your task is to identify implicit risks that the reviewer signals. "
                    "Use the provided risk and tacit concern taxonomies. "
                    "Ground your interpretation in observable textual traces. "
                    "Do not claim to know the reviewer's true psychology. "
                    "Return only valid JSON with the following structure:\n"
                    "{\n"
                    "  \"risk_interpretation\": [\n"
                    "    {\n"
                    "      \"risk_type\": \"<taxonomy label>\",\n"
                    "      \"tacit_concern\": \"<taxonomy label>\",\n"
                    "      \"observable_trace\": \"<textual evidence>\",\n"
                    "      \"boundary\": \"Observable textual trace only; not a claim about reviewer psychology.\"\n"
                    "    }\n"
                    "  ],\n"
                    "  \"reasoning\": \"<brief explanation>\"\n"
                    "}"
                )
            },
            {
                "role": "user",
                "content": json.dumps(attach_refinement_context({
                    "review_text": review_text,
                    "concern_map": concern_map,
                    "risk_taxonomy": risk_taxonomy,
                    "tacit_concern_taxonomy": tacit_taxonomy,
                    "task": "Identify implicit risks and tacit concerns"
                }, inputs), ensure_ascii=False, indent=2)
            }
        ]

    def parse_response(self, response: dict[str, Any]) -> dict[str, Any]:
        return parse_agent_json_response(response)

    def validate_output(self, output: dict[str, Any]) -> tuple[bool, Optional[str]]:
        error = require_field(output, "risk_interpretation", list)
        if error:
            return False, error
        error = require_list_item_fields(
            output["risk_interpretation"],
            "risk_interpretation",
            {
                "risk_type": str,
                "tacit_concern": str,
                "observable_trace": str,
                "boundary": str,
            },
        )
        if error:
            return False, error
        return True, None


class InstitutionalSignalInterpreterAgent(BaseAgent):
    """
    Layer 2: Interprets institutional and editorial signals.

    Identifies journal norms, transparency requirements, and editorial context.
    """

    def build_prompt(self, inputs: dict[str, Any]) -> list[dict[str, str]]:
        review_text = inputs.get("review_text", "")
        concern_map = inputs.get("concern_map", {})
        taxonomies = _taxonomy_context(inputs)
        institutional_taxonomy = taxonomies.get("institutional_signal", {})

        return [
            {
                "role": "system",
                "content": (
                    "You are an institutional signal interpreter for an author rebuttal assistant. "
                    "Your task is to identify institutional and editorial signals in the review. "
                    "Consider: journal scope, transparency norms, community standards, editorial expectations. "
                    "Use the provided institutional signal taxonomy. "
                    "Do NOT predict acceptance rates. "
                    "Do NOT interpret politeness as institutional pressure. "
                    "Return only valid JSON with the following structure:\n"
                    "{\n"
                    "  \"institutional_signal_note\": [\n"
                    "    {\n"
                    "      \"institutional_signal\": \"<taxonomy label>\",\n"
                    "      \"action_link\": \"<how this translates to author choices>\",\n"
                    "      \"boundary\": \"Not an acceptance prediction; author judgment required.\"\n"
                    "    }\n"
                    "  ],\n"
                    "  \"reasoning\": \"<brief explanation>\"\n"
                    "}"
                )
            },
            {
                "role": "user",
                "content": json.dumps(attach_refinement_context({
                    "review_text": review_text,
                    "concern_map": concern_map,
                    "institutional_taxonomy": institutional_taxonomy,
                    "task": "Identify institutional and editorial signals"
                }, inputs), ensure_ascii=False, indent=2)
            }
        ]

    def parse_response(self, response: dict[str, Any]) -> dict[str, Any]:
        return parse_agent_json_response(response)

    def validate_output(self, output: dict[str, Any]) -> tuple[bool, Optional[str]]:
        error = require_field(output, "institutional_signal_note", list)
        if error:
            return False, error
        error = require_list_item_fields(
            output["institutional_signal_note"],
            "institutional_signal_note",
            {
                "institutional_signal": str,
                "action_link": str,
                "boundary": str,
            },
        )
        if error:
            return False, error
        return True, None


class EvidenceActionPlannerAgent(BaseAgent):
    """
    Layer 2: Plans evidence actions needed to address concerns.

    Determines what evidence, experiments, or artifacts are needed.
    """

    def build_prompt(self, inputs: dict[str, Any]) -> list[dict[str, str]]:
        concern_map = inputs.get("concern_map", {})
        risk_interpretation = inputs.get("risk_interpretation", {})
        retrieved_cases = inputs.get("retrieved_cases", [])
        manuscript_evidence = inputs.get("manuscript_evidence", {})
        case_interpretation = inputs.get("case_interpretation", {})
        taxonomies = _taxonomy_context(inputs)
        evidence_taxonomy = taxonomies.get("evidence_action", {})

        return [
            {
                "role": "system",
                "content": (
                    "You are an evidence action planner for an author rebuttal assistant. "
                    "Your task is to determine what evidence actions are needed to address reviewer concerns. "
                    "Use the provided evidence action taxonomy, manuscript evidence map, "
                    "and retrieved case interpretation. "
                    "Ground your plan in what evidence can actually be provided. "
                    "Do NOT invent experiments, data, or citations. "
                    "All evidence actions require author confirmation. "
                    "Use Nature-response action hints when useful: ACCEPT_TEXT, "
                    "ACCEPT_ANALYSIS, ACCEPT_EXPERIMENT, ACCEPT_FIGURE, "
                    "CLARIFY_EXISTING, ADD_CITATION, SOFTEN_CLAIM, PARTIAL, "
                    "DISAGREE, OUT_OF_SCOPE, AUTHOR_INPUT_NEEDED, BLOCKING. "
                    "If the author only says \"we revised it\" without location and "
                    "details, use AUTHOR_INPUT_NEEDED. If a central claim remains "
                    "unsupported, use SOFTEN_CLAIM or BLOCKING. Do not mark "
                    "ACCEPT_ANALYSIS, ACCEPT_EXPERIMENT, ACCEPT_FIGURE, or "
                    "ADD_CITATION unless the artifact is supplied or explicitly "
                    "marked as missing author input. "
                    "Return only valid JSON with the following structure:\n"
                    "{\n"
                    "  \"evidence_action_plan\": [\n"
                    "    {\n"
                    "      \"action_type\": \"<taxonomy label>\",\n"
                    "      \"required_artifact\": \"<what is needed>\",\n"
                    "      \"supporting_case_ids\": [\"<case IDs from retrieved cases>\"],\n"
                    "      \"requires_author_confirmation\": true,\n"
                    "      \"nature_action_hint\": \"ACCEPT_TEXT|ACCEPT_ANALYSIS|ACCEPT_EXPERIMENT|ACCEPT_FIGURE|CLARIFY_EXISTING|ADD_CITATION|SOFTEN_CLAIM|PARTIAL|DISAGREE|OUT_OF_SCOPE|AUTHOR_INPUT_NEEDED|BLOCKING\",\n"
                    "      \"missing_author_input\": [\"<specific missing author fact>\"],\n"
                    "      \"evidence_anchor\": \"<section id, figure, table, citation id, or empty>\"\n"
                    "    }\n"
                    "  ],\n"
                    "  \"author_confirmation_questions\": [\"<questions for author>\"],\n"
                    "  \"reasoning\": \"<brief explanation>\"\n"
                    "}"
                )
            },
            {
                "role": "user",
                "content": json.dumps(attach_refinement_context({
                    "concern_map": concern_map,
                    "risk_interpretation": risk_interpretation,
                    "retrieved_cases": retrieved_cases[:5],  # Top 5 cases
                    "manuscript_evidence": manuscript_evidence,
                    "case_interpretation": case_interpretation,
                    "evidence_taxonomy": evidence_taxonomy,
                    "task": "Plan evidence actions to address concerns"
                }, inputs), ensure_ascii=False, indent=2)
            }
        ]

    def parse_response(self, response: dict[str, Any]) -> dict[str, Any]:
        return parse_agent_json_response(response)

    def validate_output(self, output: dict[str, Any]) -> tuple[bool, Optional[str]]:
        error = require_field(output, "evidence_action_plan", list)
        if error:
            return False, error
        error = require_bool_in_list_items(
            output["evidence_action_plan"],
            "evidence_action_plan",
            "requires_author_confirmation",
        )
        if error:
            return False, error
        error = require_optional_field(output, "author_confirmation_questions", list)
        if error:
            return False, error
        return True, None


class AuthorPositioningAgent(BaseAgent):
    """
    Layer 3: Determines author positioning options.

    Identifies how the author can position their response (acknowledge, defend, etc.).
    """

    def build_prompt(self, inputs: dict[str, Any]) -> list[dict[str, str]]:
        response_text = inputs.get("response_text", "")
        evidence_plan = inputs.get("evidence_plan", {})
        taxonomies = _taxonomy_context(inputs)
        positioning_taxonomy = taxonomies.get("author_positioning", {})

        return [
            {
                "role": "system",
                "content": (
                    "You are an author positioning agent for an author rebuttal assistant. "
                    "Your task is to identify how the author positions their response. "
                    "Use the provided author positioning taxonomy. "
                    "Offer options for author judgment; do not force concession. "
                    "Return only valid JSON with the following structure:\n"
                    "{\n"
                    "  \"author_positioning\": [\n"
                    "    {\n"
                    "      \"position\": \"<taxonomy label>\",\n"
                    "      \"stance_boundary\": \"Offer options for author judgment; do not force concession.\",\n"
                    "      \"alternative_positions\": [\"<other options>\"]\n"
                    "    }\n"
                    "  ],\n"
                    "  \"reasoning\": \"<brief explanation>\"\n"
                    "}"
                )
            },
            {
                "role": "user",
                "content": json.dumps(attach_refinement_context({
                    "response_text": response_text,
                    "evidence_plan": evidence_plan,
                    "positioning_taxonomy": positioning_taxonomy,
                    "task": "Identify author positioning options"
                }, inputs), ensure_ascii=False, indent=2)
            }
        ]

    def parse_response(self, response: dict[str, Any]) -> dict[str, Any]:
        return parse_agent_json_response(response)

    def validate_output(self, output: dict[str, Any]) -> tuple[bool, Optional[str]]:
        error = require_field(output, "author_positioning", list)
        if error:
            return False, error
        error = require_list_item_fields(
            output["author_positioning"],
            "author_positioning",
            {
                "position": str,
                "stance_boundary": str,
                "alternative_positions": list,
            },
        )
        if error:
            return False, error
        return True, None


class ToneCommitmentCalibratorAgent(BaseAgent):
    """
    Layer 3: Calibrates tone and commitment levels.

    Ensures tone is appropriate and commitments are not overstated.
    """

    def build_prompt(self, inputs: dict[str, Any]) -> list[dict[str, str]]:
        response_text = inputs.get("response_text", "")
        evidence_plan = inputs.get("evidence_plan", {})
        author_positioning = inputs.get("author_positioning", {})
        taxonomies = _taxonomy_context(inputs)
        tone_taxonomy = taxonomies.get("tone_commitment", {})

        return [
            {
                "role": "system",
                "content": (
                    "You are a tone and commitment calibrator for an author rebuttal assistant. "
                    "Your task is to assess tone appropriateness and commitment safety. "
                    "Use the provided tone/commitment taxonomy. "
                    "Flag: defensive tone, unsupported commitments, overclaiming, excessive concession. "
                    "Do NOT diagnose author or reviewer emotions. "
                    "Do NOT use gentle tone as substitute for evidence. "
                    "Return only valid JSON with the following structure:\n"
                    "{\n"
                    "  \"tone_commitment_warnings\": [\n"
                    "    {\n"
                    "      \"tone\": \"<taxonomy label>\",\n"
                    "      \"commitment_level\": \"<taxonomy label>\",\n"
                    "      \"risk_flags\": [\"<issues found>\"],\n"
                    "      \"boundary\": \"Not a psychological diagnosis; observable text only.\"\n"
                    "    }\n"
                    "  ],\n"
                    "  \"reasoning\": \"<brief explanation>\"\n"
                    "}"
                )
            },
            {
                "role": "user",
                "content": json.dumps(attach_refinement_context({
                    "response_text": response_text,
                    "evidence_plan": evidence_plan,
                    "author_positioning": author_positioning,
                    "tone_taxonomy": tone_taxonomy,
                    "task": "Calibrate tone and commitment levels"
                }, inputs), ensure_ascii=False, indent=2)
            }
        ]

    def parse_response(self, response: dict[str, Any]) -> dict[str, Any]:
        return parse_agent_json_response(response)

    def validate_output(self, output: dict[str, Any]) -> tuple[bool, Optional[str]]:
        error = require_field(output, "tone_commitment_warnings", list)
        if error:
            return False, error
        error = require_list_item_fields(
            output["tone_commitment_warnings"],
            "tone_commitment_warnings",
            {
                "tone": str,
                "commitment_level": str,
                "risk_flags": list,
                "boundary": str,
            },
        )
        if error:
            return False, error
        return True, None


# Continue in next file due to length...
