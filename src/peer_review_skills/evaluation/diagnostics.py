import json
from collections import Counter
from pathlib import Path
from typing import Any

from peer_review_skills.config import (
    LEGACY_RAW_DATA_DIR,
    LEGACY_RAW_INDEX_PATH,
    RAW_DATA_DIR,
    RAW_INDEX_PATH,
    resolve_project_path,
)


RESPONSE_MARKERS = (
    "response:",
    "author response",
    "response to reviewer",
    "responses to reviewer",
    "author reply",
)
REVIEWER_MARKERS = (
    "reviewer #",
    "reviewer 1",
    "reviewer 2",
    "reviewer 3",
    "reviewer 4",
    "reviewer 5",
    "reviewer 6",
    "referee #",
    "referee 1",
    "referee 2",
    "referee 3",
    "remarks to the author",
    "reviewer report",
    "reviewer comments",
)
EDITOR_MARKERS = ("decision letter", "editorial decision", "senior editor", "editor")


def _contains_any(text: str, markers: tuple[str, ...]) -> bool:
    lowered = text.lower()
    return any(marker in lowered for marker in markers)


def doi_to_paper_id(doi: str) -> str:
    return doi.strip().replace("/", "_")


def load_json(path: str | Path) -> Any:
    with Path(path).open("r", encoding="utf-8") as handle:
        return json.load(handle)


def iter_raw_paper_paths(raw_data_dir: str | Path) -> list[Path]:
    data_dir = resolve_project_path(raw_data_dir)
    return sorted(data_dir.glob("*.json"))


def audit_dataset(raw_data_dir: str | Path, raw_index_path: str | Path) -> dict[str, Any]:
    data_dir = resolve_project_path(raw_data_dir)
    index_path = resolve_project_path(raw_index_path)
    if Path(raw_data_dir) == RAW_DATA_DIR and not data_dir.exists():
        data_dir = resolve_project_path(LEGACY_RAW_DATA_DIR)
    if Path(raw_index_path) == RAW_INDEX_PATH and not index_path.exists():
        index_path = resolve_project_path(LEGACY_RAW_INDEX_PATH)
    raw_paths = iter_raw_paper_paths(data_dir)
    index_records = load_json(index_path)

    report_block_count = 0
    author_response_field_count = 0
    response_marker_paper_ids: set[str] = set()
    reviewer_marker_paper_ids: set[str] = set()
    editor_marker_paper_ids: set[str] = set()
    peer_review_file_block_paper_ids: set[str] = set()
    paper_ids: list[str] = []
    journal_counts: Counter[str] = Counter()
    quality_counts: Counter[str] = Counter()
    reviewer_report_counts: Counter[int] = Counter()
    publisher_family_counts: Counter[str] = Counter()
    journal_family_counts: Counter[str] = Counter()
    interaction_level_counts: Counter[str] = Counter()
    response_presence_count = 0
    decision_presence_count = 0
    scientific_reports_count = 0

    index_by_doi = {
        record.get("doi"): record
        for record in index_records
        if isinstance(record, dict) and record.get("doi")
    }

    for raw_path in raw_paths:
        paper = load_json(raw_path)
        doi = str(paper.get("doi") or raw_path.stem.replace("_", "/"))
        paper_id = doi_to_paper_id(doi)
        paper_ids.append(paper_id)

        index_record = index_by_doi.get(doi, {})
        journal = paper.get("journal") or index_record.get("journal") or "unknown"
        quality = index_record.get("quality") or paper.get("quality") or "unknown"
        journal_counts[str(journal)] += 1
        quality_counts[str(quality)] += 1
        publisher_family = index_record.get("publisher_family") or paper.get("publisher_family") or "unknown"
        journal_family = index_record.get("journal_family") or paper.get("journal_family") or "unknown"
        interaction_level = index_record.get("interaction_level") or paper.get("interaction_level") or "unknown"
        publisher_family_counts[str(publisher_family)] += 1
        journal_family_counts[str(journal_family)] += 1
        interaction_level_counts[str(interaction_level)] += 1
        if bool(index_record.get("response_presence")):
            response_presence_count += 1
        if bool(index_record.get("decision_presence")):
            decision_presence_count += 1
        if str(journal) == "Scientific Reports" or str(journal_family) == "scientific_reports":
            scientific_reports_count += 1

        peer_review = paper.get("peer_review") or {}
        reports = peer_review.get("reviewer_reports") or []
        report_block_count += len(reports)
        reviewer_report_counts[len(reports)] += 1

        author_response = peer_review.get("author_response")
        if isinstance(author_response, str) and author_response.strip():
            author_response_field_count += 1

        for report in reports:
            if not isinstance(report, dict):
                continue
            label = str(report.get("reviewer") or "")
            text = str(report.get("text") or "")
            combined = f"{label}\n{text}"
            if _contains_any(combined, RESPONSE_MARKERS):
                response_marker_paper_ids.add(paper_id)
            if _contains_any(combined, REVIEWER_MARKERS):
                reviewer_marker_paper_ids.add(paper_id)
            if _contains_any(combined, EDITOR_MARKERS):
                editor_marker_paper_ids.add(paper_id)
            if "peer review file" in label.lower():
                peer_review_file_block_paper_ids.add(paper_id)

    return {
        "raw_data_dir": str(Path(raw_data_dir).as_posix()),
        "raw_index_path": str(Path(raw_index_path).as_posix()),
        "index_record_count": len(index_records),
        "paper_count": len(raw_paths),
        "report_block_count": report_block_count,
        "author_response_field_count": author_response_field_count,
        "response_marker_paper_count": len(response_marker_paper_ids),
        "reviewer_marker_paper_count": len(reviewer_marker_paper_ids),
        "editor_marker_paper_count": len(editor_marker_paper_ids),
        "peer_review_file_block_paper_count": len(peer_review_file_block_paper_ids),
        "response_marker_paper_ids": sorted(response_marker_paper_ids),
        "reviewer_marker_paper_ids": sorted(reviewer_marker_paper_ids),
        "editor_marker_paper_ids": sorted(editor_marker_paper_ids),
        "peer_review_file_block_paper_ids": sorted(peer_review_file_block_paper_ids),
        "paper_ids": sorted(paper_ids),
        "journal_counts": dict(journal_counts.most_common()),
        "quality_counts": dict(quality_counts.most_common()),
        "publisher_family_counts": dict(publisher_family_counts.most_common()),
        "journal_family_counts": dict(journal_family_counts.most_common()),
        "interaction_level_counts": dict(interaction_level_counts.most_common()),
        "response_presence_count": response_presence_count,
        "decision_presence_count": decision_presence_count,
        "scientific_reports_count": scientific_reports_count,
        "reviewer_report_count_distribution": dict(sorted(reviewer_report_counts.items())),
    }
