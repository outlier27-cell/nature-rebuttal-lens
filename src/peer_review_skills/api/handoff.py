from typing import Any


def build_api_handoff(
    interactions: list[dict[str, Any]],
    skill_cards: list[dict[str, Any]],
    review_units: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    author_units_by_paper = _author_units_by_paper(review_units or [])
    alignment_requests = [
        _alignment_request(record, author_units_by_paper.get(str(record.get("paper_id") or ""), []))
        for record in interactions
        if record.get("alignment_status") in {"ambiguous", "missing_response", "unsupported"}
    ]
    skill_enrichment_requests = [
        _skill_enrichment_request(record)
        for record in skill_cards
        if _needs_skill_semantic_enrichment(record)
    ]
    summary = {
        "alignment_request_count": len(alignment_requests),
        "skill_enrichment_request_count": len(skill_enrichment_requests),
        "total_request_count": len(alignment_requests) + len(skill_enrichment_requests),
        "alignment_response_contract": {
            "interaction_id": "string",
            "alignment_status": "matched|ambiguous|missing_response|unsupported",
            "selected_author_unit_ids": "list[string]",
            "rationale": "string",
            "confidence": "float 0..1",
        },
        "skill_enrichment_response_contract": {
            "skill_id": "string",
            "concern_type": "taxonomy label",
            "recommended_response_strategies": "list[taxonomy label]",
            "rationale": "string",
            "confidence": "float 0..1",
        },
    }
    return {
        "summary": summary,
        "alignment_requests": alignment_requests,
        "skill_enrichment_requests": skill_enrichment_requests,
    }


def render_api_handoff_report(summary: dict[str, Any]) -> str:
    return (
        "# API Handoff Report\n\n"
        "## Summary\n\n"
        f"- Alignment request count: {summary['alignment_request_count']}\n"
        f"- Skill enrichment request count: {summary['skill_enrichment_request_count']}\n"
        f"- Total request count: {summary['total_request_count']}\n\n"
        "## Alignment Response Contract\n\n"
        + _render_contract(summary["alignment_response_contract"])
        + "\n"
        "## Skill Enrichment Response Contract\n\n"
        + _render_contract(summary["skill_enrichment_response_contract"])
    )


def _alignment_request(record: dict[str, Any], paper_author_units: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "request_id": f"alignment::{record.get('interaction_id')}",
        "task_type": "resolve_interaction_alignment",
        "interaction_id": record.get("interaction_id"),
        "paper_id": record.get("paper_id"),
        "alignment_status": record.get("alignment_status"),
        "alignment_method": record.get("alignment_method"),
        "review_unit_ids": record.get("review_unit_ids", []),
        "candidate_author_unit_ids": record.get("author_unit_ids", []),
        "review_span_text": record.get("review_span_text", ""),
        "candidate_author_response_text": record.get("author_response_text", ""),
        "author_search_context": _author_search_context(record, paper_author_units),
        "concern_type": record.get("concern_type", "unknown"),
        "concern_claim": record.get("concern_claim", ""),
        "evidence_request": record.get("evidence_request", "unknown"),
        "source_trace": record.get("source_trace", {}),
    }


def _author_units_by_paper(review_units: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    by_paper: dict[str, list[dict[str, Any]]] = {}
    for unit in review_units:
        if unit.get("speaker_type") != "author":
            continue
        by_paper.setdefault(str(unit.get("paper_id") or ""), []).append(unit)
    return by_paper


def _author_search_context(
    record: dict[str, Any],
    paper_author_units: list[dict[str, Any]],
    limit: int = 12,
) -> list[dict[str, Any]]:
    candidate_ids = {str(unit_id) for unit_id in record.get("author_unit_ids", [])}
    selected = []
    for unit in paper_author_units:
        if candidate_ids and str(unit.get("unit_id")) not in candidate_ids:
            continue
        selected.append(unit)
    if not selected and record.get("alignment_status") == "missing_response":
        selected = paper_author_units
    return [
        {
            "unit_id": unit.get("unit_id"),
            "speaker_id": unit.get("speaker_id"),
            "text": str(unit.get("text") or "")[:1200],
            "source_trace": unit.get("source_trace", {}),
        }
        for unit in selected[:limit]
    ]


def _skill_enrichment_request(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "request_id": f"skill_semantics::{record.get('skill_id')}",
        "task_type": "enrich_skill_semantics",
        "skill_id": record.get("skill_id"),
        "name": record.get("name"),
        "definition": record.get("definition"),
        "trigger_pattern": record.get("trigger_pattern"),
        "reviewer_intent": record.get("reviewer_intent"),
        "recommended_response_strategies": record.get("recommended_response_strategies", []),
        "required_evidence_types": record.get("required_evidence_types", []),
        "successful_example_ids": record.get("successful_example_ids", []),
        "quality_score": record.get("quality_score"),
        "quality_metrics": record.get("quality_metrics", {}),
    }


def _needs_skill_semantic_enrichment(record: dict[str, Any]) -> bool:
    if record.get("review_recommendation") != "model_review_required":
        return False
    if record.get("evidence_status") != "validated":
        return False
    if float(record.get("quality_score", 0.0)) < 0.7:
        return False
    skill_id = str(record.get("skill_id") or "")
    strategies = [str(item) for item in record.get("recommended_response_strategies", [])]
    return "unknown" in skill_id or "unknown" in strategies


def _render_contract(contract: dict[str, Any]) -> str:
    return "\n".join(f"- {key}: {value}" for key, value in contract.items()) + "\n"
