import argparse
import json
import shutil
from pathlib import Path
from typing import Any

from peer_review_skills.config import project_relative_path, resolve_project_path
from peer_review_skills.evaluation.p0_baselines import generate_p0_baselines
from peer_review_skills.io.jsonl import read_jsonl, write_jsonl


DEFAULT_ORIGINAL_PHASE1_DIR = Path("data/evaluation/phase1_pair_validation/v2709")
DEFAULT_REVISED_MODEL_DIR = Path("data/evaluation/phase1_pair_validation/v2709/model_revised_mini_gold")
DEFAULT_ORIGINAL_P0_DIR = Path("data/evaluation/p0_baselines/v2709")
DEFAULT_REVISED_P0_DIR = Path("data/evaluation/p0_baselines/v2709_model_revised")
DEFAULT_COMPARISON_DIR = Path("data/evaluation/p0_baselines/v2709_comparison")
REVISED_SOURCE_FILE = "phase1_mini_gold_seed_50_model_revised.jsonl"


def prepare_revised_seed_records(
    records: list[dict[str, Any]],
    *,
    include_unusable: bool = False,
) -> list[dict[str, Any]]:
    prepared = []
    for record in records:
        if not include_unusable and record.get("revised_usable_for_evaluation") != "yes":
            continue
        converted = dict(record)
        converted["concern_type_gold"] = record.get("revised_concern_type_gold") or record.get("concern_type_gold")
        converted["response_strategy_gold"] = record.get("revised_response_strategy_gold") or record.get(
            "response_strategy_gold"
        )
        converted["evidence_type"] = record.get("revised_evidence_type") or record.get("evidence_type")
        converted["usable_for_retrieval"] = record.get("revised_usable_for_retrieval") or record.get(
            "usable_for_retrieval"
        )
        converted["usable_for_evaluation"] = record.get("revised_usable_for_evaluation") or record.get(
            "usable_for_evaluation"
        )
        converted["alignment_correct"] = record.get("revised_alignment_correct") or record.get("alignment_correct")
        converted["mini_gold_status"] = record.get("model_revision_status") or "model_revised_needs_human_confirmation"
        converted["mini_gold_source"] = "deepseek_v3_model_revision"
        prepared.append(converted)
    return sorted(prepared, key=lambda item: str(item.get("sample_id") or ""))


def compare_p0_summaries(original_summary: dict[str, Any], revised_summary: dict[str, Any]) -> dict[str, Any]:
    metrics = {
        "concern_accuracy": (
            _metric(original_summary, ("concern_extraction", "metrics", "accuracy")),
            _metric(revised_summary, ("concern_extraction", "metrics", "accuracy")),
        ),
        "concern_macro_f1": (
            _metric(original_summary, ("concern_extraction", "metrics", "macro_f1")),
            _metric(revised_summary, ("concern_extraction", "metrics", "macro_f1")),
        ),
        "strategy_recall_at_1": (
            _metric(original_summary, ("strategy_retrieval", "metrics", "strategy_recall_at_1")),
            _metric(revised_summary, ("strategy_retrieval", "metrics", "strategy_recall_at_1")),
        ),
        "strategy_recall_at_3": (
            _metric(original_summary, ("strategy_retrieval", "metrics", "strategy_recall_at_3")),
            _metric(revised_summary, ("strategy_retrieval", "metrics", "strategy_recall_at_3")),
        ),
        "strategy_recall_at_5": (
            _metric(original_summary, ("strategy_retrieval", "metrics", "strategy_recall_at_5")),
            _metric(revised_summary, ("strategy_retrieval", "metrics", "strategy_recall_at_5")),
        ),
        "concern_match_at_5": (
            _metric(original_summary, ("strategy_retrieval", "metrics", "concern_match_at_5")),
            _metric(revised_summary, ("strategy_retrieval", "metrics", "concern_match_at_5")),
        ),
        "joint_strategy_concern_match_at_5": (
            _metric(original_summary, ("strategy_retrieval", "metrics", "joint_strategy_concern_match_at_5")),
            _metric(revised_summary, ("strategy_retrieval", "metrics", "joint_strategy_concern_match_at_5")),
        ),
    }
    return {
        "original_mini_gold_count": int(_metric(original_summary, ("input", "mini_gold_count"))),
        "revised_mini_gold_count": int(_metric(revised_summary, ("input", "mini_gold_count"))),
        "metrics": {
            name: {"original": original, "revised": revised}
            for name, (original, revised) in metrics.items()
        },
        "metric_deltas": {
            name: revised - original
            for name, (original, revised) in metrics.items()
        },
    }


def generate_p0_baseline_comparison(
    original_phase1_dir: str | Path = DEFAULT_ORIGINAL_PHASE1_DIR,
    revised_model_dir: str | Path = DEFAULT_REVISED_MODEL_DIR,
    original_p0_dir: str | Path = DEFAULT_ORIGINAL_P0_DIR,
    revised_p0_dir: str | Path = DEFAULT_REVISED_P0_DIR,
    comparison_dir: str | Path = DEFAULT_COMPARISON_DIR,
    *,
    top_k: int = 5,
    include_unusable: bool = False,
) -> dict[str, Any]:
    phase1_dir = resolve_project_path(original_phase1_dir)
    model_dir = resolve_project_path(revised_model_dir)
    original_output_dir = resolve_project_path(original_p0_dir)
    revised_output_dir = resolve_project_path(revised_p0_dir)
    comparison_output_dir = resolve_project_path(comparison_dir)
    comparison_output_dir.mkdir(parents=True, exist_ok=True)

    revised_records = list(read_jsonl(model_dir / REVISED_SOURCE_FILE))
    revised_seed_records = prepare_revised_seed_records(revised_records, include_unusable=include_unusable)
    revised_input_jsonl = comparison_output_dir / "phase1_mini_gold_seed_50_revised_for_p0.jsonl"
    revised_input_dir = comparison_output_dir / "revised_phase1_input"
    revised_input_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(revised_input_jsonl, revised_seed_records)
    write_jsonl(revised_input_dir / "phase1_mini_gold_seed_50.jsonl", revised_seed_records)
    shutil.copyfile(
        phase1_dir / "phase1_retrieval_candidate_pool.jsonl",
        revised_input_dir / "phase1_retrieval_candidate_pool.jsonl",
    )

    original_summary_path = original_output_dir / "p0_baseline_summary.json"
    if original_summary_path.exists():
        original_summary = json.loads(original_summary_path.read_text(encoding="utf-8"))
    else:
        original_summary = generate_p0_baselines(phase1_dir, original_output_dir, top_k=top_k)
    revised_summary = generate_p0_baselines(revised_input_dir, revised_output_dir, top_k=top_k)
    comparison = compare_p0_summaries(original_summary, revised_summary)

    summary = {
        "comparison_id": "p0_original_vs_deepseek_revised_mini_gold",
        "input": {
            "original_phase1_dir": project_relative_path(phase1_dir),
            "revised_model_dir": project_relative_path(model_dir),
            "include_unusable": include_unusable,
            "top_k": top_k,
        },
        "comparison": comparison,
        "files": {
            "revised_seed_for_p0": project_relative_path(revised_input_jsonl),
            "revised_phase1_input_dir": project_relative_path(revised_input_dir),
            "original_p0_summary": project_relative_path(original_output_dir / "p0_baseline_summary.json"),
            "revised_p0_summary": project_relative_path(revised_output_dir / "p0_baseline_summary.json"),
            "summary": project_relative_path(comparison_output_dir / "p0_baseline_original_vs_model_revised_summary.json"),
            "report": project_relative_path(comparison_output_dir / "p0_baseline_original_vs_model_revised_report.md"),
        },
        "notes": [
            "Revised mini-gold labels are model-assisted and still need human confirmation.",
            "Comparison metrics are sanity checks over small candidate labels, not final benchmark results.",
            "By default, revised rows marked revised_usable_for_evaluation=no are excluded.",
        ],
    }
    summary_path = comparison_output_dir / "p0_baseline_original_vs_model_revised_summary.json"
    report_path = comparison_output_dir / "p0_baseline_original_vs_model_revised_report.md"
    summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    report_path.write_text(_report(summary), encoding="utf-8")
    return summary


def _metric(summary: dict[str, Any], path: tuple[str, ...]) -> float:
    value: Any = summary
    for key in path:
        if not isinstance(value, dict) or key not in value:
            return 0.0
        value = value[key]
    try:
        return float(value)
    except (TypeError, ValueError):
        return 0.0


def _report(summary: dict[str, Any]) -> str:
    comparison = summary["comparison"]
    metrics = comparison["metrics"]
    deltas = comparison["metric_deltas"]
    return f"""# P0 Baseline Comparison: Original vs Model-Revised Mini-Gold

## Scope

This compares the original 50-row candidate mini-gold seed with the DeepSeek-v3 model-revised seed. The revised run excludes rows marked `revised_usable_for_evaluation=no` unless explicitly configured otherwise.

These are workflow sanity-check metrics over model-assisted candidate labels, not final benchmark results.

## Input Counts

- Original mini-gold rows: `{comparison["original_mini_gold_count"]}`
- Revised mini-gold rows used for P0: `{comparison["revised_mini_gold_count"]}`
- Retrieval top-k: `{summary["input"]["top_k"]}`
- Include unusable revised rows: `{summary["input"]["include_unusable"]}`

## Metric Comparison

| Metric | Original | Revised | Delta |
|---|---:|---:|---:|
| Concern accuracy | {metrics["concern_accuracy"]["original"]:.4f} | {metrics["concern_accuracy"]["revised"]:.4f} | {deltas["concern_accuracy"]:+.4f} |
| Concern macro-F1 | {metrics["concern_macro_f1"]["original"]:.4f} | {metrics["concern_macro_f1"]["revised"]:.4f} | {deltas["concern_macro_f1"]:+.4f} |
| Strategy Recall@1 | {metrics["strategy_recall_at_1"]["original"]:.4f} | {metrics["strategy_recall_at_1"]["revised"]:.4f} | {deltas["strategy_recall_at_1"]:+.4f} |
| Strategy Recall@3 | {metrics["strategy_recall_at_3"]["original"]:.4f} | {metrics["strategy_recall_at_3"]["revised"]:.4f} | {deltas["strategy_recall_at_3"]:+.4f} |
| Strategy Recall@5 | {metrics["strategy_recall_at_5"]["original"]:.4f} | {metrics["strategy_recall_at_5"]["revised"]:.4f} | {deltas["strategy_recall_at_5"]:+.4f} |
| Concern Match@5 | {metrics["concern_match_at_5"]["original"]:.4f} | {metrics["concern_match_at_5"]["revised"]:.4f} | {deltas["concern_match_at_5"]:+.4f} |
| Joint Match@5 | {metrics["joint_strategy_concern_match_at_5"]["original"]:.4f} | {metrics["joint_strategy_concern_match_at_5"]["revised"]:.4f} | {deltas["joint_strategy_concern_match_at_5"]:+.4f} |

## Files

- Revised seed for P0: `{summary["files"]["revised_seed_for_p0"]}`
- Revised P0 summary: `{summary["files"]["revised_p0_summary"]}`
- Full comparison summary: `{summary["files"]["summary"]}`
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Compare original and model-revised v2709 P0 baselines.")
    parser.add_argument("--original-phase1-dir", default=str(DEFAULT_ORIGINAL_PHASE1_DIR))
    parser.add_argument("--revised-model-dir", default=str(DEFAULT_REVISED_MODEL_DIR))
    parser.add_argument("--original-p0-dir", default=str(DEFAULT_ORIGINAL_P0_DIR))
    parser.add_argument("--revised-p0-dir", default=str(DEFAULT_REVISED_P0_DIR))
    parser.add_argument("--comparison-dir", default=str(DEFAULT_COMPARISON_DIR))
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--include-unusable", action="store_true")
    args = parser.parse_args()
    summary = generate_p0_baseline_comparison(
        original_phase1_dir=args.original_phase1_dir,
        revised_model_dir=args.revised_model_dir,
        original_p0_dir=args.original_p0_dir,
        revised_p0_dir=args.revised_p0_dir,
        comparison_dir=args.comparison_dir,
        top_k=args.top_k,
        include_unusable=args.include_unusable,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
