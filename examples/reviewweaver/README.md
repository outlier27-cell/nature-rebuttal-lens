# ReviewWeaver Example

This folder contains a minimal manuscript-aware Author Rebuttal Assistant example.

Run with a real OpenAI-compatible provider:

```powershell
$env:PYTHONPATH='src'
$env:PEER_REVIEW_API_BASE_URL='https://xh.v1api.cc'
$env:PEER_REVIEW_API_MODEL='deepseek-v3'
$env:PEER_REVIEW_API_KEY='YOUR_KEY'
python -m peer_review_skills.cli.main run-reviewweaver `
  --review-file examples/reviewweaver/reviewer_comment.txt `
  --manuscript-file examples/reviewweaver/manuscript_excerpt.md `
  --response-file examples/reviewweaver/author_draft_response.txt `
  --output-dir data/evaluation/reviewweaver_demo
```

The output is a workflow trace, not final submission-ready rebuttal text.
