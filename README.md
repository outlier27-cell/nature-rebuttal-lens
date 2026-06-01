# Nature RebuttalLens

Nature RebuttalLens is a manuscript-aware, multi-agent author response assistant for peer-review rebuttal work. It helps an author analyze reviewer comments, connect concerns back to manuscript evidence, plan evidence actions, calibrate tone and commitments, and write an auditable workflow trace.

This project is not affiliated with, endorsed by, or operated by Nature Portfolio or Springer Nature. The name describes the intended journal-style use case, not an official product relationship.

## What It Does

The system is a non-training, cross-disciplinary workflow. It does not train or fine-tune models, and it is not a RAG system: retrieved cases are supporting context, while the core value is the structured agent workflow and traceable evidence boundary.

| Layer | Agent | Main output |
|---|---|---|
| Layer 0 | `manuscript_context_extractor` | manuscript sections, limits, evidence boundary |
| Layer 1 | `reviewer_understanding_agent` | explicit reviewer concerns and observable evidence |
| Layer 1 | `tacit_concern_interpreter` | bounded risk interpretation, not private intent |
| Layer 1 | `manuscript_evidence_locator` | manuscript evidence status and gaps |
| Layer 2 | `institutional_signal_interpreter` | editor-facing and journal-facing signals |
| Layer 2 | `case_retrieval_interpreter` | bounded historical analogies from retrieved cases |
| Layer 2 | `evidence_action_planner` | author-confirmed evidence actions |
| Layer 3 | `author_positioning_agent` | response stance and author agency |
| Layer 3 | `tone_commitment_calibrator` | tone, commitment, and overclaim risks |
| Layer 4 | `actor_network_mapper` | author, reviewer, editor, data, code, figure, citation actors |
| Layer 4 | `cross_disciplinary_lens_interpreter` | tacit knowledge boundary, institutional dependence, actor-network alignment, fast/slow cognitive correction, tone/commitment calibration, author agency gate |
| Layer 5 | `integrity_adequacy_checker` | final adequacy, provenance, safety, and responsible-use checks |

Each agent constructs its own prompt and calls the configured OpenAI-compatible model client. The final output is a structured trace, not a hidden one-shot rebuttal.

## Output: Not a Trace Dump

Nature RebuttalLens writes three levels of output:

1. `rebuttal_lens_trace.json` - full auditable agent trace.
2. `final_user_report.json` - structured author-facing report for downstream UI/API use.
3. `final_user_report.md` - readable response-planning report for authors.

Current runs also write `privacy_manifest.json`, `run_manifest.json`, and
`author_workspace.html`. The final report includes an `evidence_ledger` so each
comment card can be checked against a concern id, manuscript span, support
status, case ids, required author action, unsafe claim boundary, and author
confirmation requirement. The HTML workspace is a planning surface with action
statuses such as `needs evidence` and `needs author confirmation`; it is not
final submission text.

The default `layered` workflow is stable and cost-conscious. For deeper research evaluation, the CLI also supports an experimental DAG/committee/tournament mode:

```powershell
run-rebuttal-lens `
  --review-file examples/rebuttal_lens/reviewer_comment.txt `
  --manuscript-file examples/rebuttal_lens/manuscript_excerpt.txt `
  --response-file examples/rebuttal_lens/author_draft_response.txt `
  --retrieved-cases-file examples/rebuttal_lens/retrieved_cases.json `
  --allow-external-manuscript-upload `
  --workflow-engine dag `
  --enable-committee `
  --enable-strategy-tournament `
  --output-dir data/evaluation/rebuttal_lens_demo
```

In DAG mode, dependency-bound steps still run in order, but reviewer committee nodes and strategy analysis are represented as graph stages with explicit dependencies and meta-synthesis. This makes the workflow easier to audit and evaluate than a simple fixed chain.

## Repository Layout

```text
config/                  agent and workflow configuration
data/                    release-safe schemas, taxonomies, summaries, and evaluation artifacts
examples/rebuttal_lens/   runnable demo inputs
src/peer_review_skills/  Python package and CLI implementation
tests/                   regression and workflow tests
README.md                public project guide
LICENSE                  Apache-2.0 license
pyproject.toml           package metadata and console scripts
```

Internal planning notes, Codex session notes, upgrade logs, local knowledge-graph exports, and generated documentation folders are intentionally not part of the public repository.

## Installation

The project uses Python 3.10+ and a standard `src/` layout.

```powershell
git clone https://github.com/outlier27-cell/nature-rebuttal-lens.git
cd nature-rebuttal-lens
python -m pip install -e .
```

For PDF manuscript text extraction:

```powershell
python -m pip install -e ".[pdf]"
```

For local development without installing:

```powershell
$env:PYTHONPATH="src"
```

## Configuration

Set an OpenAI-compatible endpoint before running the real workflow:

```powershell
$env:PEER_REVIEW_API_BASE_URL="https://xh.v1api.cc"
$env:PEER_REVIEW_API_KEY="YOUR_KEY"
$env:PEER_REVIEW_API_MODEL="deepseek-v3"
```

If `PEER_REVIEW_API_KEY` is missing, the CLI fails fast instead of producing fake or partial model outputs.
When using an external provider with manuscript text, the CLI also requires
`--allow-external-manuscript-upload`; omit `--manuscript-file` if you do not
have policy approval and author consent.

## Quick Start

```powershell
$env:PYTHONPATH="src"
python -m peer_review_skills.cli.main run-rebuttal-lens `
  --review-file examples/rebuttal_lens/reviewer_comment.txt `
  --manuscript-file examples/rebuttal_lens/manuscript_excerpt.txt `
  --response-file examples/rebuttal_lens/author_draft_response.txt `
  --retrieved-cases-file examples/rebuttal_lens/retrieved_cases.json `
  --allow-external-manuscript-upload `
  --output-dir data/evaluation/rebuttal_lens_demo
```

After installation, the console script is also available:

```powershell
run-rebuttal-lens `
  --review-file examples/rebuttal_lens/reviewer_comment.txt `
  --manuscript-file examples/rebuttal_lens/manuscript_excerpt.txt `
  --response-file examples/rebuttal_lens/author_draft_response.txt `
  --retrieved-cases-file examples/rebuttal_lens/retrieved_cases.json `
  --allow-external-manuscript-upload `
  --output-dir data/evaluation/rebuttal_lens_demo
```

Main outputs:

```text
data/evaluation/rebuttal_lens_demo/rebuttal_lens_trace.json
data/evaluation/rebuttal_lens_demo/rebuttal_lens_summary.json
data/evaluation/rebuttal_lens_demo/final_user_report.json
data/evaluation/rebuttal_lens_demo/final_user_report.md
data/evaluation/rebuttal_lens_demo/checkpoints/
```

If a later agent fails after the workflow has already produced state, the system writes `rebuttal_lens_failure_trace.json` with completed message bus entries, execution trace, and sanitized metadata.

## Evaluation and Replay

RebuttalLens includes offline utilities for reproducibility and benchmark work:

```powershell
python -m peer_review_skills.cli.main replay-rebuttal-lens-trace `
  --trace-file data/evaluation/rebuttal_lens_demo/rebuttal_lens_trace.json `
  --output-dir data/evaluation/rebuttal_lens_replay

python -m peer_review_skills.cli.main build-rebuttal-lens-benchmark `
  --input-file openreview_discussions.json `
  --output-dir data/evaluation/rebuttal_lens_benchmark_v1

python -m peer_review_skills.cli.main calibrate-rebuttal-lens-judge `
  --human-file human_eval.csv `
  --judge-file judge_scores.jsonl `
  --output-dir data/evaluation/rebuttal_lens_judge_calibration
```

Replay is trace-only and makes no model calls. Benchmark adapters are
evaluation-only and non-training by default. Judge calibration is diagnostic
unless agreement and trace/ledger provenance are strong enough to justify a
bounded assistive role.

## Worked Example

The included example starts with four inputs:

- `examples/rebuttal_lens/reviewer_comment.txt`: reviewer comment.
- `examples/rebuttal_lens/manuscript_excerpt.txt`: author-provided manuscript excerpt.
- `examples/rebuttal_lens/author_draft_response.txt`: optional draft response.
- `examples/rebuttal_lens/retrieved_cases.json`: optional retrieved peer-review cases.

The CLI loads the files, builds a `unit` with `review_text`, `response_text`, optional `editor_text`, and `manuscript_context`, then runs the 12-agent workflow layer by layer. Upstream outputs are passed into downstream agents as structured context: manuscript context informs concern understanding and evidence location; concern and tacit-risk outputs feed institutional signal and evidence planning; evidence plans feed author positioning and tone calibration; all prior outputs feed actor-network, cross-disciplinary, and integrity checks.

Supported manuscript inputs include plain text, Markdown, LaTeX-like text, extractable PDF text, DOCX, and legacy DOC through LibreOffice conversion. PDF support is text extraction only, not OCR, image understanding, or complex table reconstruction.

## Current Status

- API seed review has been executed for 200 / 200 seed requests.
- Current seed and KB labels are model-assisted, not human gold.
- Workflow traces include agent intermediate outputs, case explanations, evidence action plans, author confirmation questions, response adequacy checks, and cross-disciplinary lens maps.
- Final user reports include a machine-checkable evidence ledger, privacy manifest, run manifest, replay path, and HTML author workspace.
- Simulation artifacts model reviewer, author rebuttal, and editor signal roles for evaluation only; they are not real peer review.
- Training and fine-tuning are outside the public v0.1 core scope.

## Verification

Recommended local checks:

```powershell
$env:PYTHONPATH="src"
python -m pytest -q
python -m compileall -q src tests
python -m peer_review_skills.cli.main validate-naturereview-v01
python -m pip install --dry-run -e .
```

The validation command checks release-safe schemas, taxonomies, model-assisted seed records, retrieval metrics, workflow traces, simulation traces, API handoff status, secret scan, and mojibake scan. It writes the machine-readable validation summary to `data/evaluation/naturereview_v01_validation_summary.json`.

## Responsible Use

Nature RebuttalLens is intended to help authors think, organize, and check rebuttal work. It must not be used to:

- fabricate experiments, data, citations, figures, analyses, or commitments;
- overstate what the manuscript supports;
- impersonate reviewers, editors, or authors;
- predict acceptance probability;
- manipulate reviewers or evade scientific problems;
- upload confidential manuscript material to an external API without policy and author approval.

When manuscript evidence is missing or uncertain, the system should state the gap and ask for author confirmation rather than inventing a claim.

## License

Apache License 2.0. See `LICENSE`.
