# Nature RebuttalLens

**A manuscript-aware, cross-disciplinary Author Rebuttal Assistant workflow built from Nature transparent peer-review interaction cases.**

Nature RebuttalLens helps authors and researchers inspect reviewer comments as structured scholarly interactions: explicit concern, tacit risk, manuscript evidence, historical Nature case analogy, author stance, tone/commitment, and integrity boundary.

This is an independent open-source research project. It is not affiliated with, endorsed by, or operated by Nature Portfolio or Springer Nature.

## Why This Project Exists

Most rebuttal tools treat review comments as ordinary text-generation prompts. Nature RebuttalLens treats peer review as an interaction among scientific claims, manuscript evidence, reviewer concerns, journal norms, author agency, editor-readable signals, and responsible-use boundaries.

The project is therefore not a RAG demo and not an automatic rebuttal writer. Retrieval is only support infrastructure. The core contribution is a **recordable and evaluable review-interaction workflow** grounded in:

- reviewer concern understanding;
- tacit risk interpretation from observable text;
- manuscript evidence location;
- bounded analogy to Nature transparent peer-review cases;
- evidence action planning;
- author positioning and tone/commitment calibration;
- actor-network and cross-disciplinary interpretation;
- integrity, provenance, and author-confirmation checks.

## What It Does

Nature RebuttalLens turns a reviewer comment, optional manuscript text, optional draft response, optional editor letter, and optional retrieved Nature case analogies into a structured workflow trace.

| Capability | Output |
| --- | --- |
| Reviewer understanding | Concern map and observable textual evidence |
| Tacit risk interpretation | Risk notes without claiming private reviewer psychology |
| Manuscript evidence location | Supported / partial / missing evidence map over supplied manuscript text |
| Nature case interpretation | Historical case analogies with transfer boundaries |
| Evidence action planning | Required artifacts and author-confirmation questions |
| Author positioning | Response stance options, not forced concessions |
| Tone and commitment calibration | Defensive tone, overclaim, and unsupported commitment warnings |
| Actor-network mapping | Evidence carriers such as figures, datasets, code, tables, supplements |
| Cross-disciplinary lensing | Tacit knowledge, institutional dependence, actor-network alignment, fast/slow correction, tone/commitment, author agency |
| Integrity checking | Adequacy, provenance, and responsible-use warnings |

It does **not** generate submission-ready final rebuttals by default, predict acceptance probability, replace author judgment, or invent experiments, data, citations, or commitments.

## System Workflow

Nature RebuttalLens runs a 12-agent manuscript-aware workflow:

```text
User inputs
  reviewer comment
  manuscript text / Markdown / LaTeX-like text
  optional draft response
  optional editor letter
  optional retrieved Nature cases
        |
        v
Layer 0: Manuscript context
  1. manuscript_context_extractor
        |
        v
Layer 1: Review understanding
  2. reviewer_understanding_agent
  3. tacit_concern_interpreter
  4. manuscript_evidence_locator
        |
        v
Layer 2: Strategy and evidence
  5. institutional_signal_interpreter
  6. case_retrieval_interpreter
  7. evidence_action_planner
        |
        v
Layer 3: Author response planning
  8. author_positioning_agent
  9. tone_commitment_calibrator
        |
        v
Layer 4: Cross-disciplinary interpretation
  10. actor_network_mapper
  11. cross_disciplinary_lens_interpreter
        |
        v
Layer 5: Integrity gate
  12. integrity_adequacy_checker
        |
        v
Trace output
  rebuttal_lens_trace.json
  rebuttal_lens_summary.json
```

For a visual local diagram, open:

```text
docs/rebuttal_lens_system_flow.html
```

## Installation

The repository uses a standard Python `src/` layout and requires Python 3.10+.

```powershell
git clone https://github.com/outlier27-cell/nature-rebuttal-lens.git
cd nature-rebuttal-lens
python -m pip install -e .
```

For local development without installing:

```powershell
$env:PYTHONPATH="src"
```

## Quick Start

Nature RebuttalLens uses an OpenAI-compatible chat completion API. The default examples use a DeepSeek-compatible endpoint, but any compatible provider can be configured.

```powershell
$env:PEER_REVIEW_API_BASE_URL="https://xh.v1api.cc"
$env:PEER_REVIEW_API_KEY="YOUR_KEY"
$env:PEER_REVIEW_API_MODEL="deepseek-v3"
```

Run the included example:

```powershell
python -m peer_review_skills.cli.main run-rebuttal-lens `
  --review-file examples/rebuttal_lens/reviewer_comment.txt `
  --manuscript-file examples/rebuttal_lens/manuscript_excerpt.md `
  --response-file examples/rebuttal_lens/author_draft_response.txt `
  --retrieved-cases-file examples/rebuttal_lens/retrieved_cases.json `
  --output-dir data/evaluation/rebuttal_lens_demo
```

Installed console scripts are also available after `pip install -e .`:

```powershell
run-rebuttal-lens `
  --review-file examples/rebuttal_lens/reviewer_comment.txt `
  --manuscript-file examples/rebuttal_lens/manuscript_excerpt.md `
  --response-file examples/rebuttal_lens/author_draft_response.txt `
  --retrieved-cases-file examples/rebuttal_lens/retrieved_cases.json `
  --output-dir data/evaluation/rebuttal_lens_demo
```

The workflow writes:

- `data/evaluation/rebuttal_lens_demo/rebuttal_lens_trace.json`
- `data/evaluation/rebuttal_lens_demo/rebuttal_lens_summary.json`

The legacy alias `run-reviewweaver` is kept only for compatibility. The public project name is **Nature RebuttalLens**.

## Example Inputs

The minimal demo lives in `examples/rebuttal_lens/`:

| File | Purpose |
| --- | --- |
| `reviewer_comment.txt` | Reviewer critique or review excerpt |
| `manuscript_excerpt.md` | Author-supplied manuscript excerpt |
| `author_draft_response.txt` | Optional draft author response |
| `retrieved_cases.json` | Optional retrieved Nature case analogies |

Current manuscript loading supports text, Markdown, and LaTeX-like plain text. PDF/DOCX parsing is intentionally not claimed in this release.

## Current Status

This is an alpha research-software release focused on the non-training workflow and evaluation scaffold.

Current release artifacts include:

- release-safe schema and taxonomy files;
- derived KB summaries and validation reports;
- retrieval and workflow evaluation scaffolds;
- model-assisted seed review results;
- 12-agent Nature RebuttalLens workflow;
- responsible-use, data-boundary, and agent-card documentation.

Known status boundaries:

- API seed review has been executed for 200 / 200 seed requests.
- Current seed and KB labels are model-assisted, not human gold.
- Human-confirmed labels are future work, not a v0.1 release blocker.
- Training and fine-tuning are outside the v0.1 core scope.
- The system does not prove acceptance-rate improvement or causal outcome effects.

## Data Boundary

This repository contains a release-safe subset of derived schemas, taxonomies, summaries, documentation, examples, and evaluation scaffolds.

Large scraped data, local caches, API outputs, PDFs, private working files, and full raw peer-review corpora are excluded by `.gitignore`.

Current labels and traces are model-assisted research artifacts. They are useful for workflow development, auditing, and evaluation design, but should not be presented as expert-labeled ground truth.

## Verification

Recommended local checks:

```powershell
$env:PYTHONPATH="src"
python -m pytest -q
python -m compileall -q src tests
python -m peer_review_skills.cli.main validate-naturereview-v01
python -m pip install --dry-run -e .
```

The validation command checks the release-safe NatureReview v0.1 artifacts that support the Nature RebuttalLens workflow.

Latest local release-readiness check recorded in `UPGRADE.md`:

- full pytest: `80 passed`;
- compileall: pass;
- v0.1 artifact validation: `PASS`;
- package dry-run: would install `nature-rebuttal-lens-0.1.0`;
- secret scan: no persisted real API keys or bearer tokens found.

## Key Documents

| Document | Purpose |
| --- | --- |
| `docs/2026-05-26-open-source-review-interaction-agent-full-plan-zh.md` | Full cross-disciplinary open-source research plan |
| `docs/REBUTTAL_LENS_WORKFLOW_zh.md` | Final workflow explanation |
| `docs/INTERDISCIPLINARY_SYSTEM_FRAME_zh.md` | Interdisciplinary system frame |
| `docs/PDF_DERIVED_DESIGN_LENSES_zh.md` | Design lenses derived from project PDFs |
| `docs/RESPONSIBLE_USE_zh.md` | Responsible-use boundaries |
| `docs/DATA_CARD_zh.md` | Data card |
| `docs/AGENT_CARD_zh.md` | Agent card |
| `docs/EVALUATION_PROTOCOL_zh.md` | Evaluation protocol |
| `docs/DATA_RELEASE_BOUNDARY_zh.md` | Data release boundary |
| `docs/MODEL_AND_AGENT_LIMITATIONS_zh.md` | Model and agent limitations |
| `docs/rebuttal_lens_system_flow.html` | Local visual workflow diagram |
| `codex.md` | Current Chinese project overview for future coding sessions |

## Responsible Use

Nature RebuttalLens is intended to help authors think, organize, and check their rebuttal work. It must not be used to:

- fabricate experiments, data, citations, figures, analyses, or commitments;
- overstate what the manuscript supports;
- impersonate reviewers, editors, or authors;
- predict acceptance probability;
- manipulate reviewers or evade real scientific problems;
- upload confidential manuscript material to an external API without policy and author approval.

When the supplied manuscript does not support a response, the system should state the gap and require author confirmation rather than inventing a claim.

## License

Apache License 2.0. See `LICENSE`.
