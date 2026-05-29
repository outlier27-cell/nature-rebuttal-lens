# RebuttalLens / Multi-Agent System Usage Guide

RebuttalLens is the final manuscript-aware system name. The older `run-naturereview-multi-agent` command remains available for v0.1 KB traces; the final user-facing research assistant command is `run-rebuttal-lens`.

```powershell
$env:PYTHONPATH='src'
$env:PEER_REVIEW_API_BASE_URL='https://xh.v1api.cc'
$env:PEER_REVIEW_API_MODEL='deepseek-v3'
$env:PEER_REVIEW_API_KEY='YOUR_KEY'
python -m peer_review_skills.cli.main run-rebuttal-lens `
  --review-file examples/rebuttal_lens/reviewer_comment.txt `
  --manuscript-file examples/rebuttal_lens/manuscript_excerpt.md `
  --response-file examples/rebuttal_lens/author_draft_response.txt `
  --output-dir data/evaluation/rebuttal_lens_demo
```

The RebuttalLens trace adds manuscript context extraction, manuscript evidence location, and bounded Nature case interpretation before the existing cross-disciplinary multi-agent workflow.

---

# Legacy NatureReview-Interact v0.1 Multi-Agent Usage

## Overview

NatureReview-Interact now has a real multi-agent entry point for the v0.1
knowledge base. It runs 9 independent LLM reasoning agents over the official
NatureReview KB and retrieval artifacts, then records a trace for concern
understanding, tacit risk, institutional signal, evidence action, author
positioning, tone/commitment, actor-network mapping, cross-disciplinary lens
interpretation, and integrity checking.

This is still an assistant workflow, not a final rebuttal writer, not an
acceptance predictor, and not a replacement for author judgment.

## Quick Start

### 1. Set up API credentials

```powershell
$env:PEER_REVIEW_API_BASE_URL='https://xh.v1api.cc'
$env:PEER_REVIEW_API_KEY='YOUR_KEY'
$env:PEER_REVIEW_API_MODEL='deepseek-v3'
```

### 2. Run multi-agent workflow

```powershell
$env:PYTHONPATH='src'
python -m peer_review_skills.cli.main run-naturereview-multi-agent --limit 1
```

The output is written to:

```text
data/evaluation/workflow_v3/workflow_traces.jsonl
data/evaluation/workflow_v3/workflow_summary.json
```

## Configuration

Edit `config/multi_agent_config.yaml`:

```yaml
workflow:
  mode: "multi_agent"

multi_agent:
  enable_refinement: false
  max_refinement_iterations: 2
  sequential_dependency_layers: true
```

## The 9 Agents

### Layer 1: Understanding

1. **ReviewerUnderstandingAgent**
   - Identifies what reviewer is asking for
   - Maps to concern taxonomy
   - Grounds in observable text

2. **TacitConcernInterpreterAgent**
   - Interprets implicit risks
   - Maps to risk/tacit concern taxonomies
   - Avoids psychological claims
   - Runs after reviewer understanding so it can use the concern map

### Layer 2: Strategy & Evidence

3. **InstitutionalSignalInterpreterAgent**
   - Identifies institutional/editorial signals
   - Maps to institutional signal taxonomy
   - No acceptance predictions

4. **EvidenceActionPlannerAgent**
   - Plans evidence actions
   - Uses retrieved similar cases
   - Requires author confirmation

### Layer 3: Positioning

5. **AuthorPositioningAgent**
   - Identifies positioning options
   - Offers choices, doesn't force concession
   - Maps to positioning taxonomy

6. **ToneCommitmentCalibratorAgent**
   - Calibrates tone and commitments
   - Flags risks (defensive, overclaiming)
   - No psychological diagnosis
   - Runs after author positioning so it can calibrate stance and commitment together

### Layer 4: Network & Context

7. **ActorNetworkMapperAgent**
   - Maps human/non-human actors
   - Identifies who/what carries evidence
   - Observable alignment only

8. **CrossDisciplinaryLensInterpreterAgent**
   - Applies 6 theoretical lenses
   - Uses prior agent outputs and retrieved Nature case IDs
   - Provides evaluation questions
   - Does not infer private reviewer psychology or manipulate reviewer motives

### Layer 5: Integrity (Sequential)

9. **IntegrityAdequacyCheckerAgent**
   - Final quality control
   - Provenance checking
   - Responsible use warnings

## Agent Communication

Agents communicate through `AgentMessage` objects:

```python
@dataclass
class AgentMessage:
    agent_id: str
    timestamp: str
    message_type: str  # "output", "question", "refinement_request"
    content: dict[str, Any]
    metadata: dict[str, Any]
```

## Refinement Loops

Enable refinement to allow agents to improve each other's outputs:

```powershell
python -m peer_review_skills.cli.main run-naturereview-multi-agent `
  --enable-refinement \
  --max-refinement-iterations 2
```

How it works:
1. IntegrityAdequacyChecker identifies issues
2. Sends a refinement request to the specific agent, including the previous output and feedback
3. The agent revises its output using the original task context
4. Downstream dependent agents rerun with the revised output
5. IntegrityAdequacyChecker re-checks the propagated workflow
6. Repeat up to max iterations, or fail fast if critical issues remain

## Cost Control

Use `--limit` for release smoke tests and small-batch evaluation. Full KB runs
make 9 model calls per interaction unit, so they should be explicit.

```powershell
python -m peer_review_skills.cli.main run-naturereview-multi-agent --limit 5
```

### Batch Processing

Process a bounded number of units per run:

```yaml
optimization:
  batch_size: 10
```

## Output Format

Multi-agent workflow produces:

```json
{
  "trace_id": "workflow_v3_unit_123",
  "query_unit_id": "unit_123",
  "agent_intermediate_outputs": {
    "reviewer_understanding_agent": {...},
    "tacit_concern_interpreter": {...},
    // ... all 9 agents
  },
  "message_bus": [
    {
      "agent_id": "reviewer_understanding_agent",
      "timestamp": "2026-05-28T10:30:00",
      "message_type": "output",
      "content": {...},
      "metadata": {
        "model": "deepseek-v3",
        "prompt_tokens": 500,
        "completion_tokens": 200
      }
    }
    // ... all messages
  ],
  "execution_trace": [
    {
      "layer": "Layer 1: Reviewer Understanding",
      "agents": ["reviewer_understanding_agent"],
      "success_count": 1,
      "error_count": 0
    }
    // ... all execution steps
  ],
  "execution_metadata": {
    "total_llm_calls": 9,
    "layers_executed": 8,
    "agents_executed": 9,
    "refinement_iterations": 0
  }
}
```

## Debugging

### View execution trace

```python
from peer_review_skills.agents.workflow_integration import run_multi_agent_workflow

result = run_multi_agent_workflow(
    project_root=Path("."),
    scope="mvp",
    config={"limit": 1},
)

print(result)
```

### View message bus

```python
traces = list(read_jsonl("data/evaluation/workflow_v3/workflow_traces.jsonl"))
for trace in traces:
    print(f"Unit: {trace['query_unit_id']}")
    print(f"Messages: {len(trace['message_bus'])}")
    for msg in trace['message_bus']:
        print(f"  - {msg['agent_id']}: {msg['message_type']}")
```

### Check agent errors

```python
for trace in traces:
    for layer in trace["execution_trace"]:
        if layer.get("errors"):
            print(f"Layer {layer['layer']}: {layer['errors']}")
```

## Integration with Existing Workflow

The v3 multi-agent entry point reads these existing v0.1 artifacts:

- `data/processed/review_interaction_kb/v1/interaction_units.jsonl`
- `data/evaluation/retrieval_v2/predictions.jsonl`
- `data/processed/taxonomies/*.json`

```python
from peer_review_skills.agents.workflow_integration import run_multi_agent_workflow

run_multi_agent_workflow(
    project_root,
    scope="mvp",
    config={"limit": 1},
)
```

## Current Smoke-Test Evidence

With `PEER_REVIEW_API_MODEL=deepseek-v3`, a `--limit 1` run produced:

```json
{"total_traces": 1, "total_llm_calls": 9, "input_interaction_units": 245, "input_retrieval_predictions": 100}
```

This is a smoke test, not a quality-improvement claim.

## Troubleshooting

### "API configuration required"

Set environment variables:
```bash
export PEER_REVIEW_API_BASE_URL="..."
export PEER_REVIEW_API_KEY="..."
export PEER_REVIEW_API_MODEL="deepseek-v3"
```

### "Agent output validation failed"

Check agent prompts and output schemas. Enable debug logging:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

### High costs

Use a small `--limit` while iterating. Full runs are explicit because each unit
uses 9 model calls.

## Next Steps

1. Inspect `data/evaluation/workflow_v3/workflow_traces.jsonl`.
2. Check whether cross-disciplinary lenses remain grounded in observable traces.
3. Add human/expert evaluation before claiming quality improvement.
4. Enable refinement only for small, auditable batches.

## References

- Architecture design: `docs/architecture/true-multi-agent-design.md`
- Agent implementation: `src/peer_review_skills/agents/`
- Configuration: `config/multi_agent_config.yaml`
