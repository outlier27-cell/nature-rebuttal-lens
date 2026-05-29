from typing import Any

from peer_review_skills.config import project_relative_path
from peer_review_skills.evaluation.diagnostics import doi_to_paper_id
from peer_review_skills.schemas.review_unit import ReviewUnit
from peer_review_skills.segment.marker_patterns import find_markers
from peer_review_skills.segment.speaker_segmenter import segment_report_text


def build_review_units_for_paper(
    paper_id: str | None,
    raw_json_path: str,
    paper: dict[str, Any],
) -> list[ReviewUnit]:
    resolved_paper_id = paper_id or doi_to_paper_id(str(paper.get("doi") or "unknown"))
    trace_path = project_relative_path(raw_json_path)
    peer_review = paper.get("peer_review") or {}
    reports = peer_review.get("reviewer_reports") or []
    units: list[ReviewUnit] = []

    for report_index, report in enumerate(reports):
        if not isinstance(report, dict):
            continue
        source_reviewer = str(report.get("reviewer") or "")
        text = str(report.get("text") or "")
        segments = segment_report_text(text, source_reviewer)
        for segment_index, segment in enumerate(segments):
            if not segment.text.strip():
                continue
            unit_id = f"{resolved_paper_id}:r{report_index}:u{segment_index}"
            units.append(
                ReviewUnit(
                    unit_id=unit_id,
                    paper_id=resolved_paper_id,
                    source_report_index=report_index,
                    source_report_reviewer=source_reviewer,
                    round_id=segment.round_id,
                    speaker_type=segment.speaker_type,
                    speaker_id=segment.speaker_id,
                    section_label=segment.section_label,
                    text=segment.text,
                    char_start=segment.char_start,
                    char_end=segment.char_end,
                    marker_text=segment.marker_text,
                    segmentation_method=segment.segmentation_method,
                    segmentation_confidence=segment.segmentation_confidence,
                    source_trace={
                        "raw_json_path": trace_path,
                        "json_pointer": f"/peer_review/reviewer_reports/{report_index}/text",
                        "source_report_index": report_index,
                    },
                )
            )

    author_response = peer_review.get("author_response")
    if isinstance(author_response, str) and author_response.strip():
        has_speaker_markers = any(
            marker.marker_type in {"reviewer", "author", "editor"}
            for marker in find_markers(author_response)
        )
        if has_speaker_markers:
            prefix_hint = None
            first_marker_start = min(
                (
                    marker.start
                    for marker in find_markers(author_response)
                    if marker.marker_type in {"reviewer", "author", "editor"}
                ),
                default=0,
            )
            prefix_text = author_response[:first_marker_start].lower()
            if any(
                phrase in prefix_text
                for phrase in (
                    "dear reviewers",
                    "dear reviewer",
                    "thank all reviewers",
                    "thank you for the constructive",
                    "we thank",
                    "we sincerely thank",
                    "we would like to thank",
                    "we appreciate",
                )
            ):
                prefix_hint = "author"
            segments = segment_report_text(author_response, "", prefix_speaker_hint=prefix_hint)
            for segment_index, segment in enumerate(segments):
                if not segment.text.strip():
                    continue
                units.append(
                    ReviewUnit(
                        unit_id=f"{resolved_paper_id}:author_response:u{segment_index}",
                        paper_id=resolved_paper_id,
                        source_report_index=-1,
                        source_report_reviewer="",
                        round_id=segment.round_id,
                        speaker_type=segment.speaker_type,
                        speaker_id=segment.speaker_id,
                        section_label=segment.section_label,
                        text=segment.text,
                        char_start=segment.char_start,
                        char_end=segment.char_end,
                        marker_text=segment.marker_text,
                        segmentation_method="author_response_field_marker_based",
                        segmentation_confidence=segment.segmentation_confidence,
                        source_trace={
                            "raw_json_path": trace_path,
                            "json_pointer": "/peer_review/author_response",
                            "source_report_index": -1,
                        },
                    )
                )
        else:
            units.append(
                ReviewUnit(
                    unit_id=f"{resolved_paper_id}:author_response:u0",
                    paper_id=resolved_paper_id,
                    source_report_index=-1,
                    source_report_reviewer="",
                    round_id="round_unknown",
                    speaker_type="author",
                    speaker_id="author",
                    section_label="author_response",
                    text=author_response,
                    char_start=0,
                    char_end=len(author_response),
                    marker_text="author_response",
                    segmentation_method="author_response_field",
                    segmentation_confidence=0.95,
                    source_trace={
                        "raw_json_path": trace_path,
                        "json_pointer": "/peer_review/author_response",
                        "source_report_index": -1,
                    },
                )
            )
    return units
