import argparse
import csv
import json
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any

from peer_review_skills.config import project_relative_path, resolve_project_path
from peer_review_skills.evaluation.phase1_pair_autofill import CONCERN_KEYWORDS
from peer_review_skills.io.jsonl import read_jsonl, write_jsonl


DEFAULT_INPUT_DIR = Path("data/evaluation/phase1_pair_validation/v2709")
DEFAULT_OUTPUT_DIR = Path("data/evaluation/p0_baselines/v2709")
DEFAULT_TOP_K = 5

UNKNOWN_LABELS = {"", "unknown", "none", "n/a", "nan", "null"}
TOKEN_RE = re.compile(r"[a-zA-Z][a-zA-Z0-9_-]+")
STOPWORDS = {
    "about",
    "above",
    "after",
    "again",
    "against",
    "also",
    "although",
    "among",
    "analysis",
    "and",
    "any",
    "are",
    "author",
    "authors",
    "been",
    "being",
    "but",
    "can",
    "could",
    "data",
    "did",
    "does",
    "doing",
    "due",
    "each",
    "figure",
    "for",
    "from",
    "had",
    "has",
    "have",
    "how",
    "into",
    "its",
    "manuscript",
    "may",
    "more",
    "most",
    "not",
    "now",
    "our",
    "paper",
    "please",
    "reviewer",
    "should",
    "show",
    "shown",
    "some",
    "study",
    "supplementary",
    "than",
    "that",
    "the",
    "their",
    "there",
    "these",
    "this",
    "those",
    "was",
    "were",
    "which",
    "with",
    "would",
}


def predict_concern_type(text: str) -> dict[str, Any]:
    lowered = str(text or "").lower()
    label_details = {}
    for label, keywords in CONCERN_KEYWORDS.items():
        matched: list[str] = []
        score = 0.0
        for keyword in keywords:
            term = keyword.lower()
            count = lowered.count(term)
            if count:
                matched.append(keyword)
                weight = 1.0 + 0.25 * max(len(term.split()) - 1, 0)
                score += count * weight
        label_details[label] = {"score": round(score, 6), "matched_keywords": matched}

    predicted_label, detail = max(
        label_details.items(),
        key=lambda item: (item[1]["score"], item[0]),
    )
    if detail["score"] <= 0:
        predicted_label = "unknown"
        detail = {"score": 0.0, "matched_keywords": []}

    return {
        "predicted_concern_type": predicted_label,
        "score": detail["score"],
        "matched_keywords": detail["matched_keywords"],
        "label_scores": {label: info["score"] for label, info in label_details.items()},
    }


def classification_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    evaluated: list[tuple[str, str]] = []
    skipped_unknown = 0
    for row in rows:
        gold = _label(row.get("gold"))
        predicted = _label(row.get("predicted"))
        if _is_unknown(gold):
            skipped_unknown += 1
            continue
        evaluated.append((gold, predicted))

    labels = sorted({gold for gold, _ in evaluated})
    per_label = {}
    for label in labels:
        tp = sum(1 for gold, predicted in evaluated if gold == label and predicted == label)
        fp = sum(1 for gold, predicted in evaluated if gold != label and predicted == label)
        fn = sum(1 for gold, predicted in evaluated if gold == label and predicted != label)
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        per_label[label] = {
            "support": sum(1 for gold, _ in evaluated if gold == label),
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }

    correct = sum(1 for gold, predicted in evaluated if gold == predicted)
    return {
        "evaluated_count": len(evaluated),
        "skipped_unknown_gold_count": skipped_unknown,
        "correct_count": correct,
        "accuracy": correct / len(evaluated) if evaluated else 0.0,
        "macro_precision": _mean(item["precision"] for item in per_label.values()),
        "macro_recall": _mean(item["recall"] for item in per_label.values()),
        "macro_f1": _mean(item["f1"] for item in per_label.values()),
        "per_label": per_label,
    }


def retrieve_strategy_cases(
    query_record: dict[str, Any],
    index_records: list[dict[str, Any]],
    top_k: int = DEFAULT_TOP_K,
    idf: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    query_tokens = _token_counts(str(query_record.get("review_context") or query_record.get("review_context_preview") or ""))
    query_pair_id = str(query_record.get("pair_id") or "")
    scored = []
    for candidate in index_records:
        if str(candidate.get("pair_id") or "") == query_pair_id:
            continue
        candidate_tokens = _token_counts(
            str(candidate.get("review_context") or candidate.get("review_context_preview") or "")
        )
        score = _cosine_overlap(query_tokens, candidate_tokens, idf=idf)
        scored.append((score, str(candidate.get("sample_id") or ""), candidate))

    scored.sort(key=lambda item: (-item[0], item[1], str(item[2].get("pair_id") or "")))
    retrieved = []
    for rank, (score, _sample_id, candidate) in enumerate(scored[:top_k], start=1):
        retrieved.append(
            {
                "rank": rank,
                "score": round(score, 6),
                "pair_id": candidate.get("pair_id"),
                "sample_id": candidate.get("sample_id"),
                "paper_id": candidate.get("paper_id"),
                "doi": candidate.get("doi"),
                "title": candidate.get("title"),
                "journal": candidate.get("journal"),
                "journal_family": candidate.get("journal_family"),
                "concern_type_gold": candidate.get("concern_type_gold"),
                "response_strategy_gold": candidate.get("response_strategy_gold"),
                "validation_source": candidate.get("validation_source"),
                "review_context_preview": _preview(
                    str(candidate.get("review_context") or candidate.get("review_context_preview") or "")
                ),
                "author_response_preview": _preview(
                    str(candidate.get("author_response") or candidate.get("author_response_preview") or "")
                ),
                "source_json_path": candidate.get("source_json_path"),
                "source_field": candidate.get("source_field"),
                "source_offsets": candidate.get("source_offsets"),
            }
        )
    return retrieved


def retrieval_metrics(predictions: list[dict[str, Any]], k_values: tuple[int, ...] = (1, 3, 5)) -> dict[str, Any]:
    evaluated = [
        prediction
        for prediction in predictions
        if not _is_unknown(_label(prediction.get("gold_response_strategy")))
    ]
    metrics: dict[str, Any] = {
        "evaluated_count": len(evaluated),
        "skipped_unknown_strategy_count": len(predictions) - len(evaluated),
    }
    for k in k_values:
        strategy_hits = 0
        concern_hits = 0
        joint_hits = 0
        reciprocal_rank_total = 0.0
        for prediction in evaluated:
            gold_strategy = _label(prediction.get("gold_response_strategy"))
            gold_concern = _label(prediction.get("gold_concern_type"))
            top_items = list(prediction.get("retrieved") or [])[:k]
            strategy_hit_rank = _first_rank(top_items, "response_strategy_gold", gold_strategy)
            concern_hit = (
                False
                if _is_unknown(gold_concern)
                else any(_label(item.get("concern_type_gold")) == gold_concern for item in top_items)
            )
            joint_hit = (
                False
                if _is_unknown(gold_concern)
                else any(
                    _label(item.get("response_strategy_gold")) == gold_strategy
                    and _label(item.get("concern_type_gold")) == gold_concern
                    for item in top_items
                )
            )
            if strategy_hit_rank:
                strategy_hits += 1
                reciprocal_rank_total += 1 / strategy_hit_rank
            if concern_hit:
                concern_hits += 1
            if joint_hit:
                joint_hits += 1

        denominator = len(evaluated) or 1
        metrics[f"strategy_recall_at_{k}"] = strategy_hits / denominator
        metrics[f"strategy_mrr_at_{k}"] = reciprocal_rank_total / denominator
        metrics[f"concern_match_at_{k}"] = concern_hits / denominator
        metrics[f"joint_strategy_concern_match_at_{k}"] = joint_hits / denominator
    return metrics


def generate_p0_baselines(
    input_dir: str | Path = DEFAULT_INPUT_DIR,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    top_k: int = DEFAULT_TOP_K,
) -> dict[str, Any]:
    input_path = resolve_project_path(input_dir)
    output_path = resolve_project_path(output_dir)
    mini_gold = list(read_jsonl(input_path / "phase1_mini_gold_seed_50.jsonl"))
    retrieval_pool = list(read_jsonl(input_path / "phase1_retrieval_candidate_pool.jsonl"))

    concern_predictions = build_concern_predictions(mini_gold)
    concern_metric_rows = [
        {
            "gold": row.get("gold_concern_type"),
            "predicted": row.get("predicted_concern_type"),
        }
        for row in concern_predictions
    ]
    concern_summary = {
        "metrics": classification_metrics(concern_metric_rows),
        "gold_counts": dict(Counter(row.get("gold_concern_type") for row in concern_predictions)),
        "prediction_counts": dict(Counter(row.get("predicted_concern_type") for row in concern_predictions)),
    }

    idf = _build_idf(retrieval_pool)
    retrieval_predictions = build_retrieval_predictions(mini_gold, retrieval_pool, top_k=top_k, idf=idf)
    retrieval_summary = {
        "metrics": retrieval_metrics(retrieval_predictions, k_values=_k_values(top_k)),
        "top_k": top_k,
        "index_record_count": len(retrieval_pool),
    }

    outputs = {
        "concern_predictions_jsonl": output_path / "concern_extraction_predictions.jsonl",
        "concern_predictions_csv": output_path / "concern_extraction_predictions.csv",
        "strategy_retrieval_predictions_jsonl": output_path / "strategy_retrieval_predictions.jsonl",
        "strategy_retrieval_predictions_csv": output_path / "strategy_retrieval_predictions.csv",
        "summary": output_path / "p0_baseline_summary.json",
        "report": output_path / "p0_baseline_report.md",
    }
    write_jsonl(outputs["concern_predictions_jsonl"], concern_predictions)
    write_jsonl(outputs["strategy_retrieval_predictions_jsonl"], retrieval_predictions)
    _write_csv(outputs["concern_predictions_csv"], concern_predictions)
    _write_csv(outputs["strategy_retrieval_predictions_csv"], retrieval_predictions)

    summary = {
        "baseline_id": "p0_local_keyword_and_lexical_v1",
        "input": {
            "input_dir": project_relative_path(input_path),
            "mini_gold_count": len(mini_gold),
            "retrieval_pool_count": len(retrieval_pool),
        },
        "concern_extraction": concern_summary,
        "strategy_retrieval": retrieval_summary,
        "files": {name: project_relative_path(path) for name, path in outputs.items()},
        "notes": [
            "Mini-gold labels are candidate labels requiring human confirmation.",
            "Metrics are workflow sanity checks, not final benchmark results.",
            "Retrieval scoring uses only review concern text and excludes the identical pair_id.",
        ],
    }
    outputs["summary"].write_text(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    outputs["report"].write_text(_report(summary), encoding="utf-8")
    return summary


def build_concern_predictions(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    predictions = []
    for record in records:
        review_text = str(record.get("review_context") or record.get("review_context_preview") or "")
        prediction = predict_concern_type(review_text)
        gold = _label(record.get("concern_type_gold"))
        predicted = prediction["predicted_concern_type"]
        predictions.append(
            {
                "sample_id": record.get("sample_id"),
                "pair_id": record.get("pair_id"),
                "paper_id": record.get("paper_id"),
                "doi": record.get("doi"),
                "title": record.get("title"),
                "journal": record.get("journal"),
                "journal_family": record.get("journal_family"),
                "gold_concern_type": gold,
                "predicted_concern_type": predicted,
                "correct": "skipped_unknown_gold" if _is_unknown(gold) else _yes_no(gold == predicted),
                "score": prediction["score"],
                "matched_keywords": prediction["matched_keywords"],
                "label_scores": prediction["label_scores"],
                "mini_gold_status": record.get("mini_gold_status"),
                "mini_gold_source": record.get("mini_gold_source"),
                "validation_source": record.get("validation_source"),
                "review_context_preview": _preview(review_text),
                "source_json_path": record.get("source_json_path"),
                "source_field": record.get("source_field"),
                "source_offsets": record.get("source_offsets"),
            }
        )
    return predictions


def build_retrieval_predictions(
    query_records: list[dict[str, Any]],
    index_records: list[dict[str, Any]],
    top_k: int = DEFAULT_TOP_K,
    idf: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    predictions = []
    for record in query_records:
        retrieved = retrieve_strategy_cases(record, index_records, top_k=top_k, idf=idf)
        predictions.append(
            {
                "sample_id": record.get("sample_id"),
                "pair_id": record.get("pair_id"),
                "paper_id": record.get("paper_id"),
                "doi": record.get("doi"),
                "title": record.get("title"),
                "journal": record.get("journal"),
                "journal_family": record.get("journal_family"),
                "gold_concern_type": record.get("concern_type_gold"),
                "gold_response_strategy": record.get("response_strategy_gold"),
                "top_k": top_k,
                "retrieved": retrieved,
                "top_pair_ids": [item.get("pair_id") for item in retrieved],
                "top_strategy_labels": [item.get("response_strategy_gold") for item in retrieved],
                "top_concern_labels": [item.get("concern_type_gold") for item in retrieved],
                "strategy_hit_at_1": _yes_no(_has_label(retrieved[:1], "response_strategy_gold", record.get("response_strategy_gold"))),
                "strategy_hit_at_3": _yes_no(_has_label(retrieved[:3], "response_strategy_gold", record.get("response_strategy_gold"))),
                "strategy_hit_at_5": _yes_no(_has_label(retrieved[:5], "response_strategy_gold", record.get("response_strategy_gold"))),
                "concern_hit_at_1": _yes_no(_has_label(retrieved[:1], "concern_type_gold", record.get("concern_type_gold"))),
                "concern_hit_at_3": _yes_no(_has_label(retrieved[:3], "concern_type_gold", record.get("concern_type_gold"))),
                "concern_hit_at_5": _yes_no(_has_label(retrieved[:5], "concern_type_gold", record.get("concern_type_gold"))),
                "review_context_preview": _preview(
                    str(record.get("review_context") or record.get("review_context_preview") or "")
                ),
                "source_json_path": record.get("source_json_path"),
                "source_field": record.get("source_field"),
                "source_offsets": record.get("source_offsets"),
            }
        )
    return predictions


def _build_idf(records: list[dict[str, Any]]) -> dict[str, float]:
    document_frequency: Counter[str] = Counter()
    for record in records:
        text = str(record.get("review_context") or record.get("review_context_preview") or "")
        document_frequency.update(set(_token_counts(text)))
    total = len(records)
    return {
        token: math.log((1 + total) / (1 + frequency)) + 1
        for token, frequency in document_frequency.items()
    }


def _token_counts(text: str) -> Counter[str]:
    tokens = []
    for token in TOKEN_RE.findall(str(text or "").lower()):
        token = token.replace("_", "-")
        if token in STOPWORDS or len(token) < 3:
            continue
        tokens.append(token)
    return Counter(tokens)


def _cosine_overlap(
    query_tokens: Counter[str],
    candidate_tokens: Counter[str],
    idf: dict[str, float] | None = None,
) -> float:
    if not query_tokens or not candidate_tokens:
        return 0.0
    shared = set(query_tokens) & set(candidate_tokens)
    numerator = sum(
        query_tokens[token] * candidate_tokens[token] * _weight(token, idf) ** 2
        for token in shared
    )
    query_norm = math.sqrt(sum((count * _weight(token, idf)) ** 2 for token, count in query_tokens.items()))
    candidate_norm = math.sqrt(sum((count * _weight(token, idf)) ** 2 for token, count in candidate_tokens.items()))
    if not query_norm or not candidate_norm:
        return 0.0
    return numerator / (query_norm * candidate_norm)


def _weight(token: str, idf: dict[str, float] | None) -> float:
    if idf is None:
        return 1.0
    return idf.get(token, math.log(2) + 1)


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
        "gold_concern_type",
        "predicted_concern_type",
        "gold_response_strategy",
        "correct",
        "score",
        "matched_keywords",
        "top_k",
        "top_pair_ids",
        "top_strategy_labels",
        "top_concern_labels",
        "strategy_hit_at_1",
        "strategy_hit_at_3",
        "strategy_hit_at_5",
        "concern_hit_at_1",
        "concern_hit_at_3",
        "concern_hit_at_5",
        "mini_gold_status",
        "mini_gold_source",
        "validation_source",
        "review_context_preview",
        "source_json_path",
        "source_field",
        "source_offsets",
        "retrieved",
        "label_scores",
    ]
    present = set().union(*(record.keys() for record in records)) if records else set()
    extras = sorted(present - set(preferred))
    return [field for field in preferred if field in present] + extras


def _report(summary: dict[str, Any]) -> str:
    concern_metrics = summary["concern_extraction"]["metrics"]
    retrieval_metrics_summary = summary["strategy_retrieval"]["metrics"]
    return f"""# v2709 P0 Baseline Report

## Scope

This run evaluates two local baselines over the Phase 1 candidate mini-gold seed:

- Review Concern Extraction: keyword rules over `review_context`.
- Author Response Strategy Retrieval: lexical overlap over review concern text, with identical `pair_id` excluded.

The labels are candidate labels requiring human confirmation. Treat these metrics as workflow sanity checks, not final benchmark results.

## Inputs

- Mini-gold seed rows: `{summary["input"]["mini_gold_count"]}`
- Retrieval pool rows: `{summary["input"]["retrieval_pool_count"]}`
- Retrieval top-k: `{summary["strategy_retrieval"]["top_k"]}`

## Concern Extraction

- Evaluated rows: `{concern_metrics["evaluated_count"]}`
- Skipped unknown gold rows: `{concern_metrics["skipped_unknown_gold_count"]}`
- Accuracy: `{concern_metrics["accuracy"]:.4f}`
- Macro F1: `{concern_metrics["macro_f1"]:.4f}`

## Strategy Retrieval

- Evaluated rows: `{retrieval_metrics_summary["evaluated_count"]}`
- Strategy Recall@1: `{retrieval_metrics_summary.get("strategy_recall_at_1", 0.0):.4f}`
- Strategy Recall@3: `{retrieval_metrics_summary.get("strategy_recall_at_3", 0.0):.4f}`
- Strategy Recall@5: `{retrieval_metrics_summary.get("strategy_recall_at_5", 0.0):.4f}`
- Concern Match@1: `{retrieval_metrics_summary.get("concern_match_at_1", 0.0):.4f}`
- Concern Match@3: `{retrieval_metrics_summary.get("concern_match_at_3", 0.0):.4f}`
- Concern Match@5: `{retrieval_metrics_summary.get("concern_match_at_5", 0.0):.4f}`

## Output Files

- `{summary["files"]["concern_predictions_jsonl"]}`
- `{summary["files"]["concern_predictions_csv"]}`
- `{summary["files"]["strategy_retrieval_predictions_jsonl"]}`
- `{summary["files"]["strategy_retrieval_predictions_csv"]}`
- `{summary["files"]["summary"]}`
"""


def _k_values(top_k: int) -> tuple[int, ...]:
    return tuple(k for k in (1, 3, 5) if k <= top_k) or (top_k,)


def _first_rank(items: list[dict[str, Any]], field: str, gold_label: str) -> int:
    for index, item in enumerate(items, start=1):
        if _label(item.get(field)) == gold_label:
            return index
    return 0


def _has_label(items: list[dict[str, Any]], field: str, gold_label: Any) -> bool:
    gold = _label(gold_label)
    if _is_unknown(gold):
        return False
    return any(_label(item.get(field)) == gold for item in items)


def _label(value: Any) -> str:
    return str(value or "").strip()


def _is_unknown(value: str) -> bool:
    return _label(value).lower() in UNKNOWN_LABELS


def _mean(values) -> float:
    materialized = list(values)
    if not materialized:
        return 0.0
    return sum(materialized) / len(materialized)


def _preview(text: str, limit: int = 360) -> str:
    compact = " ".join(str(text or "").split())
    return compact if len(compact) <= limit else compact[: limit - 3].rstrip() + "..."


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run v2709 P0 local baselines.")
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    args = parser.parse_args()
    summary = generate_p0_baselines(args.input_dir, args.output_dir, top_k=args.top_k)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
