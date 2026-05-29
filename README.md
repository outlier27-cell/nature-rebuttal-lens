# NatureReview-Interact

NatureReview-Interact is a non-training, cross-disciplinary open research framework for studying and assisting scientific review interactions from transparent peer review data.

This is not a RAG system. Retrieval is support infrastructure; the core contribution is a cross-disciplinary workflow that turns tacit concern, institutional signal, actor-network alignment, fast/slow cognitive correction, tone/commitment calibration, and author agency into recordable and evaluable traces.

It is not:

- an automatic rebuttal-writing service;
- an acceptance-probability predictor;
- a replacement for authors, reviewers, or editors;
- not a RAG system;
- 不是单一技术套路;
- a tool for uploading confidential manuscripts to external AI services.

## What it studies

The project learns observable interaction structures:

```text
reviewer concern -> tacit / explicit risk -> institutional signal -> evidence action -> author positioning -> tone / commitment -> editor signal
```

## Current status

This repository currently contains candidate data, schema, taxonomy, retrieval baselines, workflow traces, reviewer-author-editor simulation/evaluation traces, cross-disciplinary lens maps, evaluation protocols, and API-assisted seed review results.

- API seed review has been executed for 200 / 200 seed requests.
- The current seed and KB labels are model-assisted, not human gold.
- System-side workflow traces include case explanations, evidence action plans, author confirmation questions, response adequacy checks, and not-real-peer-review simulation roles.
- Human-confirmed labels are a future extension, not a v0.1 release blocker.
- 训练和微调不属于 v0.1 核心.

## Key documents

- `docs/NON_TRAINING_OPEN_SOURCE_SCOPE_zh.md`
- `docs/PDF_DERIVED_DESIGN_LENSES_zh.md`
- `docs/INTERDISCIPLINARY_SYSTEM_FRAME_zh.md`
- `docs/OPEN_SOURCE_V0_1_COMPLETION_STATUS_zh.md`
- `docs/WORKFLOW_SPEC_zh.md`
- `docs/SIMULATION_EVALUATION_SPEC_zh.md`
- `docs/EVALUATION_PROTOCOL_zh.md`
- `docs/DATA_RELEASE_BOUNDARY_zh.md`
