import json
from pathlib import Path
from typing import Any

from peer_review_skills.io.jsonl import read_jsonl
from peer_review_skills.schemas.interaction_unit import InteractionUnit
from peer_review_skills.schemas.skill_card import SkillCard


def judge_artifacts(project_root: str | Path = ".", scope: str = "mvp") -> dict[str, Any]:
    root = Path(project_root)
    review_units_path = root / "data/processed/review_units/review_unit_index.jsonl"
    if not review_units_path.exists():
        review_units_path = root / "data/processed/review_units/review_units.jsonl"
    interactions_path = root / "data/processed/interaction_units/interaction_units.jsonl"
    skill_cards_dir = _skill_cards_dir(root, scope)

    review_unit_ids = _load_review_unit_ids(review_units_path)
    interactions = list(read_jsonl(interactions_path)) if interactions_path.exists() else []
    skill_cards = _load_skill_card_records(skill_cards_dir)

    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    accepted_interactions: list[dict[str, Any]] = []
    rejected_interactions: list[dict[str, Any]] = []
    interaction_ids: set[str] = set()

    for record in interactions:
        interaction_errors, interaction_warnings = _judge_interaction(record, review_unit_ids)
        errors.extend(interaction_errors)
        warnings.extend(interaction_warnings)
        if interaction_errors:
            rejected_interactions.append(record)
        else:
            accepted_interactions.append(record)
            interaction_ids.add(str(record.get("interaction_id")))

    accepted_skill_cards: list[dict[str, Any]] = []
    rejected_skill_cards: list[dict[str, Any]] = []
    skill_cards_for_review: list[dict[str, Any]] = []
    for record in skill_cards:
        card_errors, card_warnings = _judge_skill_card(record, interaction_ids)
        errors.extend(card_errors)
        warnings.extend(card_warnings)
        if card_errors:
            rejected_skill_cards.append(record)
        else:
            accepted_skill_cards.append(record)
            clean_record = {key: value for key, value in record.items() if not key.startswith("_")}
            recommendation = str(clean_record.get("review_recommendation") or "")
            quality_score = float(clean_record.get("quality_score", 0.0))
            if recommendation != "ready_for_api_enrichment" or quality_score < 0.7:
                skill_cards_for_review.append(clean_record)

    summary = {
        "review_unit_count": len(review_unit_ids),
        "interaction_count": len(interactions),
        "skill_card_count": len(skill_cards),
        "accepted_interaction_count": len(accepted_interactions),
        "rejected_interaction_count": len(rejected_interactions),
        "accepted_skill_card_count": len(accepted_skill_cards),
        "rejected_skill_card_count": len(rejected_skill_cards),
        "skill_card_review_count": len(skill_cards_for_review),
        "error_count": len(errors),
        "warning_count": len(warnings),
    }
    return {
        "summary": summary,
        "errors": errors,
        "warnings": warnings,
        "accepted_interactions": accepted_interactions,
        "rejected_interactions": rejected_interactions,
        "accepted_skill_cards": accepted_skill_cards,
        "rejected_skill_cards": rejected_skill_cards,
        "skill_cards_for_review": skill_cards_for_review,
    }


def _load_review_unit_ids(path: Path) -> set[str]:
    if not path.exists():
        return set()
    return {str(record.get("unit_id")) for record in read_jsonl(path) if record.get("unit_id")}


def _skill_cards_dir(root: Path, scope: str) -> Path:
    scoped_dir = root / "data/processed/skill_cards" / scope
    if scoped_dir.exists():
        return scoped_dir
    return root / "data/processed/skill_cards"


def _load_skill_card_records(skill_cards_dir: Path) -> list[dict[str, Any]]:
    if not skill_cards_dir.exists():
        return []
    records = []
    for path in sorted(skill_cards_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        data["_artifact_path"] = path.as_posix()
        records.append(data)
    return records


def _judge_interaction(
    record: dict[str, Any],
    review_unit_ids: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    interaction_id = str(record.get("interaction_id") or "")
    try:
        interaction = InteractionUnit.from_dict(record)
    except ValueError as exc:
        return (
            [
                {
                    "artifact_type": "interaction_unit",
                    "artifact_id": interaction_id,
                    "severity": "error",
                    "issue": "schema_invalid",
                    "detail": str(exc),
                }
            ],
            warnings,
        )

    missing_review_ids = [
        unit_id for unit_id in interaction.review_unit_ids if unit_id not in review_unit_ids
    ]
    missing_author_ids = [
        unit_id for unit_id in interaction.author_unit_ids if unit_id not in review_unit_ids
    ]
    if missing_review_ids or missing_author_ids:
        errors.append(
            {
                "artifact_type": "interaction_unit",
                "artifact_id": interaction.interaction_id,
                "severity": "error",
                "issue": "missing_review_unit_links",
                "missing_review_unit_ids": missing_review_ids,
                "missing_author_unit_ids": missing_author_ids,
            }
        )
    if interaction.alignment_status == "matched" and not interaction.author_unit_ids:
        errors.append(
            {
                "artifact_type": "interaction_unit",
                "artifact_id": interaction.interaction_id,
                "severity": "error",
                "issue": "matched_without_author_units",
            }
        )
    if not interaction.source_trace.get("review_unit_ids"):
        errors.append(
            {
                "artifact_type": "interaction_unit",
                "artifact_id": interaction.interaction_id,
                "severity": "error",
                "issue": "missing_source_trace_review_unit_ids",
            }
        )
    if interaction.alignment_status != "matched":
        warnings.append(
            {
                "artifact_type": "interaction_unit",
                "artifact_id": interaction.interaction_id,
                "severity": "warning",
                "issue": f"alignment_{interaction.alignment_status}",
            }
        )
    if interaction.alignment_confidence < 0.6:
        warnings.append(
            {
                "artifact_type": "interaction_unit",
                "artifact_id": interaction.interaction_id,
                "severity": "warning",
                "issue": "low_alignment_confidence",
                "confidence": interaction.alignment_confidence,
            }
        )
    return errors, warnings


def _judge_skill_card(
    record: dict[str, Any],
    interaction_ids: set[str],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    errors: list[dict[str, Any]] = []
    warnings: list[dict[str, Any]] = []
    artifact_id = str(record.get("skill_id") or record.get("_artifact_path") or "")
    clean_record = {key: value for key, value in record.items() if not key.startswith("_")}
    try:
        card = SkillCard.from_dict(clean_record)
    except ValueError as exc:
        return (
            [
                {
                    "artifact_type": "skill_card",
                    "artifact_id": artifact_id,
                    "severity": "error",
                    "issue": "schema_invalid",
                    "detail": str(exc),
                }
            ],
            warnings,
        )

    grounded_ids = card.successful_example_ids + card.failure_example_ids
    missing_interaction_ids = [
        interaction_id for interaction_id in grounded_ids if interaction_id not in interaction_ids
    ]
    if missing_interaction_ids:
        errors.append(
            {
                "artifact_type": "skill_card",
                "artifact_id": card.skill_id,
                "severity": "error",
                "issue": "missing_interaction_links",
                "missing_interaction_ids": missing_interaction_ids,
            }
        )
    if card.evidence_status == "validated" and len(card.successful_example_ids) < 3:
        errors.append(
            {
                "artifact_type": "skill_card",
                "artifact_id": card.skill_id,
                "severity": "error",
                "issue": "validated_skill_has_too_few_success_examples",
            }
        )
    if card.evidence_status == "candidate":
        warnings.append(
            {
                "artifact_type": "skill_card",
                "artifact_id": card.skill_id,
                "severity": "warning",
                "issue": "candidate_skill_requires_review",
            }
        )
    if "unknown" in card.skill_id or "ambiguous" in card.skill_id:
        warnings.append(
            {
                "artifact_type": "skill_card",
                "artifact_id": card.skill_id,
                "severity": "warning",
                "issue": "weak_taxonomy_or_alignment_signal",
            }
        )
    return errors, warnings
