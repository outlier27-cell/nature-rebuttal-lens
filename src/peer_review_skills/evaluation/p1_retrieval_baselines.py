import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path
from typing import Any

from peer_review_skills.config import project_relative_path, resolve_project_path
from peer_review_skills.evaluation.p0_baselines import (
    _build_idf,
    _has_label,
    _k_values,
    _label,
    _preview,
    _token_counts,
    retrieve_strategy_cases,
    retrieval_metrics,
)
from peer_review_skills.io.jsonl import read_jsonl, write_jsonl


DEFAULT_INPUT_DIR = Path("data/evaluation/p0_baselines/v2709_comparison/revised_phase1_input")
DEFAULT_OUTPUT_DIR = Path("data/evaluation/p1_retrieval_baselines/v2709_model_revised")
DEFAULT_TOP_K = 5
METHODS = ("lexical_cosine", "bm25", "bm25_concern_filter", "hybrid_bm25_concern_strategy")


class BM25Index:
    def __init__(self, records: list[dict[str, Any]], *, k1: float = 1.5, b: float = 0.75):
        self.records = list(records)
        self.k1 = k1
        self.b = b
        self.documents = [
            _token_counts(str(record.get("review_context") or record.get("review_context_preview") or ""))
            for record in self.records
        ]
        self.doc_lengths = [sum(document.values()) for document in self.documents]
        self.avg_doc_length = sum(self.doc_lengths) / len(self.doc_lengths) if self.doc_lengths else 0.0
        self.idf = self._build_bm25_idf()

    def search(
        self,
        query: str,
        *,
        top_k: int = DEFAULT_TOP_K,
        exclude_pair_id: str = "",
        candidate_filter: set[str] | None = None,
    ) -> list[dict[str, Any]]:
        query_terms = _token_counts(query)
        scored = []
        for index, record in enumerate(self.records):
            pair_id = str(record.get("pair_id") or "")
            if pair_id == exclude_pair_id:
                continue
            if candidate_filter is not None and pair_id not in candidate_filter:
                continue
            score = self._score_document(query_terms, index)
            scored.append((score, str(record.get("sample_id") or ""), record))
        scored.sort(key=lambda item: (-item[0], item[1], str(item[2].get("pair_id") or "")))
        return [_retrieved_record(record, rank, score) for rank, (score, _sample_id, record) in enumerate(scored[:top_k], 1)]

    def _build_bm25_idf(self) -> dict[str, float]:
        total = len(self.documents)
        document_frequency: Counter[str] = Counter()
        for document in self.documents:
            document_frequency.update(set(document))
        return {
            term: math.log(1 + (total - frequency + 0.5) / (frequency + 0.5))
            for term, frequency in document_frequency.items()
        }

    def _score_document(self, query_terms: Counter[str], document_index: int) -> float:
        document = self.documents[document_index]
        doc_length = self.doc_lengths[document_index]
        if not document or not query_terms:
            return 0.0
        score = 0.0
        for term, query_count in query_terms.items():
            term_frequency = document.get(term, 0)
            if not term_frequency:
                continue
            idf = self.idf.get(term, 0.0)
            denominator = term_frequency + self.k1 * (
                1 - self.b + self.b * doc_length / (self.avg_doc_length or 1.0)
            )
            score += query_count * idf * (term_frequency * (self.k1 + 1)) / denominator
        return score


def retrieve_cases(
    query_record: dict[str, Any],
    index_records: list[dict[str, Any]],
    *,
    method: str,
    top_k: int = DEFAULT_TOP_K,
    bm25_index: BM25Index | None = None,
    lexical_idf: dict[str, float] | None = None,
) -> list[dict[str, Any]]:
    if method == "lexical_cosine":
        retrieved = retrieve_strategy_cases(query_record, index_records, top_k=top_k, idf=lexical_idf)
        for item in retrieved:
            item["retrieval_method"] = method
            item["filter_matched"] = False
        return retrieved
    if method == "bm25":
        active_index = bm25_index or BM25Index(index_records)
        retrieved = active_index.search(
            _query_text(query_record),
            top_k=top_k,
            exclude_pair_id=str(query_record.get("pair_id") or ""),
        )
        for item in retrieved:
            item["retrieval_method"] = method
            item["filter_matched"] = False
        return retrieved
    if method == "bm25_concern_filter":
        return _bm25_concern_filter(query_record, index_records, top_k=top_k, bm25_index=bm25_index)
    if method == "hybrid_bm25_concern_strategy":
        return _hybrid_bm25_concern_strategy(query_record, index_records, top_k=top_k, bm25_index=bm25_index)
    raise ValueError(f"unknown retrieval method: {method}")


def build_method_predictions(
    query_records: list[dict[str, Any]],
    index_records: list[dict[str, Any]],
    *,
    method: str,
    top_k: int = DEFAULT_TOP_K,
) -> list[dict[str, Any]]:
    bm25_index = BM25Index(index_records) if method.startswith("bm25") or method.startswith("hybrid_bm25") else None
    lexical_idf = _build_idf(index_records) if method == "lexical_cosine" else None
    predictions = []
    for record in query_records:
        retrieved = retrieve_cases(
            record,
            index_records,
            method=method,
            top_k=top_k,
            bm25_index=bm25_index,
            lexical_idf=lexical_idf,
        )
        predictions.append(_prediction_record(record, retrieved, method, top_k))
    return predictions


def generate_p1_retrieval_baselines(
    input_dir: str | Path = DEFAULT_INPUT_DIR,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    *,
    top_k: int = DEFAULT_TOP_K,
    methods: tuple[str, ...] = METHODS,
) -> dict[str, Any]:
    source_dir = resolve_project_path(input_dir)
    target_dir = resolve_project_path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    query_records = list(read_jsonl(source_dir / "phase1_mini_gold_seed_50.jsonl"))
    index_records = list(read_jsonl(source_dir / "phase1_retrieval_candidate_pool.jsonl"))

    method_summaries = {}
    output_files: dict[str, str] = {}
    for method in methods:
        predictions = build_method_predictions(query_records, index_records, method=method, top_k=top_k)
        metrics = retrieval_metrics(predictions, k_values=_k_values(top_k))
        method_jsonl = target_dir / f"{method}_predictions.jsonl"
        method_csv = target_dir / f"{method}_predictions.csv"
        write_jsonl(method_jsonl, predictions)
        _write_csv(method_csv, predictions)
        method_summaries[method] = {
            "metrics": metrics,
            "prediction_count": len(predictions),
            "top_k": top_k,
        }
        output_files[f"{method}_jsonl"] = project_relative_path(method_jsonl)
        output_files[f"{method}_csv"] = project_relative_path(method_csv)

    summary = {
        "baseline_id": "p1_bm25_and_concern_filter_v1",
        "input": {
            "input_dir": project_relative_path(source_dir),
            "query_count": len(query_records),
            "retrieval_pool_count": len(index_records),
            "top_k": top_k,
        },
        "methods": method_summaries,
        "best_by_metric": _best_by_metric(method_summaries),
        "files": {
            **output_files,
            "summary": project_relative_path(target_dir / "p1_retrieval_summary.json"),
            "report": project_relative_path(target_dir / "p1_retrieval_report.md"),
        },
        "notes": [
            "This is evaluated over model-revised candidate mini-gold labels, not final human gold.",
            "BM25 and concern-filter retrieval use only review-context text and existing candidate labels.",
            "Identical pair_id is excluded from each query's retrieval candidates.",
        ],
    }
    (target_dir / "p1_retrieval_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (target_dir / "p1_retrieval_report.md").write_text(_report(summary), encoding="utf-8")
    return summary


def _bm25_concern_filter(
    query_record: dict[str, Any],
    index_records: list[dict[str, Any]],
    *,
    top_k: int,
    bm25_index: BM25Index | None,
) -> list[dict[str, Any]]:
    active_index = bm25_index or BM25Index(index_records)
    query_concern = str(query_record.get("concern_type_gold") or "")
    query_pair_id = str(query_record.get("pair_id") or "")
    same_concern_ids = {
        str(record.get("pair_id") or "")
        for record in index_records
        if str(record.get("concern_type_gold") or "") == query_concern
        and str(record.get("pair_id") or "") != query_pair_id
    }
    filtered = active_index.search(
        _query_text(query_record),
        top_k=top_k,
        exclude_pair_id=query_pair_id,
        candidate_filter=same_concern_ids,
    )
    for item in filtered:
        item["retrieval_method"] = "bm25_concern_filter"
        item["filter_matched"] = True
    if len(filtered) >= top_k:
        return filtered

    seen = {str(item.get("pair_id") or "") for item in filtered}
    fallback = active_index.search(_query_text(query_record), top_k=len(index_records), exclude_pair_id=query_pair_id)
    for item in fallback:
        pair_id = str(item.get("pair_id") or "")
        if pair_id in seen:
            continue
        item["retrieval_method"] = "bm25_concern_filter"
        item["filter_matched"] = False
        filtered.append(item)
        seen.add(pair_id)
        if len(filtered) >= top_k:
            break
    for rank, item in enumerate(filtered, start=1):
        item["rank"] = rank
    return filtered


def _hybrid_bm25_concern_strategy(
    query_record: dict[str, Any],
    index_records: list[dict[str, Any]],
    *,
    top_k: int,
    bm25_index: BM25Index | None,
) -> list[dict[str, Any]]:
    active_index = bm25_index or BM25Index(index_records)
    query_text = _query_text(query_record)
    query_pair_id = str(query_record.get("pair_id") or "")
    query_concern = str(query_record.get("concern_type_gold") or "")
    query_strategy = str(query_record.get("response_strategy_gold") or "")
    candidates = active_index.search(query_text, top_k=len(index_records), exclude_pair_id=query_pair_id)

    enriched = []
    for item in candidates:
        same_concern = str(item.get("concern_type_gold") or "") == query_concern
        same_strategy = str(item.get("response_strategy_gold") or "") == query_strategy
        base_score = float(item.get("score") or 0.0)
        hybrid_score = base_score + (2.0 if same_concern else 0.0) + (0.35 if same_strategy else 0.0)
        enriched_item = dict(item)
        enriched_item["retrieval_method"] = "hybrid_bm25_concern_strategy"
        enriched_item["filter_matched"] = same_concern
        enriched_item["hybrid_score"] = round(hybrid_score, 6)
        enriched_item["same_strategy_boost"] = same_strategy
        enriched.append(enriched_item)

    selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    for item in sorted(enriched, key=_hybrid_sort_key):
        if str(item.get("pair_id") or "") in selected_ids:
            continue
        selected.append(item)
        selected_ids.add(str(item.get("pair_id") or ""))
        break

    while len(selected) < top_k:
        selected_strategies = {str(item.get("response_strategy_gold") or "") for item in selected}
        novel_same_concern = [
            item
            for item in enriched
            if str(item.get("pair_id") or "") not in selected_ids
            and item.get("filter_matched")
            and str(item.get("response_strategy_gold") or "") not in selected_strategies
        ]
        same_concern = [
            item
            for item in enriched
            if str(item.get("pair_id") or "") not in selected_ids and item.get("filter_matched")
        ]
        any_remaining = [
            item
            for item in enriched
            if str(item.get("pair_id") or "") not in selected_ids
        ]
        bucket = novel_same_concern or same_concern or any_remaining
        if not bucket:
            break
        item = sorted(bucket, key=_hybrid_sort_key)[0]
        selected.append(item)
        selected_ids.add(str(item.get("pair_id") or ""))

    for rank, item in enumerate(selected, start=1):
        item["rank"] = rank
    return selected[:top_k]


def _hybrid_sort_key(item: dict[str, Any]) -> tuple[float, float, str, str]:
    return (
        -float(item.get("hybrid_score") or 0.0),
        -float(item.get("score") or 0.0),
        str(item.get("sample_id") or ""),
        str(item.get("pair_id") or ""),
    )


def _retrieved_record(record: dict[str, Any], rank: int, score: float) -> dict[str, Any]:
    return {
        "rank": rank,
        "score": round(score, 6),
        "pair_id": record.get("pair_id"),
        "sample_id": record.get("sample_id"),
        "paper_id": record.get("paper_id"),
        "doi": record.get("doi"),
        "title": record.get("title"),
        "journal": record.get("journal"),
        "journal_family": record.get("journal_family"),
        "concern_type_gold": record.get("concern_type_gold"),
        "response_strategy_gold": record.get("response_strategy_gold"),
        "validation_source": record.get("validation_source"),
        "review_context_preview": _preview(str(record.get("review_context") or record.get("review_context_preview") or "")),
        "author_response_preview": _preview(str(record.get("author_response") or record.get("author_response_preview") or "")),
        "source_json_path": record.get("source_json_path"),
        "source_field": record.get("source_field"),
        "source_offsets": record.get("source_offsets"),
    }


def _prediction_record(
    record: dict[str, Any],
    retrieved: list[dict[str, Any]],
    method: str,
    top_k: int,
) -> dict[str, Any]:
    return {
        "sample_id": record.get("sample_id"),
        "pair_id": record.get("pair_id"),
        "paper_id": record.get("paper_id"),
        "doi": record.get("doi"),
        "title": record.get("title"),
        "journal": record.get("journal"),
        "journal_family": record.get("journal_family"),
        "retrieval_method": method,
        "gold_concern_type": record.get("concern_type_gold"),
        "gold_response_strategy": record.get("response_strategy_gold"),
        "top_k": top_k,
        "retrieved": retrieved,
        "top_pair_ids": [item.get("pair_id") for item in retrieved],
        "top_strategy_labels": [item.get("response_strategy_gold") for item in retrieved],
        "top_concern_labels": [item.get("concern_type_gold") for item in retrieved],
        "filter_matched_count": sum(1 for item in retrieved if item.get("filter_matched")),
        "strategy_hit_at_1": _yes_no(_has_label(retrieved[:1], "response_strategy_gold", record.get("response_strategy_gold"))),
        "strategy_hit_at_3": _yes_no(_has_label(retrieved[:3], "response_strategy_gold", record.get("response_strategy_gold"))),
        "strategy_hit_at_5": _yes_no(_has_label(retrieved[:5], "response_strategy_gold", record.get("response_strategy_gold"))),
        "concern_hit_at_1": _yes_no(_has_label(retrieved[:1], "concern_type_gold", record.get("concern_type_gold"))),
        "concern_hit_at_3": _yes_no(_has_label(retrieved[:3], "concern_type_gold", record.get("concern_type_gold"))),
        "concern_hit_at_5": _yes_no(_has_label(retrieved[:5], "concern_type_gold", record.get("concern_type_gold"))),
        "review_context_preview": _preview(_query_text(record)),
        "source_json_path": record.get("source_json_path"),
        "source_field": record.get("source_field"),
        "source_offsets": record.get("source_offsets"),
    }


def _best_by_metric(method_summaries: dict[str, Any]) -> dict[str, str]:
    metric_names = (
        "strategy_recall_at_1",
        "strategy_recall_at_3",
        "strategy_recall_at_5",
        "concern_match_at_5",
        "joint_strategy_concern_match_at_5",
    )
    best = {}
    for metric in metric_names:
        best[metric] = max(
            method_summaries,
            key=lambda method: method_summaries[method]["metrics"].get(metric, 0.0),
        )
    return best


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
        "retrieval_method",
        "gold_concern_type",
        "gold_response_strategy",
        "top_k",
        "top_pair_ids",
        "top_strategy_labels",
        "top_concern_labels",
        "filter_matched_count",
        "strategy_hit_at_1",
        "strategy_hit_at_3",
        "strategy_hit_at_5",
        "concern_hit_at_1",
        "concern_hit_at_3",
        "concern_hit_at_5",
        "review_context_preview",
        "source_json_path",
        "source_field",
        "source_offsets",
        "retrieved",
    ]
    present = set().union(*(record.keys() for record in records)) if records else set()
    extras = sorted(present - set(preferred))
    return [field for field in preferred if field in present] + extras


def _report(summary: dict[str, Any]) -> str:
    lines = [
        "# P1 Retrieval Baselines over Model-Revised Mini-Gold",
        "",
        "## Scope",
        "",
        "This report compares retrieval baselines over the 45-row model-revised candidate mini-gold seed.",
        "These metrics are sanity checks and not final benchmark results.",
        "",
        "## Inputs",
        "",
        f"- Query rows: `{summary['input']['query_count']}`",
        f"- Retrieval pool rows: `{summary['input']['retrieval_pool_count']}`",
        f"- Top-k: `{summary['input']['top_k']}`",
        "",
        "## Metrics",
        "",
        "| Method | Strategy R@1 | Strategy R@3 | Strategy R@5 | Concern@5 | Joint@5 |",
        "|---|---:|---:|---:|---:|---:|",
    ]
    for method, payload in summary["methods"].items():
        metrics = payload["metrics"]
        lines.append(
            f"| {method} | "
            f"{metrics.get('strategy_recall_at_1', 0.0):.4f} | "
            f"{metrics.get('strategy_recall_at_3', 0.0):.4f} | "
            f"{metrics.get('strategy_recall_at_5', 0.0):.4f} | "
            f"{metrics.get('concern_match_at_5', 0.0):.4f} | "
            f"{metrics.get('joint_strategy_concern_match_at_5', 0.0):.4f} |"
        )
    lines.extend(
        [
            "",
            "## Best By Metric",
            "",
        ]
    )
    for metric, method in summary["best_by_metric"].items():
        lines.append(f"- `{metric}`: `{method}`")
    lines.extend(["", "## Files", ""])
    for key, value in summary["files"].items():
        lines.append(f"- `{key}`: `{value}`")
    return "\n".join(lines) + "\n"


def _query_text(record: dict[str, Any]) -> str:
    return str(record.get("review_context") or record.get("review_context_preview") or "")


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run P1 retrieval baselines over model-revised mini-gold.")
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    args = parser.parse_args()
    summary = generate_p1_retrieval_baselines(args.input_dir, args.output_dir, top_k=args.top_k)
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
