# RebuttalLens True Multi-Agent Architecture Design

RebuttalLens upgrades the v3 NatureReview-Interact architecture into a manuscript-aware workflow. The original `run-naturereview-multi-agent` path still runs the v0.1 KB trace workflow; the final user-facing research assistant path is `run-rebuttal-lens`.

The RebuttalLens path runs 12 independent LLM calls per interaction in default no-refinement mode:

1. ManuscriptContextExtractor
2. ManuscriptEvidenceLocator
3. ReviewerUnderstanding
4. TacitConcernInterpreter
5. InstitutionalSignalInterpreter
6. CaseRetrievalInterpreter
7. EvidenceActionPlanner
8. AuthorPositioning
9. ToneCommitmentCalibrator
10. ActorNetworkMapper
11. CrossDisciplinaryLensInterpreter
12. IntegrityAdequacyChecker

The key design change is that manuscript evidence and evidence gaps enter the workflow before evidence planning. Nature cases remain bounded analogies, not rule sources or outcome predictors.

---

# Legacy v3 Architecture

Date: 2026-05-28

This document describes the current v3 multi-agent implementation for
NatureReview-Interact. The system is a non-training, cross-disciplinary
assistant workflow over the v0.1 NatureReview knowledge base. It is not a final
rebuttal writer, not an acceptance predictor, and not a reviewer/editor
replacement.

## Entry Point

```powershell
$env:PYTHONPATH='src'
$env:PEER_REVIEW_API_BASE_URL='https://xh.v1api.cc'
$env:PEER_REVIEW_API_MODEL='deepseek-v3'
$env:PEER_REVIEW_API_KEY='YOUR_KEY'
python -m peer_review_skills.cli.main run-naturereview-multi-agent --limit 1
```

The run writes:

- `data/evaluation/workflow_v3/workflow_traces.jsonl`
- `data/evaluation/workflow_v3/workflow_summary.json`

## Inputs

The workflow reads the existing v0.1 artifacts:

- `data/processed/review_interaction_kb/v1/interaction_units.jsonl`
- `data/evaluation/retrieval_v2/predictions.jsonl`
- `data/processed/taxonomies/*.json`

The retrieval artifact supplies provenance-linked Nature case analogies. The
taxonomy loader exposes agent-facing aliases such as `concern_taxonomy`,
`tacit_concern`, `evidence_action`, `institutional_signal`,
`author_positioning`, and `tone_commitment`.

## Agents

The workflow runs 9 independent LLM calls per interaction unit.

| Step | Agent | Purpose |
| --- | --- | --- |
| 1 | `ReviewerUnderstandingAgent` | Extract observable reviewer concerns. |
| 2 | `TacitConcernInterpreterAgent` | Convert observable traces into bounded tacit-risk hypotheses. |
| 3 | `InstitutionalSignalInterpreterAgent` | Identify journal/community/editorial signals without predicting acceptance. |
| 4 | `EvidenceActionPlannerAgent` | Plan evidence actions grounded in retrieved Nature cases and requiring author confirmation. |
| 5 | `AuthorPositioningAgent` | Present author stance options without forcing concession. |
| 6 | `ToneCommitmentCalibratorAgent` | Check defensiveness, overclaiming, unsupported commitments, and excessive concession. |
| 7 | `ActorNetworkMapperAgent` | Map reviewers, authors, figures, datasets, code, supplements, and other evidence carriers. |
| 8 | `CrossDisciplinaryLensInterpreterAgent` | Apply the six project lenses over prior agent outputs and retrieved case IDs. |
| 9 | `IntegrityAdequacyCheckerAgent` | Check adequacy, provenance, author agency, responsible-use warnings, and unsupported claims. |

## Execution Order

```text
Layer 1a: Reviewer Understanding
  reviewer_understanding_agent

Layer 1b: Tacit Concern Interpretation
  tacit_concern_interpreter

Layer 2: Strategy & Evidence
  institutional_signal_interpreter
  evidence_action_planner

Layer 3a: Author Positioning
  author_positioning_agent

Layer 3b: Tone & Commitment
  tone_commitment_calibrator

Layer 4a: Actor Network
  actor_network_mapper

Layer 4b: Cross-Disciplinary Lenses
  cross_disciplinary_lens_interpreter

Layer 5: Integrity
  integrity_adequacy_checker
```

Layer 1 and Layer 3 are split where later agents need earlier structured
outputs. Layer 4 is split because the cross-disciplinary lens interpreter needs
the actor-network output. A no-refinement trace records eight execution steps
while still using nine LLM calls.

When refinement is enabled, an integrity finding triggers:

1. targeted agent refinement using its original task context plus feedback;
2. downstream propagation for dependent agents;
3. integrity recheck over the propagated outputs;
4. fail-fast termination if critical issues remain after the configured limit.

## Communication Protocol

Each agent emits an `AgentMessage`:

```python
{
  "agent_id": "reviewer_understanding_agent",
  "timestamp": "...",
  "message_type": "output",
  "content": {...},
  "metadata": {
    "model": "deepseek-v3",
    "temperature": 0.0
  }
}
```

The orchestrator fails fast if any agent in a step fails. This prevents partial
traces from being mistaken for complete multi-agent reasoning.

## Cross-Disciplinary Lenses

The lens interpreter applies:

- tacit knowledge boundary
- institutional dependence
- actor-network alignment
- fast/slow cognitive correction
- emotion-tone-commitment calibration
- author agency gate

The prompt explicitly forbids:

- inferring private reviewer psychology;
- claiming to know reviewer motives;
- predicting acceptance probability;
- inferring hidden institutional decisions;
- manipulating reviewer motivations.

Each lens should be framed as support for author reflection, evidence planning,
and integrity checking.

## Output Contract

Each trace includes:

- `agent_intermediate_outputs`
- `message_bus`
- `execution_trace`
- `execution_metadata.total_llm_calls`
- `execution_metadata.layers_executed`

For a successful single-unit run, current expected smoke-test values are:

```json
{
  "total_traces": 1,
  "total_llm_calls": 9,
  "input_interaction_units": 245,
  "input_retrieval_predictions": 100
}
```

This is a smoke-test result, not a claim of quality improvement.

## Boundaries

The system must keep these boundaries:

- model-assisted labels are not human gold;
- all evidence actions require author confirmation;
- retrieved cases are analogies, not proof that a strategy will work;
- the assistant does not write final submission-ready rebuttals by default;
- the assistant does not predict acceptance or editorial outcomes;
- private manuscripts should not be uploaded to uncontrolled external APIs.
