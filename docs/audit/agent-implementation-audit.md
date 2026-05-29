# Agent Implementation Audit - Model vs Rule-Based

## Audit Date: 2026-05-28
## Critical Finding: Agent Implementation Method

---

## 🚨 Executive Summary

**CRITICAL DISCOVERY**: The 9 "agents" in the workflow traces are **NOT independent LLM-based agents**. They are **rule-based transformations** that assemble pre-labeled data from interaction units into structured outputs.

---

## Detailed Analysis

### What the System Actually Does

The workflow in `build_naturereview_v01.py` works as follows:

1. **Input**: Pre-labeled interaction units with fields like:
   - `concern_type` (already labeled)
   - `risk_type` (already labeled)
   - `tacit_concern` (already labeled)
   - `institutional_signal` (already labeled)
   - `evidence_action` (already labeled)
   - `author_positioning` (already labeled)
   - `tone_commitment` (already labeled)
   - `label_source: "model_assisted"` (labels came from earlier API calls)

2. **Processing**: The `_agent_intermediate_outputs()` function (line 1751) **assembles** these pre-existing labels into agent-like output structures:

```python
def _agent_intermediate_outputs(unit: dict[str, Any], pred: dict[str, Any]) -> dict[str, Any]:
    return {
        "reviewer_understanding_agent": {
            "concern_map": [{
                "concern_type": unit["concern_type"],  # ← Already labeled!
                "surface_request": _preview(unit["review_text"], 180),
                "implicit_risk": _implicit_risk_note(unit),
                "text_evidence": _preview(unit["review_text"]),
                "label_source": unit.get("label_source"),
            }]
        },
        "tacit_concern_interpreter": {
            "risk_interpretation": [{
                "risk_type": unit["risk_type"],  # ← Already labeled!
                "tacit_concern": unit["tacit_concern"],  # ← Already labeled!
                "boundary": "Observable textual trace only...",
            }]
        },
        # ... 7 more "agents" that just reformat existing labels
    }
```

3. **No Real Agent Execution**: These are **not** independent agent calls. They are **data transformations** that:
   - Take pre-labeled fields from interaction units
   - Add static text (boundaries, warnings)
   - Format into agent-like JSON structures
   - Return as "agent_intermediate_outputs"

---

## Where the Real Model Calls Happen

### Phase 1: Seed Review (API-based labeling)

The **actual LLM calls** happen in the **seed review phase** (line 3800):

```python
def _execute_seed_review_request(client: Any, request: dict[str, Any]) -> dict[str, Any]:
    response = client.create_chat_completion(
        _seed_review_messages(request),
        response_format={"type": "json_object"},
        temperature=0.0,
    )
    result = _normalize_seed_review_result(response)
    _validate_seed_review_result(result)
    return result
```

This is where:
- A **single LLM call** labels an interaction unit
- The model receives review/response text
- The model outputs: `concern_type`, `risk_type`, `tacit_concern`, `evidence_action`, etc.
- These labels are stored in the interaction unit with `label_source: "model_assisted"`

### Phase 2: Workflow Assembly (Rule-based)

The "9 agents" in workflow traces are **not making new model calls**. They are:
- Reading pre-labeled fields
- Applying retrieval logic (case matching)
- Formatting outputs
- Adding static warnings and boundaries

---

## Model Architecture

### Actual Model Usage

**Single Model Call per Interaction Unit**:
- **When**: During seed review phase
- **Input**: Review text + response text + taxonomies
- **Output**: All labels at once (concern_type, risk_type, evidence_action, etc.)
- **Model**: OpenAI-compatible API (configurable)
- **Temperature**: 0.0 (deterministic)
- **Format**: JSON object

**System Prompt** (line 3816):
```
"You review peer-review interaction seed labels for an Author Rebuttal Assistant.
Return only one valid JSON object. Use the provided taxonomy-like labels when possible.
Ground every revision in observable review/response text. Do not infer private reviewer intent,
do not predict acceptance, and do not invent experiments, data, citations, or commitments."
```

### "Agent" Implementation

The 9 "agents" are **Python functions** that:
1. `reviewer_understanding_agent` → Reads `unit["concern_type"]`
2. `tacit_concern_interpreter` → Reads `unit["risk_type"]` and `unit["tacit_concern"]`
3. `institutional_signal_interpreter` → Reads `unit["institutional_signal"]`
4. `evidence_action_planner` → Reads `unit["evidence_action"]` + retrieval results
5. `author_positioning_agent` → Reads `unit["author_positioning"]`
6. `tone_commitment_calibrator` → Reads `unit["tone_commitment"]`
7. `actor_network_mapper` → Reads `unit["actor_links"]`
8. `integrity_adequacy_checker` → Generates static warnings
9. `cross_disciplinary_lens_interpreter` → Generates lens map from unit fields

---

## Implications

### ✓ What This Means (Positive)

1. **Efficient**: One model call per unit, not 9 calls
2. **Consistent**: All labels come from same model context
3. **Traceable**: Clear separation between model output and rule-based assembly
4. **Cost-effective**: ~245 model calls total (not 245 × 9 = 2205 calls)

### ⚠️ What This Means (Concerns)

1. **Misleading Architecture Diagram**: The design spec shows "9 agents" as if they're independent reasoning units
2. **Not Multi-Agent**: This is a **single-agent labeling + rule-based assembly** system
3. **Limited Agent Autonomy**: No agent-to-agent communication, no iterative refinement
4. **Workflow is Deterministic**: Given the same labels, workflow output is always the same

### 🔍 What This Actually Is

**Correct Description**:
- **Phase 1**: Single LLM call for multi-label classification
- **Phase 2**: Rule-based workflow assembly using pre-labeled data
- **Phase 3**: Case retrieval (similarity matching)
- **Phase 4**: Output formatting with static boundaries

**Not**:
- Multi-agent system with independent reasoning
- Iterative agent collaboration
- Agent-based refinement loops

---

## Model Information

### Current Model

Based on the code:
- **API Type**: OpenAI-compatible endpoint
- **Configuration**: Via environment variables
  - `PEER_REVIEW_API_BASE_URL`
  - `PEER_REVIEW_API_KEY`
  - `PEER_REVIEW_API_MODEL`
- **Temperature**: 0.0 (deterministic)
- **Response Format**: JSON object
- **Usage**: Single call per interaction unit during seed review

### Label Source

All 245 interaction units have:
```json
{
  "label_source": "model_assisted"
}
```

This confirms:
- Labels came from model API calls
- Not human-annotated
- Not rule-based heuristics
- Model-assisted but not human-verified

---

## Recommendations

### For Documentation

1. **Update Architecture Description**:
   - Change "9-agent system" to "single-model labeling + rule-based workflow"
   - Clarify that "agents" are data transformation functions, not independent LLMs
   - Show the actual architecture: `LLM labeling → Rule-based assembly → Retrieval → Output`

2. **Add Model Card**:
   - Document which model was used for labeling
   - Show example prompts and responses
   - Explain temperature=0.0 choice

3. **Clarify "Model-Assisted"**:
   - Explain that one model call produces all labels
   - Show the prompt structure
   - Document the JSON schema

### For Future Work

1. **True Multi-Agent System** (if desired):
   - Each agent makes its own LLM call
   - Agents can refine each other's outputs
   - Iterative improvement loops

2. **Hybrid Approach** (recommended):
   - Keep efficient single-call labeling
   - Add optional refinement agents for critical decisions
   - Use rule-based assembly for deterministic parts

3. **Transparency**:
   - Rename "agents" to "modules" or "components"
   - Or keep "agents" but clarify they're rule-based

---

## Conclusion

The system is **not a multi-agent LLM system**. It is:
- **Single LLM call** for multi-label classification (seed review phase)
- **Rule-based workflow assembly** using pre-labeled data
- **Retrieval-based case matching** for evidence planning
- **Static boundary generation** for responsible use

This is actually a **more efficient and traceable design** than true multi-agent systems, but the documentation should accurately reflect this architecture.

**Status**: System works as implemented, but documentation overstates the "multi-agent" nature.

**Recommendation**: Update documentation to accurately describe the architecture as "model-assisted labeling + rule-based workflow assembly" rather than "9-agent system".
