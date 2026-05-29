import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from peer_review_skills.config import project_relative_path, resolve_project_path
from peer_review_skills.io.jsonl import read_jsonl, write_jsonl


DEFAULT_INPUT_DIR = Path("data/evaluation/phase1_pair_validation/v2709")

ERROR_RECOMMENDATIONS = {
    "reversed_context_response": "Detect author-rebuttal section headers and prevent windows from crossing from response preamble back into reviewer text.",
    "wrong_or_too_broad_response_window": "Tighten response-end detection; stop at next numbered reviewer point, response marker, or page boundary when the next reviewer concern begins.",
    "wrong_or_too_broad_concern_window": "Tighten concern-start detection; avoid including previous author response text before the reviewer question.",
    "wrong_concern_window": "Re-anchor context to the nearest reviewer/comment/question marker preceding the response marker.",
    "no_direct_answer": "Keep as hard negative or exclude from gold alignment; direct response cannot be assumed from proximity alone.",
    "unknown_concern": "Send to taxonomy review; do not force unknown concerns into existing labels.",
    "unclear": "Route to manual review; current evidence is insufficient for automated decision.",
}


def build_error_analysis(records: list[dict[str, Any]]) -> dict[str, Any]:
    error_type_counts = Counter(record.get("error_case_type") or "unknown" for record in records)
    by_type: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        by_type[str(record.get("error_case_type") or "unknown")].append(record)

    error_types = {}
    for error_type, grouped in sorted(by_type.items()):
        error_types[error_type] = {
            "count": len(grouped),
            "share": round(len(grouped) / len(records), 4) if records else 0.0,
            "recommendation": ERROR_RECOMMENDATIONS.get(error_type, "Inspect examples and add a specific extraction guard."),
            "example_sample_ids": [str(record.get("sample_id")) for record in grouped[:5]],
            "example_pair_ids": [str(record.get("pair_id")) for record in grouped[:5]],
            "journal_family_counts": dict(Counter(record.get("journal_family") for record in grouped)),
        }

    return {
        "total_error_cases": len(records),
        "affected_paper_count": len({record.get("paper_id") for record in records}),
        "error_type_counts": dict(error_type_counts),
        "error_types": error_types,
        "top_recommendations": _top_recommendations(error_type_counts),
    }


def build_mini_gold_seed(records: list[dict[str, Any]], target_count: int = 50) -> list[dict[str, Any]]:
    ordered = _nested_round_robin(
        records,
        primary_key="concern_type_gold",
        secondary_keys=("response_strategy_gold", "journal_family", "validation_source"),
    )
    seed: list[dict[str, Any]] = []
    seen_pairs: set[str] = set()
    for record in ordered:
        if len(seed) >= target_count:
            break
        pair_id = str(record.get("pair_id") or "")
        if not pair_id or pair_id in seen_pairs:
            continue
        seeded = dict(record)
        seeded["mini_gold_status"] = "candidate_needs_human_confirmation"
        seeded["mini_gold_source"] = record.get("validation_source") or "unknown"
        seed.append(seeded)
        seen_pairs.add(pair_id)
    return seed


def generate_error_analysis_and_seed(input_dir: str | Path = DEFAULT_INPUT_DIR, target_count: int = 50) -> dict[str, Any]:
    directory = resolve_project_path(input_dir)
    error_cases = list(read_jsonl(directory / "phase1_extraction_error_cases.jsonl"))
    evaluation_pool = list(read_jsonl(directory / "phase1_evaluation_candidate_pool.jsonl"))

    analysis = build_error_analysis(error_cases)
    seed = build_mini_gold_seed(evaluation_pool, target_count=target_count)
    outputs = {
        "error_analysis_json": directory / "phase1_extraction_error_analysis.json",
        "error_analysis_md": directory / "phase1_extraction_error_analysis.md",
        "mini_gold_jsonl": directory / "phase1_mini_gold_seed_50.jsonl",
        "mini_gold_csv": directory / "phase1_mini_gold_seed_50.csv",
        "mini_gold_summary": directory / "phase1_mini_gold_seed_50_summary.json",
    }
    outputs["error_analysis_json"].write_text(
        json.dumps(analysis, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    outputs["error_analysis_md"].write_text(_error_report(analysis), encoding="utf-8")
    write_jsonl(outputs["mini_gold_jsonl"], seed)
    _write_csv(outputs["mini_gold_csv"], seed)

    summary = {
        "mini_gold_seed_count": len(seed),
        "target_count": target_count,
        "source_evaluation_pool_count": len(evaluation_pool),
        "mini_gold_source_counts": dict(Counter(record.get("mini_gold_source") for record in seed)),
        "concern_type_counts": dict(Counter(record.get("concern_type_gold") for record in seed)),
        "response_strategy_counts": dict(Counter(record.get("response_strategy_gold") for record in seed)),
        "journal_family_counts": dict(Counter(record.get("journal_family") for record in seed)),
        "files": {key: project_relative_path(path) for key, path in outputs.items()},
        "notes": [
            "Mini-gold seed rows are candidates requiring human confirmation.",
            "Use them to start P0 baseline scaffolding, not to report final benchmark performance.",
        ],
    }
    outputs["mini_gold_summary"].write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return {"error_analysis": analysis, "mini_gold_summary": summary}


def _top_recommendations(error_type_counts: Counter) -> list[dict[str, Any]]:
    return [
        {
            "error_case_type": error_type,
            "count": count,
            "recommendation": ERROR_RECOMMENDATIONS.get(error_type, "Inspect examples and add a specific extraction guard."),
        }
        for error_type, count in error_type_counts.most_common()
    ]


def _nested_round_robin(
    records: list[dict[str, Any]],
    primary_key: str,
    secondary_keys: tuple[str, ...],
) -> list[dict[str, Any]]:
    primary_groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        primary_groups[str(record.get(primary_key) or "")].append(record)

    ordered_groups = {
        key: _round_robin_by_keys(group, secondary_keys)
        for key, group in primary_groups.items()
    }
    ordered: list[dict[str, Any]] = []
    keys = sorted(ordered_groups)
    while keys:
        next_keys = []
        for key in keys:
            group = ordered_groups[key]
            if group:
                ordered.append(group.pop(0))
            if group:
                next_keys.append(key)
        keys = next_keys
    return ordered


def _round_robin_by_keys(records: list[dict[str, Any]], keys: tuple[str, ...]) -> list[dict[str, Any]]:
    grouped: dict[tuple[str, ...], list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        grouped[tuple(str(record.get(key) or "") for key in keys)].append(record)
    for group in grouped.values():
        group.sort(key=lambda record: str(record.get("sample_id") or ""))
    ordered: list[dict[str, Any]] = []
    group_keys = sorted(grouped)
    while group_keys:
        next_group_keys = []
        for key in group_keys:
            group = grouped[key]
            if group:
                ordered.append(group.pop(0))
            if group:
                next_group_keys.append(key)
        group_keys = next_group_keys
    return ordered


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
        "pair_id",
        "paper_id",
        "doi",
        "title",
        "journal",
        "journal_family",
        "mini_gold_status",
        "mini_gold_source",
        "concern_type_gold",
        "response_strategy_gold",
        "validation_source",
        "llm_confidence",
        "review_context_preview",
        "author_response_preview",
        "source_json_path",
        "source_field",
        "source_offsets",
    ]
    present = set().union(*(record.keys() for record in records)) if records else set()
    extras = sorted(present - set(preferred) - {"review_context", "author_response"})
    return [field for field in preferred if field in present] + extras


def _error_report(analysis: dict[str, Any]) -> str:
    lines = [
        "# v2709 Phase 1 Extraction Error Analysis",
        "",
        "## Summary",
        "",
        f"- Total error cases: `{analysis['total_error_cases']}`",
        f"- Affected papers: `{analysis['affected_paper_count']}`",
        f"- Error type counts: `{analysis['error_type_counts']}`",
        "",
        "## Recommended Fixes",
        "",
    ]
    for item in analysis["top_recommendations"]:
        lines.append(
            f"- `{item['error_case_type']}` ({item['count']}): {item['recommendation']}"
        )
    lines.extend(["", "## Error Type Details", ""])
    for error_type, detail in analysis["error_types"].items():
        lines.extend(
            [
                f"### {error_type}",
                "",
                f"- Count: `{detail['count']}`",
                f"- Share: `{detail['share']}`",
                f"- Journal families: `{detail['journal_family_counts']}`",
                f"- Example sample ids: `{detail['example_sample_ids']}`",
                f"- Recommendation: {detail['recommendation']}",
                "",
            ]
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Phase 1 extraction error analysis and mini-gold seed.")
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    parser.add_argument("--target-count", type=int, default=50)
    args = parser.parse_args()
    result = generate_error_analysis_and_seed(args.input_dir, target_count=args.target_count)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
