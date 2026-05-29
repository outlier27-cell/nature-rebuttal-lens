import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from peer_review_skills.api.openai_compatible import build_client_from_environment
from peer_review_skills.config import project_relative_path, resolve_project_path
from peer_review_skills.evaluation.phase1_pair_llm_review import (
    CONCERN_LABELS,
    RESPONSE_STRATEGY_LABELS,
    _normalize_bool,
    _normalize_choice,
    _normalize_confidence,
    _normalize_label_choice,
    _normalize_text_label,
    _truncate_text,
)
from peer_review_skills.io.jsonl import read_jsonl, write_jsonl


DEFAULT_INPUT_DIR = Path("data/evaluation/phase1_pair_validation/v2709")
DEFAULT_INPUT_FILE = "phase1_mini_gold_seed_50.jsonl"
DEFAULT_OUTPUT_DIR = Path("data/evaluation/phase1_pair_validation/v2709/model_revised_mini_gold")
DEFAULT_OUTPUT_STEM = "phase1_mini_gold_seed_50_model_revised"

ALIGNMENT_VALUES = {"yes", "no", "needs_review"}
BOOL_VALUES = {"yes", "no"}
EVIDENCE_TYPES = {
    "new_experiment",
    "new_analysis",
    "existing_evidence_or_explanation",
    "manuscript_or_supplement_revision",
    "resource_or_reproducibility_update",
    "statistical_evidence",
    "editorial_revision",
    "future_work_commitment",
    "claim_scope_revision",
    "unknown",
}


def build_revision_messages(record: dict[str, Any]) -> list[dict[str, str]]:
    payload = {
        "sample_id": record.get("sample_id"),
        "pair_id": record.get("pair_id"),
        "paper": {
            "doi": record.get("doi"),
            "title": record.get("title"),
            "journal": record.get("journal"),
            "year": record.get("year"),
            "journal_family": record.get("journal_family"),
        },
        "candidate_labels": {
            "concern_type_gold": record.get("concern_type_gold"),
            "response_strategy_gold": record.get("response_strategy_gold"),
            "evidence_type": record.get("evidence_type"),
            "mini_gold_status": record.get("mini_gold_status"),
            "mini_gold_source": record.get("mini_gold_source"),
            "alignment_correct": record.get("alignment_correct"),
            "usable_for_retrieval": record.get("usable_for_retrieval"),
            "usable_for_evaluation": record.get("usable_for_evaluation"),
        },
        "text": {
            "review_context": _truncate_text(str(record.get("review_context") or ""), 3200),
            "author_response": _truncate_text(str(record.get("author_response") or ""), 3200),
        },
        "source": {
            "source_json_path": record.get("source_json_path"),
            "source_field": record.get("source_field"),
            "source_offsets": record.get("source_offsets"),
            "offset_recoverable": record.get("offset_recoverable"),
            "auto_offset_recoverable": record.get("auto_offset_recoverable"),
        },
    }
    schema = {
        "alignment_correct": "yes|no|needs_review",
        "concern_type_gold": sorted(CONCERN_LABELS),
        "response_strategy_gold": sorted(RESPONSE_STRATEGY_LABELS),
        "evidence_type": sorted(EVIDENCE_TYPES),
        "usable_for_retrieval": "yes|no",
        "usable_for_evaluation": "yes|no",
        "needs_human_review": "yes|no",
        "revision_summary": "short description of changed or kept labels",
        "rationale": "short evidence-grounded explanation using only provided text",
        "confidence": "float 0..1",
    }
    return [
        {
            "role": "system",
            "content": (
                "You revise candidate mini-gold labels for a peer-review review-response dataset. "
                "Return only one JSON object. Use only the supplied review and author response text. "
                "Do not invent experiments, outcomes, or source facts. If the pair is not clearly aligned, "
                "set alignment_correct=no or needs_review and usable_for_evaluation=no."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "task": "mini_gold_revision",
                    "allowed_schema": schema,
                    "normalized_output_fields": [
                        "revised_alignment_correct",
                        "revised_concern_type_gold",
                        "revised_response_strategy_gold",
                        "revised_evidence_type",
                        "revised_usable_for_retrieval",
                        "revised_usable_for_evaluation",
                        "model_needs_human_review",
                    ],
                    "label_definitions": {
                        "concern_type_gold": sorted(CONCERN_LABELS),
                        "response_strategy_gold": sorted(RESPONSE_STRATEGY_LABELS),
                    },
                    "record": payload,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
        },
    ]


def normalize_revision_result(result: dict[str, Any], source_record: dict[str, Any]) -> dict[str, Any]:
    alignment = _normalize_choice(
        result.get("alignment_correct", result.get("revised_alignment_correct")),
        ALIGNMENT_VALUES,
        "needs_review",
    )
    concern = _normalize_label_choice(
        result.get("concern_type_gold", result.get("revised_concern_type_gold")),
        CONCERN_LABELS,
        str(source_record.get("concern_type_gold") or "unknown"),
    )
    strategy = _normalize_label_choice(
        result.get("response_strategy_gold", result.get("revised_response_strategy_gold")),
        RESPONSE_STRATEGY_LABELS,
        str(source_record.get("response_strategy_gold") or ""),
    )
    evidence_type = _normalize_text_label(result.get("evidence_type", result.get("revised_evidence_type")), "unknown")
    if evidence_type not in EVIDENCE_TYPES:
        evidence_type = "unknown"
    return {
        **source_record,
        "model_revision_reviewer_id": "deepseek-v3",
        "model_revision_status": "model_revised_needs_human_confirmation",
        "original_concern_type_gold": source_record.get("concern_type_gold"),
        "original_response_strategy_gold": source_record.get("response_strategy_gold"),
        "original_evidence_type": source_record.get("evidence_type"),
        "revised_alignment_correct": alignment,
        "revised_concern_type_gold": concern,
        "revised_response_strategy_gold": strategy,
        "revised_evidence_type": evidence_type,
        "revised_usable_for_retrieval": _normalize_bool(
            result.get("usable_for_retrieval", result.get("revised_usable_for_retrieval"))
        ),
        "revised_usable_for_evaluation": _normalize_bool(
            result.get("usable_for_evaluation", result.get("revised_usable_for_evaluation"))
        ),
        "model_needs_human_review": _normalize_bool(
            result.get("needs_human_review", result.get("model_needs_human_review"))
        ),
        "model_revision_summary": str(result.get("revision_summary") or "").strip(),
        "model_revision_rationale": str(result.get("rationale") or "").strip(),
        "model_revision_confidence": _normalize_confidence(result.get("confidence")),
    }


def revise_records(
    records: list[dict[str, Any]],
    client: Any,
    output_dir: str | Path,
    *,
    output_stem: str = DEFAULT_OUTPUT_STEM,
    existing_results: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    directory = Path(output_dir)
    directory.mkdir(parents=True, exist_ok=True)
    existing_by_sample = {
        str(record.get("sample_id")): record
        for record in (existing_results or [])
        if record.get("sample_id") and not record.get("error")
    }
    revised_records: list[dict[str, Any]] = list(existing_by_sample.values())
    errors: list[dict[str, Any]] = []

    for record in records:
        sample_id = str(record.get("sample_id") or "")
        if sample_id in existing_by_sample:
            continue
        try:
            result = client.create_chat_completion(
                build_revision_messages(record),
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            revised_records.append(normalize_revision_result(result, record))
        except Exception as exc:  # noqa: BLE001 - keep per-sample API errors for resumability.
            errors.append(
                {
                    "sample_id": record.get("sample_id"),
                    "pair_id": record.get("pair_id"),
                    "error": str(exc),
                }
            )

    revised_records = sorted(revised_records, key=lambda item: str(item.get("sample_id") or ""))
    output_jsonl = directory / f"{output_stem}.jsonl"
    output_csv = directory / f"{output_stem}.csv"
    confirmation_jsonl = directory / f"{output_stem}_human_confirmation.jsonl"
    confirmation_csv = directory / f"{output_stem}_human_confirmation.csv"
    summary_path = directory / f"{output_stem}_summary.json"
    errors_path = directory / f"{output_stem}_errors.jsonl"
    report_path = directory / f"{output_stem}_report.md"
    confirmation_records = [_human_confirmation_record(record) for record in revised_records]

    write_jsonl(output_jsonl, revised_records)
    _write_csv(output_csv, revised_records)
    write_jsonl(confirmation_jsonl, confirmation_records)
    _write_csv(confirmation_csv, confirmation_records)
    write_jsonl(errors_path, errors)
    summary = _summary(revised_records, errors, directory, output_stem)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(_report(summary), encoding="utf-8")
    return summary


def revise_package(
    input_dir: str | Path = DEFAULT_INPUT_DIR,
    *,
    input_file: str = DEFAULT_INPUT_FILE,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    output_stem: str = DEFAULT_OUTPUT_STEM,
    limit: int | None = None,
    client: Any | None = None,
) -> dict[str, Any]:
    source_dir = resolve_project_path(input_dir)
    target_dir = resolve_project_path(output_dir)
    records = list(read_jsonl(source_dir / input_file))
    if limit is not None:
        records = records[:limit]
    output_jsonl = target_dir / f"{output_stem}.jsonl"
    existing = list(read_jsonl(output_jsonl)) if output_jsonl.exists() else []
    active_client = client or build_client_from_environment()
    return revise_records(records, active_client, target_dir, output_stem=output_stem, existing_results=existing)


def _summary(
    revised_records: list[dict[str, Any]],
    errors: list[dict[str, Any]],
    directory: Path,
    output_stem: str,
) -> dict[str, Any]:
    changed_concern_count = sum(
        1
        for record in revised_records
        if record.get("original_concern_type_gold") != record.get("revised_concern_type_gold")
    )
    changed_strategy_count = sum(
        1
        for record in revised_records
        if record.get("original_response_strategy_gold") != record.get("revised_response_strategy_gold")
    )
    changed_evidence_count = sum(
        1
        for record in revised_records
        if record.get("original_evidence_type") != record.get("revised_evidence_type")
    )
    return {
        "reviewed_count": len(revised_records),
        "error_count": len(errors),
        "reviewer_model": "deepseek-v3",
        "changed_concern_count": changed_concern_count,
        "changed_strategy_count": changed_strategy_count,
        "changed_evidence_type_count": changed_evidence_count,
        "model_revision_status_counts": dict(Counter(record.get("model_revision_status") for record in revised_records)),
        "revised_alignment_correct_counts": dict(Counter(record.get("revised_alignment_correct") for record in revised_records)),
        "revised_usable_for_retrieval_counts": dict(
            Counter(record.get("revised_usable_for_retrieval") for record in revised_records)
        ),
        "revised_usable_for_evaluation_counts": dict(
            Counter(record.get("revised_usable_for_evaluation") for record in revised_records)
        ),
        "model_needs_human_review_counts": dict(
            Counter(record.get("model_needs_human_review") for record in revised_records)
        ),
        "revised_concern_type_counts": dict(Counter(record.get("revised_concern_type_gold") for record in revised_records)),
        "revised_response_strategy_counts": dict(
            Counter(record.get("revised_response_strategy_gold") for record in revised_records)
        ),
        "revised_evidence_type_counts": dict(Counter(record.get("revised_evidence_type") for record in revised_records)),
        "files": {
            "jsonl": project_relative_path(directory / f"{output_stem}.jsonl"),
            "csv": project_relative_path(directory / f"{output_stem}.csv"),
            "human_confirmation_jsonl": project_relative_path(directory / f"{output_stem}_human_confirmation.jsonl"),
            "human_confirmation_csv": project_relative_path(directory / f"{output_stem}_human_confirmation.csv"),
            "summary": project_relative_path(directory / f"{output_stem}_summary.json"),
            "errors": project_relative_path(directory / f"{output_stem}_errors.jsonl"),
            "report": project_relative_path(directory / f"{output_stem}_report.md"),
        },
        "notes": [
            "This is model-assisted revision, not final human gold.",
            "Rows remain marked model_revised_needs_human_confirmation.",
            "API key is read from environment and is not written to output files.",
        ],
    }


def _write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = _csv_fields(records)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            row = dict(record)
            for key, value in list(row.items()):
                if isinstance(value, (dict, list)):
                    row[key] = json.dumps(value, ensure_ascii=False, sort_keys=True)
            writer.writerow(row)


def _human_confirmation_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "sample_id": record.get("sample_id"),
        "pair_id": record.get("pair_id"),
        "paper_id": record.get("paper_id"),
        "doi": record.get("doi"),
        "title": record.get("title"),
        "journal": record.get("journal"),
        "journal_family": record.get("journal_family"),
        "original_concern_type_gold": record.get("original_concern_type_gold"),
        "model_revised_concern_type_gold": record.get("revised_concern_type_gold"),
        "human_final_concern_type_gold": "",
        "original_response_strategy_gold": record.get("original_response_strategy_gold"),
        "model_revised_response_strategy_gold": record.get("revised_response_strategy_gold"),
        "human_final_response_strategy_gold": "",
        "original_evidence_type": record.get("original_evidence_type"),
        "model_revised_evidence_type": record.get("revised_evidence_type"),
        "human_final_evidence_type": "",
        "model_revised_alignment_correct": record.get("revised_alignment_correct"),
        "human_final_alignment_correct": "",
        "model_revised_usable_for_retrieval": record.get("revised_usable_for_retrieval"),
        "human_final_usable_for_retrieval": "",
        "model_revised_usable_for_evaluation": record.get("revised_usable_for_evaluation"),
        "human_final_usable_for_evaluation": "",
        "human_accept_model_revision": "",
        "human_notes": "",
        "model_revision_confidence": record.get("model_revision_confidence"),
        "model_revision_summary": record.get("model_revision_summary"),
        "model_revision_rationale": record.get("model_revision_rationale"),
        "review_context_preview": record.get("review_context_preview"),
        "author_response_preview": record.get("author_response_preview"),
        "source_json_path": record.get("source_json_path"),
        "source_field": record.get("source_field"),
        "source_offsets": record.get("source_offsets"),
    }


def _csv_fields(records: list[dict[str, Any]]) -> list[str]:
    preferred = [
        "sample_id",
        "pair_id",
        "paper_id",
        "doi",
        "title",
        "journal",
        "journal_family",
        "model_revision_reviewer_id",
        "model_revision_status",
        "original_concern_type_gold",
        "revised_concern_type_gold",
        "original_response_strategy_gold",
        "revised_response_strategy_gold",
        "original_evidence_type",
        "revised_evidence_type",
        "revised_alignment_correct",
        "revised_usable_for_retrieval",
        "revised_usable_for_evaluation",
        "model_needs_human_review",
        "model_revision_confidence",
        "model_revision_summary",
        "model_revision_rationale",
        "mini_gold_status",
        "mini_gold_source",
        "review_context_preview",
        "author_response_preview",
        "source_json_path",
        "source_field",
        "source_offsets",
    ]
    present = set().union(*(record.keys() for record in records)) if records else set()
    extras = sorted(present - set(preferred) - {"review_context", "author_response"})
    return [field for field in preferred if field in present] + extras


def _report(summary: dict[str, Any]) -> str:
    return f"""# v2709 Phase 1 Mini-Gold Model Revision Report

## Scope

This report summarizes DeepSeek-v3 assisted revision of the 50-row Phase 1 candidate mini-gold seed. The result is a model-revised seed for the next baseline iteration. It is not final human gold.

## Counts

- Reviewed count: `{summary["reviewed_count"]}`
- Error count: `{summary["error_count"]}`
- Reviewer model: `{summary["reviewer_model"]}`
- Changed concern labels: `{summary["changed_concern_count"]}`
- Changed strategy labels: `{summary["changed_strategy_count"]}`
- Changed evidence labels: `{summary["changed_evidence_type_count"]}`

## Revised Usability

- Alignment: `{summary["revised_alignment_correct_counts"]}`
- Usable for retrieval: `{summary["revised_usable_for_retrieval_counts"]}`
- Usable for evaluation: `{summary["revised_usable_for_evaluation_counts"]}`
- Needs human review: `{summary["model_needs_human_review_counts"]}`

## Label Distributions

- Concern types: `{summary["revised_concern_type_counts"]}`
- Response strategies: `{summary["revised_response_strategy_counts"]}`
- Evidence types: `{summary["revised_evidence_type_counts"]}`

## Files

- `{summary["files"]["jsonl"]}`
- `{summary["files"]["csv"]}`
- `{summary["files"]["human_confirmation_jsonl"]}`
- `{summary["files"]["human_confirmation_csv"]}`
- `{summary["files"]["summary"]}`
- `{summary["files"]["errors"]}`
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Revise v2709 Phase 1 mini-gold seed with an LLM.")
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    parser.add_argument("--input-file", default=DEFAULT_INPUT_FILE)
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--output-stem", default=DEFAULT_OUTPUT_STEM)
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    summary = revise_package(
        args.input_dir,
        input_file=args.input_file,
        output_dir=args.output_dir,
        output_stem=args.output_stem,
        limit=args.limit,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
