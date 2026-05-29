# RebuttalLens Final Workflow Upgrade Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the current NatureReview-Interact v3 workflow into RebuttalLens, a manuscript-aware, cross-disciplinary Author Rebuttal Assistant workflow that remains non-training, provenance-first, and not rule-generated.

**Architecture:** Keep the existing independent LLM-agent foundation and add a manuscript context layer before reviewer understanding. The final workflow accepts reviewer comments, optional manuscript text/file, optional author draft response, Nature case retrieval context, and returns a trace with manuscript evidence maps, case analogies, evidence plans, cross-disciplinary lenses, and integrity gates.

**Tech Stack:** Python 3.12, existing `peer_review_skills` package, OpenAI-compatible DeepSeek client, JSONL artifacts, pytest, PowerShell CLI commands.

---

## Scope and Constraints

- Do not implement training or fine-tuning.
- Do not continue crawling.
- Do not generate final submission-ready rebuttal text by default.
- Do not use keyword/rule/heuristic matching to generate user-facing advice.
- Allow deterministic structure parsing for manuscript text sections and safety/schema validation.
- Keep API keys in environment variables only.
- GitHub upload is blocked unless a remote repository and authentication are available. Prepare local git state and release instructions.

## File Structure

- Create `src/peer_review_skills/agents/manuscript_context.py`
  - Defines manuscript section extraction, file loading, and evidence-context payloads.
- Create `src/peer_review_skills/agents/rebuttal_lens_agents.py`
  - Adds manuscript-aware LLM agents: `ManuscriptContextExtractorAgent`, `ManuscriptEvidenceLocatorAgent`, `CaseRetrievalInterpreterAgent`.
- Create `src/peer_review_skills/agents/rebuttal_lens_workflow.py`
  - Adds `run_rebuttal_lens_workflow`, file-input wrapper, trace serialization, and config redaction reuse.
- Modify `src/peer_review_skills/agents/specialized_agents.py`
  - Feed manuscript evidence into reviewer, tacit, institutional, evidence, author-positioning, and tone agents.
- Modify `src/peer_review_skills/agents/specialized_agents_part2.py`
  - Feed manuscript evidence into actor-network, cross-disciplinary lens, and integrity agents.
- Modify `src/peer_review_skills/agents/multi_agent_orchestrator.py`
  - Add optional manuscript context and case interpretation inputs.
- Modify `src/peer_review_skills/cli/main.py`
  - Add `run-rebuttal-lens` CLI.
- Create `examples/rebuttal_lens/`
  - Include sample manuscript excerpt, reviewer comment, author draft response, and README.
- Modify `README.md`, `codex.md`, `docs/MULTI_AGENT_USAGE.md`, `docs/architecture/true-multi-agent-design.md`.
- Create `docs/REBUTTAL_LENS_WORKFLOW_zh.md`.
- Modify `UPGRADE.md` with Phase 10.
- Add tests in `tests/test_rebuttal_lens_workflow.py`.

## Tasks

### Task 1: Manuscript Context Data Layer

- [ ] Write failing tests for text/file manuscript context loading.
- [ ] Implement `ManuscriptContext`, `ManuscriptSection`, `load_manuscript_context`, and `build_rebuttal_lens_unit`.
- [ ] Verify missing manuscript uses explicit `review_only` mode, not silent evidence claims.

### Task 2: Manuscript-Aware Agents

- [ ] Write failing tests that the new manuscript agents make independent LLM calls and return required JSON fields.
- [ ] Implement `ManuscriptContextExtractorAgent`, `ManuscriptEvidenceLocatorAgent`, and `CaseRetrievalInterpreterAgent`.
- [ ] Ensure outputs require evidence provenance and author confirmation.

### Task 3: RebuttalLens Orchestrator Integration

- [ ] Write failing tests for a complete RebuttalLens trace containing manuscript context, evidence map, case interpretation, 12 agent outputs, and responsible warnings.
- [ ] Modify orchestration so manuscript context flows into downstream agents.
- [ ] Preserve existing v3 NatureReview multi-agent workflow compatibility.

### Task 4: CLI and Examples

- [ ] Write failing CLI/help and mock-workflow tests.
- [ ] Add `run-rebuttal-lens` CLI supporting `--review-file`, `--manuscript-file`, `--response-file`, `--output-dir`, `--enable-refinement`, and `--limit-cases`.
- [ ] Add example inputs under `examples/rebuttal_lens/`.

### Task 5: Docs and Naming

- [ ] Update public docs to foreground RebuttalLens name, manuscript-aware workflow, and cross-disciplinary value.
- [ ] Add `docs/REBUTTAL_LENS_WORKFLOW_zh.md`.
- [ ] Update `UPGRADE.md` Phase 10 with evidence, review, verification, and GitHub release constraints.

### Task 6: Review, Verification, and GitHub Preparation

- [ ] Run targeted tests, full pytest, compileall, validator, secret scan, and rule/legacy wording scans.
- [ ] Review code for rule-generated advice leakage and manuscript evidence overclaiming.
- [ ] Initialize local git if needed, add `.gitignore`, inspect tracked set.
- [ ] Attempt GitHub remote/project preparation only if tooling and credentials are available; otherwise write exact release instructions.

## Acceptance Criteria

- `run-rebuttal-lens` can run with sample text files using a mockable model client path in tests.
- Workflow trace includes manuscript mode, section evidence, evidence gaps, Nature case interpretation, 12 agent outputs, cross-disciplinary lens output, and integrity warnings.
- Existing `run-naturereview-multi-agent` tests still pass.
- No API key is persisted.
- No user-facing advice path uses keyword/rule/heuristic generation.
- Public docs state the project is RebuttalLens / NatureReview-Interact derived, manuscript-aware, assistant-only, not final rebuttal generation.
- GitHub publishing state is honestly reported with local git status and any authentication/tooling blockers.
