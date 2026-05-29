# Evaluation Protocol

## Tasks

1. Review concern extraction
2. Risk point classification
3. Author response strategy retrieval
4. Evidence recommendation
5. Rebuttal outline generation
6. Tone / structure revision
7. Decision-aware case retrieval
8. Tacit concern interpretation
9. Institutional positioning assessment
10. Actor-network case retrieval
11. Cognitive trace quality assessment

## Task Contracts

### Review concern extraction

- **Input**: Reviewer comment span plus provenance.
- **Output**: Concern map with concern_type, quoted evidence, and uncertainty note.
- **Supervision signal**: Heuristic/model-assisted concern labels; future human-confirmed labels.
- **Automatic metrics**: Exact/partial label match, evidence-span recoverability, unknown-rate.
- **Human evaluation metrics**: Concern correctness, evidence grounding, boundary awareness.
- **Baselines**: Historical local classifier, majority concern baseline, lightweight LLM zero-shot.
- **Failure modes**: Over-broad concern, confusing praise with concern, missing multi-issue comments.

### Risk point classification

- **Input**: Concern map, review text, response text, tacit concern taxonomy.
- **Output**: Risk type and tacit concern interpretation grounded in observable text.
- **Supervision signal**: Risk labels derived from taxonomy plus human adjudication slots.
- **Automatic metrics**: Risk label agreement, consistency with concern_type, unsupported-inference rate.
- **Human evaluation metrics**: Tacit concern interpretation quality and no mind-reading compliance.
- **Baselines**: Concern-to-risk lookup table, zero-shot classifier.
- **Failure modes**: Attributing hidden reviewer intent, flattening institutional risk into wording advice.

### Author response strategy retrieval

- **Input**: New review concern/risk query and optional filters.
- **Output**: Top-k historical interaction units with response_strategy and provenance.
- **Supervision signal**: Candidate response_strategy labels; future human relevance judgments.
- **Automatic metrics**: Strategy R@1/R@3/R@5, concern@5, joint strategy+concern@5, diversity.
- **Human evaluation metrics**: Case relevance, strategic usefulness, provenance traceability.
- **Baselines**: BM25, BM25+concern filter, lexical cosine, random same-concern baseline.
- **Failure modes**: Retrieving same-paper leakage, high text similarity but wrong strategy, low diversity.

### Evidence recommendation

- **Input**: Risk interpretation, retrieved cases, evidence_action taxonomy.
- **Output**: Evidence action plan: analysis, experiment, figure/table, supplement, code/data, or clarification.
- **Supervision signal**: Evidence action labels and retrieved author response actions.
- **Automatic metrics**: Evidence action match, unsupported action rate, provenance coverage.
- **Human evaluation metrics**: Evidence groundedness, feasibility, no fabricated experiment/data/citation.
- **Baselines**: Concern-to-evidence lookup, retrieved-nearest evidence action.
- **Failure modes**: Inventing new experiments, recommending infeasible work, ignoring claim boundary.

### Rebuttal outline generation

- **Input**: Concern map, risk interpretation, evidence plan, retrieved cases.
- **Output**: Structured outline, not submission-ready rebuttal text.
- **Supervision signal**: Workflow trace adequacy labels and human outline scores.
- **Automatic metrics**: Required-section coverage, provenance citation coverage, overclaim flags.
- **Human evaluation metrics**: Adequacy of response, organization, usefulness for author thinking.
- **Baselines**: Direct LLM outline, template-only outline, retrieval-only summary.
- **Failure modes**: Generating polished but unsupported rebuttal, skipping limitations, over-promising.

### Tone / structure revision

- **Input**: Draft outline or author notes plus tone/commitment taxonomy.
- **Output**: Tone warnings, commitment-level flags, safer structure suggestions.
- **Supervision signal**: Tone/commitment labels and human ratings.
- **Automatic metrics**: Unsupported commitment count, acceptance-prediction absence, banned behavior checks.
- **Human evaluation metrics**: Tone calibration, commitment safety, clarity without sycophancy.
- **Baselines**: Structured tone checklist, direct LLM editing.
- **Failure modes**: Politeness replacing substance, excessive concession, unverifiable promises.

### Decision-aware case retrieval

- **Input**: Concern/risk query plus optional decision/editor signal filters.
- **Output**: Cases with editor-readable signals and decision-context caveats.
- **Supervision signal**: Available editor_signal metadata and human case relevance labels.
- **Automatic metrics**: Decision-signal match@k, provenance completeness, case diversity.
- **Human evaluation metrics**: Decision-context usefulness and no acceptance prediction.
- **Baselines**: Concern-only retrieval, BM25 over review text.
- **Failure modes**: Inferring acceptance probability, treating editor signal as causal proof.

### Tacit concern interpretation

- **Input**: Concern/risk evidence and tacit concern taxonomy.
- **Output**: Observable trace of tacit judgment with boundary statement.
- **Supervision signal**: Taxonomy labels plus human cross-disciplinary rubric.
- **Automatic metrics**: Taxonomy coverage, evidence quote presence, mind-reading phrase absence.
- **Human evaluation metrics**: Tacit concern interpretation score.
- **Baselines**: Explicit concern restatement, direct LLM interpretation.
- **Failure modes**: Psychologizing reviewer, making unverifiable claims about hidden motives.

### Institutional positioning assessment

- **Input**: Concern, response, journal/policy/editor signal context when available.
- **Output**: Institutional signal note linked to author action options.
- **Supervision signal**: Institutional signal taxonomy and human ratings.
- **Automatic metrics**: Signal label match, link-to-action coverage, acceptance-prediction absence.
- **Human evaluation metrics**: Institutional positioning quality.
- **Baselines**: No-institution baseline, policy-signal detector.
- **Failure modes**: Ignoring journal/community norms, predicting editorial outcome.

### Actor-network case retrieval

- **Input**: Query plus desired actors such as figure, dataset, code, benchmark, supplement.
- **Output**: Cases showing how human and non-human actors are realigned.
- **Supervision signal**: Actor_links metadata and human relevance judgments.
- **Automatic metrics**: Actor type match@k, actor evidence coverage, case diversity.
- **Human evaluation metrics**: Actor-network alignment score.
- **Baselines**: Text-only retrieval, actor-metadata filter.
- **Failure modes**: Mentioning objects without explaining their interaction role.

### Cognitive trace quality assessment

- **Input**: Full workflow trace.
- **Output**: Trace quality score and missing-stage warnings.
- **Supervision signal**: Rubric scores from human evaluation sheet.
- **Automatic metrics**: Required stage completion, provenance checks, unsupported commitment flags.
- **Human evaluation metrics**: Cognitive trace quality and responsible-use compliance.
- **Baselines**: Direct response generation, trace without integrity checker.
- **Failure modes**: Post-hoc rationalization, missing commitment check, hidden direct generation.

## Label status

Current candidate labels are heuristic or model-assisted. They are not human gold.

Retrieval baselines, BM25-style baselines, and local comparison baselines are support infrastructure only. They are included to make the system auditable and comparable, but the project contribution is not RAG-only. The core value is a cross-disciplinary review-interaction workflow that turns tacit concern, institutional signal, actor-network alignment, cognitive correction, tone/commitment calibration, and author agency into recordable and evaluable traces.
