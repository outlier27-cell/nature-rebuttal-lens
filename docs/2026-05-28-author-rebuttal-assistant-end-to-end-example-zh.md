# Author Rebuttal Assistant 端到端输入输出详解示例

更新时间：2026-05-28
适用项目：NatureReview-Interact / Agnes Author Rebuttal Assistant
目标读者：第一次接触本项目的人、准备开源介绍的人、后续准备封装 demo/API 的开发者

## 0. 先说清楚：这个系统现在到底是什么

当前系统不是“输入一句审稿意见，直接生成一封最终 rebuttal”的工具。

它现在是一个基于 Nature 系列公开同行评审互动案例的、可追溯、可评估、非训练版 Author Rebuttal Assistant workflow。它的核心价值不是简单检索，也不是普通聊天模型代写，而是把审稿互动拆成一组可检查的中间判断：

```text
审稿意见
  -> 显性 concern
  -> 隐性风险 / tacit concern
  -> 期刊和共同体制度信号
  -> 历史 Nature 案例类比
  -> 证据动作计划
  -> 作者回应姿态
  -> 语气与承诺强度
  -> 完整性 / 过度承诺检查
  -> 可审查的 rebuttal plan
```

当前 v0.1 的主要实现形式是“批处理构建 artifacts”：

```powershell
$env:PYTHONPATH='src'; python -m peer_review_skills.cli.main build-naturereview-v01
```

这个命令会从现有 v2709 数据和 API-assisted seed review 结果中构建：

- review interaction knowledge base
- retrieval predictions
- workflow traces
- simulation traces
- validation report

也就是说，现在还没有一个正式的实时 Web API，比如 `/assist-rebuttal`。但内部的数据结构和函数已经足够清晰，后续封装单条输入服务时，本质上就是把下面这个流程从批处理改成单条调用。

## 1. 一个完整的假设输入

假设作者收到 Nature Communications 的一条审稿意见：

```text
Reviewer #2:

The manuscript proposes a machine-learning model for early sepsis prediction.
The reported AUROC is promising, but the comparison is limited to logistic regression
and does not include recent transformer-based or temporal deep learning baselines.
It is also unclear whether the model generalizes beyond the single hospital cohort.
The authors should provide stronger baseline comparisons and external validation,
or substantially narrow the claims.
```

作者希望系统帮忙判断：

1. 这个 reviewer 真正在担心什么？
2. 我应该补实验、补分析、改语气，还是收窄 claim？
3. 历史 Nature 审稿互动里类似问题一般怎么回应？
4. 我能不能直接写“we have addressed this concern”？
5. 最后 rebuttal 应该怎么组织？

如果未来封装成单条服务，用户输入可以长这样：

```json
{
  "paper_context": {
    "journal": "Nature Communications",
    "field": "clinical machine learning",
    "claim_summary": "A machine-learning model predicts early sepsis risk from EHR time series.",
    "available_artifacts": [
      "internal validation on one hospital cohort",
      "AUROC table",
      "model description",
      "supplementary methods"
    ]
  },
  "reviewer_comment": "The manuscript proposes a machine-learning model for early sepsis prediction. The reported AUROC is promising, but the comparison is limited to logistic regression and does not include recent transformer-based or temporal deep learning baselines. It is also unclear whether the model generalizes beyond the single hospital cohort. The authors should provide stronger baseline comparisons and external validation, or substantially narrow the claims.",
  "author_draft_response": "",
  "author_constraints": {
    "can_run_new_external_validation": true,
    "can_add_new_baseline_comparison": true,
    "cannot_collect_new_patient_data": true,
    "needs_conservative_claim_boundary": true
  }
}
```

注意：当前代码里这个“单条 JSON 输入接口”还没有正式封装。现在已有的是批处理构建路径。这个 JSON 是为了说明后续产品化时，单条输入应该如何进入同一套内部结构。

## 2. 第一步：把原始输入转成 ReviewInteractionUnit

系统内部不会直接把原始文本交给最后的输出模块。它会先把输入转成一个标准数据单元。

对应 schema 文件：

```text
data/processed/schemas/review_interaction_unit.schema.json
```

核心字段包括：

```json
{
  "unit_id": "demo_unit_0001",
  "paper_id": "demo_sepsis_prediction_paper",
  "journal": "Nature Communications",
  "review_text": "...reviewer comment...",
  "response_text": "",
  "concern_type": "baseline_comparison",
  "risk_type": "comparative_validity",
  "tacit_concern": "community_standard_fit",
  "institutional_signal": "community_norm_expectation",
  "response_strategy": "add_new_analysis",
  "evidence_action": "new_baseline_or_comparison",
  "author_positioning": "accept_and_revise",
  "tone_commitment": {
    "tone": "cooperative",
    "commitment_level": "promised_change",
    "risk_flags": ["none"]
  },
  "actor_links": [
    {
      "actor_type": "reviewer",
      "evidence": "asks for stronger baseline comparisons and external validation",
      "role_in_interaction": "raises concern"
    },
    {
      "actor_type": "benchmark",
      "evidence": "recent transformer-based or temporal deep learning baselines",
      "role_in_interaction": "comparison object"
    },
    {
      "actor_type": "dataset",
      "evidence": "single hospital cohort / external validation",
      "role_in_interaction": "generalization evidence carrier"
    }
  ],
  "label_source": "model_assisted",
  "provenance": {
    "source_file": "user_input_or_future_api_request",
    "source_hash": "hash_of_input_payload",
    "offset_recoverable": true,
    "url": null
  }
}
```

在当前 v0.1 中，类似的 model-assisted 字段来自 DeepSeek API 对 seed review 的复核和合并。

相关代码位置：

```text
src/peer_review_skills/execution/build_naturereview_v01.py
  - _run_naturereview_seed_api_review()
  - _merge_seed_api_review_result()
  - _build_interaction_units()
```

这里最关键的不是“给文本贴一个标签”，而是把 reviewer comment 转成多个维度：

| 维度 | 示例值 | 含义 |
|---|---|---|
| concern_type | `baseline_comparison` | 显性问题：baseline 不够强 |
| risk_type | `comparative_validity` | 科学风险：结果是否真的优于已有方法 |
| tacit_concern | `community_standard_fit` | 隐性知识：该领域默认期待强 baseline |
| institutional_signal | `community_norm_expectation` | 制度信号：共同体标准和期刊门槛 |
| evidence_action | `new_baseline_or_comparison` | 推荐证据动作：补 baseline / comparison |
| author_positioning | `accept_and_revise` | 作者姿态：承认问题并修订 |
| tone_commitment | cooperative + promised_change | 语气合作，承诺必须可验证 |

## 3. 第二步：进入 Nature 审稿互动知识库

当前知识库位置：

```text
data/processed/review_interaction_kb/v1/
```

主要文件：

```text
interaction_units.jsonl
case_index.jsonl
actor_network_cases.jsonl
kb_summary.json
```

其中 `interaction_units.jsonl` 是系统最核心的案例单元。每个 unit 都是一个 reviewer concern 和 author response 的互动片段，并带有：

- concern type
- response strategy
- evidence action
- tacit concern
- institutional signal
- actor links
- provenance

当新输入进来时，系统会把它作为 query unit，去已有 Nature 案例中找相似互动案例。

相关代码位置：

```text
src/peer_review_skills/execution/build_naturereview_v01.py
  - _build_case_index()
  - _build_actor_network_cases()
  - _build_retrieval_v2()
```

## 4. 第三步：Case Retrieval Agent 找相似案例

对这个输入来说，系统会优先找这些类型的历史案例：

```text
concern_type 相同：
  baseline_comparison

risk_type 相近：
  comparative_validity / generalization risk

institutional_signal 相近：
  community_norm_expectation / transparency_norm / replicability_norm

actor_links 相近：
  benchmark / dataset / method / reviewer / author

provenance 完整：
  能回溯到原始 Nature 公开审稿文件
```

当前代码里的检索逻辑在：

```text
src/peer_review_skills/execution/build_naturereview_v01.py
  - _build_retrieval_v2()
```

该函数会对候选案例打分。重要的是：它不把目标答案里的 `response_strategy` 当成排序依据，因为那会造成 evaluation leakage。它主要使用：

- concern_type
- risk_type
- institutional_signal
- actor_links
- provenance
- model-supported evidence_action availability

一个可能的 retrieval output 长这样：

```json
{
  "query_unit_id": "demo_unit_0001",
  "method": "case_metadata_interdisciplinary_rerank_v3",
  "query_concern_type": "baseline_comparison",
  "query_strategy_label_used_for_ranking": false,
  "top_k": [
    {
      "unit_id": "riu_v1_example_101",
      "paper_id": "nature_case_a",
      "concern_type": "baseline_comparison",
      "institutional_signal": "community_norm_expectation",
      "response_strategy": "add_new_analysis",
      "evidence_action": "new_baseline_or_comparison"
    },
    {
      "unit_id": "riu_v1_example_102",
      "paper_id": "nature_case_b",
      "concern_type": "generalization_scope",
      "institutional_signal": "replicability_norm",
      "response_strategy": "add_new_analysis",
      "evidence_action": "new_analysis"
    },
    {
      "unit_id": "riu_v1_example_103",
      "paper_id": "nature_case_c",
      "concern_type": "baseline_comparison",
      "institutional_signal": "community_norm_expectation",
      "response_strategy": "narrow_claim_scope",
      "evidence_action": "claim_narrowing"
    }
  ]
}
```

这里的 `riu_v1_example_xxx` 是说明性 ID，不是当前数据里的真实 trace。真实运行时会是实际的 `riu_v1_...`。

## 5. 第四步：Case Explanation 解释为什么这些案例相关

系统不会只返回“找到了几个相似案例”。它会解释每个案例为什么相关，以及哪些部分可以迁移。

相关代码位置：

```text
src/peer_review_skills/execution/build_naturereview_v01.py
  - _case_explanation()
```

示例输出：

```json
{
  "unit_id": "riu_v1_example_101",
  "paper_id": "nature_case_a",
  "why_relevant": "Retrieved as a Nature case analogy because it shares concern=baseline_comparison and shares institutional_signal=community_norm_expectation and shares risk_type=comparative_validity with the query.",
  "matched_signals": {
    "concern_type": "baseline_comparison",
    "institutional_signal": "community_norm_expectation",
    "risk_type": "comparative_validity",
    "actor_types": ["reviewer", "author", "benchmark", "dataset"],
    "case_metadata_basis": [
      "concern_type",
      "risk_type",
      "institutional_signal",
      "actor_links",
      "provenance"
    ]
  },
  "transferable_pattern": {
    "concern": "baseline_comparison",
    "risk": "comparative_validity",
    "strategy": "add_new_analysis",
    "evidence_action": "new_baseline_or_comparison",
    "author_positioning": "accept_and_revise",
    "tone_commitment": {
      "tone": "cooperative",
      "commitment_level": "completed_change",
      "risk_flags": ["none"]
    },
    "label_source": "model_assisted"
  },
  "provenance": {
    "source_file": "scraped_data/.../nature_case_a.json",
    "source_hash": "case_hash",
    "offset_recoverable": true
  }
}
```

这一步的意义是：系统不是给一个抽象建议“你应该补实验”，而是说：

```text
历史 Nature 案例里，类似 baseline concern 通常不是靠礼貌回应解决，
而是通过新增 baseline/comparison、补充分析或收窄 claim 来处理。
```

## 6. 第五步：构建 Workflow Trace

相关代码位置：

```text
src/peer_review_skills/execution/build_naturereview_v01.py
  - _build_workflow_traces()
  - _agent_intermediate_outputs()
```

这一步把 query unit、retrieved cases 和所有 agent 中间结果合成一个完整 trace。

trace 顶层结构大致是：

```json
{
  "trace_id": "workflow_demo_0001",
  "query_unit_id": "demo_unit_0001",
  "input_review_text": "...reviewer comment...",
  "agent_intermediate_outputs": {},
  "cross_disciplinary_lens_map": {},
  "case_explanations": [],
  "cognitive_trace": {},
  "case_selection_basis": {},
  "retrieved_case_ids": [],
  "outline": [],
  "integrity_checks": [],
  "provenance": [],
  "errors": []
}
```

其中真正重要的是 `agent_intermediate_outputs` 和 `cognitive_trace`。

## 7. 第六步：各 Agent 内部如何工作

### 7.1 Review Understanding Agent

输入：

```text
reviewer_comment
model-assisted concern labels
observable text evidence
```

输出：

```json
{
  "concern_map": [
    {
      "concern_type": "baseline_comparison",
      "surface_request": "The comparison is limited to logistic regression and does not include recent transformer-based or temporal deep learning baselines...",
      "implicit_risk": "community_standard_fit / comparative_validity based on observable text only.",
      "text_evidence": "does not include recent transformer-based or temporal deep learning baselines",
      "label_source": "model_assisted"
    }
  ]
}
```

它做的事情：

```text
把 reviewer 的表面要求转成可追踪 concern。
```

在这个例子里，显性 concern 是：

```text
baseline_comparison
```

但它同时保留原文证据，避免变成不可追溯的抽象判断。

### 7.2 Tacit Concern Interpreter

输入：

```text
concern_type
risk_type
tacit_concern
review_text
```

输出：

```json
{
  "risk_interpretation": [
    {
      "risk_type": "comparative_validity",
      "tacit_concern": "community_standard_fit",
      "boundary": "Observable textual trace only; not a claim about reviewer psychology."
    }
  ]
}
```

它做的事情：

```text
识别 reviewer 没有明说但在学术共同体里非常重要的默会关切。
```

在这个例子里，reviewer 真正担心的可能是：

```text
你的模型看起来 AUROC 不错，但如果只和 logistic regression 比，
就不能证明它达到当前领域标准。
```

系统会把这个解释写成“可观察文本上的风险假设”，而不是声称自己知道 reviewer 的真实心理。

### 7.3 Institutional Signal Interpreter

输入：

```text
journal
concern_type
tacit_concern
institutional_signal
```

输出：

```json
{
  "institutional_signal_note": [
    {
      "institutional_signal": "community_norm_expectation",
      "action_link": "Translate institutional signal into evidence and positioning choices without predicting acceptance."
    }
  ]
}
```

它做的事情：

```text
把期刊和共同体标准转成作者可以回应的具体问题。
```

在这个例子里，制度信号是：

```text
Nature Communications 语境下，临床机器学习模型不能只展示一个不错的 AUROC；
它需要和强 baseline 比较，还需要说明泛化能力。
```

### 7.4 Case Retrieval Agent

输入：

```text
query unit
case_index
actor_network_cases
```

输出：

```json
{
  "retrieved_case_ids": [
    "riu_v1_example_101",
    "riu_v1_example_102",
    "riu_v1_example_103"
  ],
  "case_selection_basis": {
    "method": "case_metadata_interdisciplinary_rerank_v3",
    "advice_boundary": "model-assisted labels, controlled Nature case metadata, provenance-linked case analogies, cross-disciplinary traces, and author-confirmation gates"
  }
}
```

它做的事情：

```text
找出历史 Nature 案例里类似的 reviewer-author 互动。
```

这些案例不是答案库，不是模板库，也不是可复制文本，而是“策略类比”。

### 7.5 Evidence Planner

相关代码位置：

```text
src/peer_review_skills/execution/build_naturereview_v01.py
  - _resolve_evidence_action()
  - _build_evidence_action_plan()
  - _required_artifact_for_action()
  - _author_confirmation_questions()
```

输入：

```text
query unit 的 evidence_action
retrieved cases 的 transferable_pattern
author constraints
```

输出：

```json
{
  "evidence_action_plan": [
    {
      "action_type": "new_baseline_or_comparison",
      "evidence_action": "new_baseline_or_comparison",
      "required_artifact": "additional baseline or comparative result verified by the author",
      "feasibility": "needs_author_confirmation",
      "author_must_confirm": true,
      "linked_concern_type": "baseline_comparison",
      "retrieved_case_patterns": [
        "new_baseline_or_comparison",
        "new_analysis",
        "claim_narrowing"
      ],
      "decision_basis": {
        "action_type": "new_baseline_or_comparison",
        "basis_type": "model_assisted_unit_label",
        "supporting_case_ids": [],
        "support_count": 1,
        "requires_author_confirmation": true
      },
      "overclaim_risk": [
        "fabricated_evidence_if_author_cannot_verify_artifact"
      ],
      "no_fabrication_boundary": "Do not invent experiments, data, citations, or commitments."
    }
  ],
  "author_confirmation_questions": [
    "Can the author verify that the proposed artifact exists or can be added: additional baseline or comparative result verified by the author?",
    "Where should the response cite the manuscript change for concern_type=baseline_comparison?",
    "Does the author need to narrow the claim if new_baseline_or_comparison cannot be completed?"
  ]
}
```

这里非常关键。

系统不会直接说：

```text
你已经补了 transformer baseline。
```

它只能说：

```text
建议证据动作是 new_baseline_or_comparison；
但作者必须确认是否真的能补、已经补到哪里、能否引用具体表格或 supplement。
```

### 7.6 Author Positioning Agent

输入：

```text
concern_type
institutional_signal
available evidence action
historical cases
```

输出：

```json
{
  "author_positioning": [
    {
      "position": "accept_and_revise",
      "stance_boundary": "Offer options for author judgment; do not force concession."
    }
  ]
}
```

它做的事情：

```text
决定作者应该用什么姿态回应。
```

这个例子里，比较合理的姿态是：

```text
承认 reviewer 的 baseline concern 是合理的，并说明作者会补充比较；
如果外部验证有限，则同时收窄 claim。
```

不是：

```text
强硬反驳 reviewer。
```

也不是：

```text
无条件说 reviewer 完全正确，然后做无法完成的承诺。
```

### 7.7 Tone and Commitment Calibrator

输入：

```text
author_positioning
evidence_action
author constraints
tone_commitment label
```

输出：

```json
{
  "tone_commitment_warnings": [
    {
      "tone": "cooperative",
      "commitment_level": "promised_change",
      "risk_flags": ["none"]
    }
  ]
}
```

它做的事情：

```text
控制语气、承诺强度和不确定性。
```

在这个例子里，推荐语气是：

```text
cooperative
```

承诺强度是：

```text
promised_change
```

但如果作者已经完成了新 baseline 和 external validation，承诺强度可以变成：

```text
completed_change
```

如果作者不能做外部验证，则系统应该建议：

```text
不要承诺 external validation；
改成 claim_narrowing 或 limitation_discussion。
```

### 7.8 Actor Network Mapper

输入：

```text
reviewer comment
actor_links
retrieved cases
```

输出：

```json
{
  "actor_network_note": [
    {
      "actor_type": "reviewer",
      "evidence": "asks for stronger baseline comparisons and external validation",
      "role_in_interaction": "raises concern"
    },
    {
      "actor_type": "benchmark",
      "evidence": "recent transformer-based or temporal deep learning baselines",
      "role_in_interaction": "comparison object"
    },
    {
      "actor_type": "dataset",
      "evidence": "single hospital cohort / external validation",
      "role_in_interaction": "generalization evidence carrier"
    }
  ],
  "retrieved_case_ids": [
    "riu_v1_example_101",
    "riu_v1_example_102",
    "riu_v1_example_103"
  ]
}
```

它做的事情：

```text
把 reviewer、author、benchmark、dataset、supplement 等都看作互动中的行动者。
```

这就是 2026.5.15.pdf 里人文社科分析真正进入系统的地方：问题不是“审稿人说了 baseline 这个词”，而是：

```text
baseline 是共同体标准的承载物；
dataset 是泛化能力的承载物；
supplement / table 是作者证明自己已经回应的证据载体。
```

### 7.9 Integrity / Overclaim Checker

相关代码位置：

```text
src/peer_review_skills/execution/build_naturereview_v01.py
  - _assess_response_adequacy()
  - _overclaim_risks()
```

输入：

```text
response_text
evidence_action_plan
tone_commitment
label_source
```

输出：

```json
{
  "adequacy_report": [
    "Trace is provenance-linked but not human evaluated.",
    "Do not treat this as final rebuttal text.",
    "Do not predict acceptance probability."
  ],
  "response_adequacy": {
    "coverage_status": "needs_author_confirmation",
    "unresolved_concerns": [
      "Need confirmation that response addresses baseline_comparison with new_baseline_or_comparison."
    ],
    "missing_evidence_actions": [
      "new_baseline_or_comparison"
    ],
    "adequacy_rationale": "Coverage is needs_author_confirmation; assessed from model-assisted alignment, evidence-action labels, case-derived support, and author-confirmation boundaries. This is not human gold.",
    "decision_basis": {
      "basis_type": "insufficient_model_or_case_adequacy_signal",
      "source": "model_assisted_labels_and_case_metadata",
      "supporting_case_ids": []
    },
    "needs_author_confirmation": true
  },
  "responsible_use_warnings": [
    "assistant_only",
    "author_must_verify_all_claims"
  ]
}
```

它做的事情：

```text
检查系统是否正在越权。
```

比如，这个例子里，如果作者还没有提供新 baseline 结果，系统不能写：

```text
We have now comprehensively validated the model against all recent baselines.
```

只能写成计划或待确认动作：

```text
If the additional baseline comparison has been completed, cite the new table / supplement.
If not, narrow the claim and explain the limitation.
```

### 7.10 Cross-Disciplinary Lens Interpreter

相关代码位置：

```text
src/peer_review_skills/execution/build_naturereview_v01.py
  - _cross_disciplinary_lens_map()
```

这个 agent 输出六个 lens：

```json
{
  "tacit_knowledge_boundary": {
    "source_pdf": "2026.5.15.pdf",
    "concept": "默会知识只能作为公开文本中的可观察痕迹来处理",
    "observable_trace": "tacit_concern=community_standard_fit; risk_type=comparative_validity; concern_type=baseline_comparison",
    "system_action": "把 reviewer concern 转成可追溯的风险假设，并要求证据片段支持。",
    "boundary": "不推断真实心理，不声称 AI 掌握专家默会知识，只保留可观察文本痕迹。",
    "evaluation_question": "系统是否把隐含风险解释为可检查假设，而不是写成 reviewer 的真实意图？"
  },
  "institutional_dependence": {
    "source_pdf": "2026.5.15.pdf",
    "concept": "制度依赖和发表压力会影响作者回应姿态",
    "observable_trace": "institutional_signal=community_norm_expectation; author_positioning=accept_and_revise",
    "system_action": "把期刊范围、透明性规范、共同体标准等制度信号转成作者可选择的回应位置。",
    "boundary": "不预测接收率，不把礼貌或让步自动解释为服从制度压力；作者确认和作者判断必须保留。",
    "evaluation_question": "系统是否帮助作者识别制度语境，同时保留作者判断和责任？"
  },
  "actor_network_alignment": {
    "source_pdf": "2026.5.15.pdf",
    "concept": "行动者网络把 reviewer、author、editor 与 figure/dataset/code/benchmark 等对象一起建模",
    "observable_trace": "actor_types=['benchmark', 'dataset', 'reviewer']; retrieved_cases=['riu_v1_example_101', 'riu_v1_example_102', 'riu_v1_example_103']",
    "system_action": "记录哪些人类和非人类行动者承载证据、修订、透明性或编辑可读信号。",
    "boundary": "不还原真实社会因果，只描述公开文本中可观察的行动者对齐关系。",
    "evaluation_question": "系统是否说明了 evidence action 由哪些对象承载，而不是只给出抽象建议？"
  },
  "fast_slow_cognitive_correction": {
    "source_pdf": "2026.5.23.pdf",
    "concept": "快思维先反应，慢思维负责校准、证据约束和完整性检查",
    "observable_trace": "understand -> question -> evidence_plan -> position -> tone_calibrate -> commitment_check -> integrity_check -> output",
    "system_action": "强制 plan-first workflow，先做 concern/risk/evidence/commitment 检查，再输出结构化建议。",
    "boundary": "不直接生成最终 rebuttal，不把流畅文本当成充分回应；作者确认必须先于任何承诺。",
    "evaluation_question": "系统是否有明确慢思维纠偏链条来减少过度自信、迎合和编造风险？"
  },
  "emotion_tone_commitment_calibration": {
    "source_pdf": "2026.5.23.pdf",
    "concept": "情绪维度不是表演共情，而是学术互动姿态、承诺强度和不确定性管理",
    "observable_trace": "tone=cooperative; commitment_level=promised_change; risk_flags=['none']",
    "system_action": "校准语气、承诺强度、防御性、迎合风险和 unsupported commitment。",
    "boundary": "不诊断作者或 reviewer 情绪，不推断真实心理，不用温和语气替代实质证据。",
    "evaluation_question": "系统是否既降低冲突风险，又避免无证据让步或承诺？"
  },
  "author_agency_gate": {
    "source_pdf": "2026.5.23.pdf + 2026.5.15.pdf",
    "concept": "assistant 必须保留作者主体性和专业判断",
    "observable_trace": "evidence_action=new_baseline_or_comparison; author_confirmation_required=true; label_status=model_assisted_not_human_gold",
    "system_action": "对所有证据动作、实验、数据、引用和承诺设置作者确认门禁。",
    "boundary": "作者确认必需；系统不替代作者、不替代 reviewer、不替代 editor。",
    "evaluation_question": "系统是否把建议变成作者可审查的选择，而不是替作者做承诺？"
  }
}
```

这部分是项目的跨学科核心。

它把两个 PDF 里的分析转成系统可执行结构：

- 默会知识边界
- 制度依赖
- 行动者网络
- 快慢思维纠偏
- 情绪、语气、承诺校准
- 作者主体性门禁

## 8. 最终输出：系统给作者什么

最终不是一封完整 rebuttal，而是一个可审查的 plan。

相关代码位置：

```text
src/peer_review_skills/execution/build_naturereview_v01.py
  - _build_rebuttal_plan()
  - _structured_output()
```

示例输出：

```json
{
  "final_structured_output": [
    "Concern map: baseline_comparison -> comparative_validity.",
    "Evidence action before drafting: new_baseline_or_comparison.",
    "Author stance: accept_and_revise; keep all commitments verifiable.",
    "Use 4 plan sections before drafting any final response."
  ],
  "rebuttal_plan": {
    "plan_id": "plan::demo_unit_0001",
    "label_status": "model_assisted_not_human_gold",
    "author_confirmation_required": true,
    "sections": [
      {
        "name": "concern_acknowledgement",
        "purpose": "Address reviewer concern type baseline_comparison without defensiveness.",
        "suggested_move": "Acknowledge the reviewer concern about baseline_comparison and restate the scientific risk.",
        "source": "reviewer_understanding_agent"
      },
      {
        "name": "evidence_action",
        "purpose": "Convert the reviewer concern into a verifiable evidence or revision action.",
        "suggested_move": "Evaluate the case-supported action candidate: new_baseline_or_comparison; cite the manuscript location only after author confirmation.",
        "source": "evidence_action_planner",
        "action_type": "new_baseline_or_comparison",
        "decision_basis": {
          "action_type": "new_baseline_or_comparison",
          "basis_type": "model_assisted_unit_label",
          "supporting_case_ids": [],
          "support_count": 1,
          "requires_author_confirmation": true
        }
      },
      {
        "name": "case_grounded_strategy",
        "purpose": "Use retrieved Nature cases as strategy analogies, not as copied text.",
        "suggested_move": "Compare against retrieved cases riu_v1_example_101, riu_v1_example_102, riu_v1_example_103 to choose a bounded response strategy.",
        "source": "case_retrieval_agent"
      },
      {
        "name": "claim_boundary_and_tone",
        "purpose": "Calibrate author commitment and avoid overclaiming.",
        "suggested_move": "Use author positioning=accept_and_revise and tone=cooperative while preserving uncertainty boundaries.",
        "source": "tone_commitment_calibrator"
      }
    ]
  },
  "author_confirmation_questions": [
    "Can the author verify that additional baseline or comparative result exists or can be added?",
    "Where should the response cite the manuscript change for concern_type=baseline_comparison?",
    "Does the author need to narrow the claim if new_baseline_or_comparison cannot be completed?"
  ],
  "integrity_warnings": [
    "Do not invent experiments, data, citations, or commitments.",
    "Do not predict acceptance probability.",
    "Do not treat this as final rebuttal text.",
    "Author must verify all claims."
  ]
}
```

## 9. 如果把最终 plan 翻译成人能直接理解的话

系统实际想告诉作者的是：

```text
这个 reviewer 的主要关切不是单纯“想看更多数字”，而是怀疑你的模型比较基准不足，
因此现有结果可能不足以支撑强 claim。

你应该优先考虑两类回应：

1. 如果可以补强：
   - 增加 recent transformer-based 或 temporal deep learning baseline；
   - 补充外部验证，或至少在另一个独立 cohort 上验证；
   - 在 rebuttal 里明确指出新增结果的位置，例如 Table X、Supplementary Table Y；
   - 说明新增比较如何改变或支持原始 claim。

2. 如果不能补强：
   - 不要硬说已经解决；
   - 明确收窄 claim；
   - 把 single-hospital cohort 的限制写清楚；
   - 把 external validation 放进 limitation 或 future work，但不要把 future work 伪装成已完成证据。

推荐语气：
   cooperative，但不要过度道歉。

推荐姿态：
   accept_and_revise。

禁止行为：
   不要编造已经完成的 external validation；
   不要声称模型超过所有 SOTA baseline，除非表格中真实比较过；
   不要预测 editor 会因此接受。
```

## 10. 一个可能的“草稿框架”，不是最终 rebuttal

系统可以帮助作者组织成这样的草稿框架：

```text
We thank the reviewer for raising the important point about comparative evaluation
and generalizability.

To address this concern, we have added [AUTHOR MUST CONFIRM: specific baseline models]
to the comparative evaluation and report the results in [AUTHOR MUST CONFIRM: Table / Supplement].

We have also evaluated the model on [AUTHOR MUST CONFIRM: external cohort or validation split],
which helps assess whether the reported performance is specific to the original hospital cohort.

Where external validation remains limited, we have narrowed the claim from
[AUTHOR MUST CONFIRM: original broad claim] to [AUTHOR MUST CONFIRM: revised bounded claim]
and added this limitation to [AUTHOR MUST CONFIRM: manuscript section].
```

这段故意保留 `AUTHOR MUST CONFIRM`。因为系统不能替作者确认实验是否真的完成、表格是否存在、claim 是否已经修改。

## 11. 整体数据流图

```text
User reviewer comment
  |
  v
Input adapter / model-assisted labeling
  |
  v
ReviewInteractionUnit
  |
  +--> Review Understanding Agent
  |      -> concern_map
  |
  +--> Tacit Concern Interpreter
  |      -> risk_interpretation
  |
  +--> Institutional Signal Interpreter
  |      -> institutional_signal_note
  |
  +--> Case Retrieval Agent
  |      -> retrieved_case_ids
  |      -> case_explanations
  |
  +--> Evidence Planner
  |      -> evidence_action_plan
  |      -> author_confirmation_questions
  |
  +--> Author Positioning Agent
  |      -> author_positioning
  |
  +--> Tone / Commitment Calibrator
  |      -> tone_commitment_warnings
  |
  +--> Actor Network Mapper
  |      -> actor_network_note
  |
  +--> Cross-Disciplinary Lens Interpreter
  |      -> six-lens map
  |
  +--> Integrity / Overclaim Checker
         -> response_adequacy
         -> responsible_use_warnings

  |
  v
Structured Rebuttal Plan
  |
  v
Author-confirmed final drafting
```

## 12. 和当前代码的对应关系

| 系统阶段 | 当前代码 / 数据位置 | 说明 |
|---|---|---|
| 构建 v0.1 artifacts | `src/peer_review_skills/execution/build_naturereview_v01.py::main()` | 批处理总入口 |
| seed API 复核 | `_run_naturereview_seed_api_review()` | 使用 OpenAI-compatible API 做 model-assisted review |
| API 结果合并 | `_merge_seed_api_review_result()` | 把模型复核结果合并进 seed labels |
| 标准互动单元 | `_build_interaction_units()` | 生成 ReviewInteractionUnit |
| schema | `data/processed/schemas/review_interaction_unit.schema.json` | 定义 unit 必需字段 |
| 案例索引 | `_build_case_index()` | 生成可检索 case index |
| 行动者网络案例 | `_build_actor_network_cases()` | 生成 actor-network cases |
| 检索 | `_build_retrieval_v2()` | 根据 case metadata 和跨学科信号检索 |
| 案例解释 | `_case_explanation()` | 解释每个 retrieved case 为什么相关 |
| workflow trace | `_build_workflow_traces()` | 合成完整 agent trace |
| agent 中间输出 | `_agent_intermediate_outputs()` | 生成每个 agent 的输出 |
| 证据动作决策 | `_resolve_evidence_action()` | 选择 evidence_action |
| 证据计划 | `_build_evidence_action_plan()` | 生成 evidence action plan |
| 作者确认问题 | `_author_confirmation_questions()` | 生成必须由作者确认的问题 |
| 回应充分性检查 | `_assess_response_adequacy()` | 检查是否 covered / partially covered / needs confirmation |
| 跨学科 lens | `_cross_disciplinary_lens_map()` | 把 PDF-derived lenses 转成 trace |
| rebuttal plan | `_build_rebuttal_plan()` | 生成四段式 plan |
| 最终结构输出 | `_structured_output()` | 生成简短结构化摘要 |
| workflow artifacts | `data/evaluation/workflow_v2/workflow_traces.jsonl` | 当前实际 trace 文件 |
| validation | `validate-naturereview-v01` | 检查核心 artifacts 和边界 |

## 13. 当前已有入口和未来单条输入入口的差异

当前已有入口：

```powershell
$env:PYTHONPATH='src'; python -m peer_review_skills.cli.main build-naturereview-v01
```

它会批量生成：

```text
data/processed/review_interaction_kb/v1/
data/evaluation/retrieval_v2/
data/evaluation/workflow_v2/
data/evaluation/simulation_v1/
docs/NATUREREVIEW_V01_VALIDATION_REPORT_zh.md
```

未来如果要做真正的单条输入 assistant，可以封装成：

```text
assist_rebuttal(user_input)
  -> model-assisted label adapter
  -> ReviewInteractionUnit
  -> retrieve_cases_from_kb
  -> build_agent_intermediate_outputs
  -> build_cross_disciplinary_lens_map
  -> build_rebuttal_plan
  -> return structured output
```

伪代码如下：

```python
def assist_rebuttal(user_input):
    unit = model_label_to_review_interaction_unit(user_input)
    prediction = retrieve_similar_nature_cases(unit, kb)
    agent_outputs = _agent_intermediate_outputs(unit, prediction)
    lens_map = _cross_disciplinary_lens_map(unit, prediction)
    plan = _build_rebuttal_plan(unit, prediction)
    adequacy = _assess_response_adequacy(unit, agent_outputs["evidence_action_planner"]["evidence_action_plan"])
    return {
        "unit": unit,
        "retrieved_cases": prediction["case_explanations"],
        "agent_outputs": agent_outputs,
        "cross_disciplinary_lens_map": lens_map,
        "rebuttal_plan": plan,
        "integrity_check": adequacy,
    }
```

这段不是当前仓库里的现成函数，而是说明当前代码最自然的产品化封装方式。

## 14. 这个例子体现了系统真正学到的东西

这个系统不是只学到“baseline 这个词出现了，所以建议补 baseline”。

它学到的是一组审稿互动里的结构性知识：

1. **显性问题和隐性风险不同**
   reviewer 明说 baseline 不足，背后是 comparative validity 和 community standard fit。

2. **审稿意见有制度语境**
   Nature 系列期刊不只是检查有没有结果，还会检查贡献是否达到共同体可接受标准。

3. **证据不是抽象的**
   baseline、dataset、supplement、table 都是行动者网络里的 evidence carrier。

4. **回应策略需要历史案例支持**
   系统用真实 Nature 案例找“类似问题通常如何被转成证据动作”。

5. **语气不是礼貌包装**
   语气和承诺强度必须和证据状态匹配。

6. **作者主体性必须保留**
   所有实验、数据、引用、修改位置和承诺都必须由作者确认。

7. **assistant 不能越权**
   系统不能预测接收，不能伪造修改，不能把 plan 当最终 rebuttal。

## 15. 最终可以对外怎么介绍这个系统

可以这样介绍：

```text
NatureReview-Interact / Agnes 不是一个普通的 rebuttal 代写器。
它是一个基于 Nature 公开同行评审互动案例的跨学科 assistant workflow。

用户输入一条审稿意见后，系统会识别 reviewer 的显性 concern、隐性风险、
期刊和共同体制度信号，并检索历史 Nature 案例，生成可追溯的证据动作计划、
作者回应姿态、语气和承诺边界，最后输出一个需要作者确认的 rebuttal plan。

系统强调作者主体性、证据完整性和 responsible use，
不会编造实验、不会预测接收率，也不会把模型输出当作最终学术判断。
```

## 16. 当前输出应该如何被使用

正确使用方式：

```text
作者把系统输出当成 checklist 和 reasoning scaffold。
作者逐条确认：
  - 我是否真的补了这个 baseline？
  - 我是否真的做了 external validation？
  - manuscript 里具体在哪一节、哪张表、哪个 supplement？
  - 如果没有完成，我是否需要收窄 claim？
  - 我的语气是否过度防御或过度迎合？
```

错误使用方式：

```text
直接复制系统草稿作为最终 rebuttal。
让系统编造不存在的实验。
让系统承诺作者没有完成的修改。
让系统预测 editor 是否会接受。
把 model-assisted label 当成人工金标准。
```

## 17. 总结

给系统一个 reviewer comment 后，系统内部真正发生的是：

```text
文本输入
  -> 结构化审稿互动单元
  -> Nature 案例检索
  -> 多 agent 中间推理
  -> 跨学科 lens map
  -> 证据动作和作者确认门禁
  -> 完整性检查
  -> 结构化 rebuttal plan
```

最终输出不是“替作者写完”，而是：

```text
帮助作者理解 reviewer 真正关切，
找到历史案例中的可迁移回应策略，
把回应拆成证据、姿态、语气、边界和确认问题，
并防止过度承诺或伪造证据。
```

这就是当前非训练版 NatureReview-Interact 的核心工作方式。
