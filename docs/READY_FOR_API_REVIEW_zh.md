# API Seed Review Status

API seed review has been executed for 200 / 200 seed requests.

## Executed request queue

- `data/evaluation/api_handoff/naturereview_v01/seed_review_requests.jsonl`
- `data/evaluation/api_results/naturereview_v01/seed_review_results.jsonl`
- request_count: 200
- result_count: 200
- error_count: 0
- model: deepseek-v3

## Rebuild status

The validated API results have been merged into:

- `data/evaluation/seed_set/v1/seed_model_reviewed_200.jsonl`
- `data/processed/review_interaction_kb/v1/interaction_units.jsonl`
- `data/evaluation/retrieval_v2/`
- `data/evaluation/workflow_v2/`

## Boundary

The API output is model-assisted, not human gold. It is acceptable as the v0.1 default seed review layer, but any formal benchmark claim must still disclose the label source.
