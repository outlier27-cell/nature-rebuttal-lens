# True Multi-Agent Implementation Summary

Date: 2026-05-28

This summary reflects the current v3 implementation state. Earlier prototype
notes are superseded by the verified workflow and verification log below.

## Current Status

The v3 workflow is a working DeepSeek/OpenAI-compatible multi-agent entry point
over the NatureReview-Interact v0.1 artifacts.

Current smoke-test evidence:

```json
{
  "total_traces": 1,
  "total_llm_calls": 9,
  "input_interaction_units": 245,
  "input_retrieval_predictions": 100
}
```

This proves the integration path runs. It does not prove quality improvement;
that requires separate human/expert evaluation.

## Implemented Components

- `src/peer_review_skills/agents/base.py`
  - `BaseAgent`
  - `AgentMessage`
  - parsed/raw OpenAI-compatible response normalization

- `src/peer_review_skills/agents/multi_agent_orchestrator.py`
  - dependency-aware execution
  - fail-fast layer handling
  - message bus
  - refinement with original context, downstream propagation, and integrity recheck
  - execution metadata

- `src/peer_review_skills/agents/specialized_agents.py`
  - Reviewer understanding
  - Tacit concern interpretation
  - Institutional signal interpretation
  - Evidence action planning
  - Author positioning
  - Tone/commitment calibration

- `src/peer_review_skills/agents/specialized_agents_part2.py`
  - Actor-network mapping
  - Cross-disciplinary lens interpretation
  - Integrity/adequacy checking

- `src/peer_review_skills/agents/workflow_integration.py`
  - official v0.1 KB loading
  - official retrieval v2 loading
  - taxonomy alias loading
  - DeepSeek/OpenAI-compatible client creation
  - workflow v3 JSONL output

- `src/peer_review_skills/cli/main.py`
  - `run-naturereview-multi-agent`

## Agent Sequence

```text
reviewer_understanding_agent
tacit_concern_interpreter
institutional_signal_interpreter
evidence_action_planner
author_positioning_agent
tone_commitment_calibrator
actor_network_mapper
cross_disciplinary_lens_interpreter
integrity_adequacy_checker
```

The cross-disciplinary lens interpreter runs after actor-network mapping so it
can use observable evidence carriers rather than free-floating theory.

The default no-refinement run uses 9 LLM calls across 8 dependency-aware
execution steps. If refinement is enabled, the orchestrator revises the flagged
agent output, reruns dependent downstream agents, and then runs an integrity
recheck. Remaining critical issues after the configured limit fail the workflow.

## Boundaries

The system is:

- an assistant workflow;
- model-assisted, not human gold;
- provenance-aware;
- case-grounded;
- author-confirmation gated.

The system is not:

- a final rebuttal writer;
- an acceptance predictor;
- a replacement for authors, reviewers, or editors;
- a claim that AI can read private reviewer intent;
- a claim that multi-agent output is automatically better.

## Verification

Phase 7 verification is recorded in `UPGRADE.md`.
