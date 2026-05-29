"""RebuttalLens manuscript-aware frontend agents."""

import json
from typing import Any, Optional

from peer_review_skills.agents.base import (
    BaseAgent,
    attach_refinement_context,
    parse_agent_json_response,
)


class ManuscriptContextExtractorAgent(BaseAgent):
    """Summarizes supplied manuscript context for downstream review interaction agents."""

    def build_prompt(self, inputs: dict[str, Any]) -> list[dict[str, str]]:
        manuscript_context = inputs.get("manuscript_context", {})
        sections = manuscript_context.get("sections", [])
        section_preview = [
            {
                "section_id": section.get("section_id"),
                "heading": section.get("heading"),
                "text_preview": str(section.get("text", ""))[:500],
            }
            for section in sections[:12]
        ]
        return [
            {
                "role": "system",
                "content": (
                    "You are a manuscript context extractor for RebuttalLens, a "
                    "manuscript-aware author rebuttal assistant. Summarize the supplied "
                    "manuscript sections as usable evidence context for reviewer-response "
                    "planning. Do NOT invent manuscript content. Do NOT infer experiments "
                    "that are not present in the supplied text. Return only valid JSON:\n"
                    "{\n"
                    "  \"manuscript_context_note\": {\n"
                    "    \"mode\": \"manuscript_aware|review_only\",\n"
                    "    \"usable_sections\": [\"<section_id>\"],\n"
                    "    \"limits\": [\"<limits of supplied manuscript context>\"]\n"
                    "  },\n"
                    "  \"section_inventory\": [\n"
                    "    {\n"
                    "      \"section_id\": \"<section id>\",\n"
                    "      \"heading\": \"<heading>\",\n"
                    "      \"evidence_role\": \"<what kind of evidence this section may carry>\"\n"
                    "    }\n"
                    "  ],\n"
                    "  \"author_confirmation_questions\": [\"<questions>\"],\n"
                    "  \"reasoning\": \"<brief explanation>\"\n"
                    "}"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(attach_refinement_context({
                    "manuscript_mode": manuscript_context.get("mode", "review_only"),
                    "evidence_boundary": manuscript_context.get("evidence_boundary", {}),
                    "sections": section_preview,
                    "task": "Summarize manuscript context for evidence-grounded rebuttal planning",
                }, inputs), ensure_ascii=False, indent=2),
            },
        ]

    def parse_response(self, response: dict[str, Any]) -> dict[str, Any]:
        return parse_agent_json_response(response)

    def validate_output(self, output: dict[str, Any]) -> tuple[bool, Optional[str]]:
        if "manuscript_context_note" not in output:
            return False, "Missing 'manuscript_context_note' field"
        if "section_inventory" not in output:
            return False, "Missing 'section_inventory' field"
        return True, None


class ManuscriptEvidenceLocatorAgent(BaseAgent):
    """Locates manuscript evidence and gaps for reviewer concerns."""

    def build_prompt(self, inputs: dict[str, Any]) -> list[dict[str, str]]:
        manuscript_context = inputs.get("manuscript_context", {})
        sections = manuscript_context.get("sections", [])
        section_preview = [
            {
                "section_id": section.get("section_id"),
                "heading": section.get("heading"),
                "text_preview": str(section.get("text", ""))[:800],
            }
            for section in sections[:12]
        ]
        return [
            {
                "role": "system",
                "content": (
                    "You are a manuscript evidence locator for RebuttalLens. Given reviewer "
                    "concerns and supplied manuscript context, identify which concerns are "
                    "supported, partially supported, contradicted, or missing in the manuscript. "
                    "Use only supplied manuscript text and prior agent outputs. Do NOT invent "
                    "evidence, experiments, citations, sections, figures, or tables. Every "
                    "evidence action must preserve author confirmation. Return only valid JSON:\n"
                    "{\n"
                    "  \"manuscript_evidence_map\": [\n"
                    "    {\n"
                    "      \"concern_id\": \"<id>\",\n"
                    "      \"status\": \"supported|partially_supported|missing|uncertain\",\n"
                    "      \"section_id\": \"<section id or none>\",\n"
                    "      \"text_evidence\": \"<short supplied text evidence or empty>\",\n"
                    "      \"gap\": \"<what remains unresolved>\"\n"
                    "    }\n"
                    "  ],\n"
                    "  \"evidence_gaps\": [\"<gaps>\"],\n"
                    "  \"author_confirmation_questions\": [\"<questions>\"],\n"
                    "  \"reasoning\": \"<brief explanation>\"\n"
                    "}"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(attach_refinement_context({
                    "review_text": inputs.get("review_text", ""),
                    "concern_map": inputs.get("concern_map", {}),
                    "manuscript_context_note": inputs.get("manuscript_context_note", {}),
                    "manuscript_mode": manuscript_context.get("mode", "review_only"),
                    "sections": section_preview,
                    "task": "Locate manuscript evidence and gaps for reviewer concerns",
                }, inputs), ensure_ascii=False, indent=2),
            },
        ]

    def parse_response(self, response: dict[str, Any]) -> dict[str, Any]:
        return parse_agent_json_response(response)

    def validate_output(self, output: dict[str, Any]) -> tuple[bool, Optional[str]]:
        if "manuscript_evidence_map" not in output:
            return False, "Missing 'manuscript_evidence_map' field"
        if "evidence_gaps" not in output:
            return False, "Missing 'evidence_gaps' field"
        return True, None


class CaseRetrievalInterpreterAgent(BaseAgent):
    """Interprets retrieved Nature cases as bounded analogies."""

    def build_prompt(self, inputs: dict[str, Any]) -> list[dict[str, str]]:
        retrieved_cases = inputs.get("retrieved_cases", [])
        case_preview = [
            {
                "unit_id": case.get("unit_id"),
                "score": case.get("score"),
                "concern_type": case.get("concern_type"),
                "risk_type": case.get("risk_type"),
                "response_strategy": case.get("response_strategy"),
            }
            for case in retrieved_cases[:8]
        ]
        return [
            {
                "role": "system",
                "content": (
                    "You are a Nature case retrieval interpreter for RebuttalLens. Interpret "
                    "retrieved transparent peer-review cases as bounded analogies for the current "
                    "review interaction. Do NOT treat retrieved cases as rules. Do NOT predict "
                    "acceptance or editorial outcomes. Return only valid JSON:\n"
                    "{\n"
                    "  \"case_interpretation\": [\n"
                    "    {\n"
                    "      \"case_id\": \"<retrieved case id>\",\n"
                    "      \"analogy\": \"<why it is relevant>\",\n"
                    "      \"transferable_strategy\": \"<strategy that may transfer>\",\n"
                    "      \"boundary\": \"case analogy only; not outcome prediction\"\n"
                    "    }\n"
                    "  ],\n"
                    "  \"case_use_boundary\": \"<how cases may and may not be used>\",\n"
                    "  \"reasoning\": \"<brief explanation>\"\n"
                    "}"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(attach_refinement_context({
                    "review_text": inputs.get("review_text", ""),
                    "concern_map": inputs.get("concern_map", {}),
                    "risk_interpretation": inputs.get("risk_interpretation", {}),
                    "retrieved_cases": case_preview,
                    "task": "Interpret retrieved cases as bounded Nature peer-review analogies",
                }, inputs), ensure_ascii=False, indent=2),
            },
        ]

    def parse_response(self, response: dict[str, Any]) -> dict[str, Any]:
        return parse_agent_json_response(response)

    def validate_output(self, output: dict[str, Any]) -> tuple[bool, Optional[str]]:
        if "case_interpretation" not in output:
            return False, "Missing 'case_interpretation' field"
        if "case_use_boundary" not in output:
            return False, "Missing 'case_use_boundary' field"
        return True, None


def create_rebuttal_lens_frontend_agents(model_client: Any) -> dict[str, BaseAgent]:
    return {
        "manuscript_context_extractor": ManuscriptContextExtractorAgent(
            "manuscript_context_extractor",
            model_client,
            temperature=0.0,
        ),
        "manuscript_evidence_locator": ManuscriptEvidenceLocatorAgent(
            "manuscript_evidence_locator",
            model_client,
            temperature=0.0,
        ),
        "case_retrieval_interpreter": CaseRetrievalInterpreterAgent(
            "case_retrieval_interpreter",
            model_client,
            temperature=0.0,
        ),
    }
