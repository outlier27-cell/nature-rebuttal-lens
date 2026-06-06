# Nature RebuttalLens 最终作者回应辅助报告

本报告是 assistant 输出，不是可直接提交的最终 rebuttal。所有实验、证据、引用和承诺都必须由作者确认。

## 1. 核心判断

系统识别出 2 个 reviewer concern。其中 0 个 claim 暂时不可追溯或证据不足。建议先补证据和缩窄承诺，再组织 rebuttal 草稿。
Package readiness: decision_deferred

## 2. Reviewer Concern Cards

### comment_001 - experimental_design

- 表层要求：Provide a more transparent account of the split construction, add robustness checks under at least one temporally held-out split, and clarify whether the reported gains remain when near-duplicate review-response pairs are removed.
- 深层风险：The dataset appears to be drawn from multiple Nature-family journals over several years, yet the manuscript does not explain how temporal leakage was avoided when constructing train, validation, and test splits. It is also unclear whether papers from the same journal issue, topic cluster, or review round can appear across different splits.
- 证据状态：partially_supported / section_004
- 证据缺口：The manuscript does not explain how temporal leakage was avoided or whether papers from the same journal issue, topic cluster, or review round can appear across different splits.
- 建议动作：Explanation of how temporal leakage was avoided in split construction
- 作者确认必需：True
- Severity: major
- Category: methodological
- Proposed action: AUTHOR_INPUT_NEEDED
- Readiness: needs_author_input
- Risk level: high
- Evidence anchor: section_004
- Missing author input: ['Explanation of how temporal leakage was avoided in split construction']
- 安全表达：We will report this analysis if completed, or narrow the claim if it cannot be supported.
- 避免表达：Avoid claiming that the concern is fully resolved before evidence is available.

### comment_002 - generalization_scope

- 表层要求：Clarify whether the reported gains remain when near-duplicate review-response pairs are removed.
- 深层风险：Without this, the central claim that the method generalizes across peer-review contexts is overstated.
- 证据状态：missing / none
- 证据缺口：The manuscript does not clarify whether the reported gains remain when near-duplicate review-response pairs are removed beyond exact duplicates.
- 建议动作：Robustness checks under temporally held-out splits
- 作者确认必需：True
- Severity: major
- Category: editorial_presentation
- Proposed action: AUTHOR_INPUT_NEEDED
- Readiness: decision_deferred
- Risk level: high
- Evidence anchor: none
- Missing author input: ['Robustness checks under temporally held-out splits']
- 安全表达：We will report this analysis if completed, or narrow the claim if it cannot be supported.
- 避免表达：Avoid claiming that the concern is fully resolved before evidence is available.

## 3. Reviewer Committee 综合

```json
{
  "priority_actions": [
    {
      "action": "Perform temporal hold-out validation",
      "supporting_committees": [
        "methodology_committee_reviewer",
        "claim_committee_reviewer"
      ],
      "confidence": "high",
      "required_author_confirmation": true
    },
    {
      "action": "Implement and report near-duplicate detection analysis",
      "supporting_committees": [
        "methodology_committee_reviewer",
        "claim_committee_reviewer"
      ],
      "confidence": "high",
      "required_author_confirmation": true
    },
    {
      "action": "Narrow generalization claims in abstract and discussion",
      "supporting_committees": [
        "claim_committee_reviewer",
        "tone_committee_reviewer"
      ],
      "confidence": "high",
      "required_author_confirmation": true
    },
    {
      "action": "Revise response tone to focus on evidence adequacy",
      "supporting_committee": "tone_committee_reviewer",
      "confidence": "medium",
      "required_author_confirmation": true
    }
  ],
  "preserved_disagreements": [],
  "evidence_gaps": [
    {
      "gap": "Temporal split performance metrics",
      "noted_by": [
        "methodology_committee_reviewer",
        "claim_committee_reviewer"
      ],
      "author_action_required": true
    },
    {
      "gap": "Near-duplicate removal impact on metrics",
      "noted_by": [
        "methodology_committee_reviewer",
        "claim_committee_reviewer"
      ],
      "author_action_required": true
    },
    {
      "gap": "Documentation of split procedures",
      "noted_by": "methodology_committee_reviewer",
      "author_action_required": true
    }
  ]
}
```

## 4. 选择后的回应策略

```json
{
  "strategy_family": "acknowledge_and_fix",
  "evidence_anchor": "section_004",
  "overclaim_gate": "Avoid claiming generalization without new evidence",
  "concern_coverage": 0.8,
  "evidence_grounding": 0.7,
  "feasibility": 0.9,
  "overclaim_risk": 0.3,
  "tone_risk": 0.2,
  "provenance_strength": 0.8,
  "reasoning": "This strategy directly addresses the reviewer's concerns by acknowledging the need for methodological clarification and promising concrete changes. It leverages existing manuscript evidence about the split methodology while avoiding overclaiming by not expanding generalization claims without new analyses.",
  "strategy_id": "strategy_001",
  "name": "acknowledge_and_fix",
  "response_position": "acknowledge_and_fix",
  "required_actions": [
    "Avoid claiming generalization without new evidence"
  ],
  "rubric_scores": {
    "concern_coverage": 0.8,
    "evidence_grounding": 0.7,
    "feasibility": 0.9,
    "overclaim_risk": 0.3,
    "tone_risk": 0.2,
    "provenance_strength": 0.8
  },
  "author_confirmation_required": false
}
```

## 5. 推荐回应结构

- Thank the reviewer and restate the concern as an evidence/validity issue.
- Use response position: acknowledge_and_fix.
- Complete or explicitly qualify this planned action: Avoid claiming generalization without new evidence.
- Address comment_001 by explaining: Explanation of how temporal leakage was avoided in split construction.
- Address comment_002 by explaining: Robustness checks under temporally held-out splits.
- Do not overclaim until this missing element is resolved: Specific details on temporal split methodology.
- Do not overclaim until this missing element is resolved: Results from temporal hold-out analysis.
- Do not overclaim until this missing element is resolved: Results from deduplication sensitivity analysis.
- Close by distinguishing completed revisions from analyses that require author confirmation.

## 6. 作者必须确认的问题

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
