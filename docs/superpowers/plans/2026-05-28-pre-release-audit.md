# NatureReview-Interact v0.1 Pre-Release Audit Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Comprehensive audit to verify NatureReview-Interact v0.1 implementation matches design specification in `docs/2026-05-26-open-source-review-interaction-agent-full-plan-zh.md` before public release.

**Architecture:** Systematic verification of all components against design document sections 1-15, covering data assets, core objects, agent framework, evaluation system, and open-source boundaries.

**Tech Stack:** Python 3.12+, existing codebase validation, document comparison

---

## Audit Scope

This audit verifies:
1. Data foundation matches Section 2 (v2709 dataset claims)
2. Core learning objects match Section 6 (Concern, Strategy, Evidence, Tone, Adequacy, Editorial Signal)
3. Agent framework matches Section 7 (5-layer architecture)
4. Evaluation system matches Section 10 (evaluation dimensions)
5. Open-source boundaries match Section 9 (what to release)
6. Responsible use policies match Section 11 (ethical boundaries)

---

## Task 1: Verify Data Foundation (Section 2)

**Files:**
- Read: `data/processed/review_interaction_kb/v1/kb_summary.json`
- Read: `data/evaluation/author_rebuttal_mvp_candidates/`
- Verify: Current data counts match design claims

- [ ] **Step 1: Check interaction units count**

Run:
```bash
PYTHONPATH=src python -c "from peer_review_skills.io.jsonl import read_jsonl; units = list(read_jsonl('data/processed/review_interaction_kb/v1/interaction_units.jsonl')); print(f'Interaction units: {len(units)}')"
```

Expected: Should match "interaction_units: 245" from validation

Design claim (Section 2): "core full-chain papers: 339"
Verify: Check if 245 units derived from subset of 339 papers

- [ ] **Step 2: Verify v2709 paper records**

Run:
```bash
find scraped_data -name "*.json" | wc -l
```

Expected: ~2709 files
Design claim: "paper records: 2709"

- [ ] **Step 3: Check demo-ready pairs count**

Run:
```bash
PYTHONPATH=src python -c "from peer_review_skills.io.jsonl import read_jsonl; import os; \
if os.path.exists('data/evaluation/author_rebuttal_mvp_candidates/all_author_rebuttal_mvp_audit_rows.jsonl'): \
    rows = list(read_jsonl('data/evaluation/author_rebuttal_mvp_candidates/all_author_rebuttal_mvp_audit_rows.jsonl')); \
    print(f'MVP audit rows: {len(rows)}'); \
else: print('File not found')"
```

Design claim: "demo-ready pairs: 9858"
Verify: Current count and explain any discrepancy

- [ ] **Step 4: Document data foundation audit results**

Create: `docs/audit/data-foundation-audit.md`

```markdown
# Data Foundation Audit Results

## Verification Date: 2026-05-28

### Design Claims (Section 2)
- paper records: 2709
- core full-chain papers: 339
- demo-ready pairs: 9858
- model-confirmed subset: 45

### Actual Counts
- interaction_units: [FILL]
- scraped papers: [FILL]
- workflow traces: [FILL]

### Status: [PASS/FAIL/PARTIAL]

### Discrepancies:
[List any differences and explanations]
```

- [ ] **Step 5: Commit audit results**

```bash
git add docs/audit/data-foundation-audit.md
git commit -m "audit: verify data foundation against design spec"
```

---

## Task 2: Verify Core Learning Objects (Section 6)

**Files:**
- Read: `data/processed/review_interaction_kb/v1/interaction_units.jsonl`
- Read: `data/processed/schemas/review_interaction_unit.schema.json`
- Verify: All 6 core objects are modeled

- [ ] **Step 1: Check Concern modeling**

Run:
```bash
PYTHONPATH=src python -c "from peer_review_skills.io.jsonl import read_jsonl; \
units = list(read_jsonl('data/processed/review_interaction_kb/v1/interaction_units.jsonl')); \
sample = units[0] if units else {}; \
print('Concern fields:', [k for k in sample.keys() if 'concern' in k.lower()])"
```

Expected fields (Section 6.1):
- concern_type
- implicit_risk or tacit_concern
- risk_type

- [ ] **Step 2: Check Strategy modeling**

Run:
```bash
PYTHONPATH=src python -c "from peer_review_skills.io.jsonl import read_jsonl; \
units = list(read_jsonl('data/processed/review_interaction_kb/v1/interaction_units.jsonl')); \
sample = units[0] if units else {}; \
print('Strategy fields:', [k for k in sample.keys() if 'strategy' in k.lower()])"
```

Expected fields (Section 6.2):
- response_strategy

- [ ] **Step 3: Check Evidence Action modeling**

Run:
```bash
PYTHONPATH=src python -c "from peer_review_skills.io.jsonl import read_jsonl; \
units = list(read_jsonl('data/processed/review_interaction_kb/v1/interaction_units.jsonl')); \
sample = units[0] if units else {}; \
print('Evidence fields:', [k for k in sample.keys() if 'evidence' in k.lower()])"
```

Expected fields (Section 6.3):
- evidence_action

- [ ] **Step 4: Check Tone/Stance/Commitment modeling**

Expected fields (Section 6.4):
- tone_commitment (or similar structure)
- author_positioning

- [ ] **Step 5: Check Response Adequacy modeling**

Check if adequacy assessment exists in workflow traces:
```bash
PYTHONPATH=src python -c "from peer_review_skills.io.jsonl import read_jsonl; \
traces = list(read_jsonl('data/evaluation/workflow_v2/workflow_traces.jsonl')); \
sample = traces[0] if traces else {}; \
agent_outputs = sample.get('agent_intermediate_outputs', {}); \
print('Has adequacy checker:', 'integrity_adequacy_checker' in agent_outputs)"
```

- [ ] **Step 6: Check Editorial Signal modeling**

Expected fields (Section 6.6):
- institutional_signal
- (editorial_signal - may be in workflow traces)

- [ ] **Step 7: Document core objects audit**

Create: `docs/audit/core-objects-audit.md`

```markdown
# Core Learning Objects Audit

## Verification Date: 2026-05-28

### Section 6 Requirements

#### 6.1 Concern ✓/✗
- concern_type: [PRESENT/MISSING]
- risk_type: [PRESENT/MISSING]
- tacit_concern: [PRESENT/MISSING]

#### 6.2 Strategy ✓/✗
- response_strategy: [PRESENT/MISSING]

#### 6.3 Evidence Action ✓/✗
- evidence_action: [PRESENT/MISSING]

#### 6.4 Tone/Stance/Commitment ✓/✗
- tone_commitment: [PRESENT/MISSING]
- author_positioning: [PRESENT/MISSING]

#### 6.5 Response Adequacy ✓/✗
- adequacy assessment: [PRESENT/MISSING]

#### 6.6 Editorial Signal ✓/✗
- institutional_signal: [PRESENT/MISSING]

### Status: [PASS/FAIL/PARTIAL]
```

- [ ] **Step 8: Commit core objects audit**

```bash
git add docs/audit/core-objects-audit.md
git commit -m "audit: verify core learning objects"
```

---

## Task 3: Verify Agent Framework (Section 7)

**Files:**
- Read: `src/peer_review_skills/execution/build_naturereview_v01.py`
- Read: `data/evaluation/workflow_v2/workflow_traces.jsonl`
- Verify: 5-layer architecture with all agents

- [ ] **Step 1: Verify Layer 1 - Interaction Understanding**

Check for agents (Section 7.1):
- Concern Understanding Model
- Risk Classification Model

Run:
```bash
PYTHONPATH=src python -c "from peer_review_skills.io.jsonl import read_jsonl; \
traces = list(read_jsonl('data/evaluation/workflow_v2/workflow_traces.jsonl')); \
sample = traces[0] if traces else {}; \
agents = sample.get('agent_intermediate_outputs', {}).keys(); \
print('Layer 1 agents:', [a for a in agents if 'concern' in a.lower() or 'understanding' in a.lower()])"
```

Expected: reviewer_understanding_agent, tacit_concern_interpreter

- [ ] **Step 2: Verify Layer 2 - Strategy and Evidence Learning**

Expected agents (Section 7.2):
- Strategy Selection Model
- Evidence Action Model
- Response Adequacy Model

Check:
```bash
PYTHONPATH=src python -c "from peer_review_skills.io.jsonl import read_jsonl; \
traces = list(read_jsonl('data/evaluation/workflow_v2/workflow_traces.jsonl')); \
sample = traces[0] if traces else {}; \
agents = sample.get('agent_intermediate_outputs', {}).keys(); \
print('Layer 2 agents:', [a for a in agents if 'evidence' in a.lower() or 'adequacy' in a.lower()])"
```

Expected: evidence_action_planner, integrity_adequacy_checker

- [ ] **Step 3: Verify Layer 3 - Rebuttal Planning**

Expected (Section 7.3):
- Rebuttal plan generation (not direct text generation)
- Output structure with concern_map, strategy_plan, evidence_plan

Check:
```bash
PYTHONPATH=src python -c "from peer_review_skills.io.jsonl import read_jsonl; \
traces = list(read_jsonl('data/evaluation/workflow_v2/workflow_traces.jsonl')); \
sample = traces[0] if traces else {}; \
print('Has rebuttal_plan:', 'rebuttal_plan' in sample)"
```

- [ ] **Step 4: Verify Layer 4 - Response Generation and Calibration**

Expected agents (Section 7.4):
- Tone and Commitment Calibrator
- Integrity Checker

Check:
```bash
PYTHONPATH=src python -c "from peer_review_skills.io.jsonl import read_jsonl; \
traces = list(read_jsonl('data/evaluation/workflow_v2/workflow_traces.jsonl')); \
sample = traces[0] if traces else {}; \
agents = sample.get('agent_intermediate_outputs', {}).keys(); \
print('Layer 4 agents:', [a for a in agents if 'tone' in a.lower() or 'calibrat' in a.lower()])"
```

Expected: tone_commitment_calibrator

- [ ] **Step 5: Verify Layer 5 - Simulation and Evaluation**

Check for simulation traces (Section 7.5):
```bash
ls -la data/evaluation/simulation_v1/
```

Expected: simulation_traces.jsonl with reviewer/author/editor agent roles

- [ ] **Step 6: Count total agents**

Design requirement (Section 7): 5 layers with specific agents

Run:
```bash
PYTHONPATH=src python -c "from peer_review_skills.io.jsonl import read_jsonl; \
traces = list(read_jsonl('data/evaluation/workflow_v2/workflow_traces.jsonl')); \
sample = traces[0] if traces else {}; \
agents = list(sample.get('agent_intermediate_outputs', {}).keys()); \
print(f'Total agents: {len(agents)}'); \
for agent in sorted(agents): print(f'  - {agent}')"
```

Expected: 9 agents as documented in end-to-end example

- [ ] **Step 7: Document agent framework audit**

Create: `docs/audit/agent-framework-audit.md`

```markdown
# Agent Framework Audit

## Verification Date: 2026-05-28

### Section 7 Requirements: 5-Layer Architecture

#### Layer 1: Interaction Understanding ✓/✗
- reviewer_understanding_agent: [PRESENT/MISSING]
- tacit_concern_interpreter: [PRESENT/MISSING]

#### Layer 2: Strategy and Evidence Learning ✓/✗
- evidence_action_planner: [PRESENT/MISSING]
- integrity_adequacy_checker: [PRESENT/MISSING]

#### Layer 3: Rebuttal Planning ✓/✗
- rebuttal_plan structure: [PRESENT/MISSING]

#### Layer 4: Response Generation and Calibration ✓/✗
- tone_commitment_calibrator: [PRESENT/MISSING]

#### Layer 5: Simulation and Evaluation ✓/✗
- simulation_traces: [PRESENT/MISSING]

### Total Agents Found: [COUNT]

### Status: [PASS/FAIL/PARTIAL]
```

- [ ] **Step 8: Commit agent framework audit**

```bash
git add docs/audit/agent-framework-audit.md
git commit -m "audit: verify agent framework architecture"
```

---

## Task 4: Verify Cross-Disciplinary Lenses (Section 3 & PDF Integration)

**Files:**
- Read: `data/evaluation/workflow_v2/workflow_traces.jsonl`
- Verify: Six lenses from 2026.5.15.pdf and 2026.5.23.pdf

- [ ] **Step 1: Check for cross-disciplinary lens map**

Run:
```bash
PYTHONPATH=src python -c "from peer_review_skills.io.jsonl import read_jsonl; \
traces = list(read_jsonl('data/evaluation/workflow_v2/workflow_traces.jsonl')); \
sample = traces[0] if traces else {}; \
lens_map = sample.get('cross_disciplinary_lens_map', {}); \
print(f'Lenses found: {len(lens_map)}'); \
for lens in sorted(lens_map.keys()): print(f'  - {lens}')"
```

Expected 6 lenses (Section 3.3):
1. tacit_knowledge_boundary
2. institutional_dependence
3. actor_network_alignment
4. fast_slow_cognitive_correction
5. emotion_tone_commitment_calibration
6. author_agency_gate

- [ ] **Step 2: Verify each lens has required fields**

Check lens structure:
```bash
PYTHONPATH=src python -c "from peer_review_skills.io.jsonl import read_jsonl; \
traces = list(read_jsonl('data/evaluation/workflow_v2/workflow_traces.jsonl')); \
sample = traces[0] if traces else {}; \
lens_map = sample.get('cross_disciplinary_lens_map', {}); \
if lens_map: \
    first_lens = list(lens_map.values())[0]; \
    print('Lens fields:', list(first_lens.keys()))"
```

Expected fields per lens:
- source_pdf
- concept
- observable_trace
- system_action
- boundary
- evaluation_question

- [ ] **Step 3: Document cross-disciplinary lenses audit**

Create: `docs/audit/cross-disciplinary-lenses-audit.md`

```markdown
# Cross-Disciplinary Lenses Audit

## Verification Date: 2026-05-28

### Section 3.3 Requirements: 6 Lenses

1. tacit_knowledge_boundary: [PRESENT/MISSING]
2. institutional_dependence: [PRESENT/MISSING]
3. actor_network_alignment: [PRESENT/MISSING]
4. fast_slow_cognitive_correction: [PRESENT/MISSING]
5. emotion_tone_commitment_calibration: [PRESENT/MISSING]
6. author_agency_gate: [PRESENT/MISSING]

### Lens Structure Completeness
- All lenses have source_pdf: [YES/NO]
- All lenses have observable_trace: [YES/NO]
- All lenses have boundary: [YES/NO]

### Status: [PASS/FAIL/PARTIAL]
```

- [ ] **Step 4: Commit lenses audit**

```bash
git add docs/audit/cross-disciplinary-lenses-audit.md
git commit -m "audit: verify cross-disciplinary lenses integration"
```

---

## Task 5: Verify Evaluation System (Section 10)

**Files:**
- Check: Evaluation dimensions implementation
- Verify: Not just BLEU/ROUGE

- [ ] **Step 1: Check evaluation dimensions**

Design requirements (Section 10):
- concern coverage
- risk accuracy
- strategy appropriateness
- evidence grounding
- actionability
- response adequacy
- tone calibration
- commitment safety
- overclaim prevention
- provenance

Check if adequacy assessment covers these:
```bash
PYTHONPATH=src python -c "from peer_review_skills.io.jsonl import read_jsonl; \
traces = list(read_jsonl('data/evaluation/workflow_v2/workflow_traces.jsonl')); \
sample = traces[0] if traces else {}; \
adequacy = sample.get('agent_intermediate_outputs', {}).get('integrity_adequacy_checker', {}); \
print('Adequacy fields:', list(adequacy.keys()) if adequacy else 'Not found')"
```

- [ ] **Step 2: Verify no BLEU/ROUGE evaluation**

Search codebase for surface-level metrics:
```bash
grep -r "BLEU\|ROUGE\|bleu\|rouge" src/ --include="*.py" || echo "No BLEU/ROUGE found (good)"
```

Expected: No BLEU/ROUGE metrics (design explicitly rejects these)

- [ ] **Step 3: Check provenance tracking**

Verify all units have provenance:
```bash
PYTHONPATH=src python -c "from peer_review_skills.io.jsonl import read_jsonl; \
units = list(read_jsonl('data/processed/review_interaction_kb/v1/interaction_units.jsonl')); \
with_provenance = sum(1 for u in units if 'provenance' in u); \
print(f'Units with provenance: {with_provenance}/{len(units)}')"
```

Expected: All units have provenance field

- [ ] **Step 4: Check label_source tracking**

Verify model-assisted vs human labels:
```bash
PYTHONPATH=src python -c "from peer_review_skills.io.jsonl import read_jsonl; \
units = list(read_jsonl('data/processed/review_interaction_kb/v1/interaction_units.jsonl')); \
label_sources = {}; \
for u in units: \
    src = u.get('label_source', 'unknown'); \
    label_sources[src] = label_sources.get(src, 0) + 1; \
print('Label sources:', label_sources)"
```

Expected: Mostly "model_assisted", some may be "heuristic"

- [ ] **Step 5: Document evaluation system audit**

Create: `docs/audit/evaluation-system-audit.md`

```markdown
# Evaluation System Audit

## Verification Date: 2026-05-28

### Section 10 Requirements

#### Evaluation Dimensions Implemented
- concern coverage: [YES/NO/PARTIAL]
- risk accuracy: [YES/NO/PARTIAL]
- strategy appropriateness: [YES/NO/PARTIAL]
- evidence grounding: [YES/NO/PARTIAL]
- response adequacy: [YES/NO/PARTIAL]
- tone calibration: [YES/NO/PARTIAL]
- commitment safety: [YES/NO/PARTIAL]
- overclaim prevention: [YES/NO/PARTIAL]
- provenance: [YES/NO/PARTIAL]

#### Anti-Requirements (Should NOT exist)
- BLEU/ROUGE metrics: [ABSENT/PRESENT]

### Provenance Tracking
- Units with provenance: [COUNT/TOTAL]
- Label source tracking: [YES/NO]

### Status: [PASS/FAIL/PARTIAL]
```

- [ ] **Step 6: Commit evaluation audit**

```bash
git add docs/audit/evaluation-system-audit.md
git commit -m "audit: verify evaluation system"
```

---

## Task 6: Verify Open-Source Boundaries (Section 9 & 11)

**Files:**
- Check: What is currently in repository
- Verify: Matches Section 9 "可以优先开源" list
- Verify: Avoids Section 9 "谨慎开源" and "不建议开源" items

- [ ] **Step 1: Check for schema files**

Design requirement (Section 9.1): Schema should be open-sourced

```bash
find data/processed/schemas -name "*.json" -o -name "*.schema.json"
```

Expected: review_interaction_unit.schema.json exists

- [ ] **Step 2: Check for taxonomy files**

Design requirement (Section 9.1): Taxonomy should be open-sourced

```bash
find data/processed/taxonomies -name "*.json"
```

Expected: Taxonomy files for concern types, risk types, etc.

- [ ] **Step 3: Check for README and documentation**

Design requirement (Section 11.1): README, project motivation, data card, etc.

```bash
ls -la README.md docs/*.md | head -20
```

Expected files:
- README.md
- Data card or equivalent
- Responsible use policy

- [ ] **Step 4: Verify no full-text redistribution**

Design warning (Section 9.2): "谨慎开源" - author response 长文本, reviewer report 长文本

Check if full review/response texts are in repo:
```bash
PYTHONPATH=src python -c "from peer_review_skills.io.jsonl import read_jsonl; \
units = list(read_jsonl('data/processed/review_interaction_kb/v1/interaction_units.jsonl')); \
sample = units[0] if units else {}; \
has_full_text = 'review_text' in sample or 'response_text' in sample; \
if has_full_text: \
    review_len = len(sample.get('review_text', '')); \
    response_len = len(sample.get('response_text', '')); \
    print(f'Has full text - review: {review_len} chars, response: {response_len} chars'); \
else: \
    print('No full text found (good for open-source)')"
```

If full texts exist, verify they're from public transparent peer review

- [ ] **Step 5: Check for responsible use policy**

Design requirement (Section 11.2): README should include responsible use warnings

```bash
grep -i "responsible\|ethical\|不应\|禁止" README.md
```

Expected: Warnings about:
- Not uploading confidential manuscripts
- Not replacing authors/reviewers/editors
- Author confirmation required

- [ ] **Step 6: Verify no acceptance prediction**

Design prohibition (Section 9.3): "号称预测接收率或操纵 reviewer 的模块"

```bash
grep -ri "acceptance.*predict\|predict.*acceptance\|接收率" src/ --include="*.py" || echo "No acceptance prediction found (good)"
```

Expected: No acceptance rate prediction code

- [ ] **Step 7: Document open-source boundaries audit**

Create: `docs/audit/open-source-boundaries-audit.md`

```markdown
# Open-Source Boundaries Audit

## Verification Date: 2026-05-28

### Section 9.1: Should Be Open-Sourced ✓/✗
- README: [PRESENT/MISSING]
- Schema: [PRESENT/MISSING]
- Taxonomy: [PRESENT/MISSING]
- Evaluation protocol: [PRESENT/MISSING]
- Agent framework: [PRESENT/MISSING]
- Responsible use policy: [PRESENT/MISSING]

### Section 9.2: Cautious Open-Source ✓/✗
- Full review/response texts: [ABSENT/PRESENT - explain if present]
- Provenance links only: [YES/NO]

### Section 9.3: Should NOT Be Open-Sourced ✓/✗
- Confidential manuscripts: [ABSENT/PRESENT]
- Acceptance prediction: [ABSENT/PRESENT]
- Auto-submit functionality: [ABSENT/PRESENT]

### Status: [PASS/FAIL/PARTIAL]

### Recommendations:
[Any changes needed before release]
```

- [ ] **Step 8: Commit open-source boundaries audit**

```bash
git add docs/audit/open-source-boundaries-audit.md
git commit -m "audit: verify open-source boundaries"
```

---

## Task 7: Verify Research Questions (Section 8)

**Files:**
- Review: Main research question alignment
- Verify: System addresses the stated research problem

- [ ] **Step 1: Review main research question**

Design (Section 8):
> "Can open transparent peer review data be used to learn structured interaction patterns that improve evidence-grounded, strategy-aware, and integrity-preserving author rebuttal assistance?"

Check if system demonstrates:
1. Uses transparent peer review data ✓ (v2709 Nature data)
2. Learns structured patterns ✓ (interaction units with concern/strategy/evidence)
3. Evidence-grounded ✓ (evidence_action, provenance)
4. Strategy-aware ✓ (response_strategy, case retrieval)
5. Integrity-preserving ✓ (integrity checker, author confirmation gates)

- [ ] **Step 2: Check sub-questions coverage**

Sub-question 1: "Nature 公开审稿互动中 reviewer concern、author strategy、evidence action 和 editor signal 是否存在可归纳的结构模式？"

Verify: Taxonomy files show structured patterns

```bash
ls data/processed/taxonomies/
```

Sub-question 2: "从这些模式中学习出来的策略模型，是否比直接 LLM 生成更能覆盖 reviewer concern？"

Verify: Retrieval-based approach (not direct generation)

```bash
grep -r "retrieval\|case.*retrieval" src/peer_review_skills/execution/ --include="*.py" | head -5
```

Sub-question 3: "evidence action modeling 是否能降低 unsupported commitment 和 overclaim 风险？"

Verify: Integrity checker exists

```bash
grep -r "overclaim\|unsupported.*commit\|fabricat" src/ --include="*.py" | head -5
```

- [ ] **Step 3: Document research questions audit**

Create: `docs/audit/research-questions-audit.md`

```markdown
# Research Questions Audit

## Verification Date: 2026-05-28

### Main Research Question (Section 8)
"Can open transparent peer review data be used to learn structured interaction patterns..."

#### Components Verified:
1. Uses transparent peer review data: [YES/NO]
2. Learns structured patterns: [YES/NO]
3. Evidence-grounded: [YES/NO]
4. Strategy-aware: [YES/NO]
5. Integrity-preserving: [YES/NO]

### Sub-Questions Coverage:
1. Structured patterns exist: [YES/NO/PARTIAL]
2. Better than direct LLM: [YES/NO/NOT_TESTED]
3. Reduces overclaim risk: [YES/NO/PARTIAL]

### Status: [PASS/FAIL/PARTIAL]
```

- [ ] **Step 4: Commit research questions audit**

```bash
git add docs/audit/research-questions-audit.md
git commit -m "audit: verify research questions alignment"
```

---

## Task 8: Final Integration Check

**Files:**
- Run: Complete system validation
- Verify: All components work together

- [ ] **Step 1: Run full system validation**

```bash
PYTHONPATH=src python -m peer_review_skills.cli.main validate-naturereview-v01
```

Expected output: `PASS` status with all artifact counts

- [ ] **Step 2: Run smoke test**

```bash
PYTHONPATH=src python .claude/skills/run-naturereview/smoke.py
```

Expected: Exit code 0, all sections complete successfully

- [ ] **Step 3: Check for critical errors in logs**

```bash
find data/evaluation -name "*error*.jsonl" -exec wc -l  \;
```

Review any error files for critical issues

- [ ] **Step 4: Verify end-to-end example matches documentation**

Compare actual workflow trace structure with:
`docs/2026-05-28-author-rebuttal-assistant-end-to-end-example-zh.md`

```bash
PYTHONPATH=src python -c "from peer_review_skills.io.jsonl import read_jsonl; \
traces = list(read_jsonl('data/evaluation/workflow_v2/workflow_traces.jsonl')); \
sample = traces[0]; \
print('Trace structure:'); \
for key in sorted(sample.keys()): print(f'  - {key}')"
```

Expected keys match documentation Section 6

- [ ] **Step 5: Create final audit summary**

Create: `docs/audit/FINAL-AUDIT-SUMMARY.md`

```markdown
# NatureReview-Interact v0.1 Final Audit Summary

## Audit Date: 2026-05-28
## Auditor: Claude Opus 4.7
## Design Spec: docs/2026-05-26-open-source-review-interaction-agent-full-plan-zh.md

---

## Executive Summary

[Overall assessment: READY/NOT_READY for release]

### Critical Issues: [COUNT]
[List any blocking issues]

### Important Issues: [COUNT]
[List issues that should be fixed before release]

### Minor Issues: [COUNT]
[List nice-to-have improvements]

---

## Component Audit Results

### 1. Data Foundation (Section 2)
Status: [PASS/FAIL/PARTIAL]
- v2709 dataset: [✓/✗]
- Interaction units: [✓/✗]
- Provenance: [✓/✗]

### 2. Core Learning Objects (Section 6)
Status: [PASS/FAIL/PARTIAL]
- Concern modeling: [✓/✗]
- Strategy modeling: [✓/✗]
- Evidence action: [✓/✗]
- Tone/commitment: [✓/✗]
- Adequacy: [✓/✗]
- Editorial signal: [✓/✗]

### 3. Agent Framework (Section 7)
Status: [PASS/FAIL/PARTIAL]
- 5-layer architecture: [✓/✗]
- All required agents: [✓/✗]
- Workflow traces: [✓/✗]

### 4. Cross-Disciplinary Lenses (Section 3)
Status: [PASS/FAIL/PARTIAL]
- 6 lenses present: [✓/✗]
- PDF integration: [✓/✗]

### 5. Evaluation System (Section 10)
Status: [PASS/FAIL/PARTIAL]
- Evaluation dimensions: [✓/✗]
- No BLEU/ROUGE: [✓/✗]
- Provenance tracking: [✓/✗]

### 6. Open-Source Boundaries (Section 9)
Status: [PASS/FAIL/PARTIAL]
- Required docs: [✓/✗]
- No prohibited content: [✓/✗]
- Responsible use: [✓/✗]

### 7. Research Questions (Section 8)
Status: [PASS/FAIL/PARTIAL]
- Main question addressed: [✓/✗]
- Sub-questions covered: [✓/✗]

### 8. System Integration
Status: [PASS/FAIL/PARTIAL]
- Validation passes: [✓/✗]
- Smoke test passes: [✓/✗]
- Documentation matches: [✓/✗]

---

## Recommendations

### Before Release:
1. [Action item 1]
2. [Action item 2]

### Post-Release:
1. [Future improvement 1]
2. [Future improvement 2]

---

## Sign-Off

This audit verifies that NatureReview-Interact v0.1 [DOES/DOES NOT] conform to the design specification in `docs/2026-05-26-open-source-review-interaction-agent-full-plan-zh.md`.

**Recommendation:** [APPROVE FOR RELEASE / REQUIRES FIXES / MAJOR REVISION NEEDED]

**Auditor:** Claude Opus 4.7
**Date:** 2026-05-28
```

- [ ] **Step 6: Commit final audit summary**

```bash
git add docs/audit/
git commit -m "audit: complete pre-release audit with final summary"
```

---

## Execution Instructions

Plan complete and saved to `docs/superpowers/plans/2026-05-28-pre-release-audit.md`.

**Two execution options:**

**1. Subagent-Driven (recommended)** - Fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
