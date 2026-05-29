import argparse
import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from peer_review_skills.config import project_relative_path, resolve_project_path
from peer_review_skills.io.jsonl import read_jsonl, write_jsonl


DEFAULT_MINI_GOLD_PATH = Path(
    "data/evaluation/phase1_pair_validation/v2709/model_revised_mini_gold/phase1_mini_gold_seed_50_model_revised.jsonl"
)
DEFAULT_WORKFLOW_TRACE_PATH = Path(
    "data/evaluation/author_rebuttal_workflow/v2709_model_revised/workflow_traces.jsonl"
)
DEFAULT_OUTPUT_DIR = Path("data/evaluation/p2_model_confirmed_subset/v2709")


def build_model_confirmed_subset(
    mini_gold_path: str | Path = DEFAULT_MINI_GOLD_PATH,
    workflow_trace_path: str | Path = DEFAULT_WORKFLOW_TRACE_PATH,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
) -> dict[str, Any]:
    mini_gold_records = list(read_jsonl(resolve_project_path(mini_gold_path)))
    workflow_traces = list(read_jsonl(resolve_project_path(workflow_trace_path)))
    workflow_by_pair = {
        str(trace.get("pair_id") or ""): trace
        for trace in workflow_traces
        if trace.get("pair_id")
    }

    confirmed_records = []
    workflow_alignment = []
    unresolved_records = []

    for record in mini_gold_records:
        if str(record.get("revised_usable_for_evaluation") or "") != "yes":
            unresolved_records.append(_unresolved_record(record))
            continue
        pair_id = str(record.get("pair_id") or "")
        trace = workflow_by_pair.get(pair_id)
        confirmed = _confirmed_record(record, trace)
        confirmed_records.append(confirmed)
        workflow_alignment.append(_workflow_alignment_record(record, trace))

    confirmed_records = sorted(confirmed_records, key=lambda item: str(item.get("sample_id") or ""))
    workflow_alignment = sorted(workflow_alignment, key=lambda item: str(item.get("sample_id") or ""))
    unresolved_records = sorted(unresolved_records, key=lambda item: str(item.get("sample_id") or ""))

    target_dir = resolve_project_path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    confirmed_jsonl = target_dir / "phase2_model_confirmed_subset_45.jsonl"
    confirmed_csv = target_dir / "phase2_model_confirmed_subset_45.csv"
    alignment_jsonl = target_dir / "phase2_workflow_alignment_45.jsonl"
    alignment_csv = target_dir / "phase2_workflow_alignment_45.csv"
    unresolved_jsonl = target_dir / "phase2_unresolved_or_excluded_5.jsonl"
    unresolved_csv = target_dir / "phase2_unresolved_or_excluded_5.csv"
    summary_path = target_dir / "phase2_model_confirmed_subset_summary.json"
    report_path = target_dir / "phase2_model_confirmed_subset_report.md"

    write_jsonl(confirmed_jsonl, confirmed_records)
    _write_csv(confirmed_csv, confirmed_records)
    write_jsonl(alignment_jsonl, workflow_alignment)
    _write_csv(alignment_csv, workflow_alignment)
    write_jsonl(unresolved_jsonl, unresolved_records)
    _write_csv(unresolved_csv, unresolved_records)

    summary = _summary(
        confirmed_records=confirmed_records,
        workflow_alignment=workflow_alignment,
        unresolved_records=unresolved_records,
        target_dir=target_dir,
    )
    summary_path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    report_path.write_text(_report(summary), encoding="utf-8")
    return summary


def _confirmed_record(record: dict[str, Any], trace: dict[str, Any] | None) -> dict[str, Any]:
    trace_summary = {}
    if trace is not None:
        trace_summary = {
            "workflow_id": trace.get("workflow_id"),
            "workflow_stage_status": trace.get("stage_status"),
            "workflow_retrieval_method": trace.get("agents", {})
            .get("case_retrieval_agent", {})
            .get("retrieval_method"),
            "workflow_strategy_hit_at_5": trace.get("evaluation_signals", {}).get("strategy_hit_at_5"),
            "workflow_concern_hit_at_5": trace.get("evaluation_signals", {}).get("concern_hit_at_5"),
            "workflow_joint_hit_at_5": trace.get("evaluation_signals", {}).get("joint_hit_at_5"),
            "workflow_integrity_passed": trace.get("evaluation_signals", {}).get("integrity_passed"),
        }
    return {
        "sample_id": record.get("sample_id"),
        "pair_id": record.get("pair_id"),
        "paper_id": record.get("paper_id"),
        "doi": record.get("doi"),
        "title": record.get("title"),
        "journal": record.get("journal"),
        "journal_family": record.get("journal_family"),
        "validation_status": "model_confirmed_subset_not_human_gold",
        "validation_tier": "P2_model_confirmed",
        "alignment_correct": record.get("revised_alignment_correct"),
        "concern_type_label": record.get("revised_concern_type_gold"),
        "response_strategy_label": record.get("revised_response_strategy_gold"),
        "evidence_type_label": record.get("revised_evidence_type"),
        "usable_for_retrieval": record.get("revised_usable_for_retrieval"),
        "usable_for_evaluation": record.get("revised_usable_for_evaluation"),
        "model_revision_confidence": record.get("model_revision_confidence"),
        "model_revision_summary": record.get("model_revision_summary"),
        "model_revision_rationale": record.get("model_revision_rationale"),
        "review_context_preview": record.get("review_context_preview"),
        "author_response_preview": record.get("author_response_preview"),
        "source_json_path": record.get("source_json_path"),
        "source_field": record.get("source_field"),
        "source_offsets": record.get("source_offsets"),
        "offset_recoverable": record.get("offset_recoverable"),
        **trace_summary,
    }


def _workflow_alignment_record(record: dict[str, Any], trace: dict[str, Any] | None) -> dict[str, Any]:
    if trace is None:
        return {
            "sample_id": record.get("sample_id"),
            "pair_id": record.get("pair_id"),
            "workflow_trace_found": "no",
            "alignment_status": "missing_workflow_trace",
        }
    evidence_plan = trace.get("evidence_plan", {})
    return {
        "sample_id": record.get("sample_id"),
        "pair_id": record.get("pair_id"),
        "workflow_trace_found": "yes",
        "alignment_status": "aligned",
        "workflow_id": trace.get("workflow_id"),
        "workflow_stage_status": trace.get("stage_status"),
        "revised_concern_type_gold": record.get("revised_concern_type_gold"),
        "workflow_concern_type": trace.get("labels", {}).get("concern_type"),
        "workflow_risk_type": evidence_plan.get("risk_type"),
        "revised_response_strategy_gold": record.get("revised_response_strategy_gold"),
        "workflow_recommended_response_strategy": evidence_plan.get("recommended_response_strategy"),
        "workflow_strategy_hit_at_5": trace.get("evaluation_signals", {}).get("strategy_hit_at_5"),
        "workflow_concern_hit_at_5": trace.get("evaluation_signals", {}).get("concern_hit_at_5"),
        "workflow_joint_hit_at_5": trace.get("evaluation_signals", {}).get("joint_hit_at_5"),
        "workflow_integrity_passed": trace.get("evaluation_signals", {}).get("integrity_passed"),
        "outline_generation_mode": trace.get("outline", {}).get("generation_mode"),
        "outline_confidence": trace.get("outline", {}).get("confidence"),
        "integrity_issue_count": len(trace.get("integrity_check", {}).get("issues", [])),
    }


def _unresolved_record(record: dict[str, Any]) -> dict[str, Any]:
    return {
        "sample_id": record.get("sample_id"),
        "pair_id": record.get("pair_id"),
        "paper_id": record.get("paper_id"),
        "doi": record.get("doi"),
        "title": record.get("title"),
        "journal": record.get("journal"),
        "journal_family": record.get("journal_family"),
        "revised_alignment_correct": record.get("revised_alignment_correct"),
        "revised_usable_for_retrieval": record.get("revised_usable_for_retrieval"),
        "revised_usable_for_evaluation": record.get("revised_usable_for_evaluation"),
        "revised_concern_type_gold": record.get("revised_concern_type_gold"),
        "revised_response_strategy_gold": record.get("revised_response_strategy_gold"),
        "revised_evidence_type": record.get("revised_evidence_type"),
        "model_revision_summary": record.get("model_revision_summary"),
        "model_revision_rationale": record.get("model_revision_rationale"),
        "source_json_path": record.get("source_json_path"),
        "source_field": record.get("source_field"),
        "source_offsets": record.get("source_offsets"),
    }


def _summary(
    *,
    confirmed_records: list[dict[str, Any]],
    workflow_alignment: list[dict[str, Any]],
    unresolved_records: list[dict[str, Any]],
    target_dir: Path,
) -> dict[str, Any]:
    return {
        "subset_id": "p2_model_confirmed_subset_v2709",
        "confirmed_count": len(confirmed_records),
        "unresolved_or_excluded_count": len(unresolved_records),
        "workflow_aligned_count": sum(1 for row in workflow_alignment if row.get("workflow_trace_found") == "yes"),
        "workflow_missing_count": sum(1 for row in workflow_alignment if row.get("workflow_trace_found") != "yes"),
        "label_counts": {
            "concern_type": dict(Counter(row.get("concern_type_label") for row in confirmed_records)),
            "response_strategy": dict(Counter(row.get("response_strategy_label") for row in confirmed_records)),
            "evidence_type": dict(Counter(row.get("evidence_type_label") for row in confirmed_records)),
        },
        "workflow_signal_counts": {
            "strategy_hit_at_5": dict(Counter(row.get("workflow_strategy_hit_at_5") for row in confirmed_records)),
            "concern_hit_at_5": dict(Counter(row.get("workflow_concern_hit_at_5") for row in confirmed_records)),
            "joint_hit_at_5": dict(Counter(row.get("workflow_joint_hit_at_5") for row in confirmed_records)),
            "integrity_passed": dict(Counter(row.get("workflow_integrity_passed") for row in confirmed_records)),
        },
        "files": {
            "confirmed_jsonl": project_relative_path(target_dir / "phase2_model_confirmed_subset_45.jsonl"),
            "confirmed_csv": project_relative_path(target_dir / "phase2_model_confirmed_subset_45.csv"),
            "workflow_alignment_jsonl": project_relative_path(target_dir / "phase2_workflow_alignment_45.jsonl"),
            "workflow_alignment_csv": project_relative_path(target_dir / "phase2_workflow_alignment_45.csv"),
            "unresolved_jsonl": project_relative_path(target_dir / "phase2_unresolved_or_excluded_5.jsonl"),
            "unresolved_csv": project_relative_path(target_dir / "phase2_unresolved_or_excluded_5.csv"),
            "summary": project_relative_path(target_dir / "phase2_model_confirmed_subset_summary.json"),
            "report": project_relative_path(target_dir / "phase2_model_confirmed_subset_report.md"),
        },
        "notes": [
            "This subset is model-confirmed and organized for small-batch evaluation, not final human gold.",
            "It should be used for controlled baseline iteration and workflow inspection, not final benchmark claims.",
            "Rows excluded here should remain in unresolved review queues until manual confirmation is available.",
        ],
    }


def _report(summary: dict[str, Any]) -> str:
    return f"""# P2 Model-Confirmed Small-Batch Subset Report

## Scope

This report organizes the current 50-row model-revised mini-gold into a smaller usable subset for controlled evaluation.
It is not final human gold.

## Counts

- Confirmed subset count: `{summary["confirmed_count"]}`
- Unresolved or excluded count: `{summary["unresolved_or_excluded_count"]}`
- Workflow aligned count: `{summary["workflow_aligned_count"]}`
- Workflow missing count: `{summary["workflow_missing_count"]}`

## Label Distribution

- Concern types: `{summary["label_counts"]["concern_type"]}`
- Response strategies: `{summary["label_counts"]["response_strategy"]}`
- Evidence types: `{summary["label_counts"]["evidence_type"]}`

## Workflow Signal Distribution

- Strategy hit@5: `{summary["workflow_signal_counts"]["strategy_hit_at_5"]}`
- Concern hit@5: `{summary["workflow_signal_counts"]["concern_hit_at_5"]}`
- Joint hit@5: `{summary["workflow_signal_counts"]["joint_hit_at_5"]}`
- Integrity passed: `{summary["workflow_signal_counts"]["integrity_passed"]}`

## Files

- `{summary["files"]["confirmed_jsonl"]}`
- `{summary["files"]["confirmed_csv"]}`
- `{summary["files"]["workflow_alignment_jsonl"]}`
- `{summary["files"]["workflow_alignment_csv"]}`
- `{summary["files"]["unresolved_jsonl"]}`
- `{summary["files"]["unresolved_csv"]}`
- `{summary["files"]["summary"]}`
- `{summary["files"]["report"]}`
"""


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


def _csv_fields(records: list[dict[str, Any]]) -> list[str]:
    preferred = [
        "sample_id",
        "pair_id",
        "paper_id",
        "doi",
        "title",
        "journal",
        "journal_family",
        "validation_status",
        "validation_tier",
        "alignment_correct",
        "concern_type_label",
        "response_strategy_label",
        "evidence_type_label",
        "usable_for_retrieval",
        "usable_for_evaluation",
        "model_revision_confidence",
        "workflow_id",
        "workflow_stage_status",
        "workflow_retrieval_method",
        "workflow_strategy_hit_at_5",
        "workflow_concern_hit_at_5",
        "workflow_joint_hit_at_5",
        "workflow_integrity_passed",
        "source_json_path",
        "source_field",
        "source_offsets",
    ]
    present = set().union(*(record.keys() for record in records)) if records else set()
    extras = sorted(present - set(preferred))
    return [field for field in preferred if field in present] + extras


def main() -> None:
    parser = argparse.ArgumentParser(description="Build model-confirmed small-batch subset from revised mini-gold and workflow traces.")
    parser.add_argument("--mini-gold-path", default=str(DEFAULT_MINI_GOLD_PATH))
    parser.add_argument("--workflow-trace-path", default=str(DEFAULT_WORKFLOW_TRACE_PATH))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    args = parser.parse_args()
    summary = build_model_confirmed_subset(
        mini_gold_path=args.mini_gold_path,
        workflow_trace_path=args.workflow_trace_path,
        output_dir=args.output_dir,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
