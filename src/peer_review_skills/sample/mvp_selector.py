import json
from pathlib import Path
from typing import Any

from peer_review_skills.config import (
    LEGACY_RAW_DATA_DIR,
    LEGACY_RAW_INDEX_PATH,
    RAW_DATA_DIR,
    RAW_INDEX_PATH,
    project_relative_path,
    resolve_project_path,
)
from peer_review_skills.evaluation.diagnostics import (
    EDITOR_MARKERS,
    RESPONSE_MARKERS,
    _contains_any,
    doi_to_paper_id,
    load_json,
)


TARGET_JOURNALS = (
    "Nature Communications",
    "Nature",
    "Nature Methods",
    "Nature Medicine",
)


def _load_index_by_doi(raw_index_path: str | Path) -> dict[str, dict[str, Any]]:
    index_path = resolve_project_path(raw_index_path)
    if Path(raw_index_path) == RAW_INDEX_PATH and not index_path.exists():
        index_path = resolve_project_path(LEGACY_RAW_INDEX_PATH)
    records = load_json(index_path)
    return {
        record.get("doi"): record
        for record in records
        if isinstance(record, dict) and record.get("doi")
    }


def _paper_features(raw_path: Path, index_record: dict[str, Any], audit: dict[str, Any]) -> dict[str, Any]:
    paper = load_json(raw_path)
    doi = str(paper.get("doi") or index_record.get("doi") or raw_path.stem.replace("_", "/"))
    paper_id = doi_to_paper_id(doi)
    peer_review = paper.get("peer_review") or {}
    reports = peer_review.get("reviewer_reports") or []
    max_report_chars = max((len(str(report.get("text") or "")) for report in reports), default=0)
    combined_text = "\n".join(
        f"{report.get('reviewer') or ''}\n{report.get('text') or ''}"
        for report in reports
        if isinstance(report, dict)
    )

    has_response_marker = paper_id in set(audit.get("response_marker_paper_ids", []))
    has_difficult_label = paper_id in set(audit.get("peer_review_file_block_paper_ids", []))
    has_long_report = max_report_chars >= 25000
    has_editor_marker = _contains_any(combined_text, EDITOR_MARKERS)
    has_round_marker = any(
        marker in combined_text.lower()
        for marker in ("round 1", "round 2", "first revision", "second revision", "reviewers' comments")
    )
    suspected_multi_round = len(reports) >= 10 or has_round_marker or has_editor_marker

    return {
        "paper_id": paper_id,
        "doi": doi,
        "title": str(paper.get("title") or index_record.get("title") or ""),
        "journal": str(paper.get("journal") or index_record.get("journal") or "unknown"),
        "year": paper.get("year") or index_record.get("year"),
        "quality": str(index_record.get("quality") or paper.get("quality") or "unknown"),
        "ai_relevance_score": index_record.get("ai_relevance_score") or paper.get("ai_relevance_score") or 0,
        "reviewer_report_count": len(reports),
        "raw_json_path": project_relative_path(raw_path),
        "has_response_marker": has_response_marker,
        "has_difficult_label": has_difficult_label,
        "has_long_report": has_long_report,
        "suspected_multi_round": suspected_multi_round,
        "max_report_chars": max_report_chars,
        "has_author_response_field": bool(str(peer_review.get("author_response") or "").strip()),
    }


def _score(feature: dict[str, Any]) -> tuple[Any, ...]:
    return (
        0 if feature["quality"] == "high" else 1,
        -int(feature["has_response_marker"]),
        -int(feature["suspected_multi_round"]),
        -int(feature["has_difficult_label"] or feature["has_long_report"]),
        -int(feature["ai_relevance_score"] or 0),
        -int(feature["reviewer_report_count"]),
        feature["paper_id"],
    )


def _report_count_bin(count: int) -> str:
    if count <= 7:
        return "low"
    if count <= 15:
        return "medium"
    return "high"


def _add_first_matching(
    selected: list[dict[str, Any]],
    seen: set[str],
    candidates: list[dict[str, Any]],
    predicate,
    limit: int,
) -> None:
    for feature in candidates:
        if len([item for item in selected if predicate(item)]) >= limit:
            return
        if feature["paper_id"] in seen or not predicate(feature):
            continue
        selected.append(feature)
        seen.add(feature["paper_id"])


def select_mvp_papers(
    raw_data_dir: str | Path,
    raw_index_path: str | Path,
    audit: dict[str, Any],
    n: int = 100,
    review_samples: int = 30,
) -> dict[str, Any]:
    data_dir = resolve_project_path(raw_data_dir)
    if Path(raw_data_dir) == RAW_DATA_DIR and not data_dir.exists():
        data_dir = resolve_project_path(LEGACY_RAW_DATA_DIR)
    index_by_doi = _load_index_by_doi(raw_index_path)
    features = [
        _paper_features(path, index_by_doi.get(load_json(path).get("doi"), {}), audit)
        for path in sorted(data_dir.glob("*.json"))
    ]
    candidates = sorted(features, key=_score)

    selected: list[dict[str, Any]] = []
    seen: set[str] = set()

    _add_first_matching(selected, seen, candidates, lambda item: item["has_response_marker"], 30)
    _add_first_matching(selected, seen, candidates, lambda item: item["suspected_multi_round"], 20)
    _add_first_matching(
        selected,
        seen,
        candidates,
        lambda item: item["has_difficult_label"] or item["has_long_report"],
        10,
    )
    for report_bin in ("low", "medium", "high"):
        _add_first_matching(
            selected,
            seen,
            candidates,
            lambda item, bin_name=report_bin: _report_count_bin(item["reviewer_report_count"]) == bin_name,
            1,
        )
    for journal in TARGET_JOURNALS:
        _add_first_matching(selected, seen, candidates, lambda item, j=journal: item["journal"] == j, 1)

    for feature in candidates:
        if len(selected) >= n:
            break
        if feature["paper_id"] not in seen:
            selected.append(feature)
            seen.add(feature["paper_id"])

    selected = selected[:n]
    selected_ids = [item["paper_id"] for item in selected]

    sample_candidates = sorted(
        selected,
        key=lambda item: (
            -int(item["has_difficult_label"] or item["has_long_report"]),
            -int(item["has_response_marker"]),
            -int(item["suspected_multi_round"]),
            -item["reviewer_report_count"],
            item["paper_id"],
        ),
    )
    samples = []
    for item in sample_candidates[:review_samples]:
        reasons = []
        if item["has_response_marker"]:
            reasons.append("response_marker")
        if item["suspected_multi_round"]:
            reasons.append("suspected_multi_round")
        if item["has_difficult_label"]:
            reasons.append("peer_review_file_block")
        if item["has_long_report"]:
            reasons.append("long_report_block")
        samples.append(
            {
                "paper_id": item["paper_id"],
                "doi": item["doi"],
                "title": item["title"],
                "journal": item["journal"],
                "reviewer_report_count": item["reviewer_report_count"],
                "raw_json_path": item["raw_json_path"],
                "reasons": reasons,
            }
        )

    coverage = {
        "response_marker_papers": sum(1 for item in selected if item["has_response_marker"]),
        "multi_round_or_suspected_papers": sum(1 for item in selected if item["suspected_multi_round"]),
        "difficult_papers": sum(
            1 for item in selected if item["has_difficult_label"] or item["has_long_report"]
        ),
        "reviewer_report_count_bins": {
            report_bin: sum(
                1 for item in selected if _report_count_bin(item["reviewer_report_count"]) == report_bin
            )
            for report_bin in ("low", "medium", "high")
        },
        "journals": sorted({item["journal"] for item in selected}),
    }
    return {
        "mvp_paper_ids": selected_ids,
        "selected_features": selected,
        "segmentation_review_samples": samples,
        "coverage": coverage,
    }


def render_mvp_ids(paper_ids: list[str]) -> str:
    return "".join(f"{paper_id}\n" for paper_id in paper_ids)


def render_review_samples(samples: list[dict[str, Any]]) -> str:
    return "".join(json.dumps(sample, ensure_ascii=False, sort_keys=True) + "\n" for sample in samples)
