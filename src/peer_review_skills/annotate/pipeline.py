from collections import Counter
from typing import Any

from peer_review_skills.annotate.rule_based import annotate_review_unit
from peer_review_skills.schemas.annotation import AuthorAnnotation, ReviewerAnnotation


LOW_CONFIDENCE_THRESHOLD = 0.6


def annotate_units(units: list[dict[str, Any]]) -> dict[str, Any]:
    reviewer_annotations: list[ReviewerAnnotation] = []
    author_annotations: list[AuthorAnnotation] = []
    low_confidence_annotations: list[dict[str, Any]] = []
    skipped_units = 0

    for unit in units:
        annotation = annotate_review_unit(unit)
        if annotation is None:
            skipped_units += 1
            continue
        if isinstance(annotation, ReviewerAnnotation):
            reviewer_annotations.append(annotation)
        else:
            author_annotations.append(annotation)
        if annotation.confidence < LOW_CONFIDENCE_THRESHOLD:
            low_confidence_annotations.append(
                {
                    "unit_id": annotation.unit_id,
                    "paper_id": annotation.paper_id,
                    "speaker_type": unit.get("speaker_type"),
                    "confidence": annotation.confidence,
                    "annotation_method": annotation.annotation_method,
                    "annotation": annotation.to_dict(),
                    "text_preview": " ".join(str(unit.get("text") or "").split())[:500],
                    "review_reason": "low_confidence_rule_annotation",
                }
            )

    return {
        "reviewer_annotations": reviewer_annotations,
        "author_annotations": author_annotations,
        "low_confidence_annotations": low_confidence_annotations,
        "summary": build_annotation_summary(
            reviewer_annotations,
            author_annotations,
            low_confidence_annotations,
            skipped_units,
        ),
    }


def build_annotation_summary(
    reviewer_annotations: list[ReviewerAnnotation],
    author_annotations: list[AuthorAnnotation],
    low_confidence_annotations: list[dict[str, Any]],
    skipped_units: int,
) -> dict[str, Any]:
    return {
        "reviewer_annotation_count": len(reviewer_annotations),
        "author_annotation_count": len(author_annotations),
        "low_confidence_count": len(low_confidence_annotations),
        "skipped_units": skipped_units,
        "concern_type_counts": dict(Counter(a.concern_type for a in reviewer_annotations).most_common()),
        "reviewer_sentiment_counts": dict(
            Counter(a.reviewer_sentiment for a in reviewer_annotations).most_common()
        ),
        "reviewer_severity_counts": dict(
            Counter(a.reviewer_severity for a in reviewer_annotations).most_common()
        ),
        "author_strategy_counts": dict(Counter(a.author_strategy for a in author_annotations).most_common()),
        "response_stance_counts": dict(Counter(a.response_stance for a in author_annotations).most_common()),
    }
