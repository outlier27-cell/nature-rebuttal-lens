import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from peer_review_skills.config import project_relative_path, resolve_project_path
from peer_review_skills.io.jsonl import read_jsonl, write_jsonl


DEFAULT_INPUT_DIR = Path("data/evaluation/phase1_pair_validation/v2709")


def build_validation_pool(
    all_autofilled_records: list[dict[str, Any]],
    llm_reviewed_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    pool_by_pair: dict[str, dict[str, Any]] = {}

    for record in all_autofilled_records:
        if record.get("usable_for_evaluation") != "yes":
            continue
        candidate = dict(record)
        candidate["validation_source"] = "rule_autofill"
        candidate["validation_status"] = "candidate_needs_human_gold"
        pool_by_pair[str(candidate.get("pair_id"))] = candidate

    for record in llm_reviewed_records:
        if record.get("llm_usable_for_evaluation") != "yes" or record.get("llm_alignment_correct") != "yes":
            continue
        pair_id = str(record.get("pair_id"))
        candidate = dict(record)
        candidate["validation_source"] = "llm_rescued"
        candidate["validation_status"] = "candidate_needs_human_gold"
        candidate["concern_type_gold"] = record.get("llm_concern_type_gold") or record.get("concern_type_gold")
        candidate["response_strategy_gold"] = record.get("llm_response_strategy_gold") or record.get(
            "response_strategy_gold"
        )
        candidate["usable_for_evaluation"] = "yes"
        candidate["usable_for_retrieval"] = "yes"
        pool_by_pair[pair_id] = candidate

    return sorted(pool_by_pair.values(), key=lambda record: str(record.get("sample_id") or ""))


def build_retrieval_pool(
    all_autofilled_records: list[dict[str, Any]],
    llm_reviewed_records: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    pool_by_pair: dict[str, dict[str, Any]] = {}
    for record in all_autofilled_records:
        if record.get("usable_for_retrieval") != "yes":
            continue
        candidate = dict(record)
        candidate["validation_source"] = "rule_autofill"
        candidate["validation_status"] = "retrieval_candidate_needs_spot_check"
        pool_by_pair[str(candidate.get("pair_id"))] = candidate

    for record in llm_reviewed_records:
        if record.get("llm_usable_for_retrieval") != "yes" or record.get("llm_alignment_correct") != "yes":
            continue
        pair_id = str(record.get("pair_id"))
        candidate = dict(record)
        candidate["validation_source"] = "llm_rescued"
        candidate["validation_status"] = "retrieval_candidate_needs_spot_check"
        candidate["concern_type_gold"] = record.get("llm_concern_type_gold") or record.get("concern_type_gold")
        candidate["response_strategy_gold"] = record.get("llm_response_strategy_gold") or record.get(
            "response_strategy_gold"
        )
        candidate["usable_for_retrieval"] = "yes"
        pool_by_pair[pair_id] = candidate
    return sorted(pool_by_pair.values(), key=lambda record: str(record.get("sample_id") or ""))


def build_extraction_error_cases(llm_reviewed_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    for record in llm_reviewed_records:
        if record.get("llm_alignment_correct") not in {"no", "needs_review"}:
            continue
        error = dict(record)
        error["error_case_type"] = record.get("llm_alignment_error_type") or record.get("alignment_error_type")
        error["error_status"] = "confirmed_or_unresolved_by_llm"
        errors.append(error)
    return sorted(errors, key=lambda record: str(record.get("sample_id") or ""))


def generate_phase1_pools(input_dir: str | Path = DEFAULT_INPUT_DIR) -> dict[str, Any]:
    directory = resolve_project_path(input_dir)
    autofilled = list(read_jsonl(directory / "phase1_pair_validation_sample_autofilled.jsonl"))
    llm_disputed = list(read_jsonl(directory / "phase1_pair_validation_sample_llm_reviewed_disputed68.jsonl"))

    evaluation_pool = build_validation_pool(autofilled, llm_disputed)
    retrieval_pool = build_retrieval_pool(autofilled, llm_disputed)
    error_cases = build_extraction_error_cases(llm_disputed)

    outputs = {
        "evaluation_jsonl": directory / "phase1_evaluation_candidate_pool.jsonl",
        "evaluation_csv": directory / "phase1_evaluation_candidate_pool.csv",
        "retrieval_jsonl": directory / "phase1_retrieval_candidate_pool.jsonl",
        "retrieval_csv": directory / "phase1_retrieval_candidate_pool.csv",
        "errors_jsonl": directory / "phase1_extraction_error_cases.jsonl",
        "errors_csv": directory / "phase1_extraction_error_cases.csv",
        "summary": directory / "phase1_pool_summary.json",
        "report": directory / "phase1_pool_report.md",
    }
    write_jsonl(outputs["evaluation_jsonl"], evaluation_pool)
    write_jsonl(outputs["retrieval_jsonl"], retrieval_pool)
    write_jsonl(outputs["errors_jsonl"], error_cases)
    _write_csv(outputs["evaluation_csv"], evaluation_pool)
    _write_csv(outputs["retrieval_csv"], retrieval_pool)
    _write_csv(outputs["errors_csv"], error_cases)

    summary = _summary(evaluation_pool, retrieval_pool, error_cases, outputs)
    outputs["summary"].write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    outputs["report"].write_text(_report(summary), encoding="utf-8")
    return summary


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
        "sample_bucket",
        "validation_source",
        "validation_status",
        "error_case_type",
        "alignment_correct",
        "alignment_error_type",
        "llm_alignment_correct",
        "llm_alignment_error_type",
        "heuristic_concern_type",
        "concern_type_gold",
        "llm_concern_type_gold",
        "heuristic_response_strategy",
        "response_strategy_gold",
        "llm_response_strategy_gold",
        "evidence_type",
        "llm_evidence_type",
        "usable_for_retrieval",
        "usable_for_evaluation",
        "llm_usable_for_retrieval",
        "llm_usable_for_evaluation",
        "llm_confidence",
        "llm_rationale",
        "review_context_preview",
        "author_response_preview",
        "source_json_path",
        "source_field",
        "source_offsets",
    ]
    present = set().union(*(record.keys() for record in records)) if records else set()
    extras = sorted(present - set(preferred) - {"review_context", "author_response"})
    return [field for field in preferred if field in present] + extras


def _summary(
    evaluation_pool: list[dict[str, Any]],
    retrieval_pool: list[dict[str, Any]],
    error_cases: list[dict[str, Any]],
    outputs: dict[str, Path],
) -> dict[str, Any]:
    return {
        "evaluation_candidate_count": len(evaluation_pool),
        "retrieval_candidate_count": len(retrieval_pool),
        "extraction_error_case_count": len(error_cases),
        "evaluation_validation_source_counts": dict(Counter(record.get("validation_source") for record in evaluation_pool)),
        "retrieval_validation_source_counts": dict(Counter(record.get("validation_source") for record in retrieval_pool)),
        "error_case_type_counts": dict(Counter(record.get("error_case_type") for record in error_cases)),
        "evaluation_concern_type_counts": dict(Counter(record.get("concern_type_gold") for record in evaluation_pool)),
        "evaluation_response_strategy_counts": dict(
            Counter(record.get("response_strategy_gold") for record in evaluation_pool)
        ),
        "files": {name: project_relative_path(path) for name, path in outputs.items()},
        "notes": [
            "Pools are candidates for next-stage human gold review or baseline development.",
            "They are not final gold labels.",
            "LLM-rescued rows come from strict disputed68 DeepSeek review.",
        ],
    }


def _report(summary: dict[str, Any]) -> str:
    return f"""# v2709 Phase 1 Candidate Pools

## Purpose

This report consolidates rule-assisted and LLM-reviewed Phase 1 samples into candidate pools for Author Rebuttal Assistant development.

## Counts

- Evaluation candidate pool: `{summary["evaluation_candidate_count"]}`
- Retrieval candidate pool: `{summary["retrieval_candidate_count"]}`
- Extraction error cases: `{summary["extraction_error_case_count"]}`

## Sources

- Evaluation sources: `{summary["evaluation_validation_source_counts"]}`
- Retrieval sources: `{summary["retrieval_validation_source_counts"]}`

## Error Types

`{summary["error_case_type_counts"]}`

## Use

Use the evaluation pool for the next human-gold subset. Use the retrieval pool for early retrieval baseline experiments after spot checks. Use extraction error cases to improve segmentation and pair extraction.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Phase 1 candidate pools from autofill and LLM review.")
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    args = parser.parse_args()
    summary = generate_phase1_pools(args.input_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
