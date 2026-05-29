# Upgrade Plan

## Goal

- Target outcome: upgrade NatureReview-Interact into a non-training, cross-disciplinary open-source system aligned with `docs/2026-05-26-open-source-review-interaction-agent-full-plan-zh.md`, `2026.5.23.pdf`, and `2026.5.15.pdf`.
- Acceptance criteria:
  - Public docs foreground the interdisciplinary value: tacit knowledge boundaries, institutional dependence, actor-network alignment, fast/slow cognitive correction, emotion-tone-commitment calibration, and responsible governance.
  - Training/fine-tuning is explicitly out of v0.1 core scope; any existing training seed is legacy/optional and not a release blocker.
  - Workflow traces include a first-class `cross_disciplinary_lens_map` with provenance, observable trace, system action, and boundary for each lens.
  - Simulation traces include cross-disciplinary evaluation, forbidden behaviors, and non-real-peer-review boundaries.
  - Evaluation docs state that retrieval/RAG/local comparison baselines are support infrastructure only, not the intellectual contribution.
  - Validation checks the non-training scope, PDF-derived design lenses, workflow lens maps, and simulation cross-disciplinary layer.
  - No API keys or bearer tokens are persisted.
  - Agnes/workflow user-facing advice path does not use keyword, lexical-overlap, or hard-coded heuristic fallback to decide evidence actions, response adequacy, case rationales, tone, or user suggestions.
  - Advice outputs are derived from model-assisted fields, Nature case metadata, cross-disciplinary lens traces, and provenance-linked retrieved cases; when support is insufficient, the system must say so and require author confirmation.
- Non-goals:
  - No new crawling.
  - No model training or fine-tuning.
  - No claim of human gold labels.
  - No final submission-ready rebuttal generator.
  - No claim that AI can read private reviewer intent or fully master tacit knowledge.

## System Inventory

- Stack: Python standard library, JSONL/JSON/Markdown artifacts, pytest acceptance tests.
- Key modules:
  - `src/peer_review_skills/execution/build_naturereview_v01.py`
  - `tests/test_naturereview_v01_acceptance.py`
  - `data/processed/review_interaction_kb/v1/`
  - `data/evaluation/retrieval_v2/`
  - `data/evaluation/workflow_v2/`
  - `data/evaluation/simulation_v1/`
- Test/build commands:
  - `$env:PYTHONPATH='src'; python -m pytest -q`
  - `$env:PYTHONPATH='src'; python -m compileall -q src tests`
  - `$env:PYTHONPATH='src'; python -m peer_review_skills.cli.main validate-naturereview-v01`
- Constraints:
  - This directory is not currently a git repository, so review uses file and test inspection rather than `git diff`.
  - Current labels are model-assisted, not human gold.
  - API key must not be persisted.
  - Generated artifacts must stay rebuildable.
  - Public docs must avoid positioning the project as ordinary RAG, a single technical recipe, or a training pipeline.

## Evidence

| Finding | Evidence | Source | Impact | Priority | Status |
| --- | --- | --- | --- | --- | --- |
| Training/fine-tuning is still treated as a core artifact | README listed `TRAINING_AND_LEARNING_DESIGN_zh.md`; validation had `Model-assisted training seed export is complete`; completion status listed training seed rows | `README.md`, `docs/NATUREREVIEW_V01_VALIDATION_REPORT_zh.md`, `build_naturereview_v01.py` | Conflicted with current project scope | P1 | Fixed |
| Cross-disciplinary PDF insights were not first-class in traces | Workflow trace had tacit/institutional/actor fields but no explicit lens map tying outputs to the PDFs and system actions | `data/evaluation/workflow_v2/workflow_traces.jsonl` | Core value could be mistaken for generic labels | P1 | Fixed |
| Simulation layer lacked explicit interdisciplinary evaluation | Simulation had role traces and generic cross-disciplinary trace list, but no lens-level evaluation and forbidden behavior contract | `data/evaluation/simulation_v1/simulation_traces.jsonl` | Hard to evaluate the stated interdisciplinary contribution | P1 | Fixed |
| Public docs over-emphasized RAG/local baselines as system framing | Evaluation and paper docs mentioned BM25/local baselines/RAG without always marking them as support only | `build_naturereview_v01.py`, generated docs | Risked making the project look like a technical stack rather than a cross-disciplinary system | P2 | Fixed for public v0.1 docs |
| Several generated public docs contain mojibake | Existing target plan and some historical generated Chinese docs render as garbled text in terminal reads | docs/generated files | Weakens open-source readability | P2 | Touched core public docs regenerated; historical docs remain out of scope |
| Agnes advice path still used lexical/keyword fallbacks | `_effective_evidence_action()` mapped words like baseline/code/figure to actions; `_assess_response_adequacy()` marked coverage via term hits; workflow traces exposed lexical-overlap rationale | `src/peer_review_skills/execution/build_naturereview_v01.py`, `data/evaluation/workflow_v2/workflow_traces.jsonl` | Contradicted the goal that Agnes outputs are based on Nature case data, model-assisted labels, and interdisciplinary workflow rather than shortcut matching | P1 | Fixed |

## Proposed Upgrade Phases

### Phase 10: ReviewWeaver Manuscript-Aware Final Workflow

- Goal: upgrade the public system name and workflow from NatureReview-Interact v3 traces to ReviewWeaver, a manuscript-aware, cross-disciplinary Author Rebuttal Assistant workflow.
- Changes:
  - Add conservative manuscript context loading for text, Markdown, and LaTeX-like files.
  - Add `ManuscriptContextExtractorAgent`, `ManuscriptEvidenceLocatorAgent`, and `CaseRetrievalInterpreterAgent` as independent LLM agents.
  - Add a 12-agent `execute_reviewweaver_workflow` orchestration path.
  - Add `run_reviewweaver_workflow` and `run-reviewweaver` CLI.
  - Add examples and public documentation for the ReviewWeaver name, manuscript-aware inputs, bounded Nature case analogies, and responsible-use boundaries.
  - Initialize local git and add `.gitignore` to prevent caches, node modules, API outputs, generated workflow demos, and large PDFs from accidental release.
- Affected files/modules: `src/peer_review_skills/agents/manuscript_context.py`, `src/peer_review_skills/agents/reviewweaver_agents.py`, `src/peer_review_skills/agents/reviewweaver_workflow.py`, `src/peer_review_skills/agents/multi_agent_orchestrator.py`, `src/peer_review_skills/agents/specialized_agents.py`, `src/peer_review_skills/agents/specialized_agents_part2.py`, `src/peer_review_skills/agents/providers.py`, `src/peer_review_skills/cli/main.py`, `tests/test_reviewweaver_workflow.py`, `README.md`, `codex.md`, `docs/REVIEWWEAVER_WORKFLOW_zh.md`, `examples/reviewweaver/*`, `.gitignore`.
- Risks: PDF/DOCX parsing is intentionally not claimed in this phase; user manuscripts should not be uploaded to external APIs unless the user controls the privacy/legal risk.
- Verification: targeted ReviewWeaver tests, full pytest, compileall, v0.1 validator, secret scan, rule/legacy scan, local git tracked-file audit.
- Rollback: remove ReviewWeaver files and CLI command; existing `run-naturereview-multi-agent` path remains independent.
- Status: Completed.

### Phase 1: Acceptance Tests

- Goal: encode the non-training, cross-disciplinary acceptance criteria before implementation.
- Changes:
  - Replace training-first tests with non-training scope tests.
  - Add tests for PDF-derived design docs.
  - Add tests for workflow and simulation cross-disciplinary lens maps.
  - Add validation tests for new checks and counts.
- Affected files/modules: `tests/test_naturereview_v01_acceptance.py`.
- Risks: generated docs may need broad updates to satisfy stricter public framing.
- Verification: run targeted pytest and confirm new tests fail before implementation, then pass after.
- Rollback: revert test additions and implementation patch.
- Status: Completed.

### Phase 2: Cross-Disciplinary Lens Layer

- Goal: make the two PDFs and final plan operational in system artifacts.
- Changes:
  - Add reusable lens definitions for tacit knowledge, institutional dependence, actor-network theory, fast/slow cognition, emotion-tone-commitment calibration, and author agency.
  - Add `cross_disciplinary_lens_map` to each workflow trace.
  - Add lens outputs to agent intermediate outputs.
- Affected files/modules: `build_naturereview_v01.py`, workflow JSONL artifacts.
- Risks: lens text must avoid claiming hidden psychology or real causal inference.
- Verification: workflow trace tests and validation checks.
- Rollback: remove lens map fields and validation checks.
- Status: Completed.

### Phase 3: Non-Training Open-Source Scope And PDF-Derived Docs

- Goal: make public docs readable and aligned with the current scope.
- Changes:
  - Generate `PDF_DERIVED_DESIGN_LENSES_zh.md`, `INTERDISCIPLINARY_SYSTEM_FRAME_zh.md`, and `NON_TRAINING_OPEN_SOURCE_SCOPE_zh.md`.
  - Update README, release plan, completion status, limitations, simulation spec, evaluation protocol, and risk register.
  - Keep legacy training seed export only as optional contract, not v0.1 core.
- Affected files/modules: generator docs functions and generated docs.
- Risks: older docs may still mention training as future work; public docs must clearly mark that as out of scope.
- Verification: doc tests, validation, mojibake scan on key public docs.
- Rollback: restore previous generated docs.
- Status: Completed.

### Phase 4: Simulation And Validation Upgrade

- Goal: prove the non-training interdisciplinary system layer is present and evaluable.
- Changes:
  - Add `cross_disciplinary_evaluation` to simulation traces.
  - Add validation checks and counts for lens maps.
  - Remove training seed export as a core validation blocker.
- Affected files/modules: simulation builder, validator, validation report.
- Risks: validation must not hide old training artifacts but should not treat them as core.
- Verification: full pytest, compileall, CLI validation, secret scan.
- Rollback: restore previous validation checks.
- Status: Completed.

### Phase 5: Remove Lexical/Keyword Fallbacks From Agnes Advice Path

- Goal: ensure all user-facing Agnes/workflow outputs are based on model-assisted data fields, Nature case patterns, provenance, and cross-disciplinary lenses rather than keyword or lexical shortcuts.
- Changes:
  - Replace `_effective_evidence_action()` keyword/concern fallback with data/model/case-supported action resolution.
  - Replace `_assess_response_adequacy()` term matching with provenance-aware model/case-field adequacy assessment and explicit uncertainty.
  - Remove lexical-overlap/fallback wording from workflow case explanations and final traces.
  - Keep local comparison methods only as baseline/evaluation infrastructure, not as advice basis.
  - Add validation checks that workflow traces and retrieval advice boundaries do not expose lexical/keyword rationales as recommendation grounds.
  - Make the public `run-agents` CLI accept only the external model provider and default model `deepseek-v3`; legacy local provider classes remain internal baseline code, not a public Agnes entry.
  - Gate the legacy annotation stage so external-model public workflow runs cannot silently execute local baseline annotations.
- Affected files/modules: `build_naturereview_v01.py`, `tests/test_naturereview_v01_acceptance.py`, regenerated `data/evaluation/workflow_v2/`, `data/evaluation/retrieval_v2/`, validation reports.
- Risks: older evaluation tests and baseline names may still mention historical local baselines; the acceptance boundary is advice path, not historical baseline artifacts.
- Verification: red/green pytest for rule-removal behavior, full pytest, compileall, CLI build, CLI validation, code review search for advice-path rule leakage.
- Rollback: restore previous evidence action and adequacy functions, then rebuild generated artifacts.
- Status: Completed.

### Phase 6: Final Public API Hardening

- Goal: close remaining open-source entry-point risks after the final audit.
- Changes:
  - Require an explicit `allow_legacy_baseline=True` flag before `run_agent_workflow()` can execute with `RuleBasedProvider`.
  - Keep the CLI external-model-only; direct Python calls should also make legacy baseline usage intentional and auditable.
  - Update tests to prove the default Python API rejects legacy local providers and that explicit legacy use remains possible for research baselines.
- Affected files/modules: `src/peer_review_skills/agents/orchestrator.py`, `tests/test_naturereview_v01_acceptance.py`, `codex.md`, `UPGRADE.md`.
- Risks: callers that used `run_agent_workflow(..., provider=RuleBasedProvider())` without acknowledging legacy mode will now fail fast; this is intentional for open-source safety.
- Verification: red/green pytest for provider gate, full pytest, compileall, CLI build, CLI validation, public artifact scan, secret scan.
- Rollback: remove the `allow_legacy_baseline` gate and restore prior `run_agent_workflow` signature.
- Status: Completed.

### Phase 7: True Multi-Agent Mainline Integration

- Goal: turn the new multi-agent prototype into a working NatureReview-Interact entry point aligned with the open-source cross-disciplinary plan, rather than a disconnected demo.
- Changes:
  - Fix specialized-agent factory imports so all 9 agents instantiate.
  - Normalize agent parsing so it accepts both raw OpenAI chat responses and the repo's parsed `OpenAICompatibleChatClient` JSON dict.
  - Fix API client construction to use the existing `model` parameter and default to `deepseek-v3`.
  - Load the official v0.1 KB and retrieval artifacts from `review_interaction_kb/v1` and `retrieval_v2`.
  - Fail fast when interaction units or retrieval predictions are missing instead of silently producing zero traces.
  - Add a first-class `run-naturereview-multi-agent` CLI command for the true multi-agent workflow.
  - Preserve the open plan boundaries: model-assisted labels, author confirmation, provenance, no acceptance prediction, no final rebuttal replacement.
- Affected files/modules: `src/peer_review_skills/agents/*`, `src/peer_review_skills/cli/main.py`, `tests/test_multi_agent.py`, `UPGRADE.md`.
- Risks: real API calls are slower and cost-bearing; tests use mock clients for CI and only smoke a small DeepSeek run when explicitly configured.
- Verification: red/green multi-agent tests, compileall, official build/validate, one limited DeepSeek-backed workflow run, secret scan.
- Rollback: remove the new CLI command and restore the previous standalone prototype files.
- Status: Completed.

### Phase 8: Dependency-Aware Refinement And Release Hardening

- Goal: close final v3 orchestration gaps before open-source release.
- Changes:
  - Split dependency-sensitive execution steps so tacit concern receives reviewer understanding output and tone calibration receives author positioning output.
  - Restrict the v3 loader to official v0.1 KB and retrieval v2 paths; remove legacy path fallback from the true multi-agent entry point.
  - Make refinement auditable by passing original task context, previous output, feedback, and integrity issues into the refined agent prompt.
  - Propagate refined upstream outputs through dependent downstream agents before integrity recheck.
  - Fail fast if critical integrity issues remain after configured refinement iterations.
  - Refresh v3 docs to state the current 9-call / 8-step no-refinement execution contract and rewrite the final completion report in readable Chinese.
- Affected files/modules: `src/peer_review_skills/agents/base.py`, `src/peer_review_skills/agents/multi_agent_orchestrator.py`, `src/peer_review_skills/agents/specialized_agents.py`, `src/peer_review_skills/agents/specialized_agents_part2.py`, `src/peer_review_skills/agents/workflow_integration.py`, `tests/test_multi_agent.py`, `docs/MULTI_AGENT_USAGE.md`, `docs/architecture/true-multi-agent-design.md`, `docs/MULTI_AGENT_IMPLEMENTATION_SUMMARY.md`, `docs/FINAL_COMPLETION_REPORT.md`.
- Risks: refinement increases API calls because dependent downstream agents rerun; keep refinement disabled by default and use bounded `--limit` for release smoke tests.
- Verification: targeted refinement/dependency tests, full multi-agent tests, full pytest, compileall, official validation, secret scan, public wording scan.
- Rollback: restore prior orchestrator and workflow integration behavior, then remove Phase 8 tests.
- Status: Completed.

### Phase 9: Final Pre-Release Review Hardening

- Goal: remove final release-surface defects found in the last full review pass.
- Changes:
  - Redact secret-bearing config values from `workflow_summary.json` and returned summary objects, including nested `Authorization` fields and Bearer-like string values.
  - Normalize cross-disciplinary lens prompt wording to readable Chinese names matching the project documents: 默会知识边界、制度依赖、行动者网络对齐、快慢思维校正、情绪-语气-承诺校准、作者主体性门控。
  - Clean the direct test runner output in `tests/test_multi_agent.py` to avoid Unicode/mojibake issues when users execute the file directly.
- Affected files/modules: `src/peer_review_skills/agents/workflow_integration.py`, `src/peer_review_skills/agents/specialized_agents_part2.py`, `tests/test_multi_agent.py`, `UPGRADE.md`.
- Risks: summary config now intentionally hides sensitive values; debugging should use non-secret identifiers or environment inspection outside persisted artifacts.
- Verification: targeted red/green tests for secret redaction and lens names, full test suite, compileall, v0.1 validation, secret scan, rule/legacy wording scan, mojibake scan.
- Rollback: restore previous summary serialization and prompt wording, then remove Phase 9 regression tests.
- Status: Completed.

## Rejected Options

| Option | Why Rejected |
| --- | --- |
| Train classifiers or fine-tune models now | User explicitly asked to discard training/fine-tuning for now. |
| Continue crawling | Current project shift is to use existing v2709 data. |
| Replace everything with DeepSeek API calls | The project needs rebuildable open-source artifacts; API may assist labels, but should not be required for core repo generation. |
| Present retrieval/RAG as the main contribution | The desired contribution is cross-disciplinary review-interaction learning and responsible workflow design. |
| Generate final rebuttal letters | Conflicts with responsible-use boundaries and author agency. |
| Delete all baseline evaluation references | Rejected because baselines remain useful for research comparison; the required fix is to keep them out of Agnes advice and workflow recommendation rationale. |

## Review Log

| Pass | Findings | Fix Status |
| --- | --- | --- |
| Initial inventory | Training and RAG framing remain too prominent; lens-level trace layer missing | Planned fixes in phases 1-4 |
| Implementation review | Found non-core training/RAG framing in public artifacts and missing validation checks | Fixed with non-training scope docs, lens maps, simulation evaluation, and validation checks |
| Final review | No actionable correctness findings after tests and validation; residual risk is historical mojibake in out-of-scope older docs | Documented residual risk |
| Phase 5 initial review | Advice path still used keyword evidence-action fallback, term-hit adequacy, and lexical-overlap case rationale | Fixed with model/case-supported evidence actions, adequacy uncertainty, positive case-boundary text, validation scan, external-model-only public CLI, and legacy annotation gate |
| Phase 5 final review | Static scan found no forbidden lexical/keyword/rule markers in workflow, retrieval, simulation, validation, README, or core public docs; remaining marker strings are validator/test guardrails or legacy baseline modules outside Agnes advice path | No actionable findings for implemented Phase 5 scope |
| Phase 6 audit | Direct Python API still allowed `run_agent_workflow(..., provider=RuleBasedProvider())`, bypassing the external-model-only CLI boundary | Planned provider gate and regression tests |
| Phase 6 final review | Direct Python API now rejects legacy local providers unless `allow_legacy_baseline=True`; CLI remains external-model-only; `codex.md` was refreshed as the current Chinese project entry summary | No actionable findings after full tests, rebuild, validation, secret scan, and public advice artifact scan |
| Phase 7 initial review | New multi-agent prototype failed instantiation, API client construction, real response parsing, and official data-path integration | Planned fixes in Phase 7 |
| Phase 7 implementation review | DeepSeek smoke trace exposed two quality gaps: cross-disciplinary lens initially lacked prior agent context and could emit private-psychology language | Fixed taxonomy aliases, prior-output wiring, actor-network-before-lens dependency, and lens output safety validation |
| Phase 7 final review | Public v3 entry is multi-agent only; no rule-based compare mode remains in the v3 integration path; fail-fast orchestration prevents partial traces; docs no longer claim unverified quality gains | No actionable findings after full tests, build, validation, DeepSeek smoke test, secret scan, and public wording scans |
| Phase 8 initial review | v3 orchestration still treated dependent agents as same-layer calls; refinement did not propagate revised outputs to downstream agents; v3 loader still had legacy path fallback; final Chinese report had mojibake | Fixed with dependency-aware execution, refinement context + propagation + recheck, official-path-only v3 loading, and readable Chinese completion report |
| Phase 8 final review | Refinement could loop until the iteration cap when integrity returned a critical issue for an unknown/missing agent | Fixed with fail-fast unrefinable critical issue handling and regression test |
| Phase 9 review | Python config could persist API keys/Bearer values into `workflow_summary.json`; cross-disciplinary prompt used inconsistent Chinese lens names; direct test runner printed fragile Unicode marks | Fixed with recursive config redaction, value-shape secret redaction, readable lens prompt names, and ASCII direct-run test output |
| Phase 9 final review | Taxonomy-aware agents could fail when external callers passed `taxonomies=None`; direct-run and public release scans needed fresh verification after the fix | Fixed with shared taxonomy-context normalization, regression tests, direct test runner verification, full pytest, compileall, validator, secret scan, and rule/legacy wording scans |
| Phase 10 review | Final user workflow lacked manuscript context, original-manuscript evidence grounding, bounded case interpretation, clean project naming, and a GitHub release boundary | Fixed with ReviewWeaver 12-agent workflow, manuscript-aware evidence map, case interpreter, CLI, examples, docs, local git initialization, and release blocker documentation |

## Verification Log

| Command/Test | Result | Notes |
| --- | --- | --- |
| `$env:PYTHONPATH='src'; python -m pytest ...new non-training/lens tests... -q` | PASS | 5 passed after red/green cycle |
| `$env:PYTHONPATH='src'; python -m pytest -q` | PASS | 27 passed |
| `$env:PYTHONPATH='src'; python -m compileall -q src tests` | PASS | No compile errors |
| `$env:PYTHONPATH='src'; python -m peer_review_skills.cli.main validate-naturereview-v01` | PASS | Includes `cross_disciplinary_lens_trace_count: 50` |
| `rg --pcre2 ...secret patterns... src tests docs data\evaluation data\processed data\training README.md` | PASS | Exit 1 from `rg` means no matches found |
| `$env:PYTHONPATH='src'; python -m pytest ...Phase 5 advice-path tests... -q` | PASS | 6 passed after red/green cycle |
| `$env:PYTHONPATH='src'; python -m pytest -q` | PASS | 33 passed |
| `$env:PYTHONPATH='src'; python -m compileall -q src tests` | PASS | No compile errors |
| `$env:PYTHONPATH='src'; python -m peer_review_skills.cli.main build-naturereview-v01` | PASS | Rebuilt v0.1 artifacts |
| `$env:PYTHONPATH='src'; python -m peer_review_skills.cli.main validate-naturereview-v01` | PASS | `agnes_advice_leakage_hit_count: 0`; `workflow_traces: 50`; `cross_disciplinary_lens_trace_count: 50` |
| `rg ...forbidden advice markers... data\evaluation\workflow_v2 data\evaluation\retrieval_v2 data\evaluation\simulation_v1 docs\...\ README.md` | PASS | Exit 1 from `rg` means no forbidden markers found in Agnes/public advice artifacts |
| `$env:PYTHONPATH='src'; python -m pytest tests\test_naturereview_v01_acceptance.py::test_python_agent_workflow_requires_explicit_legacy_baseline_flag tests\test_naturereview_v01_acceptance.py::test_python_agent_workflow_allows_explicit_legacy_baseline_for_research -q` | PASS | 2 passed; verifies Phase 6 Python API gate |
| `$env:PYTHONPATH='src'; python -m pytest -q` | PASS | 35 passed |
| `$env:PYTHONPATH='src'; python -m compileall -q src tests` | PASS | No compile errors |
| `$env:PYTHONPATH='src'; python -m peer_review_skills.cli.main build-naturereview-v01` | PASS | Rebuilt v0.1 artifacts |
| `$env:PYTHONPATH='src'; python -m peer_review_skills.cli.main validate-naturereview-v01` | PASS | Counts stable: `interaction_units: 245`, `workflow_traces: 50`, `simulation_traces: 50`, `cross_disciplinary_lens_trace_count: 50`; `agnes_advice_leakage_hit_count: 0` |
| `rg --pcre2 ...secret patterns... README.md codex.md UPGRADE.md src tests docs data/evaluation data/processed data/training` | PASS | No persisted real API keys or bearer values found; placeholder terms are allowed where documented |
| `rg ...forbidden advice markers... data\evaluation\workflow_v2 data\evaluation\retrieval_v2 data\evaluation\simulation_v1 docs\...\ README.md codex.md` | PASS | No forbidden advice-basis markers found in public Agnes/workflow artifacts |
| Final verification on 2026-05-28: pytest, compileall, validator, secret scan, public advice marker scan | PASS | Fresh final run: `35 passed`; validation `PASS`; counts stable; no persisted real API key; no forbidden advice-basis markers in public Agnes/workflow artifacts |
| Phase 7 red/green multi-agent tests | PASS | `tests/test_multi_agent.py`: 12 passed after red tests for official paths, API client signature, parsed JSON responses, taxonomy aliases, prior agent context, no empty traces, layer metadata, and lens safety validation |
| Phase 7 full pytest | PASS | `47 passed` |
| Phase 7 compileall | PASS | `$env:PYTHONPATH='src'; python -m compileall -q src tests` |
| Phase 7 DeepSeek smoke run | PASS | `run-naturereview-multi-agent --limit 1`: `total_traces=1`, `total_llm_calls=9`, `input_interaction_units=245`, `input_retrieval_predictions=100` |
| Phase 7 official rebuild | PASS | `python -m peer_review_skills.cli.main build-naturereview-v01` |
| Phase 7 official validation | PASS | `validate-naturereview-v01`: `PASS`; counts stable with 245 interaction units, 100 retrieval predictions, 50 workflow traces, 50 simulation traces |
| Phase 7 secret scan | PASS | No persisted real API keys or bearer tokens found in public project files |
| Phase 7 wording and trace scans | PASS | No obsolete GPT/rule-based/parallel/quality-gain wording in current v3 docs/config; no private-psychology lens leakage in `workflow_v3` |
| Phase 8 targeted tests | PASS | Dependency ordering, refinement context/recheck/propagation, unrefinable critical issue fail-fast, and official-path-only v3 loader tests pass |
| Phase 8 full pytest | PASS | `52 passed` |
| Phase 8 compileall | PASS | `$env:PYTHONPATH='src'; python -m compileall -q src tests` |
| Phase 8 official validation | PASS | `validate-naturereview-v01`: `PASS`; counts stable with 245 interaction units, 100 retrieval predictions, 50 workflow traces, 50 simulation traces |
| Phase 8 secret scan | PASS | No persisted real API keys or bearer tokens found in public project files |
| Phase 8 public wording and v3 trace scans | PASS | No obsolete v3 prototype wording in current public multi-agent docs/config/agent code; no private-psychology lens leakage in `workflow_v3` |
| Phase 9 secret-redaction and lens-name targeted tests | PASS | Regression tests verify workflow summary redacts secret-like config values and the cross-disciplinary prompt uses readable Chinese lens names |
| Phase 9 taxonomy boundary targeted tests | PASS | 7 tests pass; taxonomy-aware agents tolerate missing taxonomy context and `taxonomies=None` from external callers |
| Phase 9 direct test runner | PASS | `$env:PYTHONPATH='src'; python tests\test_multi_agent.py`; direct Windows execution uses ASCII status output |
| Phase 9 full pytest | PASS | `61 passed` |
| Phase 9 compileall | PASS | `$env:PYTHONPATH='src'; python -m compileall -q src tests` |
| Phase 9 official validation | PASS | `validate-naturereview-v01`: `PASS`; counts stable with 245 interaction units, 100 retrieval predictions, 50 workflow traces, 50 simulation traces, 50 cross-disciplinary lens traces |
| Phase 9 secret scan | PASS | No persisted real API keys or bearer tokens found in README, codex, UPGRADE, src, tests, docs, or data release paths |
| Phase 9 public rule/legacy wording scans | PASS | No rule/keyword/lexical/heuristic/fallback markers in current v3 workflow output path and public multi-agent docs; no obsolete v3 prototype wording in current docs/config/agent code |
| Phase 9 Unicode/mojibake guard scan | PASS | No fragile direct-run status symbols remain; the only matched mojibake-like strings are intentional regression-test guardrail markers that prevent corrupted lens names from entering prompts |
| Phase 10 ReviewWeaver targeted tests | PASS | `tests/test_reviewweaver_workflow.py`: 11 passed |
| Phase 10 full pytest | PASS | `72 passed` |
| Phase 10 compileall | PASS | `$env:PYTHONPATH='src'; python -m compileall -q src tests` |
| Phase 10 official validation | PASS | `validate-naturereview-v01`: `PASS`; counts stable with 245 interaction units, 100 retrieval predictions, 50 workflow traces, 50 simulation traces |
| Phase 10 secret scan | PASS | No persisted real API keys or bearer tokens found in public project files, docs, examples, source, tests, or data release paths |
| Phase 10 rule/legacy scan | PASS | ReviewWeaver and current v3 public advice paths contain no rule/keyword/lexical/heuristic/fallback advice-basis markers after legacy provider wording cleanup |
| Phase 10 GitHub readiness | BLOCKED | Local git was initialized, but this machine has no `gh` CLI and no remote repository configured; GitHub Project upload requires repo URL and authentication/tooling |

## Residual Risks

- Model-assisted labels are not human gold.
- Cross-disciplinary lenses are interpretive scaffolds over observable text, not proof of private intentions.
- Current non-training system can plan and evaluate assistance, but it does not prove outcome improvement without human/user evaluation.
- Existing legacy training artifacts may remain in the repo, but public scope must mark them as optional/non-core.
- Some historical generated Chinese docs outside the core public v0.1 scope still display mojibake in terminal reads; the new core scope docs and validation report pass the existing mojibake scan.

## Completion Checklist

- [x] Acceptance tests updated and watched fail.
- [x] Cross-disciplinary lens map implemented in workflow traces.
- [x] Simulation traces include cross-disciplinary evaluation.
- [x] Public docs foreground non-training interdisciplinary value.
- [x] Validation checks new scope and lens artifacts.
- [x] Review has no actionable findings for implemented scope.
- [x] Targeted tests pass.
- [x] Full available system verification passes or limitations are documented.
- [x] Residual risks and rollback path are documented.
- [x] Phase 5 removes rule/keyword/lexical decision bases from Agnes advice path.
- [x] Phase 5 review has no actionable findings for implemented scope.
- [x] Phase 6 public API hardening completed.
- [x] Phase 7 true multi-agent mainline integration completed.
- [x] Phase 8 dependency-aware refinement and release hardening completed.
- [x] Phase 9 final pre-release review hardening completed.
- [x] Phase 10 ReviewWeaver manuscript-aware final workflow completed locally.
