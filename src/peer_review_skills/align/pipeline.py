from collections import Counter, defaultdict
from typing import Any

from peer_review_skills.schemas.interaction_unit import InteractionUnit


KEYWORD_STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "and",
    "are",
    "author",
    "authors",
    "because",
    "been",
    "can",
    "could",
    "does",
    "for",
    "from",
    "have",
    "into",
    "manuscript",
    "more",
    "paper",
    "please",
    "reviewer",
    "should",
    "study",
    "that",
    "the",
    "their",
    "there",
    "this",
    "was",
    "were",
    "with",
    "would",
}


def align_interactions(
    review_units: list[dict[str, Any]],
    reviewer_annotations: list[dict[str, Any]],
    author_annotations: list[dict[str, Any]],
) -> dict[str, Any]:
    units_by_id = {str(unit.get("unit_id")): unit for unit in review_units}
    author_annotations_by_unit = {
        str(annotation.get("unit_id")): annotation for annotation in author_annotations
    }
    author_units_by_paper: dict[str, list[dict[str, Any]]] = defaultdict(list)
    author_keywords_by_unit: dict[str, set[str]] = {}
    for unit in review_units:
        if unit.get("speaker_type") == "author":
            author_units_by_paper[str(unit.get("paper_id"))].append(unit)
            author_keywords_by_unit[str(unit.get("unit_id"))] = _keywords(str(unit.get("text") or ""))
    for units in author_units_by_paper.values():
        units.sort(key=_unit_sort_key)
    author_context_reviewer_by_unit = _author_context_reviewer_by_unit(review_units)

    interactions: list[InteractionUnit] = []
    unresolved: list[dict[str, Any]] = []

    for index, annotation in enumerate(reviewer_annotations):
        review_unit = units_by_id.get(str(annotation.get("unit_id")))
        if not review_unit:
            interaction = _unsupported_interaction(annotation, index)
            interactions.append(interaction)
            unresolved.append(_unresolved_item(interaction, annotation, "review_unit_not_found"))
            continue

        candidates = _rank_author_candidates(
            review_unit,
            annotation,
            author_units_by_paper.get(str(review_unit.get("paper_id")), []),
            author_annotations_by_unit,
            _keywords(str(annotation.get("concern_claim") or review_unit.get("text") or "")),
            author_keywords_by_unit,
            author_context_reviewer_by_unit,
        )
        interaction = _build_interaction(index, annotation, review_unit, candidates, author_annotations_by_unit)
        interactions.append(interaction)
        if interaction.alignment_status != "matched":
            unresolved.append(
                _unresolved_item(interaction, annotation, f"alignment_{interaction.alignment_status}")
            )

    return {
        "interaction_units": interactions,
        "unresolved_alignment_units": unresolved,
        "summary": build_alignment_summary(interactions),
    }


def align_annotations(
    reviewer_annotations: list[dict[str, Any]],
    author_annotations: list[dict[str, Any]],
    unit_index: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    index = unit_index or {}
    review_units = [_review_unit_from_annotation(annotation, index) for annotation in reviewer_annotations]
    author_units = [_author_unit_from_annotation(annotation, index) for annotation in author_annotations]
    return align_interactions(review_units + author_units, reviewer_annotations, author_annotations)


def build_alignment_summary(interactions: list[InteractionUnit]) -> dict[str, Any]:
    status_counts = Counter(interaction.alignment_status for interaction in interactions)
    method_counts = Counter(interaction.alignment_method for interaction in interactions)
    concern_counts = Counter(interaction.concern_type for interaction in interactions)
    strategy_counts = Counter(interaction.author_strategy for interaction in interactions)
    return {
        "interaction_count": len(interactions),
        "status_counts": dict(status_counts.most_common()),
        "method_counts": dict(method_counts.most_common()),
        "concern_type_counts": dict(concern_counts.most_common()),
        "author_strategy_counts": dict(strategy_counts.most_common()),
        "review_queue_count": sum(
            1 for interaction in interactions if interaction.alignment_status != "matched"
        ),
    }


def _build_interaction(
    index: int,
    annotation: dict[str, Any],
    review_unit: dict[str, Any],
    candidates: list[tuple[float, dict[str, Any]]],
    author_annotations_by_unit: dict[str, dict[str, Any]],
) -> InteractionUnit:
    paper_id = str(review_unit.get("paper_id") or annotation.get("paper_id") or "unknown")
    review_unit_id = str(review_unit.get("unit_id") or annotation.get("unit_id"))
    interaction_id = f"{paper_id}:interaction:{index:05d}"
    round_id = str(review_unit.get("round_id") or "round_unknown")
    reviewer_id = str(review_unit.get("speaker_id") or "reviewer_unknown")

    if not candidates:
        return InteractionUnit(
            interaction_id=interaction_id,
            paper_id=paper_id,
            round_id=round_id,
            reviewer_id=reviewer_id,
            review_unit_ids=[review_unit_id],
            review_span_text=str(review_unit.get("text") or ""),
            author_unit_ids=[],
            author_response_text="",
            alignment_method="no_author_candidate",
            alignment_confidence=0.0,
            alignment_status="missing_response",
            source_trace=_source_trace(review_unit, []),
            concern_type=str(annotation.get("concern_type") or "unknown"),
            concern_claim=str(annotation.get("concern_claim") or ""),
            evidence_request=str(annotation.get("evidence_request") or "unknown"),
            reviewer_sentiment=str(annotation.get("reviewer_sentiment") or "neutral"),
            reviewer_severity=str(annotation.get("reviewer_severity") or "unknown"),
            author_strategy="unknown",
            author_action="",
            response_stance="unknown",
            response_outcome="unanswered",
        )

    top_score = candidates[0][0]
    top_candidates = [candidate for score, candidate in candidates if abs(score - top_score) < 0.001]
    if len(top_candidates) > 1:
        selected = top_candidates
        status = "ambiguous"
        confidence = min(top_score, 0.55)
        method = "ambiguous_equal_score"
        outcome = "ambiguous"
    elif top_score < 0.35:
        selected = [candidates[0][1]]
        status = "ambiguous"
        confidence = top_score
        method = "weak_candidate_score"
        outcome = "ambiguous"
    else:
        selected = [candidates[0][1]]
        status = "matched"
        confidence = min(0.98, top_score)
        method = "adjacent_marker_window"
        outcome = _response_outcome(author_annotations_by_unit.get(str(selected[0].get("unit_id"))))

    author_unit_ids = [str(unit.get("unit_id")) for unit in selected]
    author_text = "\n\n".join(str(unit.get("text") or "") for unit in selected)
    author_annotation = author_annotations_by_unit.get(author_unit_ids[0]) if author_unit_ids else None

    return InteractionUnit(
        interaction_id=interaction_id,
        paper_id=paper_id,
        round_id=round_id,
        reviewer_id=reviewer_id,
        review_unit_ids=[review_unit_id],
        review_span_text=str(review_unit.get("text") or ""),
        author_unit_ids=author_unit_ids,
        author_response_text=author_text,
        alignment_method=method,
        alignment_confidence=confidence,
        alignment_status=status,
        source_trace=_source_trace(review_unit, selected),
        concern_type=str(annotation.get("concern_type") or "unknown"),
        concern_claim=str(annotation.get("concern_claim") or ""),
        evidence_request=str(annotation.get("evidence_request") or "unknown"),
        reviewer_sentiment=str(annotation.get("reviewer_sentiment") or "neutral"),
        reviewer_severity=str(annotation.get("reviewer_severity") or "unknown"),
        author_strategy=str((author_annotation or {}).get("author_strategy") or "unknown"),
        author_action=str((author_annotation or {}).get("author_action") or ""),
        response_stance=str((author_annotation or {}).get("response_stance") or "unknown"),
        response_outcome=outcome,
    )


def _rank_author_candidates(
    review_unit: dict[str, Any],
    reviewer_annotation: dict[str, Any],
    author_units: list[dict[str, Any]],
    author_annotations_by_unit: dict[str, dict[str, Any]],
    reviewer_keywords: set[str],
    author_keywords_by_unit: dict[str, set[str]],
    author_context_reviewer_by_unit: dict[str, str],
) -> list[tuple[float, dict[str, Any]]]:
    scored = []
    for author_unit in author_units:
        score = _candidate_score(
            review_unit,
            reviewer_annotation,
            author_unit,
            author_annotations_by_unit,
            reviewer_keywords,
            author_keywords_by_unit.get(str(author_unit.get("unit_id")), set()),
            author_context_reviewer_by_unit.get(str(author_unit.get("unit_id")), ""),
        )
        if score > 0.0:
            scored.append((score, author_unit))
    return sorted(scored, key=lambda item: (-item[0], _unit_sort_key(item[1])))


def _candidate_score(
    review_unit: dict[str, Any],
    reviewer_annotation: dict[str, Any],
    author_unit: dict[str, Any],
    author_annotations_by_unit: dict[str, dict[str, Any]],
    reviewer_keywords: set[str],
    author_keywords: set[str],
    author_context_reviewer_id: str = "",
) -> float:
    score = 0.15
    if author_unit.get("round_id") == review_unit.get("round_id"):
        score += 0.15
    review_report = int(review_unit.get("source_report_index", -99))
    author_report = int(author_unit.get("source_report_index", -99))
    if author_report == review_report and author_report >= 0:
        score += 0.35
        if int(author_unit.get("char_start", 0)) >= int(review_unit.get("char_end", 0)):
            distance = int(author_unit.get("char_start", 0)) - int(review_unit.get("char_end", 0))
            score += max(0.0, 0.2 - min(distance, 5000) / 25000)
    elif author_report == -1 and review_report == -1:
        score += 0.18
        if _same_source_pointer(review_unit, author_unit) and int(author_unit.get("char_start", 0)) >= int(
            review_unit.get("char_end", 0)
        ):
            distance = int(author_unit.get("char_start", 0)) - int(review_unit.get("char_end", 0))
            score += max(0.0, 0.24 - min(distance, 6000) / 25000)
    elif author_report == -1:
        score += 0.08

    reviewer_id = str(review_unit.get("speaker_id") or "")
    author_text = str(author_unit.get("text") or "")
    if reviewer_id and reviewer_id != "unknown" and _author_text_references_reviewer(author_text, reviewer_id):
        score += 0.12
    if reviewer_id and reviewer_id != "unknown" and author_context_reviewer_id == reviewer_id:
        score += 0.18
    overlap = len(reviewer_keywords & author_keywords)
    score += min(0.2, overlap * 0.04)
    author_annotation = author_annotations_by_unit.get(str(author_unit.get("unit_id")))
    if author_annotation:
        score += 0.05
    return round(min(score, 1.0), 4)


def _author_context_reviewer_by_unit(review_units: list[dict[str, Any]]) -> dict[str, str]:
    by_source: dict[tuple[str, str], list[dict[str, Any]]] = defaultdict(list)
    for unit in review_units:
        trace = dict(unit.get("source_trace") or {})
        if str(trace.get("json_pointer") or "") != "/peer_review/author_response":
            continue
        key = (str(trace.get("raw_json_path") or ""), str(trace.get("json_pointer") or ""))
        by_source[key].append(unit)

    context: dict[str, str] = {}
    for units in by_source.values():
        current_reviewer_id = ""
        for unit in sorted(units, key=_unit_sort_key):
            speaker_type = unit.get("speaker_type")
            speaker_id = str(unit.get("speaker_id") or "")
            if speaker_type == "reviewer" and speaker_id and speaker_id != "reviewer_unknown":
                current_reviewer_id = speaker_id
            elif speaker_type == "author" and current_reviewer_id:
                context[str(unit.get("unit_id"))] = current_reviewer_id
    return context


def _same_source_pointer(review_unit: dict[str, Any], author_unit: dict[str, Any]) -> bool:
    review_trace = dict(review_unit.get("source_trace") or {})
    author_trace = dict(author_unit.get("source_trace") or {})
    return (
        str(review_trace.get("raw_json_path") or "")
        == str(author_trace.get("raw_json_path") or "")
        and str(review_trace.get("json_pointer") or "")
        == str(author_trace.get("json_pointer") or "")
    )


def _author_text_references_reviewer(author_text: str, reviewer_id: str) -> bool:
    lowered = author_text.lower()
    normalized_id = reviewer_id.replace("_", " ")
    if normalized_id in lowered:
        return True
    digits = "".join(char for char in reviewer_id if char.isdigit())
    if not digits:
        return False
    compact = "".join(char for char in lowered if char.isalnum())
    return (
        f"reviewer{digits}" in compact
        or f"referee{digits}" in compact
        or f"reviewercomment{digits}" in compact
    )


def _keywords(text: str) -> set[str]:
    tokens = []
    current = []
    for char in text.lower():
        if char.isalnum() or char in {"-"}:
            current.append(char)
        elif current:
            tokens.append("".join(current))
            current = []
    if current:
        tokens.append("".join(current))
    return {token for token in tokens if len(token) >= 5 and token not in KEYWORD_STOPWORDS}


def _response_outcome(author_annotation: dict[str, Any] | None) -> str:
    if not author_annotation:
        return "unknown"
    strategy = author_annotation.get("author_strategy")
    stance = author_annotation.get("response_stance")
    if strategy == "defer_future_work":
        return "deferred"
    if strategy == "contest_reviewer_premise" or stance == "disagree":
        return "contested"
    if stance == "partial":
        return "partially_addressed"
    if strategy in {
        "acknowledge_and_fix",
        "clarify_existing_evidence",
        "add_new_experiment",
        "add_new_analysis",
        "narrow_claim_scope",
        "justify_method_choice",
        "reframe_contribution",
        "editorial_only_change",
    }:
        return "addressed"
    return "unknown"


def _source_trace(review_unit: dict[str, Any], author_units: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "raw_json_path": (review_unit.get("source_trace") or {}).get("raw_json_path", ""),
        "review_unit_ids": [str(review_unit.get("unit_id"))],
        "author_unit_ids": [str(unit.get("unit_id")) for unit in author_units],
        "review_source_trace": dict(review_unit.get("source_trace") or {}),
        "author_source_traces": [dict(unit.get("source_trace") or {}) for unit in author_units],
    }


def _unit_sort_key(unit: dict[str, Any]) -> tuple[int, int, str]:
    return (
        int(unit.get("source_report_index", 999999)),
        int(unit.get("char_start", 999999)),
        str(unit.get("unit_id") or ""),
    )


def _unsupported_interaction(annotation: dict[str, Any], index: int) -> InteractionUnit:
    paper_id = str(annotation.get("paper_id") or "unknown")
    unit_id = str(annotation.get("unit_id") or "missing_unit")
    return InteractionUnit(
        interaction_id=f"{paper_id}:interaction:{index:05d}",
        paper_id=paper_id,
        round_id="round_unknown",
        reviewer_id="reviewer_unknown",
        review_unit_ids=[unit_id],
        review_span_text="",
        author_unit_ids=[],
        author_response_text="",
        alignment_method="missing_review_unit",
        alignment_confidence=0.0,
        alignment_status="unsupported",
        source_trace={"review_unit_ids": [unit_id], "author_unit_ids": []},
        concern_type=str(annotation.get("concern_type") or "unknown"),
        concern_claim=str(annotation.get("concern_claim") or ""),
        evidence_request=str(annotation.get("evidence_request") or "unknown"),
        reviewer_sentiment=str(annotation.get("reviewer_sentiment") or "neutral"),
        reviewer_severity=str(annotation.get("reviewer_severity") or "unknown"),
        author_strategy="unknown",
        author_action="",
        response_stance="unknown",
        response_outcome="unknown",
    )


def _review_unit_from_annotation(
    annotation: dict[str, Any],
    unit_index: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    source_trace = dict(annotation.get("source_trace") or {})
    indexed = (unit_index or {}).get(str(annotation.get("unit_id") or ""), {})
    if indexed:
        return {
            "unit_id": str(indexed.get("unit_id") or annotation.get("unit_id") or ""),
            "paper_id": str(indexed.get("paper_id") or annotation.get("paper_id") or ""),
            "round_id": str(indexed.get("round_id") or "round_unknown"),
            "speaker_type": str(indexed.get("speaker_type") or "reviewer"),
            "speaker_id": str(indexed.get("speaker_id") or _reviewer_id_from_unit_id(str(annotation.get("unit_id") or ""))),
            "text": str(indexed.get("text") or indexed.get("text_preview") or annotation.get("concern_claim") or ""),
            "char_start": int(indexed.get("char_start", 0)),
            "char_end": int(
                indexed.get(
                    "char_end",
                    int(indexed.get("char_start", 0)) + len(str(annotation.get("concern_claim") or "")),
                )
            ),
            "unit_index": int(indexed.get("unit_index", _unit_index_from_unit_id(str(annotation.get("unit_id") or "")))),
            "source_report_index": int(indexed.get("source_report_index", source_trace.get("source_report_index", -1))),
            "source_trace": dict(indexed.get("source_trace") or source_trace),
        }
    source_report_index = int(indexed.get("source_report_index", source_trace.get("source_report_index", -1)))
    unit_index_value = int(indexed.get("unit_index", _unit_index_from_unit_id(str(annotation.get("unit_id") or ""))))
    char_start = int(indexed.get("char_start", unit_index_value * 1000))
    char_end = int(indexed.get("char_end", char_start + len(str(annotation.get("concern_claim") or ""))))
    return {
        "unit_id": str(annotation.get("unit_id") or ""),
        "paper_id": str(annotation.get("paper_id") or ""),
        "round_id": _round_from_unit_id(str(annotation.get("unit_id") or "")),
        "speaker_type": "reviewer",
        "speaker_id": _reviewer_id_from_unit_id(str(annotation.get("unit_id") or "")),
        "text": str(annotation.get("concern_claim") or ""),
        "char_start": char_start,
        "char_end": char_end,
        "unit_index": unit_index_value,
        "source_report_index": source_report_index,
        "source_trace": source_trace,
    }


def _author_unit_from_annotation(
    annotation: dict[str, Any],
    unit_index: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    source_trace = dict(annotation.get("source_trace") or {})
    indexed = (unit_index or {}).get(str(annotation.get("unit_id") or ""), {})
    if indexed:
        return {
            "unit_id": str(indexed.get("unit_id") or annotation.get("unit_id") or ""),
            "paper_id": str(indexed.get("paper_id") or annotation.get("paper_id") or ""),
            "round_id": str(indexed.get("round_id") or "round_unknown"),
            "speaker_type": str(indexed.get("speaker_type") or "author"),
            "speaker_id": str(indexed.get("speaker_id") or "author"),
            "text": str(indexed.get("text") or indexed.get("text_preview") or annotation.get("author_action") or ""),
            "char_start": int(indexed.get("char_start", 0)),
            "char_end": int(
                indexed.get(
                    "char_end",
                    int(indexed.get("char_start", 0)) + len(str(annotation.get("author_action") or "")),
                )
            ),
            "unit_index": int(indexed.get("unit_index", _unit_index_from_unit_id(str(annotation.get("unit_id") or "")))),
            "source_report_index": int(indexed.get("source_report_index", source_trace.get("source_report_index", -1))),
            "source_trace": dict(indexed.get("source_trace") or source_trace),
        }
    source_report_index = int(indexed.get("source_report_index", source_trace.get("source_report_index", -1)))
    unit_index_value = int(indexed.get("unit_index", _unit_index_from_unit_id(str(annotation.get("unit_id") or ""))))
    char_start = int(indexed.get("char_start", unit_index_value * 1000))
    char_end = int(indexed.get("char_end", char_start + len(str(annotation.get("author_action") or ""))))
    return {
        "unit_id": str(annotation.get("unit_id") or ""),
        "paper_id": str(annotation.get("paper_id") or ""),
        "round_id": _round_from_unit_id(str(annotation.get("unit_id") or "")),
        "speaker_type": "author",
        "speaker_id": "author",
        "text": str(annotation.get("author_action") or ""),
        "char_start": char_start,
        "char_end": char_end,
        "unit_index": unit_index_value,
        "source_report_index": source_report_index,
        "source_trace": source_trace,
    }


def _round_from_unit_id(unit_id: str) -> str:
    # Existing unit IDs encode report index, not review round. Keep the same
    # conservative default used by the segmenter unless a future parser adds it.
    return "round_unknown"


def _reviewer_id_from_unit_id(unit_id: str) -> str:
    marker = ":r"
    if marker not in unit_id:
        return "reviewer_unknown"
    suffix = unit_id.split(marker, 1)[1]
    report_digits = []
    for char in suffix:
        if char.isdigit():
            report_digits.append(char)
        else:
            break
    if not report_digits:
        return "reviewer_unknown"
    return f"reviewer_report_{''.join(report_digits)}"


def _unit_index_from_unit_id(unit_id: str) -> int:
    marker = ":u"
    if marker not in unit_id:
        return 0
    suffix = unit_id.rsplit(marker, 1)[1]
    digits = []
    for char in suffix:
        if char.isdigit():
            digits.append(char)
        else:
            break
    return int("".join(digits) or "0")


def _unresolved_item(
    interaction: InteractionUnit,
    annotation: dict[str, Any],
    reason: str,
) -> dict[str, Any]:
    return {
        "interaction_id": interaction.interaction_id,
        "paper_id": interaction.paper_id,
        "review_unit_ids": interaction.review_unit_ids,
        "author_unit_ids": interaction.author_unit_ids,
        "alignment_status": interaction.alignment_status,
        "alignment_confidence": interaction.alignment_confidence,
        "review_reason": reason,
        "concern_type": annotation.get("concern_type", "unknown"),
        "review_text_preview": " ".join(interaction.review_span_text.split())[:500],
        "author_text_preview": " ".join(interaction.author_response_text.split())[:500],
    }
