# Nature RebuttalLens 最终作者回应辅助报告

本报告是 assistant 输出，不是可直接提交的最终 rebuttal。所有实验、证据、引用和承诺都必须由作者确认。

## 1. 核心判断

系统识别出 2 个 reviewer concern。其中 0 个 claim 暂时不可追溯或证据不足。建议先补证据和缩窄承诺，再组织 rebuttal 草稿。
Package readiness: decision_deferred

## 2. Reviewer Concern Cards

### comment_001 - experimental_design

- 表层要求：Provide a more transparent account of the split construction, add robustness checks under at least one temporally held-out split, and clarify whether the reported gains remain when near-duplicate review-response pairs are removed.
- 深层风险：The manuscript does not explain how temporal leakage was avoided when constructing train, validation, and test splits. It is also unclear whether papers from the same journal issue, topic cluster, or review round can appear across different splits.
- 证据状态：partially_supported / section_004
- 证据缺口：The manuscript does not explain how temporal leakage was avoided, nor does it clarify if papers from the same journal issue, topic cluster, or review round can appear across splits. It explicitly states a temporal split experiment has not been reported.
- 建议动作：Clarification in the 'Data' or 'Methods' section on how the split construction prevents temporal leakage and cross-contamination of related papers (e.g., from same journal issue, topic cluster, or review round).
- 作者确认必需：True
- Severity: major
- Category: methodological
- Proposed action: AUTHOR_INPUT_NEEDED
- Readiness: decision_deferred
- Risk level: high
- Evidence anchor: section_004
- Missing author input: ["Clarification in the 'Data' or 'Methods' section on how the split construction prevents temporal leakage and cross-contamination of related papers (e.g., from same journal issue, topic cluster, or review round)."]
- 安全表达：We will report this analysis if completed, or narrow the claim if it cannot be supported.
- 避免表达：Avoid claiming that the concern is fully resolved before evidence is available.

### comment_002 - generalization_scope

- 表层要求：Clarify whether the reported gains remain when near-duplicate review-response pairs are removed. Without this, the central claim that the method generalizes across peer-review contexts is overstated.
- 深层风险：The central claim that the method generalizes across peer-review contexts is overstated.
- 证据状态：supported / section_006
- 证据缺口：The manuscript does not report whether gains remain under a temporal split or after stricter near-duplicate removal. It explicitly states these analyses are planned but not completed.
- 建议动作：Report of robustness checks (e.g., performance metrics) under at least one temporally held-out split.
- 作者确认必需：True
- Severity: minor
- Category: editorial_presentation
- Proposed action: AUTHOR_INPUT_NEEDED
- Readiness: needs_author_input
- Risk level: low
- Evidence anchor: section_006
- Missing author input: ['Report of robustness checks (e.g., performance metrics) under at least one temporally held-out split.']
- 安全表达：We will report this analysis if completed, or narrow the claim if it cannot be supported.
- 避免表达：Avoid overstating implications beyond the supplied manuscript evidence.

## 3. Reviewer Committee 综合

```json
{
  "prioritized_plan": [
    {
      "action": "Perform and report the requested robustness checks.",
      "priority": "highest",
      "committee_emphasis": {
        "methodology": "Essential to address the core methodological concern about evaluation validity. The manuscript explicitly states these analyses are planned but not completed.",
        "claim_calibration": "Required to generate evidence for recalibrating the generalization claim. Without these results, claim narrowing is based on absence of evidence, not new evidence.",
        "tone": "Critical to demonstrate substantive engagement with the reviewer's request for new evidence, moving beyond clarification."
      },
      "specific_subtasks": [
        "Construct a temporally held-out test split using publication year metadata and evaluate model performance (e.g., macro-F1).",
        "Apply a stricter near-duplicate removal step (e.g., MinHash or embedding similarity) to the dataset and re-evaluate performance gains."
      ],
      "manuscript_locations": [
        "New subsection in 'Results' reporting these analyses.",
        "Potential new figure/table in main text or supplement."
      ]
    },
    {
      "action": "Revise the central claim about generalization to accurately reflect the scope of current evidence.",
      "priority": "high",
      "committee_emphasis": {
        "claim_calibration": "Primary risk is overclaiming. Claims must be narrowed to match the evidence from the random split and explicitly incorporate limitations.",
        "tone": "Directly addresses the reviewer's concern about 'evidence adequacy and possible overclaiming.' Shows understanding and corrective action.",
        "methodology": "Aligns claims with the methodological scope of the evaluation performed."
      },
      "specific_subtasks": [
        "Revise abstract to qualify generalization claim (e.g., specify 'on a random split of a Nature-family corpus').",
        "Revise results and discussion to condition claims on the current evaluation design and acknowledge the need for temporal validation.",
        "Incorporate results of new robustness checks (from Action 1) into the claim language once available."
      ],
      "manuscript_locations": [
        "Abstract",
        "Results section",
        "Discussion section"
      ]
    },
    {
      "action": "Clarify the split construction methodology in the 'Data' or 'Methods' section.",
      "priority": "high",
      "committee_emphasis": {
        "methodology": "Addresses the request for a 'more transparent account.' Must explain procedures to prevent temporal leakage and cross-contamination of related papers.",
        "claim_calibration": "Provides the methodological foundation for interpreting the scope of the results.",
        "tone": "Demonstrates responsiveness to the reviewer's request for clarity, but must be paired with Action 1 to avoid appearing dismissive."
      },
      "specific_subtasks": [
        "Explicitly state whether any measures were taken to prevent papers from the same journal issue, topic cluster, or review round from appearing across different splits.",
        "If no specific measures were taken, state this clearly and discuss it as a limitation.",
        "Detail the exact process of the random paper-level split (e.g., stratification, seed)."
      ],
      "manuscript_locations": [
        "Data section",
        "Methods section",
        "Limitations section (if applicable)"
      ]
    },
    {
      "action": "Expand the limitations discussion to explicitly address the current study's constraints regarding split design and validation.",
      "priority": "medium",
      "committee_emphasis": {
        "claim_calibration": "Formally documents the boundaries of the evidence, supporting the narrowed claims.",
        "methodology": "Acknowledges methodological choices and their implications for interpretation.",
        "tone": "Shows scholarly rigor and self-awareness, building credibility."
      },
      "specific_subtasks": [
        "Explicitly state that the reported performance is based on a random split and that robustness under temporal hold-out is not yet quantified.",
        "Discuss the potential for topical clustering across splits and its possible impact.",
        "Note the use of exact duplicate removal and the need for analysis of near-duplicates."
      ],
      "manuscript_locations": [
        "Limitations section"
      ]
    }
  ],
  "preserved_disagreement": {
    "note": "No fundamental disagreement on required actions. Emphasis differs:",
    "methodology_emphasis": "Stresses the necessity of performing the new analyses as the primary corrective action to fix the evaluation design.",
    "claim_calibration_emphasis": "Stresses the immediate need to narrow claims based on existing evidence, regardless of new analysis results, to correct overstatement.",
    "tone_emphasis": "Stresses the need to rewrite the response to explicitly acknowledge the reviewer's framing and commit concretely to new work, avoiding a dismissive or vague tone."
  },
  "consensus": "All committees agree the reviewer's concern is major and valid. The current manuscript evidence is insufficient to support the broad generalization claim. The author must provide new evidence (robustness checks) and revise claims accordingly. The current draft response is inadequate and must be made more concrete and evidence-committal."
}
```

## 4. 选择后的回应策略

```json
{
  "core_actions": [
    {
      "action": "Perform and report the requested robustness checks.",
      "priority": "highest",
      "details": "Construct a temporally held-out test split using publication year metadata and evaluate model performance (e.g., macro-F1). Apply a stricter near-duplicate removal step (e.g., MinHash or embedding similarity) to the dataset and re-evaluate performance gains. Report results in a new 'Results' subsection and/or supplementary figure/table.",
      "nature_action_hint": "ACCEPT_ANALYSIS",
      "readiness_state": "needs_author_input"
    },
    {
      "action": "Revise the central claim about generalization to accurately reflect the scope of current evidence.",
      "priority": "high",
      "details": "Revise abstract to qualify generalization claim (e.g., specify 'on a random split of a Nature-family corpus'). Revise results and discussion to condition claims on the current evaluation design and acknowledge the need for temporal validation. Incorporate results of new robustness checks into the claim language once available.",
      "nature_action_hint": "SOFTEN_CLAIM",
      "readiness_state": "draft_with_placeholders"
    },
    {
      "action": "Clarify the split construction methodology in the 'Data' or 'Methods' section.",
      "priority": "high",
      "details": "Explicitly state whether any measures were taken to prevent papers from the same journal issue, topic cluster, or review round from appearing across different splits. If no specific measures were taken, state this clearly and discuss it as a limitation. Detail the exact process of the random paper-level split (e.g., stratification, seed).",
      "nature_action_hint": "CLARIFY_EXISTING",
      "readiness_state": "draft_with_placeholders"
    },
    {
      "action": "Expand the limitations discussion to explicitly address the current study's constraints regarding split design and validation.",
      "priority": "medium",
      "details": "Explicitly state that the reported performance is based on a random split and that robustness under temporal hold-out is not yet quantified. Discuss the potential for topical clustering across splits and its possible impact. Note the use of exact duplicate removal and the need for analysis of near-duplicates.",
      "nature_action_hint": "CLARIFY_EXISTING",
      "readiness_state": "draft_with_placeholders"
    }
  ],
  "response_tone": "cooperative, evidence-focused, and explicitly acknowledges the reviewer's framing of 'evidence adequacy and possible overclaiming.'",
  "commitment_level": "promised_change",
  "risk_mitigation": "Avoids restating the broad generalization claim in the response. Conditions all promised changes on the completion of new analyses. Explicitly maps each action to the reviewer's specific request."
}
```

## 5. 推荐回应结构

- Thank the reviewer and restate the concern as an evidence/validity issue.
- Address comment_001 by explaining: Clarification in the 'Data' or 'Methods' section on how the split construction prevents temporal leakage and cross-contamination of related papers (e.g., from same journal issue, topic cluster, or review round)..
- Address comment_002 by explaining: Report of robustness checks (e.g., performance metrics) under at least one temporally held-out split..
- Close by distinguishing completed revisions from analyses that require author confirmation.

## 6. 作者必须确认的问题

- Does the full manuscript contain any additional details in the 'Data' section regarding the prevention of temporal leakage or the handling of related papers (e.g., from same issue or topic cluster) during split construction?
- Are the reported performance metrics (e.g., macro-F1 of 0.62) explicitly qualified as being based solely on the random split, as indicated in the preview?
- Does the full manuscript contain any completed analysis on near-duplicate removal using methods like MinHash or embedding similarity?
- Have you performed the requested temporal split experiment? If so, what are the results?
- Have you performed the requested near-duplicate removal sensitivity analysis? If so, what are the results?
- Have you performed, or can you commit to performing, the two specific robustness checks requested by the reviewer: (1) evaluation on a temporally held-out test split, and (2) evaluation after applying stricter near-duplicate removal (e.g., using MinHash or embedding similarity)?
- What are the specific, concrete details you will add to the 'Data' or 'Methods' section to explain how your split construction prevents (or does not prevent) temporal leakage and the cross-contamination of papers from the same journal issue, topic cluster, or review round?
- Given the reviewer's concern about overclaiming, what specific revised wording do you propose for the central generalization claim in the abstract? (e.g., will you specify 'on a random split' or condition the claim on future validation?)
- Does the full manuscript contain any completed analysis on temporal splits or near-duplicate removal beyond what is stated in the provided excerpts (sections 006-008)?
- Given the reviewer's concern about overclaiming, what specific revised wording do you propose for the central generalization claim in the abstract? (e.g., will you specify 'on a random split' or condition the claim on the results of the new analyses?)
- Clarification in the 'Data' or 'Methods' section on how the split construction prevents temporal leakage and cross-contamination of related papers (e.g., from same journal issue, topic cluster, or review round).
- Report of robustness checks (e.g., performance metrics) under at least one temporally held-out split.

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
- Category registry: <repo-root>\examples\rebuttal_lens_deepseek_full_demo\output_v9_kant_phase2_full\kantian_category_registry.json
- Category confirmation threshold: 3
- Category count: 1

### 反思性判断

- Mode: reflective_judgment
- Readiness: decision_deferred
- System may commit for author: False
- Draft id: draft_provide_more_transparent_account_split
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

## 14. 计算域自我立法

```json
{
  "enabled": true,
  "maxims": [
    {
      "maxim_id": "evidence_before_persuasion",
      "maxim_zh": "回应辅助必须先尊重证据边界，再追求说服效果。",
      "forbidden": "把缺失证据包装成已经完成的修订。"
    },
    {
      "maxim_id": "author_decision_boundary",
      "maxim_zh": "系统不能替作者承诺实验、引用、修改或最终立场。",
      "forbidden": "把作者尚未确认的行动写成既成事实。"
    },
    {
      "maxim_id": "category_generation_humility",
      "maxim_zh": "新范畴只能作为未验证雏形出现，必须等待独立确认。",
      "forbidden": "把一次运行生成的范畴立即当作普遍规则。"
    },
    {
      "maxim_id": "forgetting_preserves_agency",
      "maxim_zh": "遗忘不是能力损失，而是防止旧承诺支配新判断。",
      "forbidden": "把历史偏好、旧策略或旧作者决定自动带入新运行。"
    }
  ],
  "system_may_commit_for_author": false,
  "author_confirmation_required_for": [
    "Clarification in the 'Data' or 'Methods' section on how the split construction prevents temporal leakage and cross-contamination of related papers (e.g., from same journal issue, topic cluster, or review round).",
    "Report of robustness checks (e.g., performance metrics) under at least one temporally held-out split.",
    "Report of performance metrics after removing near-duplicate review-response pairs (beyond exact duplicates, e.g., using MinHash or embedding similarity).",
    "Revision of the central claim about generalization across peer-review contexts in the abstract, results, and discussion to reflect the current evidence (random split only) and the limitations identified.",
    "Addition of a limitation in the discussion regarding the use of a random split, the potential for topical clustering, and the absence of temporal validation in the current study."
  ]
}
```

## 15. 不可知边界

```json
{
  "enabled": true,
  "boundaries": [
    {
      "boundary_type": "future_editorial_outcome",
      "description_zh": "系统不能预测接收、拒稿、编辑态度或审稿人最终满意度。",
      "status": "triggered"
    },
    {
      "boundary_type": "reviewer_inner_motive",
      "description_zh": "系统不能知道 reviewer 的真实心理动机，只能处理文本中可见的 concern。",
      "status": "standing_boundary"
    },
    {
      "boundary_type": "unperformed_analysis",
      "description_zh": "系统不能把尚未完成的实验、分析或引用验证写成已经完成。",
      "status": "standing_boundary"
    },
    {
      "boundary_type": "author_capacity",
      "description_zh": "系统不能判断作者是否一定有时间、数据或权限完成某项补充工作。",
      "status": "standing_boundary"
    },
    {
      "boundary_type": "confidential_or_private_fact",
      "description_zh": "系统不能臆测未提供的私密审稿材料、编辑通信或保密数据。",
      "status": "standing_boundary"
    }
  ],
  "blocked_inferences": [
    {
      "boundary_type": "future_editorial_outcome",
      "matched_patterns": [
        "\\bwill\\s+be\\s+accepted\\b",
        "\\bsatisfy\\s+the\\s+reviewer\\b"
      ],
      "reason_zh": "系统不能预测接收、拒稿、编辑态度或审稿人最终满意度。"
    }
  ],
  "author_questions": [
    "系统不能预测接收结果；请作者只确认可执行修改和真实证据。"
  ]
}
```

## 16. 黑箱透明化摘要

本次运行承认作者、reviewer 与 AI 都存在黑箱边界；系统只依据已提供文本、证据定位、committee 输出和审计 gate 生成辅助判断。对无法知道的未来结果、他人真实动机和作者未确认行动，系统以 defer 或 author input 形式显式保留。

```json
{
  "enabled": true,
  "summary_zh": "本次运行承认作者、reviewer 与 AI 都存在黑箱边界；系统只依据已提供文本、证据定位、committee 输出和审计 gate 生成辅助判断。对无法知道的未来结果、他人真实动机和作者未确认行动，系统以 defer 或 author input 形式显式保留。",
  "evidence_inputs": [
    "reviewer_understanding_agent",
    "manuscript_evidence_locator",
    "evidence_action_planner",
    "committee_meta_reviewer",
    "strategy_meta_planner",
    "integrity_adequacy_checker"
  ],
  "deferred_decisions": [
    "comment_001"
  ],
  "category_generation_events": [
    {
      "draft_id": "draft_provide_more_transparent_account_split",
      "status": "unverified_strategy_prototype",
      "requires_independent_confirmation": true
    }
  ],
  "memory_boundary_events": [
    {
      "retained": [],
      "forgotten": []
    }
  ]
}
```

## 17. 有机性评估

```json
{
  "enabled": true,
  "score": 1.0,
  "checks": [
    {
      "check_id": "grounded_in_evidence_gap",
      "passed": true,
      "reason_zh": "新范畴必须来自真实 evidence gap，而不是凭空发明。"
    },
    {
      "check_id": "author_confirmable",
      "passed": true,
      "reason_zh": "新范畴必须等待作者或独立运行确认。"
    },
    {
      "check_id": "forgetting_safe",
      "passed": true,
      "reason_zh": "派生范畴必须允许遗忘，避免一次运行支配后续判断。"
    },
    {
      "check_id": "non_deceptive_universalization",
      "passed": true,
      "reason_zh": "有机生成不能以削弱真实性为代价。"
    },
    {
      "check_id": "deferred_until_validated",
      "passed": true,
      "reason_zh": "未验证范畴不能直接变成最终回应承诺。"
    }
  ]
}
```

## 18. 机械-经验-范畴三层认知循环

```json
{
  "mechanical_layer": [
    "dag_or_layered_workflow",
    "response_package_schema",
    "universalization_gate"
  ],
  "empirical_layer": [
    "reviewer_understanding_agent",
    "manuscript_evidence_locator",
    "evidence_action_planner",
    "committee_meta_reviewer",
    "strategy_meta_planner"
  ],
  "category_layer": [
    "reflective_judgment",
    "computational_self_legislation",
    "unknowability_boundary",
    "blackbox_transparency",
    "organic_quality"
  ]
}
```
