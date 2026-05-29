# Retrieval v2 Report

## Input

- query_count: 100
- pool_count: 245
- method: case metadata + interdisciplinary signal rerank

## Metrics

| Metric | Value |
|---|---:|
| strategy_recall_at_1 | 0.3900 |
| strategy_recall_at_3 | 0.4800 |
| strategy_recall_at_5 | 0.5400 |
| concern_match_at_5 | 0.7400 |
| institutional_match_at_5 | 0.8900 |
| joint_strategy_concern_at_5 | 0.4500 |
| case_diversity_at_5 | 0.9840 |
| provenance_completeness | 1.0000 |
| average_distinct_paper_count | 4.9200 |
| average_distinct_strategy_count | 3.1800 |

## P1 Baseline Comparison

| P1 metric | Best P1 method | P1 value |
|---|---|---:|
| strategy_recall_at_1 | lexical_cosine | 0.4222 |
| strategy_recall_at_3 | hybrid_bm25_concern_strategy | 0.7778 |
| strategy_recall_at_5 | hybrid_bm25_concern_strategy | 0.8667 |
| concern_match_at_5 | bm25_concern_filter | 0.9778 |
| joint_strategy_concern_match_at_5 | hybrid_bm25_concern_strategy | 0.7556 |

## Improvement Attribution

- Case metadata: concern, risk, institutional signal, actor links, and provenance are explicit rerank signals.
- No strategy-label leakage: response_strategy is used only as an evaluation target, not as a ranking signal.
- Advice boundary: Agnes workflow recommendations are grounded in model-assisted labels, controlled Nature case metadata, provenance-linked case analogies, cross-disciplinary traces, and author-confirmation gates.
- Caveat: v2 and P1 are evaluated over candidate labels and different pools, so these numbers are sanity checks rather than human-gold claims.

## Limitations

This is evaluated over candidate labels, not final human gold.
