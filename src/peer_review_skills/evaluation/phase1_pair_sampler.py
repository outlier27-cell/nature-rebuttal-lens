import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from peer_review_skills.config import PROJECT_ROOT, project_relative_path, resolve_project_path
from peer_review_skills.io.jsonl import read_jsonl, write_jsonl


DEFAULT_MVP_DIR = Path("data/processed/author_rebuttal_mvp/v2709")
DEFAULT_OUTPUT_DIR = Path("data/evaluation/phase1_pair_validation/v2709")
ANNOTATION_FIELDS = (
    "annotator_id",
    "alignment_correct",
    "alignment_error_type",
    "concern_type_gold",
    "concern_type_is_multi_label",
    "response_strategy_gold",
    "response_strategy_secondary",
    "evidence_type",
    "unsafe_or_overclaiming_response",
    "offset_recoverable",
    "usable_for_retrieval",
    "usable_for_evaluation",
    "notes",
)


def build_validation_sample(
    demo_ready_records: list[dict[str, Any]],
    clean_records: list[dict[str, Any]],
    demo_target: int = 100,
    boundary_target: int = 30,
    full_chain_target: int = 20,
) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen_pair_ids: set[str] = set()

    _extend_selected(
        selected,
        seen_pair_ids,
        _stratified_records(demo_ready_records),
        demo_target,
        "demo_ready_stratified",
    )
    _extend_selected(
        selected,
        seen_pair_ids,
        _boundary_records(clean_records),
        boundary_target,
        "boundary_or_unknown",
    )
    _extend_selected(
        selected,
        seen_pair_ids,
        _full_chain_records(demo_ready_records, clean_records),
        full_chain_target,
        "full_chain_decision_aware",
    )
    return selected


def prepare_annotation_record(
    record: dict[str, Any],
    sample_index: int,
    project_root: str | Path = PROJECT_ROOT,
) -> dict[str, Any]:
    prepared = dict(record)
    prepared["sample_id"] = f"phase1_v2709_{sample_index:04d}"
    prepared["sample_index"] = sample_index
    prepared["auto_offset_recoverable"] = check_offset_recoverable(record, project_root)
    prepared["review_context_preview"] = _preview(str(record.get("review_context") or ""))
    prepared["author_response_preview"] = _preview(str(record.get("author_response") or ""))
    for field in ANNOTATION_FIELDS:
        prepared.setdefault(field, "")
    return prepared


def check_offset_recoverable(record: dict[str, Any], project_root: str | Path = PROJECT_ROOT) -> bool:
    source_path = record.get("source_json_path")
    offsets = record.get("source_offsets") or {}
    if not source_path or not isinstance(offsets, dict):
        return False

    required = ("context_start", "context_end", "response_start", "response_end")
    if any(not isinstance(offsets.get(key), int) for key in required):
        return False
    if offsets["context_start"] >= offsets["context_end"] or offsets["response_start"] >= offsets["response_end"]:
        return False

    path = Path(str(source_path))
    if not path.is_absolute():
        path = Path(project_root) / path
    if not path.exists():
        return False

    try:
        paper = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, UnicodeDecodeError):
        return False

    source_text = _source_text(paper, str(record.get("source_field") or ""))
    if not source_text:
        return False
    if offsets["context_end"] > len(source_text) or offsets["response_end"] > len(source_text):
        return False

    context_slice = source_text[offsets["context_start"] : offsets["context_end"]]
    response_slice = source_text[offsets["response_start"] : offsets["response_end"]]
    return _slice_matches(context_slice, str(record.get("review_context") or "")) and _slice_matches(
        response_slice,
        str(record.get("author_response") or ""),
    )


def generate_validation_package(
    mvp_dir: str | Path = DEFAULT_MVP_DIR,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    demo_target: int = 100,
    boundary_target: int = 30,
    full_chain_target: int = 20,
) -> dict[str, Any]:
    mvp_path = resolve_project_path(mvp_dir)
    output_path = resolve_project_path(output_dir)
    demo_ready = list(read_jsonl(mvp_path / "heuristic_rebuttal_pairs_demo_ready.jsonl"))
    clean = list(read_jsonl(mvp_path / "heuristic_rebuttal_pairs_clean.jsonl"))
    sample = build_validation_sample(demo_ready, clean, demo_target, boundary_target, full_chain_target)
    prepared = [
        prepare_annotation_record(record, sample_index=index, project_root=PROJECT_ROOT)
        for index, record in enumerate(sample, start=1)
    ]

    jsonl_path = output_path / "phase1_pair_validation_sample.jsonl"
    csv_path = output_path / "phase1_pair_validation_sample.csv"
    summary_path = output_path / "summary.json"
    readme_path = output_path / "README.md"

    write_jsonl(jsonl_path, prepared)
    _write_csv(csv_path, prepared)
    summary = _summary(prepared, mvp_path, output_path)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    readme_path.write_text(_readme(summary), encoding="utf-8")
    return summary


def _extend_selected(
    selected: list[dict[str, Any]],
    seen_pair_ids: set[str],
    candidates: list[dict[str, Any]],
    target: int,
    bucket: str,
) -> None:
    added = 0
    for candidate in candidates:
        if added >= target:
            return
        pair_id = str(candidate.get("pair_id") or "")
        if not pair_id or pair_id in seen_pair_ids:
            continue
        selected_record = dict(candidate)
        selected_record["sample_bucket"] = bucket
        selected.append(selected_record)
        seen_pair_ids.add(pair_id)
        added += 1


def _stratified_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return _nested_round_robin(
        records,
        primary_key="heuristic_concern_type",
        secondary_keys=("heuristic_response_strategy", "journal_family"),
    )


def _boundary_records(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        records,
        key=lambda record: (
            0 if str(record.get("heuristic_concern_type") or "") == "unknown" else 1,
            0 if _confidence_sort_key(record) <= 0.7 else 1,
            str(record.get("heuristic_response_strategy") or ""),
            str(record.get("journal_family") or ""),
            str(record.get("pair_id") or ""),
        ),
    )


def _full_chain_records(
    demo_ready_records: list[dict[str, Any]],
    clean_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    merged = {str(record.get("pair_id")): record for record in clean_records}
    merged.update({str(record.get("pair_id")): record for record in demo_ready_records})
    full_chain = [
        record
        for record in merged.values()
        if record.get("has_decision") or str(record.get("interaction_level") or "") == "full_chain"
    ]
    return _round_robin_by_keys(
        full_chain,
        (
            "journal_family",
            "heuristic_concern_type",
            "heuristic_response_strategy",
        ),
    )


def _nested_round_robin(
    records: list[dict[str, Any]],
    primary_key: str,
    secondary_keys: tuple[str, ...],
) -> list[dict[str, Any]]:
    primary_groups: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        primary_groups.setdefault(str(record.get(primary_key) or ""), []).append(record)

    ordered_groups = {
        key: _round_robin_by_keys(group_records, secondary_keys)
        for key, group_records in primary_groups.items()
    }
    ordered: list[dict[str, Any]] = []
    primary_keys = sorted(ordered_groups)
    while primary_keys:
        next_primary_keys: list[str] = []
        for key in primary_keys:
            group_records = ordered_groups[key]
            if group_records:
                ordered.append(group_records.pop(0))
            if group_records:
                next_primary_keys.append(key)
        primary_keys = next_primary_keys
    return ordered


def _round_robin_by_keys(records: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = {}
    for record in records:
        group_key = tuple(str(record.get(key) or "") for key in keys)
        grouped.setdefault(group_key, []).append(record)
    for group_records in grouped.values():
        group_records.sort(key=lambda record: (_confidence_sort_key(record), str(record.get("pair_id") or "")))

    ordered: list[dict[str, Any]] = []
    group_keys = sorted(grouped)
    while group_keys:
        next_group_keys: list[tuple[str, ...]] = []
        for group_key in group_keys:
            group_records = grouped[group_key]
            if group_records:
                ordered.append(group_records.pop(0))
            if group_records:
                next_group_keys.append(group_key)
        group_keys = next_group_keys
    return ordered


def _confidence_sort_key(record: dict[str, Any]) -> float:
    try:
        return float(record.get("pair_confidence") or 0)
    except (TypeError, ValueError):
        return 0.0


def _source_text(paper: dict[str, Any], source_field: str) -> str:
    peer_review = paper.get("peer_review") or {}
    if source_field == "/peer_review/author_response":
        return str(peer_review.get("author_response") or "")
    if source_field == "/peer_review/decision_letter":
        return str(peer_review.get("decision_letter") or "")
    return str(peer_review.get("author_response") or "")


def _slice_matches(source_slice: str, stored_text: str) -> bool:
    if not source_slice or not stored_text:
        return False
    normalized_source = _normalize_for_match(source_slice)
    normalized_stored = _normalize_for_match(stored_text)
    return normalized_source in normalized_stored or normalized_stored in normalized_source


def _normalize_for_match(text: str) -> str:
    return " ".join(text.split())


def _preview(text: str, limit: int = 600) -> str:
    normalized = _normalize_for_match(text)
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


def _write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = _csv_fields(records)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            row = dict(record)
            if isinstance(row.get("source_offsets"), dict):
                row["source_offsets"] = json.dumps(row["source_offsets"], ensure_ascii=False, sort_keys=True)
            writer.writerow(row)


def _csv_fields(records: list[dict[str, Any]]) -> list[str]:
    preferred = [
        "sample_id",
        "sample_index",
        "sample_bucket",
        "pair_id",
        "paper_id",
        "doi",
        "title",
        "journal",
        "year",
        "journal_family",
        "mvp_tier",
        "interaction_level",
        "has_decision",
        "pair_confidence",
        "heuristic_concern_type",
        "heuristic_response_strategy",
        "auto_offset_recoverable",
        "context_truncated",
        "response_truncated",
        "review_context_preview",
        "author_response_preview",
        "source_json_path",
        "source_field",
        "source_offsets",
        "extraction_method",
        *ANNOTATION_FIELDS,
    ]
    present = set().union(*(record.keys() for record in records)) if records else set()
    extras = sorted(present - set(preferred) - {"review_context", "author_response"})
    return [field for field in preferred if field in present or field in ANNOTATION_FIELDS] + extras


def _summary(records: list[dict[str, Any]], mvp_path: Path, output_path: Path) -> dict[str, Any]:
    return {
        "sample_count": len(records),
        "mvp_dir": project_relative_path(mvp_path),
        "output_dir": project_relative_path(output_path),
        "files": {
            "jsonl": project_relative_path(output_path / "phase1_pair_validation_sample.jsonl"),
            "csv": project_relative_path(output_path / "phase1_pair_validation_sample.csv"),
            "summary": project_relative_path(output_path / "summary.json"),
            "readme": project_relative_path(output_path / "README.md"),
        },
        "sample_bucket_counts": dict(Counter(record.get("sample_bucket") for record in records)),
        "journal_family_counts": dict(Counter(record.get("journal_family") for record in records)),
        "interaction_level_counts": dict(Counter(record.get("interaction_level") for record in records)),
        "concern_type_counts": dict(Counter(record.get("heuristic_concern_type") for record in records)),
        "response_strategy_counts": dict(Counter(record.get("heuristic_response_strategy") for record in records)),
        "auto_offset_recoverable_counts": dict(Counter(str(record.get("auto_offset_recoverable")) for record in records)),
        "annotation_fields": list(ANNOTATION_FIELDS),
        "notes": [
            "This is a Phase 1 validation sample for human or model-assisted inspection.",
            "Heuristic concern and strategy labels are candidates, not gold labels.",
            "auto_offset_recoverable is an automated pre-check, not a substitute for annotation.",
        ],
    }


def _readme(summary: dict[str, Any]) -> str:
    return f"""# v2709 Phase 1 Pair Validation Sample

This package contains a stratified sample of heuristic rebuttal pairs for checking alignment, label quality, and offset recoverability.

## Files

- `phase1_pair_validation_sample.jsonl`: machine-readable sample with full texts and blank annotation fields.
- `phase1_pair_validation_sample.csv`: spreadsheet-friendly sample with text previews and blank annotation fields.
- `summary.json`: counts and output metadata.

## Counts

- Sample count: `{summary["sample_count"]}`
- Buckets: `{summary["sample_bucket_counts"]}`
- Auto offset recoverable: `{summary["auto_offset_recoverable_counts"]}`

## Annotation Fields

{chr(10).join(f"- `{field}`" for field in summary["annotation_fields"])}

## Use Rules

- Treat `heuristic_concern_type` and `heuristic_response_strategy` as candidate labels.
- Use `alignment_correct`, `concern_type_gold`, and `response_strategy_gold` for validated labels.
- Use `source_json_path`, `source_field`, and `source_offsets` to recover original text.
- Do not use this sample as a gold benchmark until annotation fields are completed and checked.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate v2709 Phase 1 pair validation sample.")
    parser.add_argument("--mvp-dir", default=str(DEFAULT_MVP_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--demo-target", type=int, default=100)
    parser.add_argument("--boundary-target", type=int, default=30)
    parser.add_argument("--full-chain-target", type=int, default=20)
    args = parser.parse_args()

    summary = generate_validation_package(
        mvp_dir=args.mvp_dir,
        output_dir=args.output_dir,
        demo_target=args.demo_target,
        boundary_target=args.boundary_target,
        full_chain_target=args.full_chain_target,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
