# Nature RebuttalLens

**Nature RebuttalLens is a manuscript-aware, cross-disciplinary Author Rebuttal Assistant workflow built from Nature transparent peer-review interaction cases.**

It helps authors interpret reviewer comments with structure: what the reviewer explicitly asks for, what risk may sit behind the comment, what evidence in the manuscript is already usable, what still needs author confirmation, and how similar Nature review interactions can be used as bounded historical analogies.

This is an independent open-source research project. It is not affiliated with, endorsed by, or operated by Nature Portfolio or Springer Nature.

## What The System Does

Nature RebuttalLens turns a reviewer comment, optional manuscript text, optional draft response, and optional retrieved Nature peer-review cases into a traceable assistant workflow.

The system is designed to:

- identify explicit reviewer concerns and possible tacit risks;
- connect reviewer concerns back to manuscript evidence when manuscript text is provided;
- interpret institutional and editor-facing signals without claiming access to hidden reviewer intent;
- retrieve and interpret similar Nature review-response cases as historical analogies;
- plan evidence actions, response structure, tone, author positioning, and integrity checks;
- produce a recorded workflow trace that can be inspected, evaluated, and improved.

It is not a final rebuttal generator, acceptance predictor, reviewer replacement, or tool for inventing experiments, fabricating evidence, or making commitments the authors cannot support.

## Why It Exists

Most rebuttal tools treat reviewer comments as plain text tasks. This project treats peer review as an interaction among scientific claims, evidence standards, institutional expectations, author agency, editor-readable signals, and tone/commitment choices.

This is not a RAG system. Retrieval is support infrastructure; the core contribution is a cross-disciplinary workflow that turns tacit concern, institutional signal, actor-network alignment, fast/slow cognitive correction, tone/commitment calibration, and author agency into recordable and evaluable traces.

The core value is therefore not a single RAG pipeline or a single technical recipe. The current non-training release focuses on the workflow and evaluation scaffold. Training and fine-tuning are outside the v0.1 core scope.

## Workflow

Nature RebuttalLens runs a manuscript-aware multi-agent workflow:

1. Manuscript context extraction
2. Manuscript evidence location
3. Nature case retrieval interpretation
4. Reviewer understanding
5. Tacit concern interpretation
6. Institutional signal interpretation
7. Evidence action planning
8. Author positioning
9. Tone and commitment calibration
10. Actor-network mapping
11. Cross-disciplinary lens interpretation
12. Integrity and adequacy checking

Each agent is an independent model-assisted reasoning unit. The final output is a structured workflow trace, not a hidden one-shot answer.

## Quick Start

Set an OpenAI-compatible API endpoint and model. For example:

```powershell
$env:PEER_REVIEW_API_BASE_URL="https://xh.v1api.cc"
$env:PEER_REVIEW_API_KEY="YOUR_KEY"
$env:PEER_REVIEW_API_MODEL="deepseek-v3"
```

Run the included example:

```powershell
$env:PYTHONPATH="src"
python -m peer_review_skills.cli.main run-rebuttal-lens `
  --review-file examples/rebuttal_lens/reviewer_comment.txt `
  --manuscript-file examples/rebuttal_lens/manuscript_excerpt.md `
  --response-file examples/rebuttal_lens/author_draft_response.txt `
  --retrieved-cases-file examples/rebuttal_lens/retrieved_cases.json `
  --output-dir data/evaluation/rebuttal_lens_demo
```

The workflow writes:

- `data/evaluation/rebuttal_lens_demo/rebuttal_lens_trace.json`
- `data/evaluation/rebuttal_lens_demo/rebuttal_lens_summary.json`

The legacy alias `run-reviewweaver` is kept only for compatibility. The public project name is Nature RebuttalLens.

## Example Inputs

The demo files are under `examples/rebuttal_lens/`:

- `reviewer_comment.txt`: reviewer critique or review excerpt
- `manuscript_excerpt.md`: manuscript excerpt supplied by the author
- `author_draft_response.txt`: optional draft author response
- `retrieved_cases.json`: optional retrieved Nature case analogies

Current manuscript loading supports text, Markdown, and LaTeX-like plain text files. PDF/DOCX parsing is intentionally not claimed in this release.

## Current Status

This repository currently contains candidate data, schema, taxonomy, retrieval baselines, workflow traces, reviewer-author-editor simulation/evaluation traces, cross-disciplinary lens maps, evaluation protocols, and API-assisted seed review results.

- API seed review has been executed for 200 / 200 seed requests.
- The current seed and KB labels are model-assisted, not human gold.
- System-side workflow traces include case explanations, evidence action plans, author confirmation questions, response adequacy checks, and not-real-peer-review simulation roles.
- Human-confirmed labels are a future extension, not a v0.1 release blocker.
- Training and fine-tuning are outside the v0.1 core scope.

## Data Boundary

This repository contains a release-safe subset of derived schemas, taxonomies, summaries, documentation, and evaluation scaffolds. Large scraped data, local caches, API outputs, PDFs, and private working files are excluded by `.gitignore`.

Current labels and traces are model-assisted research artifacts, not human gold annotations. They are suitable for workflow development, auditing, and evaluation design, but should not be presented as expert-labeled ground truth.

## Key Documents

- `docs/2026-05-26-open-source-review-interaction-agent-full-plan-zh.md`: full cross-disciplinary open-source plan
- `docs/REBUTTAL_LENS_WORKFLOW_zh.md`: final Nature RebuttalLens workflow explanation
- `docs/INTERDISCIPLINARY_SYSTEM_FRAME_zh.md`: interdisciplinary system frame
- `docs/PDF_DERIVED_DESIGN_LENSES_zh.md`: design lenses derived from the project PDFs
- `docs/RESPONSIBLE_USE_zh.md`: responsible-use boundaries
- `docs/EVALUATION_PROTOCOL_zh.md`: evaluation protocol
- `docs/OPEN_SOURCE_V0_1_COMPLETION_STATUS_zh.md`: current release completion status
- `codex.md`: current Chinese project overview for future coding sessions

## Verification

Recommended local checks:

```powershell
$env:PYTHONPATH="src"
python -m pytest -q
python -m peer_review_skills.cli.main validate-naturereview-v01
```

The validation command checks the release-safe NatureReview v0.1 artifacts that support the Nature RebuttalLens workflow.

## Responsible Use

Nature RebuttalLens should be used to help authors think, organize, and check their rebuttal work. It must not be used to fabricate evidence, overstate manuscript support, impersonate reviewers or editors, or replace human scholarly judgment.

When the manuscript does not support a response, the system should state the gap and require author confirmation rather than inventing a claim.

## License

See `LICENSE`.
