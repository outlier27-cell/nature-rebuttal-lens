# Nature RebuttalLens Agent Implementation Audit

## Audit Date

2026-05-29

## Purpose

This document records the current implementation of the public Nature RebuttalLens agent workflow. It supersedes earlier audits written before the manuscript-aware 12-agent upgrade.

## Public Entry Point

```powershell
$env:PYTHONPATH="src"
python -m peer_review_skills.cli.main run-rebuttal-lens `
  --review-file examples/rebuttal_lens/reviewer_comment.txt `
  --manuscript-file examples/rebuttal_lens/manuscript_excerpt.md `
  --response-file examples/rebuttal_lens/author_draft_response.txt `
  --retrieved-cases-file examples/rebuttal_lens/retrieved_cases.json `
  --output-dir data/evaluation/rebuttal_lens_demo
```

## Current Implementation

Nature RebuttalLens runs 12 independent model-assisted agent calls over user-supplied review/manuscript/response inputs and optional retrieved Nature case analogies.

The workflow is implemented in:

- `src/peer_review_skills/agents/base.py`
- `src/peer_review_skills/agents/rebuttal_lens_agents.py`
- `src/peer_review_skills/agents/specialized_agents.py`
- `src/peer_review_skills/agents/specialized_agents_part2.py`
- `src/peer_review_skills/agents/multi_agent_orchestrator.py`
- `src/peer_review_skills/agents/rebuttal_lens_workflow.py`

Each agent is a `BaseAgent` subclass. Each agent:

- builds its own task-specific prompt;
- calls the configured OpenAI-compatible model client;
- parses a JSON object response;
- validates required output fields;
- emits an `AgentMessage` recorded in the trace message bus.

## Agent List

| Order | Agent | Function |
| --- | --- | --- |
| 1 | `manuscript_context_extractor` | Summarizes supplied manuscript sections and evidence boundaries. |
| 2 | `reviewer_understanding_agent` | Extracts observable reviewer concerns. |
| 3 | `tacit_concern_interpreter` | Interprets tacit risks from observable textual traces only. |
| 4 | `manuscript_evidence_locator` | Connects concerns to supplied manuscript evidence or gaps. |
| 5 | `institutional_signal_interpreter` | Identifies bounded journal/editorial/community signals. |
| 6 | `case_retrieval_interpreter` | Treats retrieved Nature cases as bounded analogies. |
| 7 | `evidence_action_planner` | Plans author-confirmed evidence actions. |
| 8 | `author_positioning_agent` | Offers author stance options without forcing concession. |
| 9 | `tone_commitment_calibrator` | Checks tone, overclaiming, and commitment safety. |
| 10 | `actor_network_mapper` | Maps actors and evidence carriers. |
| 11 | `cross_disciplinary_lens_interpreter` | Applies the six interdisciplinary lenses. |
| 12 | `integrity_adequacy_checker` | Checks adequacy, provenance, author agency, and responsible-use warnings. |

## Output Contract

The workflow writes:

- `rebuttal_lens_trace.json`
- `rebuttal_lens_summary.json`

The trace contains:

- `system_name`
- `workflow_version`
- `agent_intermediate_outputs`
- `message_bus`
- `execution_trace`
- `execution_metadata`
- `manuscript_context`
- `responsible_use_boundary`

## Safety Boundaries

The public agent path must preserve these boundaries:

- no final submission-ready rebuttal text by default;
- no acceptance prediction;
- no invented experiments, data, citations, or commitments;
- no claim to know private reviewer psychology;
- all evidence actions require author confirmation;
- retrieved Nature cases are analogies, not rules or outcome predictors;
- users must control privacy and policy compliance before sending manuscript text to external APIs.

## Legacy Note

The older v0.1 artifact generator still creates deterministic release artifacts and model-assisted labels from the existing KB. That legacy path is useful for reproducible data reports and validation, but it is not the final user-facing Nature RebuttalLens workflow.

## Audit Verdict

The current public implementation is a real manuscript-aware multi-agent workflow with 12 independent LLM calls in the default no-refinement path. Release readiness depends on fresh verification of tests, validation, compile checks, demo behavior, and secret scanning.
