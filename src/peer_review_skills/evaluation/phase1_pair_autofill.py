import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from peer_review_skills.config import project_relative_path, resolve_project_path
from peer_review_skills.io.jsonl import read_jsonl, write_jsonl


DEFAULT_INPUT_DIR = Path("data/evaluation/phase1_pair_validation/v2709")
ANNOTATOR_ID = "codex_rule_assisted_v1"

CONCERN_KEYWORDS = {
    "ablation_mechanism": ("ablation", "mechanism", "component", "contribution", "feature importance"),
    "baseline_comparison": ("baseline", "compare", "comparison", "state-of-the-art", "sota", "benchmark"),
    "clarity_presentation": ("unclear", "clarify", "figure", "legend", "typo", "wording", "presentation"),
    "dataset_bias_ethics_safety": ("bias", "privacy", "ethics", "safety", "representative", "fairness"),
    "experimental_design": ("experiment", "control", "validation", "study design", "prospective"),
    "generalization_scope": ("generalize", "robust", "external", "other dataset", "different", "scope"),
    "novelty_positioning": ("novelty", "novel", "incremental", "contribution", "related work"),
    "reproducibility_reporting": ("code", "data availability", "reproduc", "github", "protocol", "parameter"),
    "statistics_significance": ("p-value", "significant", "statistical", "sample size", "confidence interval"),
    "theoretical_validity": ("assumption", "causal", "theoretical", "validity", "rationale"),
}

STRATEGY_KEYWORDS = {
    "acknowledge_and_fix": ("we agree", "we revised", "we have revised", "we added", "we corrected"),
    "add_new_analysis": ("additional analysis", "new analysis", "we analyzed", "we re-analyzed", "analysis has been"),
    "add_new_experiment": ("we performed", "we conducted", "additional experiment", "new experiment", "we tested"),
    "clarify_existing_evidence": ("to clarify", "we clarify", "we have clarified", "we explain"),
    "contest_reviewer_premise": ("we disagree", "respectfully disagree", "not applicable", "we do not agree"),
    "defer_future_work": ("future work", "future studies", "beyond the scope", "will be addressed"),
    "editorial_only_change": ("typo", "grammar", "legend", "format", "renamed"),
    "justify_method_choice": ("we chose", "because", "rationale", "we used", "we selected"),
    "narrow_claim_scope": ("toned down", "narrowed", "removed the claim", "softened"),
    "reframe_contribution": ("we emphasize", "reframed", "highlight"),
}


def autofill_annotation_record(record: dict[str, Any]) -> dict[str, Any]:
    filled = dict(record)
    review_text = str(record.get("review_context") or "")
    response_text = str(record.get("author_response") or "")
    concern = str(record.get("heuristic_concern_type") or "unknown")
    strategy = str(record.get("heuristic_response_strategy") or "unknown")
    offset_recoverable = bool(record.get("auto_offset_recoverable"))

    alignment_correct, alignment_error_type = _alignment_decision(review_text, response_text, concern, strategy)
    concern_gold, concern_multi = _concern_gold(concern, review_text)
    strategy_gold, strategy_secondary = _strategy_gold(strategy, response_text)
    evidence_type = _evidence_type(strategy_gold, response_text)
    unsafe = _unsafe_or_overclaiming(response_text)

    usable_for_retrieval = _yes_no(
        alignment_correct == "yes"
        and offset_recoverable
        and concern_gold != "unknown"
        and bool(strategy_gold)
    )
    usable_for_evaluation = _yes_no(
        usable_for_retrieval == "yes"
        and not record.get("context_truncated")
        and not record.get("response_truncated")
        and concern != "unknown"
        and unsafe == "no"
    )

    filled.update(
        {
            "annotator_id": ANNOTATOR_ID,
            "alignment_correct": alignment_correct,
            "alignment_error_type": alignment_error_type,
            "concern_type_gold": concern_gold,
            "concern_type_is_multi_label": _yes_no(concern_multi),
            "response_strategy_gold": strategy_gold,
            "response_strategy_secondary": strategy_secondary,
            "evidence_type": evidence_type,
            "unsafe_or_overclaiming_response": unsafe,
            "offset_recoverable": _yes_no(offset_recoverable),
            "usable_for_retrieval": usable_for_retrieval,
            "usable_for_evaluation": usable_for_evaluation,
            "notes": _notes(record, alignment_error_type, concern_gold, strategy_gold, unsafe),
        }
    )
    return filled


def autofill_package(input_dir: str | Path = DEFAULT_INPUT_DIR) -> dict[str, Any]:
    directory = resolve_project_path(input_dir)
    input_jsonl = directory / "phase1_pair_validation_sample.jsonl"
    records = [autofill_annotation_record(record) for record in read_jsonl(input_jsonl)]

    output_jsonl = directory / "phase1_pair_validation_sample_autofilled.jsonl"
    output_csv = directory / "phase1_pair_validation_sample_autofilled.csv"
    summary_path = directory / "autofill_summary.json"
    report_path = directory / "autofill_report.md"

    write_jsonl(output_jsonl, records)
    _write_csv(output_csv, records)
    summary = _summary(records, directory)
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(_report(summary), encoding="utf-8")
    return summary


def _alignment_decision(review_text: str, response_text: str, concern: str, strategy: str) -> tuple[str, str]:
    if _looks_like_author_response(review_text) and _looks_like_reviewer_comment(response_text):
        return "no", "reversed_context_response"
    if not review_text.strip() or not response_text.strip():
        return "no", "empty_span"
    if concern == "unknown":
        return "needs_review", "unknown_concern"
    if _looks_like_author_response(review_text):
        return "needs_review", "wrong_or_too_broad_concern_window"
    if _looks_like_reviewer_comment(response_text) and not _looks_like_author_response(response_text):
        return "needs_review", "wrong_or_too_broad_response_window"
    if strategy == "unknown":
        return "needs_review", "unknown_strategy"
    return "yes", "correct"


def _concern_gold(concern: str, review_text: str) -> tuple[str, bool]:
    if concern == "unknown":
        detected = _best_label(review_text, CONCERN_KEYWORDS)
        return detected or "unknown", False
    secondary = _secondary_labels(review_text, CONCERN_KEYWORDS, concern)
    return concern, bool(secondary)


def _strategy_gold(strategy: str, response_text: str) -> tuple[str, str]:
    if strategy == "unknown":
        return _best_label(response_text, STRATEGY_KEYWORDS) or "", ""
    secondary = _secondary_labels(response_text, STRATEGY_KEYWORDS, strategy)
    return strategy, secondary[0] if secondary else ""


def _evidence_type(strategy: str, response_text: str) -> str:
    lowered = response_text.lower()
    if strategy == "add_new_experiment":
        return "new_experiment"
    if strategy == "add_new_analysis":
        return "new_analysis"
    if strategy == "editorial_only_change":
        return "editorial_revision"
    if strategy == "defer_future_work":
        return "future_work_commitment"
    if strategy == "narrow_claim_scope":
        return "claim_scope_revision"
    if "figure" in lowered or "table" in lowered or "supplementary" in lowered:
        return "manuscript_or_supplement_revision"
    if "code" in lowered or "github" in lowered or "data" in lowered:
        return "resource_or_reproducibility_update"
    if "p-value" in lowered or "confidence interval" in lowered or "statistical" in lowered:
        return "statistical_evidence"
    return "existing_evidence_or_explanation"


def _unsafe_or_overclaiming(response_text: str) -> str:
    lowered = response_text.lower()
    risky = (
        "guarantee",
        "prove conclusively",
        "definitely proves",
        "no limitations",
        "without any limitation",
    )
    return _yes_no(any(term in lowered for term in risky))


def _looks_like_author_response(text: str) -> bool:
    lowered = text.lower()
    cues = (
        "we thank",
        "we agree",
        "we apologize",
        "we have revised",
        "we revised",
        "we added",
        "we performed",
        "response:",
    )
    return any(cue in lowered for cue in cues)


def _looks_like_reviewer_comment(text: str) -> bool:
    lowered = text.lower()
    cues = (
        "reviewer #",
        "remarks to the author",
        "the authors should",
        "the manuscript",
        "i have concerns",
        "please",
        "major comment",
        "minor comment",
    )
    return any(cue in lowered for cue in cues)


def _best_label(text: str, keywords_by_label: dict[str, tuple[str, ...]]) -> str:
    lowered = text.lower()
    scores = {
        label: sum(1 for keyword in keywords if keyword in lowered)
        for label, keywords in keywords_by_label.items()
    }
    label, score = max(scores.items(), key=lambda item: (item[1], item[0]))
    return label if score > 0 else ""


def _secondary_labels(text: str, keywords_by_label: dict[str, tuple[str, ...]], primary: str) -> list[str]:
    lowered = text.lower()
    scored = []
    for label, keywords in keywords_by_label.items():
        if label == primary:
            continue
        score = sum(1 for keyword in keywords if keyword in lowered)
        if score:
            scored.append((label, score))
    return [label for label, _ in sorted(scored, key=lambda item: (-item[1], item[0]))]


def _notes(
    record: dict[str, Any],
    alignment_error_type: str,
    concern_gold: str,
    strategy_gold: str,
    unsafe: str,
) -> str:
    notes = ["auto-filled; requires human review before gold use"]
    if alignment_error_type != "correct":
        notes.append(f"alignment={alignment_error_type}")
    if concern_gold == "unknown":
        notes.append("concern remains unknown")
    if not strategy_gold:
        notes.append("strategy remains empty")
    if record.get("context_truncated") or record.get("response_truncated"):
        notes.append("truncated text; recover source before evaluation")
    if unsafe == "yes":
        notes.append("potential overclaiming cue detected")
    return "; ".join(notes)


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


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
        "annotator_id",
        "alignment_correct",
        "alignment_error_type",
        "concern_type_gold",
        "concern_type_is_multi_label",
        "response_strategy_gold",
        "response_strategy_secondary",
        "evidence_type",
        "unsafe_or_overclaiming_response",
        "auto_offset_recoverable",
        "offset_recoverable",
        "usable_for_retrieval",
        "usable_for_evaluation",
        "notes",
        "context_truncated",
        "response_truncated",
        "review_context_preview",
        "author_response_preview",
        "source_json_path",
        "source_field",
        "source_offsets",
        "extraction_method",
    ]
    present = set().union(*(record.keys() for record in records)) if records else set()
    extras = sorted(present - set(preferred) - {"review_context", "author_response"})
    return [field for field in preferred if field in present] + extras


def _summary(records: list[dict[str, Any]], directory: Path) -> dict[str, Any]:
    return {
        "sample_count": len(records),
        "annotator_id": ANNOTATOR_ID,
        "input_jsonl": project_relative_path(directory / "phase1_pair_validation_sample.jsonl"),
        "files": {
            "jsonl": project_relative_path(directory / "phase1_pair_validation_sample_autofilled.jsonl"),
            "csv": project_relative_path(directory / "phase1_pair_validation_sample_autofilled.csv"),
            "summary": project_relative_path(directory / "autofill_summary.json"),
            "report": project_relative_path(directory / "autofill_report.md"),
        },
        "alignment_correct_counts": dict(Counter(record.get("alignment_correct") for record in records)),
        "alignment_error_type_counts": dict(Counter(record.get("alignment_error_type") for record in records)),
        "usable_for_retrieval_counts": dict(Counter(record.get("usable_for_retrieval") for record in records)),
        "usable_for_evaluation_counts": dict(Counter(record.get("usable_for_evaluation") for record in records)),
        "offset_recoverable_counts": dict(Counter(record.get("offset_recoverable") for record in records)),
        "concern_type_gold_counts": dict(Counter(record.get("concern_type_gold") for record in records)),
        "response_strategy_gold_counts": dict(Counter(record.get("response_strategy_gold") for record in records)),
        "evidence_type_counts": dict(Counter(record.get("evidence_type") for record in records)),
        "notes": [
            "These labels are rule-assisted first-pass annotations, not human gold labels.",
            "Use them to triage samples for manual review and estimate likely usable retrieval/evaluation pools.",
        ],
    }


def _report(summary: dict[str, Any]) -> str:
    return f"""# v2709 Phase 1 Pair Autofill Report

## What This Is

This is a rule-assisted first-pass fill of the Phase 1 pair validation sample. It is intended for data triage, not as final human gold annotation.

## Counts

- Sample count: `{summary["sample_count"]}`
- Annotator id: `{summary["annotator_id"]}`
- Alignment: `{summary["alignment_correct_counts"]}`
- Alignment error types: `{summary["alignment_error_type_counts"]}`
- Usable for retrieval: `{summary["usable_for_retrieval_counts"]}`
- Usable for evaluation: `{summary["usable_for_evaluation_counts"]}`
- Offset recoverable: `{summary["offset_recoverable_counts"]}`

## Output Files

- `{summary["files"]["jsonl"]}`
- `{summary["files"]["csv"]}`
- `{summary["files"]["summary"]}`

## Interpretation

Rows marked `usable_for_evaluation=yes` are candidates for stricter benchmark use after human review. Rows marked `usable_for_retrieval=yes` can be used as candidate retrieval examples after spot checks. Rows with `alignment_correct=no` or `needs_review` should be inspected before reuse.
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Autofill v2709 Phase 1 pair validation sample.")
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    args = parser.parse_args()
    summary = autofill_package(args.input_dir)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
