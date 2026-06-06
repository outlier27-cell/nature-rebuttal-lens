# DeepSeek v7 全流程运行报告：Nature RebuttalLens + 主动遗忘伦理

## 1. 运行结论

本次使用 `deepseek-v3` 和 OpenAI-compatible 网关 `https://xh.v1api.cc`，完整运行了 Nature RebuttalLens 的 `DAG + reviewer committee + strategy tournament + memory ethics` 流程。运行已经成功完成，并生成完整 trace、summary、JSON final report、Markdown final report 与审计摘要。

- Workflow engine: dag
- Workflow version: rebuttal_lens_v1
- Manuscript mode: manuscript_aware
- LLM calls: 18
- Agent outputs: 18 / 18
- Execution errors: 0
- Execution levels: 11
- Graph nodes executed: 19 / 19
- Package readiness: decision_deferred
- Response package gate issues: 0
- Final report is submission text: False
- Memory policy: strict
- Reset memory requested: True
- Runtime memory after forgetting: empty_after_forgetting

结论：本次例子不是自动生成最终投稿 rebuttal，而是生成一个可审计、证据优先、需要作者确认的回应辅助包。系统最终状态为 `decision_deferred`，这是合理结果，因为 temporal leakage、temporally held-out split、near-duplicate removal 和 generalization claim narrowing 都还需要作者补充分析或明确确认。

## 2. 本次输入材料

- Reviewer comment: `examples/rebuttal_lens_deepseek_full_demo/reviewer_comment.txt`
- Manuscript excerpt: `examples/rebuttal_lens_deepseek_full_demo/manuscript_excerpt.txt`
- Author draft response: `examples/rebuttal_lens_deepseek_full_demo/author_draft_response.txt`
- Editor note: `examples/rebuttal_lens_deepseek_full_demo/editor_note.txt`
- Retrieved cases: `examples/rebuttal_lens_deepseek_full_demo/retrieved_cases.json`

本例的核心 reviewer concern 是：稿件当前使用 random paper-level split，但没有说明如何避免 temporal leakage；也没有报告 temporally held-out split 和 near-duplicate removal 后的稳健性，因此 “generalizes across peer-review contexts” 这个 claim 可能过强。

## 3. 实际运行命令

API key 已在命令和报告中脱敏，真实运行时只通过环境变量传入。

```powershell
$env:PYTHONPATH='src'
$env:PEER_REVIEW_API_BASE_URL='https://xh.v1api.cc'
$env:PEER_REVIEW_API_KEY='<redacted>'
$env:PEER_REVIEW_API_MODEL='deepseek-v3'
$env:PEER_REVIEW_API_TIMEOUT_SECONDS='240'
python -m peer_review_skills.cli.main run-rebuttal-lens `
  --review-file examples/rebuttal_lens_deepseek_full_demo/reviewer_comment.txt `
  --manuscript-file examples/rebuttal_lens_deepseek_full_demo/manuscript_excerpt.txt `
  --response-file examples/rebuttal_lens_deepseek_full_demo/author_draft_response.txt `
  --editor-file examples/rebuttal_lens_deepseek_full_demo/editor_note.txt `
  --retrieved-cases-file examples/rebuttal_lens_deepseek_full_demo/retrieved_cases.json `
  --workflow-engine dag `
  --enable-committee `
  --enable-strategy-tournament `
  --reset-memory `
  --memory-policy strict `
  --forget-scope latent_commitment `
  --output-dir examples/rebuttal_lens_deepseek_full_demo/output_v7_forgetting_ethics_full
```

## 4. 本轮先发现并修复的问题

第一次真实 DeepSeek v7 运行在 `cross_disciplinary_lens_interpreter` 中断，错误为：`Agent output validation failed: Missing 'lens_interpretations' field`。根因不是 API 或 DAG 配置问题，而是真实 provider 的 JSON 字段名发生轻微漂移：模型可能返回 `cross_disciplinary_lens_map` 或 `lens_map`，但系统只接受顶层 `lens_interpretations`。

本轮代码层修复是：在 `CrossDisciplinaryLensInterpreterAgent` 的 parse/validate 边界加入 provider JSON drift normalizer，只把语义等价的 lens map 字段归一到 `lens_interpretations`，但仍严格要求 6 个理论 lens 全部存在，也继续保留禁止 private reviewer psychology、manipulation 和 acceptance prediction 的安全校验。

对应回归验证：

- 新增测试：`test_cross_disciplinary_lens_normalizes_deepseek_lens_map_alias`
- 新增测试先红灯：缺少 `lens_interpretations` 时失败
- 修复后 targeted tests: 4 passed
- 相关测试集：100 passed, 1 deselected
- 已知未纳入本次放行的测试：`test_public_repository_does_not_reference_internal_docs`，它与本次 DeepSeek schema drift 无关，失败原因是当前仓库仍跟踪 `UPGRADE.md`

## 5. 输出文件

- `rebuttal_lens_trace.json`: 106944 bytes
- `rebuttal_lens_summary.json`: 3956 bytes
- `final_user_report.json`: 15212 bytes
- `final_user_report.md`: 11347 bytes
- `v7_audit_summary.json`: 2643 bytes
- `DEEPSEEK_V7_FORGETTING_ETHICS_FULL_RUN_REPORT_zh.md`: 本报告

主要文件说明：

- `rebuttal_lens_trace.json`：完整 agent trace，包含 18 个 agent 的结构化中间输出，以及 memory passport、forgetting ledger、irreversible forgetting statement。
- `rebuttal_lens_summary.json`：运行摘要、模型配置、输出路径和调用次数，API key 已脱敏。
- `final_user_report.json`：机器可读的最终作者辅助报告，包含 comment cards、readiness、committee synthesis、strategy plan、responsible-use warnings 和 memory ethics 字段。
- `final_user_report.md`：面向作者阅读的中文 Markdown 报告，不是最终投稿文本。
- `v7_audit_summary.json`：本次审计脚本生成的完整性检查摘要。

## 6. 当前完整框架

当前框架是一个 manuscript-aware、evidence-first、multi-agent rebuttal planning system。它不直接替作者写最终回复，而是把审稿意见转成可审计的行动包，并且显式加入主动遗忘伦理边界。

整体链路如下：

1. 输入层：reviewer comment、manuscript excerpt、author draft、editor note、retrieved cases。
2. DAG 调度层：显式依赖图执行 19 个 graph node，其中 18 个需要 LLM 输出，支持 committee 和 strategy tournament 并行节点。
3. 证据定位层：把 concern 对齐到 manuscript section、evidence refs 和 evidence gap。
4. 行动规划层：把 gap 转成 required artifact、Nature action、missing author input。
5. Committee 层：方法学、claim 校准、语气互动三个 reviewer lens 独立审查，再由 meta-reviewer 合成。
6. Strategy 层：生成多个回应策略并评分，再选出最稳妥策略。
7. Integrity 层：检查 provenance、adequacy、responsible-use boundary。
8. Memory Ethics 层：记录哪些记忆可以保留、哪些必须遗忘，并禁止旧作者决策和最终措辞在新运行中被重构为默认承诺。
9. Final report 层：输出 Nature-response 风格 comment cards 和中文作者辅助报告。

## 7. DAG 执行层级

| Level | Nodes | Success | Errors | Parallel groups |
| --- | --- | ---: | ---: | --- |
| 1 | manuscript_context | 1 | 0 | - |
| 2 | reviewer_understanding | 1 | 0 | - |
| 3 | manuscript_evidence, tacit_concern | 2 | 0 | - |
| 4 | case_interpretation, institutional_signal | 2 | 0 | - |
| 5 | evidence_action | 1 | 0 | - |
| 6 | author_positioning, committee_claim_review, committee_methodology_review, committee_tone_review | 4 | 0 | reviewer_committee: committee_claim_review, committee_methodology_review, committee_tone_review |
| 7 | committee_meta_review, tone_commitment | 2 | 0 | - |
| 8 | actor_network, strategy_tournament | 2 | 0 | - |
| 9 | cross_disciplinary_lens, meta_synthesis | 2 | 0 | - |
| 10 | integrity | 1 | 0 | - |
| 11 | final_user_report | 1 | 0 | - |

## 8. Final Report 输出内容

本次 final report 识别出 2 个 reviewer concern card。

### comment_001：experimental_design
- Severity: major
- Category: methodological
- Evidence status: partially_supported
- Manuscript section: section_004
- Evidence anchor: section_004
- Evidence refs: section_004
- Proposed action: AUTHOR_INPUT_NEEDED
- Readiness: needs_author_input
- Risk level: high
- Recommended action: Explanation of how temporal leakage was avoided in split construction
- Evidence gap: The manuscript does not explain how temporal leakage was avoided or whether papers from the same journal issue, topic cluster, or review round can appear across different splits.
- Missing author input: Explanation of how temporal leakage was avoided in split construction
- Memory decision boundary: author_decision_required=True, system_may_commit_for_author=False

解释：The dataset appears to be drawn from multiple Nature-family journals over several years, yet the manuscript does not explain how temporal leakage was avoided when constructing train, validation, and test splits. It is also unclear whether papers from the same journal issue, topic cluster, or review round can appear across different splits. 系统没有把这个 concern 判成已经完成，而是要求作者补充或确认关键证据。
### comment_002：generalization_scope
- Severity: major
- Category: editorial_presentation
- Evidence status: missing
- Manuscript section: none
- Evidence anchor: none
- Evidence refs: 无
- Proposed action: AUTHOR_INPUT_NEEDED
- Readiness: decision_deferred
- Risk level: high
- Recommended action: Robustness checks under temporally held-out splits
- Evidence gap: The manuscript does not clarify whether the reported gains remain when near-duplicate review-response pairs are removed beyond exact duplicates.
- Missing author input: Robustness checks under temporally held-out splits
- Memory decision boundary: author_decision_required=True, system_may_commit_for_author=False

解释：Without this, the central claim that the method generalizes across peer-review contexts is overstated. 系统没有把这个 concern 判成已经完成，而是要求作者补充或确认关键证据。

## 9. Committee 综合结果

Committee meta-reviewer 给出的优先行动包括：

- Perform temporal hold-out validation。支持方：methodology_committee_reviewer, claim_committee_reviewer；confidence=high; required_author_confirmation=True。
- Implement and report near-duplicate detection analysis。支持方：methodology_committee_reviewer, claim_committee_reviewer；confidence=high; required_author_confirmation=True。
- Narrow generalization claims in abstract and discussion。支持方：claim_committee_reviewer, tone_committee_reviewer；confidence=high; required_author_confirmation=True。
- Revise response tone to focus on evidence adequacy。支持方：tone_committee_reviewer；confidence=medium; required_author_confirmation=True。

Committee 识别出的主要 evidence gaps：

- Temporal split performance metrics。noted_by=methodology_committee_reviewer, claim_committee_reviewer; author_action_required=True。
- Near-duplicate removal impact on metrics。noted_by=methodology_committee_reviewer, claim_committee_reviewer; author_action_required=True。
- Documentation of split procedures。noted_by=methodology_committee_reviewer; author_action_required=True。

本次 committee 没有保留实质分歧，三个 lens 在 temporal split、near-duplicate removal、claim narrowing 和 response tone 上高度一致。

## 10. Strategy 输出

Strategy meta-planner 选择的核心方向是 `acknowledge_and_fix`，重点是：

- Evidence anchor: section_004
- Overclaim gate: Avoid claiming generalization without new evidence
- Concern coverage: 0.8
- Evidence grounding: 0.7
- Feasibility: 0.9
- Overclaim risk: 0.3
- Tone risk: 0.2
- Provenance strength: 0.8

被拒绝的候选策略包括：

- 无。

这说明系统没有建议“硬辩护”，而是把回应策略放在承认问题、补证据、缩窄 claim 的组合上。

## 11. 主动遗忘伦理输出

本次运行使用 `--reset-memory --memory-policy strict --forget-scope latent_commitment`。系统把“记忆”限定为证据、推理和审计痕迹，不把作者历史决策、策略偏好、最终措辞或潜在承诺带入新运行。

Memory passport：

```json
{
  "policy": "strict",
  "reset_memory_requested": true,
  "retained_memory_classes": [
    "evidence_trace",
    "reasoning_trace",
    "audit_trace"
  ],
  "forgotten_memory_classes": [
    "author_decision",
    "final_wording",
    "latent_commitment",
    "strategy_preference",
    "unsafe_claim"
  ],
  "justification_memory_not_conclusion_memory": true,
  "forgetting_is_active_boundary": true,
  "irreversible_forgetting": true
}
```

Forgetting ledger：

```json
[
  {
    "memory_class": "author_decision",
    "action": "forgotten",
    "policy": "strict",
    "reset_memory_requested": true,
    "reason": "Author agency must be renewed for every run.",
    "system_may_reconstruct_from_evidence": false
  },
  {
    "memory_class": "final_wording",
    "action": "forgotten",
    "policy": "strict",
    "reset_memory_requested": true,
    "reason": "The system plans responses; it must not preserve final author expression.",
    "system_may_reconstruct_from_evidence": false
  },
  {
    "memory_class": "latent_commitment",
    "action": "forgotten",
    "policy": "strict",
    "reset_memory_requested": true,
    "reason": "The configured memory policy marks this class as non-authoritative for future runs.",
    "system_may_reconstruct_from_evidence": true
  },
  {
    "memory_class": "strategy_preference",
    "action": "forgotten",
    "policy": "strict",
    "reset_memory_requested": true,
    "reason": "A past strategy must not become an automatic future answer.",
    "system_may_reconstruct_from_evidence": false
  },
  {
    "memory_class": "unsafe_claim",
    "action": "forgotten",
    "policy": "strict",
    "reset_memory_requested": true,
    "reason": "The configured memory policy marks this class as non-authoritative for future runs.",
    "system_may_reconstruct_from_evidence": true
  }
]
```

Irreversible forgetting statement：

```json
{
  "author_decision": "Forgotten author decisions must not be reconstructed from checkpoints, cache, retrieved cases, prior final reports, or historical run summaries.",
  "strategy_preference": "Forgotten strategy preferences must not become defaults for later runs.",
  "final_wording": "Forgotten final wording must not be reused as submission-ready author expression."
}
```

Memory ethics boundary：

```json
{
  "justification_memory_not_conclusion_memory": true,
  "cross_run_strategy_memory_used": false,
  "author_decisions_reset_each_run": true,
  "per_item_author_confirmation_required": true,
  "trace_bound_to_output": true,
  "forgetting_ledger_attached": true,
  "reset_memory_requested": true,
  "reset_memory_effect": "No cross-run strategy or author-preference memory is loaded; this run is treated independently."
}
```

`runtime_memory_after_forgetting` 在 trace 中为 `{}`，表示主动遗忘后没有可复用的跨运行作者决策或策略偏好。报告中的关键中文边界句也已验证存在：遗忘不是能力损失，而是保护作者主体性的边界。

## 12. 作者必须确认的问题

- Should we confirm the random paper-level split includes no temporal contamination?
- Would near-duplicate removal significantly change the current macro-F1 benchmark?
- Can you confirm whether the random paper-level split includes any temporal contamination?
- Can you provide performance metrics under a temporal hold-out split?
- Can you provide performance metrics after removing near-duplicate pairs?
- What specific language would you propose to narrow the generalization claims?
- Can you confirm whether the random paper-level split includes any temporal contamination across years?
- What threshold would you use for near-duplicate detection (e.g., MinHash similarity >0.8)?
- Does the temporal hold-out analysis require journal-specific year boundaries given different publication frequencies?
- Would stricter near-duplicate removal (beyond exact matches) significantly change the reported macro-F1 metrics?
- What specific language would appropriately narrow the generalization claims while preserving the core contribution?
- Should the response more prominently feature the planned temporal split and near-duplicate analyses as central to addressing the reviewer's concerns?
- Are the reported response strategy classification metrics from human-annotated test data?
- Explanation of how temporal leakage was avoided in split construction
- Robustness checks under temporally held-out splits

## 13. 推荐回应结构

- Thank the reviewer and restate the concern as an evidence/validity issue.
- Use response position: acknowledge_and_fix.
- Complete or explicitly qualify this planned action: Avoid claiming generalization without new evidence.
- Address comment_001 by explaining: Explanation of how temporal leakage was avoided in split construction.
- Address comment_002 by explaining: Robustness checks under temporally held-out splits.
- Do not overclaim until this missing element is resolved: Specific details on temporal split methodology.
- Do not overclaim until this missing element is resolved: Results from temporal hold-out analysis.
- Do not overclaim until this missing element is resolved: Results from deduplication sensitivity analysis.
- Close by distinguishing completed revisions from analyses that require author confirmation.

## 14. 可靠性与完整性检查

本次 v7 审计结果：

- 18 个预期 agent 全部有输出。
- DAG execution trace 共 11 层，`execution_errors = 0`。
- `summary_total_llm_calls = 18`，`trace_total_llm_calls = 18`。
- `response_package_gate_issues = []`。
- 每个 comment card 都包含 severity、category、proposed_action、readiness、risk_level、missing_author_input、evidence_anchor、evidence_refs、data_availability_check、citation_support_check、memory_decision_boundary。
- `not_final_submission_text = true`。
- responsible-use warnings 完整包含：assistant_only, author_must_verify_all_claims, not_final_rebuttal_text, no_acceptance_prediction, no_confidential_upload_recommendation。
- Memory ethics 字段完整包含：`memory_passport`、`forgetting_ledger`、`irreversible_forgetting_statement`、`memory_ethics_boundary`、`runtime_memory_after_forgetting`。
- Markdown final report 为 UTF-8 中文，已用 Unicode 检查确认中文标题和“遗忘不是能力损失”句子存在。

Integrity checker 保留的 warning：

- warning / tone_commitment_calibrator: Initial defensive language ('we believe this avoids leakage') lacks immediate evidence.
- warning / claim_committee_reviewer: Generalization claims in abstract may be overreaching without specific supporting data.

这些 warning 是正确的安全结果：它们指出作者初稿里 “we believe this avoids leakage” 缺少直接证据，以及 abstract/generalization claim 可能超过当前证据边界。

## 15. 当前边界

- 本系统仍然是 rebuttal assistant，不是最终投稿文本生成器。
- 本次结果不能替代作者确认；尤其 temporal split、near-duplicate analysis 和 generalization claim narrowing 必须由作者完成或确认。
- 本次 demo 输入不等于真实论文审稿结论，不能外推到实际投稿成败。
- DeepSeek API 真实运行已经通过，但 provider JSON 字段仍可能有小漂移；本轮已为 cross-disciplinary lens 加入回归测试和最小归一化保护。
- 当前完整 pytest 中有一个与本次运行无关的既有 public-doc 策略检查会因 `UPGRADE.md` 被跟踪而失败；本次 DeepSeek 流程相关测试和回归测试已通过。

## 16. 总结

本次 v7 说明当前框架已经具备完整的 manuscript-aware RebuttalLens 流程：它能把 reviewer concern 转为证据定位、行动计划、committee 审查、策略选择、完整性检查、主动遗忘伦理记录和作者辅助报告。最重要的是，系统没有把缺失分析伪装成已完成工作，而是把关键状态标记为 `decision_deferred`，并通过 responsible-use warnings 与 forgetting ledger 明确要求作者重新确认全部 claim、实验和最终措辞。
