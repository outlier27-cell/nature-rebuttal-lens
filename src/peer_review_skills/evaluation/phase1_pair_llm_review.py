import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from peer_review_skills.api.openai_compatible import build_client_from_environment
from peer_review_skills.config import project_relative_path, resolve_project_path
from peer_review_skills.io.jsonl import read_jsonl, write_jsonl


DEFAULT_INPUT_DIR = Path("data/evaluation/phase1_pair_validation/v2709")
DEFAULT_INPUT_FILE = "phase1_pair_validation_sample_autofilled.jsonl"
DEFAULT_OUTPUT_STEM = "phase1_pair_validation_sample_llm_reviewed"
CONCERN_LABELS = {
    "ablation_mechanism",
    "baseline_comparison",
    "clarity_presentation",
    "dataset_bias_ethics_safety",
    "experimental_design",
    "generalization_scope",
    "novelty_positioning",
    "reproducibility_reporting",
    "statistics_significance",
    "theoretical_validity",
    "unknown",
}
RESPONSE_STRATEGY_LABELS = {
    "acknowledge_and_fix",
    "add_new_analysis",
    "add_new_experiment",
    "clarify_existing_evidence",
    "contest_reviewer_premise",
    "defer_future_work",
    "editorial_only_change",
    "justify_method_choice",
    "narrow_claim_scope",
    "reframe_contribution",
}
ALIGNMENT_VALUES = {"yes", "no", "needs_review"}
BOOL_VALUES = {"yes", "no"}
ALIGNMENT_ERROR_TYPES = {
    "correct",
    "wrong_concern_window",
    "wrong_response_window",
    "wrong_or_too_broad_concern_window",
    "wrong_or_too_broad_response_window",
    "reversed_context_response",
    "too_broad_context",
    "multi_issue_response",
    "no_direct_answer",
    "offset_error",
    "unknown_concern",
    "unclear",
}


def select_review_candidates(records: list[dict[str, Any]], selection: str = "disputed") -> list[dict[str, Any]]:
    if selection == "all":
        return list(records)
    if selection == "evaluation_candidates":
        return [record for record in records if record.get("usable_for_evaluation") == "yes"]
    if selection != "disputed":
        raise ValueError("selection must be one of: disputed, all, evaluation_candidates")
    return [record for record in records if record.get("alignment_correct") in {"needs_review", "no"}]


def build_review_messages(record: dict[str, Any]) -> list[dict[str, str]]:
    payload = {
        "sample_id": record.get("sample_id"),
        "pair_id": record.get("pair_id"),
        "paper": {
            "doi": record.get("doi"),
            "title": record.get("title"),
            "journal": record.get("journal"),
            "year": record.get("year"),
        },
        "candidate_labels": {
            "heuristic_concern_type": record.get("heuristic_concern_type"),
            "heuristic_response_strategy": record.get("heuristic_response_strategy"),
            "rule_alignment_correct": record.get("alignment_correct"),
            "rule_alignment_error_type": record.get("alignment_error_type"),
            "rule_usable_for_retrieval": record.get("usable_for_retrieval"),
            "rule_usable_for_evaluation": record.get("usable_for_evaluation"),
        },
        "text": {
            "review_context": _truncate_text(str(record.get("review_context") or ""), 2500),
            "author_response": _truncate_text(str(record.get("author_response") or ""), 2500),
        },
        "source": {
            "source_json_path": record.get("source_json_path"),
            "source_field": record.get("source_field"),
            "source_offsets": record.get("source_offsets"),
            "auto_offset_recoverable": record.get("auto_offset_recoverable"),
        },
    }
    schema = {
        "alignment_correct": "yes|no|needs_review",
        "alignment_error_type": sorted(ALIGNMENT_ERROR_TYPES),
        "concern_type_gold": sorted(CONCERN_LABELS),
        "concern_type_is_multi_label": "yes|no",
        "response_strategy_gold": sorted(RESPONSE_STRATEGY_LABELS),
        "response_strategy_secondary": sorted(RESPONSE_STRATEGY_LABELS) + [""],
        "evidence_type": "new_experiment|new_analysis|existing_evidence_or_explanation|manuscript_or_supplement_revision|resource_or_reproducibility_update|statistical_evidence|editorial_revision|future_work_commitment|claim_scope_revision|unknown",
        "unsafe_or_overclaiming_response": "yes|no",
        "usable_for_retrieval": "yes|no",
        "usable_for_evaluation": "yes|no",
        "rationale": "short evidence-grounded explanation",
        "confidence": "float 0..1",
    }
    return [
        {
            "role": "system",
            "content": (
                "You audit peer-review review-response pair quality for a research dataset. "
                "Return only one JSON object. Do not invent facts beyond the provided text. "
                "Mark usable_for_evaluation=yes only when the review concern and author response are clearly aligned."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "task": "review_response_pair_quality_audit",
                    "allowed_schema": schema,
                    "record": payload,
                },
                ensure_ascii=False,
                sort_keys=True,
            ),
        },
    ]


def normalize_review_result(result: dict[str, Any], source_record: dict[str, Any]) -> dict[str, Any]:
    alignment = _normalize_choice(result.get("alignment_correct"), ALIGNMENT_VALUES, "needs_review")
    concern = _normalize_label_choice(result.get("concern_type_gold"), CONCERN_LABELS, "unknown")
    strategy = _normalize_label_choice(
        result.get("response_strategy_gold"),
        RESPONSE_STRATEGY_LABELS,
        str(source_record.get("response_strategy_gold") or source_record.get("heuristic_response_strategy") or ""),
    )
    secondary = _normalize_label_choice(result.get("response_strategy_secondary"), RESPONSE_STRATEGY_LABELS, "")
    if secondary == strategy:
        secondary = ""
    confidence = _normalize_confidence(result.get("confidence"))
    return {
        "sample_id": source_record.get("sample_id"),
        "pair_id": source_record.get("pair_id"),
        "llm_reviewer_id": "deepseek-v3",
        "llm_alignment_correct": alignment,
        "llm_alignment_error_type": _normalize_choice(
            result.get("alignment_error_type"),
            ALIGNMENT_ERROR_TYPES,
            "unclear" if alignment != "yes" else "correct",
        ),
        "llm_concern_type_gold": concern,
        "llm_concern_type_is_multi_label": _normalize_bool(result.get("concern_type_is_multi_label")),
        "llm_response_strategy_gold": strategy,
        "llm_response_strategy_secondary": secondary,
        "llm_evidence_type": _normalize_text_label(result.get("evidence_type"), "unknown"),
        "llm_unsafe_or_overclaiming_response": _normalize_bool(result.get("unsafe_or_overclaiming_response")),
        "llm_usable_for_retrieval": _normalize_bool(result.get("usable_for_retrieval")),
        "llm_usable_for_evaluation": _normalize_bool(result.get("usable_for_evaluation")),
        "llm_rationale": str(result.get("rationale") or "").strip(),
        "llm_confidence": confidence,
        "llm_review_status": "reviewed",
    }


def review_records(
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
    reviewed_records: list[dict[str, Any]] = list(existing_by_sample.values())
    errors: list[dict[str, Any]] = []

    for record in records:
        sample_id = str(record.get("sample_id") or "")
        if sample_id in existing_by_sample:
            continue
        try:
            result = client.create_chat_completion(
                build_review_messages(record),
                response_format={"type": "json_object"},
                temperature=0.0,
            )
            normalized = normalize_review_result(result, record)
            reviewed_records.append({**record, **normalized})
        except Exception as exc:  # noqa: BLE001 - keep per-sample API errors.
            errors.append(
                {
                    "sample_id": record.get("sample_id"),
                    "pair_id": record.get("pair_id"),
                    "error": str(exc),
                }
            )

    reviewed_records = sorted(reviewed_records, key=lambda item: str(item.get("sample_id") or ""))
    output_jsonl = directory / f"{output_stem}.jsonl"
    output_csv = directory / f"{output_stem}.csv"
    summary_path = directory / f"{output_stem}_summary.json"
    errors_path = directory / f"{output_stem}_errors.jsonl"
    report_path = directory / f"{output_stem}_report.md"

    write_jsonl(output_jsonl, reviewed_records)
    _write_csv(output_csv, reviewed_records)
    write_jsonl(errors_path, errors)
    summary = _summary(reviewed_records, errors, directory, output_stem)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(_report(summary), encoding="utf-8")
    return summary


def review_package(
    input_dir: str | Path = DEFAULT_INPUT_DIR,
    *,
    input_file: str = DEFAULT_INPUT_FILE,
    output_stem: str = DEFAULT_OUTPUT_STEM,
    selection: str = "disputed",
    limit: int | None = None,
    client: Any | None = None,
) -> dict[str, Any]:
    directory = resolve_project_path(input_dir)
    records = list(read_jsonl(directory / input_file))
    candidates = select_review_candidates(records, selection=selection)
    if limit is not None:
        candidates = candidates[:limit]
    output_jsonl = directory / f"{output_stem}.jsonl"
    existing = list(read_jsonl(output_jsonl)) if output_jsonl.exists() else []
    active_client = client or build_client_from_environment()
    return review_records(candidates, active_client, directory, output_stem=output_stem, existing_results=existing)


def _normalize_choice(value: Any, allowed: set[str], default: str) -> str:
    normalized = _normalize_yes_no_alias(value)
    if normalized in allowed:
        return normalized
    label = _normalize_text_label(value, "")
    return label if label in allowed else default


def _normalize_bool(value: Any) -> str:
    normalized = _normalize_yes_no_alias(value)
    return normalized if normalized in BOOL_VALUES else "no"


def _normalize_yes_no_alias(value: Any) -> str:
    if isinstance(value, bool):
        return "yes" if value else "no"
    lowered = str(value or "").strip().lower()
    if lowered in {"true", "correct", "aligned", "yes", "y"}:
        return "yes"
    if lowered in {"false", "incorrect", "not_aligned", "no", "n"}:
        return "no"
    return lowered


def _normalize_label_choice(value: Any, allowed: set[str], default: str) -> str:
    label = _normalize_text_label(value, "")
    aliases = {
        "presentation_clarity": "clarity_presentation",
        "new_experiment": "add_new_experiment",
        "new_analysis": "add_new_analysis",
        "textual_clarification": "clarify_existing_evidence",
        "provide_textual_clarification": "clarify_existing_evidence",
    }
    label = aliases.get(label, label)
    return label if label in allowed else default


def _normalize_text_label(value: Any, default: str) -> str:
    text = str(value or "").strip().lower()
    if not text:
        return default
    normalized = "".join(ch if ch.isalnum() else "_" for ch in text)
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    return normalized.strip("_") or default


def _normalize_confidence(value: Any) -> float:
    try:
        confidence = float(value)
    except (TypeError, ValueError):
        return 0.0
    return min(1.0, max(0.0, confidence))


def _truncate_text(text: str, limit: int) -> str:
    if len(text) <= limit:
        return text
    return text[: limit - 20] + "\n...[truncated]..."


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
        "heuristic_concern_type",
        "heuristic_response_strategy",
        "alignment_correct",
        "alignment_error_type",
        "usable_for_retrieval",
        "usable_for_evaluation",
        "llm_reviewer_id",
        "llm_alignment_correct",
        "llm_alignment_error_type",
        "llm_concern_type_gold",
        "llm_concern_type_is_multi_label",
        "llm_response_strategy_gold",
        "llm_response_strategy_secondary",
        "llm_evidence_type",
        "llm_unsafe_or_overclaiming_response",
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
    reviewed_records: list[dict[str, Any]],
    errors: list[dict[str, Any]],
    directory: Path,
    output_stem: str,
) -> dict[str, Any]:
    return {
        "reviewed_count": len(reviewed_records),
        "error_count": len(errors),
        "reviewer_model": "deepseek-v3",
        "files": {
            "jsonl": project_relative_path(directory / f"{output_stem}.jsonl"),
            "csv": project_relative_path(directory / f"{output_stem}.csv"),
            "summary": project_relative_path(directory / f"{output_stem}_summary.json"),
            "errors": project_relative_path(directory / f"{output_stem}_errors.jsonl"),
            "report": project_relative_path(directory / f"{output_stem}_report.md"),
        },
        "llm_alignment_correct_counts": dict(Counter(record.get("llm_alignment_correct") for record in reviewed_records)),
        "llm_alignment_error_type_counts": dict(
            Counter(record.get("llm_alignment_error_type") for record in reviewed_records)
        ),
        "llm_usable_for_retrieval_counts": dict(
            Counter(record.get("llm_usable_for_retrieval") for record in reviewed_records)
        ),
        "llm_usable_for_evaluation_counts": dict(
            Counter(record.get("llm_usable_for_evaluation") for record in reviewed_records)
        ),
        "llm_concern_type_counts": dict(Counter(record.get("llm_concern_type_gold") for record in reviewed_records)),
        "llm_response_strategy_counts": dict(
            Counter(record.get("llm_response_strategy_gold") for record in reviewed_records)
        ),
        "notes": [
            "LLM review is model-assisted validation, not final human gold.",
            "API key is read from environment and is not written to output files.",
        ],
    }


def _report(summary: dict[str, Any]) -> str:
    return f"""# v2709 Phase 1 LLM Review Report

## Scope

Model-assisted review for Phase 1 pair validation samples. This is used to prioritize manual verification and clean retrieval/evaluation candidates.

## Counts

- Reviewed count: `{summary["reviewed_count"]}`
- Error count: `{summary["error_count"]}`
- Reviewer model: `{summary["reviewer_model"]}`
- LLM alignment: `{summary["llm_alignment_correct_counts"]}`
- LLM usable for retrieval: `{summary["llm_usable_for_retrieval_counts"]}`
- LLM usable for evaluation: `{summary["llm_usable_for_evaluation_counts"]}`

## Files

- `{summary["files"]["jsonl"]}`
- `{summary["files"]["csv"]}`
- `{summary["files"]["summary"]}`
- `{summary["files"]["errors"]}`
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Run LLM review for v2709 Phase 1 pair validation samples.")
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    parser.add_argument("--input-file", default=DEFAULT_INPUT_FILE)
    parser.add_argument("--output-stem", default=DEFAULT_OUTPUT_STEM)
    parser.add_argument("--selection", default="disputed", choices=["disputed", "all", "evaluation_candidates"])
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()
    summary = review_package(
        args.input_dir,
        input_file=args.input_file,
        output_stem=args.output_stem,
        selection=args.selection,
        limit=args.limit,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
