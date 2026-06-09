# Nature RebuttalLens 最终作者回应辅助报告

本报告是 assistant 输出，不是可直接提交的最终 rebuttal。所有实验、证据、引用和承诺都必须由作者确认。

## 1. 核心判断

系统识别出 2 个 reviewer concern。其中 0 个 claim 暂时不可追溯或证据不足。建议先补证据和缩窄承诺，再组织 rebuttal 草稿。
Package readiness: decision_deferred

## 2. Reviewer Concern Cards

### comment_001 - experimental_design

- 表层要求：Provide a transparent account of the split construction, add robustness checks under at least one temporally held-out split, and clarify whether reported gains remain when near-duplicate review-response pairs are removed.
- 深层风险：The manuscript does not explain how temporal leakage was avoided when constructing train, validation, and test splits. It is also unclear whether papers from the same journal issue, topic cluster, or review round can appear across different splits. The authors should provide a more transparent account of the split construction, add robustness checks under at least one temporally held-out split, and clarify whether the reported gains remain when near-duplicate review-response pairs are removed.
- 证据状态：partially_supported / section_004
- 证据缺口：The manuscript does not explain how temporal leakage was avoided. It acknowledges potential topical clustering across splits and explicitly states a temporal split experiment has not been reported. It also states stricter near-duplicate removal (e.g., MinHash) has not been completed.
- 建议动作：A transparent description of how train/validation/test splits were constructed, explicitly stating how temporal leakage was avoided and whether papers from the same journal issue, topic cluster, or review round can appear across splits.
- 作者确认必需：True
- Severity: major
- Category: methodological
- Proposed action: AUTHOR_INPUT_NEEDED
- Readiness: decision_deferred
- Risk level: high
- Evidence anchor: section_004
- Missing author input: ['A transparent description of how train/validation/test splits were constructed, explicitly stating how temporal leakage was avoided and whether papers from the same journal issue, topic cluster, or review round can appear across splits.']
- 安全表达：We will report this analysis if completed, or narrow the claim if it cannot be supported.
- 避免表达：Avoid claiming that the concern is fully resolved before evidence is available.

### comment_002 - generalization_scope

- 表层要求：Clarify whether the central claim that the method generalizes across peer-review contexts is overstated.
- 深层风险：Without this, the central claim that the method generalizes across peer-review contexts is overstated.
- 证据状态：supported / section_007
- 证据缺口：The manuscript explicitly states the lack of temporal split evaluation and acknowledges potential topical clustering, which directly supports the concern that the generalization claim may be overstated without these checks.
- 建议动作：Results of a robustness check using a temporally held-out split.
- 作者确认必需：True
- Severity: minor
- Category: editorial_presentation
- Proposed action: AUTHOR_INPUT_NEEDED
- Readiness: needs_author_input
- Risk level: low
- Evidence anchor: section_007
- Missing author input: ['Results of a robustness check using a temporally held-out split.']
- 安全表达：We will report this analysis if completed, or narrow the claim if it cannot be supported.
- 避免表达：Avoid overstating implications beyond the supplied manuscript evidence.

## 3. Reviewer Committee 综合

```json
{
  "prioritized_plan": [
    {
      "action": "Perform and report the requested robustness checks.",
      "priority": "highest",
      "consensus": "All three committee lenses (methodology, claim, tone) identify this as a critical, high-severity risk. The manuscript explicitly states these analyses are not yet done. The reviewer and editor explicitly demand them.",
      "committee_emphasis": {
        "methodology": "Essential to address data leakage and inflated metric risks.",
        "claim": "Required to provide evidence for or against the generalization claim.",
        "tone": "Necessary to avoid unsupported commitment and align with reviewer/editor expectations."
      },
      "specific_subtasks": [
        "Construct a temporally held-out test split using publication year metadata and evaluate ReviewNet and baseline performance.",
        "Perform a sensitivity analysis using a stricter near-duplicate removal method (e.g., MinHash) and report impact on performance gains."
      ]
    },
    {
      "action": "Provide a detailed, transparent account of the data split construction protocol in the Methods section.",
      "priority": "high",
      "consensus": "All three lenses agree this is a major requirement for methodological transparency and reproducibility. The current description is insufficient.",
      "committee_emphasis": {
        "methodology": "Core to experimental design integrity; must detail temporal ordering and cluster isolation.",
        "claim": "Necessary to clarify the scope of the evidence and support claim calibration.",
        "tone": "Directly addresses the reviewer's specific request and demonstrates substantive engagement."
      },
      "specific_subtasks": [
        "Describe the step-by-step split procedure, including ordering criteria (e.g., by publication date).",
        "Explicitly state whether measures were taken to prevent papers from the same journal issue, topic cluster, or review round from appearing in different splits."
      ]
    },
    {
      "action": "Calibrate all claims about generalization in the manuscript (Abstract, Results, Discussion) based on the new evidence.",
      "priority": "high",
      "consensus": "Methodology and claim lenses strongly emphasize this as a high-risk overclaim. Tone lens flags the author's current response as reinforcing the overclaim.",
      "committee_emphasis": {
        "methodology": "Claims must precisely reflect the evaluation scope (e.g., 'within a random split' or 'across temporally held-out reviews').",
        "claim": "The central claim is currently overstated; must be narrowed to match demonstrated evidence.",
        "tone": "Must avoid restating broad generalization prematurely; commit to evidence-based revision."
      },
      "specific_subtasks": [
        "Revise the Abstract to state the conditions of the evaluation clearly.",
        "Update the Results and Discussion to reflect performance on the new robustness checks and discuss limitations.",
        "Remove or qualify any language implying broad generalization across peer-review contexts unless explicitly supported by new analyses."
      ]
    },
    {
      "action": "Revise the author response text to align with the above actions and avoid interactional risks.",
      "priority": "medium",
      "consensus": "Tone lens identifies specific high and medium risks in the draft response. Methodology and claim lenses support the need for a credible, evidence-focused response.",
      "committee_emphasis": {
        "methodology": "Response should commit to providing concrete methodological details and new results.",
        "claim": "Response should not repeat the broad generalization claim; should focus on evidence-based calibration.",
        "tone": "Must remove the overclaim statement, clarify the status of robustness checks, and adopt a substantive, cooperative tone."
      },
      "specific_subtasks": [
        "Remove the line: 'We will also state that our method generalizes across Nature peer-review contexts.'",
        "Clarify whether the robustness checks are planned, in progress, or completed, and summarize key outcomes if available.",
        "Replace defensive justification ('and we believe this avoids leakage') with an acknowledgment of the reviewer's point and a commitment to provide the transparent account.",
        "Anchor gratitude to the substance of the critique (e.g., '...for raising these important points about evaluation design...')."
      ]
    }
  ],
  "preserved_disagreement": {
    "note": "No fundamental disagreement on required actions. Differences are in emphasis and framing.",
    "methodology_vs_claim": "Methodology lens emphasizes the structural integrity of the experimental design as the primary issue. Claim lens frames the same issues as risks to the credibility and scope of the central claim. Both agree on the same corrective actions.",
    "tone_vs_others": "Tone lens uniquely highlights the interactional risks in the author's draft response (overclaim, unsupported commitment), which the other lenses do not explicitly address. However, the recommended actions from methodology and claim lenses inherently mitigate these tone risks if followed."
  }
}
```

## 4. 选择后的回应策略

```json
{
  "core_actions": [
    {
      "action": "Perform and report robustness checks",
      "subtasks": [
        "Construct a temporally held-out test split using publication year metadata and evaluate ReviewNet and baseline performance.",
        "Perform a sensitivity analysis using a stricter near-duplicate removal method (e.g., MinHash) and report impact on performance gains."
      ],
      "evidence_anchor": "section_007, section_008",
      "nature_action_hint": "ACCEPT_ANALYSIS"
    },
    {
      "action": "Provide detailed split construction protocol",
      "subtasks": [
        "Describe step-by-step split procedure, including ordering criteria (e.g., by publication date).",
        "Explicitly state whether measures were taken to prevent papers from same journal issue, topic cluster, or review round from appearing in different splits."
      ],
      "evidence_anchor": "section_004",
      "nature_action_hint": "CLARIFY_EXISTING"
    },
    {
      "action": "Calibrate generalization claims based on new evidence",
      "subtasks": [
        "Revise Abstract to state evaluation conditions clearly.",
        "Update Results and Discussion to reflect performance on new robustness checks.",
        "Remove or qualify language implying broad generalization across peer-review contexts unless explicitly supported."
      ],
      "evidence_anchor": "section_003, section_006, section_007",
      "nature_action_hint": "SOFTEN_CLAIM"
    },
    {
      "action": "Revise author response text",
      "subtasks": [
        "Remove statement about asserting generalization across Nature peer-review contexts.",
        "Clarify status of robustness checks (planned/in progress/completed).",
        "Replace defensive justification with acknowledgment of reviewer's point.",
        "Anchor gratitude to substance of critique."
      ],
      "evidence_anchor": "response_text",
      "nature_action_hint": "ACCEPT_TEXT"
    }
  ],
  "skill_families": [
    "evidence_upgrade",
    "scope_calibration",
    "presentation_repair"
  ],
  "institutional_signals_addressed": [
    "replicability_norm",
    "transparency_norm",
    "editorial_risk_control"
  ]
}
```

## 5. 推荐回应结构

- Thank the reviewer and restate the concern as an evidence/validity issue.
- Address comment_001 by explaining: A transparent description of how train/validation/test splits were constructed, explicitly stating how temporal leakage was avoided and whether papers from the same journal issue, topic cluster, or review round can appear across splits..
- Address comment_002 by explaining: Results of a robustness check using a temporally held-out split..
- Close by distinguishing completed revisions from analyses that require author confirmation.

## 6. 作者必须确认的问题

- Can you confirm the exact composition and size of the 'curated Nature-family corpus' mentioned in the Abstract and Data sections?
- The Methods section preview describes a pipeline. Are there specific model architectures, training procedures, or hyperparameters detailed in the full manuscript?
- The Results mention a 'small model-assisted evaluation' for concern coverage. What was the evaluation protocol and what were the specific results?
- The Limitations section mentions related papers sharing language patterns. Was any analysis done to quantify this potential clustering in the current random split?
- Can you provide the detailed methodology for constructing the data splits to ensure no temporal leakage?
- Can you perform and report the results of an evaluation using a temporally held-out test split?
- Can you perform and report the results of an analysis that removes near-duplicate pairs (beyond exact duplicates) and shows the impact on performance gains?
- Given the results of the above analyses, are you willing to revise the central claim about generalization across peer-review contexts to be more precise?
- Can you perform and report the results of the two specific robustness checks requested by the reviewer: 1) evaluation on a temporally held-out test split, and 2) analysis of performance after stricter near-duplicate removal (e.g., using MinHash)?
- Can you provide the detailed, step-by-step protocol for constructing the train/validation/test splits, including how papers were ordered (e.g., by publication date) and whether any measures were taken to isolate papers from the same journal issue, topic cluster, or review round?
- Based on the outcomes of the new robustness checks, are you prepared to revise the manuscript's claims about generalization? Specifically, will you narrow the claim in the Abstract and Discussion to precisely reflect the conditions under which ReviewNet's improvements are demonstrated?
- Will you revise the draft response text to remove the statement about asserting generalization and instead commit to clarifying the split methodology and presenting the new robustness check results?
- Can you perform and report the results of the two specific robustness checks: 1) evaluation on a temporally held-out test split, and 2) analysis of performance after stricter near-duplicate removal (e.g., using MinHash)?
- Can you provide the detailed, step-by-step protocol for constructing train/validation/test splits, including how papers were ordered and whether measures were taken to isolate papers from same journal issue, topic cluster, or review round?
- Based on the outcomes of the new robustness checks, are you prepared to revise the manuscript's claims about generalization to precisely reflect the conditions under which ReviewNet's improvements are demonstrated?
- Will you revise the draft response text to remove the statement about asserting generalization and instead commit to clarifying the split methodology and presenting new robustness check results?
- A transparent description of how train/validation/test splits were constructed, explicitly stating how temporal leakage was avoided and whether papers from the same journal issue, topic cluster, or review round can appear across splits.
- Results of a robustness check using a temporally held-out split.

## 7. 不安全或不可追溯的 claim

- 暂无由 integrity checker 标记的不可追溯 claim。

## 8. Responsible Use

- assistant_only
- author_must_verify_all_claims
- not_final_rebuttal_text
- no_acceptance_prediction
- no_confidential_upload_recommendation

## 9. Memory Ethics Boundary

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

## 10. Memory Passport

遗忘不是能力损失，而是保护作者主体性的边界。系统保留证据、推理和审计痕迹，但遗忘作者历史决策、策略偏好和最终措辞，避免旧选择在新运行中变成未经确认的承诺。

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

## 11. Irreversible Forgetting Statement

```json
{
  "author_decision": "Forgotten author decisions must not be reconstructed from checkpoints, cache, retrieved cases, prior final reports, or historical run summaries.",
  "strategy_preference": "Forgotten strategy preferences must not become defaults for later runs.",
  "final_wording": "Forgotten final wording must not be reused as submission-ready author expression."
}
```

## 12. Forgetting Ledger

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

## 康德机器运行摘要

- Kant machine enabled: True
- Category registry: <repo-root>\examples\rebuttal_lens_deepseek_full_demo\output_v8_kant_machine_full\kantian_category_registry.json
- Category confirmation threshold: 3
- Category count: 1

### 反思性判断

- Mode: reflective_judgment
- Readiness: decision_deferred
- System may commit for author: False
- Draft id: draft_provide_transparent_account_split_construction
- Draft status: unverified_strategy_prototype
- Author instruction: 请作者判断该新策略雏形是否可用；若确认有效并在多次独立运行中成功使用，再触发范畴生成流程。

## 可普遍化测试

### comment_001
- Universalizable: True
- Decision: defer
- Principle: High-risk scholarly commitments must remain author-confirmed decisions.
- Academic process effect: Academic review becomes more conservative but also more auditable and verifiable.
- Ethical block/defer reason: A high-risk author decision must be renewed by the author instead of automated.
### comment_002
- Universalizable: None
- Decision: warn
- Principle: Recommendations must remain bounded by evidence and author verification.
- Academic process effect: Academic review may benefit, but the author must verify the evidential basis.

## 伦理审计链

### 机械执行
- None / None: None
- None / None: None
- None / None: Executed a configured workflow node under the DAG contract.
- None / None: Executed a configured workflow node under the DAG contract.
- None / None: Executed a configured workflow node under the DAG contract.
- None / None: Executed a configured workflow node under the DAG contract.
- None / None: Executed a configured workflow node under the DAG contract.
- None / None: Executed a configured workflow node under the DAG contract.
- None / None: Executed a configured workflow node under the DAG contract.
- None / None: Executed a configured workflow node under the DAG contract.
- None / None: Executed a configured workflow node under the DAG contract.
- None / None: Executed a configured workflow node under the DAG contract.
- None / None: Executed a configured workflow node under the DAG contract.

### 有机生成
- category_invention_draft: Entered reflective judgment mode because existing categories did not cover the concern.
- response_suggestion_generated: None
- response_suggestion_generated: None

### 主动遗忘
- author_decision: Author agency must be renewed for every run.
- final_wording: The system plans responses; it must not preserve final author expression.
- latent_commitment: The configured memory policy marks this class as non-authoritative for future runs.
- strategy_preference: A past strategy must not become an automatic future answer.
- unsafe_claim: The configured memory policy marks this class as non-authoritative for future runs.

### 作者决策保留
- comment_001: A high-risk author decision must be renewed by the author instead of automated.

### 绝对他律下近乎自律证明

This audit chain is a heteronomous assistance layer: it does not make final author decisions, does not convert memory into author commitments, and blocks or defers suggestions that would depend on deception, concealed limitations, or unconfirmed high-risk author input.
