from collections.abc import Iterable, Iterator
from typing import Any

from peer_review_skills.config import project_relative_path
from peer_review_skills.evaluation.diagnostics import (
    RESPONSE_MARKERS,
    REVIEWER_MARKERS,
    _contains_any,
    doi_to_paper_id,
)
from peer_review_skills.normalize.loader import RawPaper
from peer_review_skills.schemas.paper_record import PaperRecord


def _has_peer_review_file_block(reports: list[dict[str, Any]]) -> bool:
    return any("peer review file" in str(report.get("reviewer") or "").lower() for report in reports)


def _combined_report_text(reports: list[dict[str, Any]]) -> str:
    return "\n".join(
        f"{report.get('reviewer') or ''}\n{report.get('text') or ''}"
        for report in reports
        if isinstance(report, dict)
    )


def _interaction_level(reports: list[dict[str, Any]], author_response: str | None, decision_letter: str | None) -> str:
    has_reports = bool(reports)
    has_response = bool(isinstance(author_response, str) and author_response.strip())
    has_decision = bool(isinstance(decision_letter, str) and decision_letter.strip())
    if has_reports and has_response and has_decision:
        return "full_chain"
    if has_reports and has_response:
        return "review+response"
    if has_reports and has_decision:
        return "review+decision"
    if has_reports:
        return "review_only"
    return "none"


def normalize_paper(raw_paper: RawPaper, index_by_doi: dict[str, dict[str, Any]]) -> PaperRecord:
    data = raw_paper.data
    doi = str(data.get("doi") or raw_paper.raw_json_path.stem.replace("_", "/"))
    index_record = index_by_doi.get(doi, {})
    peer_review = data.get("peer_review") or {}
    reports = peer_review.get("reviewer_reports") or []
    combined_text = _combined_report_text(reports)
    author_response = peer_review.get("author_response")
    decision_letter = peer_review.get("decision_letter")

    return PaperRecord(
        paper_id=doi_to_paper_id(doi),
        doi=doi,
        title=str(data.get("title") or index_record.get("title") or ""),
        journal=str(data.get("journal") or index_record.get("journal") or ""),
        year=data.get("year") or index_record.get("year"),
        abstract=str(data.get("abstract") or ""),
        quality=str(index_record.get("quality") or data.get("quality") or "unknown"),
        ai_relevance_score=index_record.get("ai_relevance_score")
        if index_record.get("ai_relevance_score") is not None
        else data.get("ai_relevance_score"),
        peer_review_source=str(
            index_record.get("peer_review_source") or peer_review.get("source") or data.get("source") or ""
        ),
        source_files=list(data.get("source_files") or index_record.get("source_files") or []),
        raw_json_path=project_relative_path(raw_paper.raw_json_path),
        reviewer_report_count=len(reports),
        has_author_response_field=bool(isinstance(author_response, str) and author_response.strip()),
        has_response_markers_in_reports=_contains_any(combined_text, RESPONSE_MARKERS),
        has_reviewer_markers_in_reports=_contains_any(combined_text, REVIEWER_MARKERS),
        has_peer_review_file_block=_has_peer_review_file_block(reports),
        publisher_family=str(index_record.get("publisher_family") or data.get("publisher_family") or "nature"),
        journal_family=str(index_record.get("journal_family") or data.get("journal_family") or ""),
        article_type=str(index_record.get("article_type") or data.get("article_type") or ""),
        interaction_level=str(
            index_record.get("interaction_level")
            or data.get("interaction_level")
            or _interaction_level(reports, author_response, decision_letter)
        ),
        response_presence=bool(
            index_record.get("response_presence")
            if index_record.get("response_presence") is not None
            else isinstance(author_response, str) and author_response.strip()
        ),
        decision_presence=bool(
            index_record.get("decision_presence")
            if index_record.get("decision_presence") is not None
            else isinstance(decision_letter, str) and decision_letter.strip()
        ),
    )


def normalize_papers(
    raw_papers: Iterable[RawPaper], index_by_doi: dict[str, dict[str, Any]]
) -> Iterator[PaperRecord]:
    for raw_paper in raw_papers:
        yield normalize_paper(raw_paper, index_by_doi)
