from collections import Counter, defaultdict
import json
from pathlib import Path
from typing import Any

from peer_review_skills.schemas.skill_card import SkillCard


TAXONOMY_VERSION = "v1"
VALIDATED_EXAMPLE_THRESHOLD = 3
MAX_CARDS = 20
VALID_SKILL_CARD_SCOPES = {"mvp", "all"}


CONCERN_NAMES = {
    "baseline_comparison": "Baseline Comparison",
    "generalization_scope": "Generalization Scope",
    "reproducibility_reporting": "Reproducibility Reporting",
    "statistics_significance": "Statistical Support",
    "ablation_mechanism": "Mechanism And Ablation",
    "clarity_presentation": "Presentation Clarity",
    "experimental_design": "Experimental Design",
    "dataset_bias_ethics_safety": "Bias Ethics Safety",
    "theoretical_validity": "Theoretical Validity",
    "novelty_positioning": "Novelty Positioning",
    "unknown": "Unclassified Concern",
}

STRATEGY_PHRASES = {
    "acknowledge_and_fix": "acknowledge the issue and make a concrete revision",
    "clarify_existing_evidence": "clarify the existing evidence",
    "add_new_experiment": "add new experimental evidence",
    "add_new_analysis": "add a targeted new analysis",
    "narrow_claim_scope": "narrow the claim to the evidence",
    "contest_reviewer_premise": "contest the premise with precise rationale",
    "defer_future_work": "defer the request as future work with a clear limitation",
    "justify_method_choice": "justify the method choice",
    "reframe_contribution": "reframe the contribution",
    "editorial_only_change": "make a targeted editorial repair",
    "unknown": "respond with a clearer strategy",
}

EVIDENCE_BY_REQUEST = {
    "baseline": "baseline comparison",
    "ablation": "ablation evidence",
    "experiment": "experimental validation",
    "statistics": "statistical support",
    "data_code": "data or code artifact",
    "clarification": "textual clarification",
    "scope": "scope statement",
    "none": "explicit rationale",
    "unknown": "grounded evidence",
}


def induce_skill_cards(interactions: list[dict[str, Any]]) -> dict[str, Any]:
    groups: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for interaction in interactions:
        if not str(interaction.get("interaction_id") or "").strip():
            continue
        key = (
            str(interaction.get("concern_type") or "unknown"),
            str(interaction.get("author_strategy") or "unknown"),
            str(interaction.get("response_outcome") or "unknown"),
        )
        groups[key].append(interaction)

    cards: list[SkillCard] = []
    rejected_groups = 0
    rejected_reason_counts: Counter[str] = Counter()
    for key, group in sorted(groups.items(), key=lambda item: (-len(item[1]), item[0])):
        concern_type, author_strategy, response_outcome = key
        if concern_type == "unknown" and author_strategy == "unknown":
            rejected_groups += 1
            rejected_reason_counts["unknown_concern_and_strategy"] += 1
            continue
        if not _has_successful_examples(group):
            rejected_groups += 1
            rejected_reason_counts["untrusted_alignment_group"] += 1
            continue
        card = _skill_card_from_group(concern_type, author_strategy, response_outcome, group)
        cards.append(card)
        if len(cards) >= MAX_CARDS:
            break

    return {
        "skill_cards": cards,
        "summary": build_skill_summary(cards, rejected_groups, len(groups), rejected_reason_counts),
    }


def skill_card_output_dir(project_root: str | Path, scope: str) -> Path:
    if scope not in VALID_SKILL_CARD_SCOPES:
        raise ValueError("scope must be 'mvp' or 'all'")
    return Path(project_root) / "data/processed/skill_cards" / scope


def write_skill_card_files(project_root: str | Path, scope: str, cards: list[SkillCard]) -> Path:
    skill_dir = skill_card_output_dir(project_root, scope)
    skill_dir.mkdir(parents=True, exist_ok=True)
    for old_card in skill_dir.glob("*.json"):
        old_card.unlink()
    for card in cards:
        (skill_dir / f"{card.skill_id}.json").write_text(
            json.dumps(card.to_dict(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return skill_dir


def build_skill_summary(
    cards: list[SkillCard],
    rejected_groups: int,
    total_groups: int,
    rejected_reason_counts: Counter[str] | None = None,
) -> dict[str, Any]:
    ready_for_api_enrichment_count = sum(
        1 for card in cards if card.review_recommendation == "ready_for_api_enrichment"
    )
    semantic_enrichment_review_count = sum(
        1
        for card in cards
        if card.review_recommendation == "model_review_required"
        and card.evidence_status == "validated"
        and card.quality_score >= 0.7
    )
    return {
        "skill_card_count": len(cards),
        "validated_count": sum(1 for card in cards if card.evidence_status == "validated"),
        "candidate_count": sum(1 for card in cards if card.evidence_status == "candidate"),
        "ready_for_api_enrichment_count": ready_for_api_enrichment_count,
        "semantic_enrichment_review_count": semantic_enrichment_review_count,
        "rejected_group_count": rejected_groups,
        "untrusted_group_count": int((rejected_reason_counts or {}).get("untrusted_alignment_group", 0)),
        "total_group_count": total_groups,
        "evidence_status_counts": dict(Counter(card.evidence_status for card in cards).most_common()),
        "rejected_reason_counts": dict((rejected_reason_counts or Counter()).most_common()),
    }


def _has_successful_examples(group: list[dict[str, Any]]) -> bool:
    return any(
        item.get("alignment_status") == "matched" and item.get("response_outcome") != "unanswered"
        for item in group
    )


def _skill_card_from_group(
    concern_type: str,
    author_strategy: str,
    response_outcome: str,
    group: list[dict[str, Any]],
) -> SkillCard:
    successes = [
        str(item["interaction_id"])
        for item in group
        if item.get("alignment_status") == "matched" and item.get("response_outcome") != "unanswered"
    ]
    failures = [
        str(item["interaction_id"])
        for item in group
        if item.get("alignment_status") != "matched" or item.get("response_outcome") == "unanswered"
    ]
    evidence_status = "validated" if len(successes) >= VALIDATED_EXAMPLE_THRESHOLD else "candidate"
    evidence_requests = [
        str(item.get("evidence_request") or "unknown")
        for item in group
        if str(item.get("evidence_request") or "unknown") != "unknown"
    ]
    required_evidence = [
        EVIDENCE_BY_REQUEST[request]
        for request in sorted(set(evidence_requests))
        if request in EVIDENCE_BY_REQUEST
    ] or ["grounded evidence"]
    skill_id = f"skill_{_slug(concern_type)}__{_slug(author_strategy)}__{_slug(response_outcome)}"
    concern_name = CONCERN_NAMES.get(concern_type, concern_type.replace("_", " ").title())
    strategy_phrase = STRATEGY_PHRASES.get(author_strategy, author_strategy.replace("_", " "))
    first = group[0]
    quality_metrics = _quality_metrics(group, successes, failures)
    quality_score = _quality_score(quality_metrics)
    return SkillCard(
        skill_id=skill_id,
        name=f"{concern_name}: {author_strategy.replace('_', ' ').title()}",
        definition=(
            f"When reviewers raise {concern_type.replace('_', ' ')} concerns, "
            f"{strategy_phrase} with evidence that directly addresses the request."
        ),
        trigger_pattern=_trigger_pattern(concern_type, first),
        reviewer_intent=_reviewer_intent(concern_type, first),
        recommended_response_strategies=[author_strategy],
        required_evidence_types=required_evidence,
        successful_example_ids=successes[:8],
        failure_example_ids=failures[:5],
        anti_patterns=_anti_patterns(response_outcome, author_strategy),
        notes=(
            f"Rule-derived from {len(group)} aligned interaction(s). "
            "Treat as bootstrap evidence until reviewed by a human or model judge."
        ),
        taxonomy_version=TAXONOMY_VERSION,
        evidence_status=evidence_status,
        quality_score=quality_score,
        quality_metrics=quality_metrics,
        review_recommendation=_review_recommendation(evidence_status, quality_score, response_outcome, author_strategy),
    )


def _trigger_pattern(concern_type: str, interaction: dict[str, Any]) -> str:
    claim = " ".join(str(interaction.get("concern_claim") or "").split())[:180]
    if claim:
        return f"Reviewer language resembling: {claim}"
    return f"Reviewer raises a {concern_type.replace('_', ' ')} concern."


def _reviewer_intent(concern_type: str, interaction: dict[str, Any]) -> str:
    evidence_request = str(interaction.get("evidence_request") or "unknown")
    return (
        f"The reviewer is testing whether the manuscript sufficiently handles "
        f"{concern_type.replace('_', ' ')} and is requesting {evidence_request.replace('_', ' ')}."
    )


def _anti_patterns(response_outcome: str, author_strategy: str) -> list[str]:
    patterns = [
        "Do not answer with a generic thank-you sentence without naming the concrete manuscript change.",
        "Do not cite an interaction unless the response can be traced to a real author unit.",
    ]
    if response_outcome == "unanswered" or author_strategy == "unknown":
        patterns.append("Do not treat this pattern as validated evidence; route similar cases for review.")
    if author_strategy == "defer_future_work":
        patterns.append("Do not defer requested work unless the limitation is explicit and proportionate.")
    return patterns


def _quality_metrics(
    group: list[dict[str, Any]],
    successes: list[str],
    failures: list[str],
) -> dict[str, float | int | str]:
    grounded_count = len(successes) + len(failures)
    matched_count = sum(1 for item in group if item.get("alignment_status") == "matched")
    mean_alignment_confidence = (
        sum(float(item.get("alignment_confidence", 0.0)) for item in group) / len(group)
        if group
        else 0.0
    )
    success_ratio = len(successes) / grounded_count if grounded_count else 0.0
    unique_papers = len({str(item.get("paper_id") or "") for item in group})
    return {
        "grounded_example_count": grounded_count,
        "successful_example_count": len(successes),
        "failure_example_count": len(failures),
        "matched_ratio": matched_count / len(group) if group else 0.0,
        "success_ratio": success_ratio,
        "mean_alignment_confidence": round(mean_alignment_confidence, 4),
        "unique_paper_count": unique_papers,
    }


def _quality_score(metrics: dict[str, float | int | str]) -> float:
    grounded = min(float(metrics["grounded_example_count"]) / 8.0, 1.0)
    successful = min(float(metrics["successful_example_count"]) / 5.0, 1.0)
    matched = float(metrics["matched_ratio"])
    confidence = float(metrics["mean_alignment_confidence"])
    paper_diversity = min(float(metrics["unique_paper_count"]) / 5.0, 1.0)
    score = (
        grounded * 0.2
        + successful * 0.25
        + matched * 0.2
        + confidence * 0.2
        + paper_diversity * 0.15
    )
    return round(min(max(score, 0.0), 1.0), 4)


def _review_recommendation(
    evidence_status: str,
    quality_score: float,
    response_outcome: str,
    author_strategy: str,
) -> str:
    if response_outcome in {"ambiguous", "unanswered"} or author_strategy == "unknown":
        return "model_review_required"
    if evidence_status == "validated" and quality_score >= 0.7:
        return "ready_for_api_enrichment"
    if quality_score >= 0.45:
        return "candidate_review"
    return "hold_for_more_evidence"


def _slug(value: str) -> str:
    slug = []
    for char in value.lower():
        if char.isalnum():
            slug.append(char)
        elif slug and slug[-1] != "_":
            slug.append("_")
    return "".join(slug).strip("_") or "unknown"
