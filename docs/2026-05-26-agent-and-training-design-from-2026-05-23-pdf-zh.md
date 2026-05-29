# 基于 2026.5.23.pdf 的 Author Rebuttal Assistant Agent 与训练设计

> 日期：2026-05-26
> 输入材料：`2026.5.23.pdf`、现有 `v2709` 数据包、当前 workflow 原型与项目总结
> 当前定位：详细设计阶段，不继续默认爬取数据

## 1. 设计结论

`2026.5.23.pdf` 给项目带来的关键启发是：我们不应该把系统设计成“直接替作者写 rebuttal 的大模型”，而应该设计成一个带有 **认知层、情绪/语气诊断、证据约束、慢思维纠偏和可追溯案例检索** 的 Author Rebuttal Assistant。

也就是说，系统核心不是生成一段好看的回复，而是帮助作者完成一个高质量 rebuttal 决策过程：

1. 先理解 reviewer 真正在担心什么；
2. 再判断这是科学风险、证据风险、统计风险、范围风险、表达风险还是编辑决策风险；
3. 检索 Nature 历史案例，看真实作者如何处理类似意见；
4. 规划需要补充或引用的证据；
5. 生成结构化回复草稿；
6. 用独立的语气、完整性和过度承诺检查器做二次校正；
7. 全流程记录 provenance，使每一个建议都能回溯到数据、案例和推理步骤。

这个方向比“训练一个会写回复的模型”更适合当前项目，因为我们手里最强的资产不是人工金标大规模训练集，而是 `v2709` 公开审稿互动数据、启发式 review-response pair、45 条 model-confirmed 小评测集，以及已经跑通的 retrieval/workflow trace 原型。

## 2. PDF 对项目的直接启发

### 2.1 双系统理论：把 rebuttal 拆成快思维和慢思维

PDF 第 4-6 页强调卡尼曼双系统理论：系统 1 快速、直觉、容易受情绪和偏见影响；系统 2 慢、理性、负责纠错和权衡。

映射到 rebuttal 场景：

| 人类/LLM 现象      | rebuttal 风险              | 系统设计含义                              |
| ------------------ | -------------------------- | ----------------------------------------- |
| 收到批评后立刻防御 | 回复强硬、激化对抗         | 需要先做情绪和关切理解                    |
| 过度迎合 reviewer  | 承诺做不到的实验或过度让步 | 需要 integrity checker                    |
| 固执维护原稿       | 忽略真实科学风险           | 需要 risk classifier 和 evidence planner  |
| 只做表面润色       | 没有解决 reviewer 核心担忧 | 需要 concern extraction 和 case retrieval |
| 直接生成最终回复   | 缺少审计链                 | 需要 traceable workflow                   |

所以 agent 不应只有一个 drafting model，而应该有一个“快判断 -> 慢校正 -> 证据约束 -> 结构化输出”的流程。

### 2.2 情绪维度：rebuttal 不是纯逻辑任务

PDF 第 20-22 页明确提出：有效回复需要识别隐藏心理状态、语言线索、情绪和合作性改变。对 rebuttal agent 来说，这里的“情绪”不能理解成讨好 reviewer，而应理解成 **学术沟通中的语气、姿态和合作信号**。

需要建模的维度包括：

| 维度                 | 在 rebuttal 中的含义                            | 可操作标签                                                     |
| -------------------- | ----------------------------------------------- | -------------------------------------------------------------- |
| reviewer stance      | reviewer 是质疑、建议、要求补证据，还是表达困惑 | critical / skeptical / constructive / blocking / clarification |
| author stance        | 作者是承认、澄清、反驳、补实验，还是缩小 claim  | acknowledge / clarify / contest / add evidence / narrow scope  |
| politeness           | 是否尊重、具体、非对抗                          | respectful / neutral / defensive / dismissive                  |
| confidence           | 是否过度自信或过度不确定                        | calibrated / overconfident / underconfident                    |
| commitment           | 是否承诺了实际修改或实验                        | done / planned / impossible / future work / not promised       |
| collaboration signal | 是否体现“我们理解并回应了该关切”              | strong / moderate / weak                                       |

这意味着训练侧不能只标注 concern_type 和 strategy，还要补充语气与承诺相关标签。

### 2.3 认知层架构：把通用 LLM 包在可审计层里

PDF 第 17 页讨论心理治疗中的 cognitive layer architecture，第 20 页提出给 AI 加认知层。对本项目的启发是：基础 LLM 可以负责语言理解和草稿生成，但关键决策必须由一个外部可审计认知层控制。

本项目中的 cognitive layer 应包含：

1. 输入解析层：拆分 reviewer comment、author response、paper metadata、decision signal；
2. 关切识别层：抽取 reviewer concern 和隐含 risk；
3. 案例检索层：从 Nature 历史案例中找相似 concern-response；
4. 证据规划层：判断应该补实验、补分析、补引用、改图表、改文字还是缩小 claim；
5. 回复生成层：只生成 outline 或 draft，不直接作为最终答案；
6. 语气结构层：检查尊重性、清晰度、顺序和结构；
7. 完整性层：检查是否编造证据、过度承诺、过度迎合、无依据反驳；
8. provenance 层：记录每个建议来自哪个历史案例、哪个字段、哪个 offset。

### 2.4 LIWC/GPT 心理文本分析：做语气和心理维度标注，而不是主模型替代

PDF 第 23-24 页讨论 LIWC 和 GPT 作为心理文本分析工具。对本项目而言，LIWC/GPT 的合理角色不是替代 agent，而是成为训练和评估中的辅助标注器：

- 给 review comment 标注批评强度、情绪倾向、确定性；
- 给 author response 标注礼貌性、防御性、谦逊性、承诺强度；
- 给生成回复标注是否过度迎合、是否过度自信；
- 形成 tone / stance / confidence / commitment 的弱监督标签；
- 用于 agent 的 tone editor 和 integrity checker。

当前可以先用 LLM 模拟 LIWC/GPT 风格的心理文本分析，后续如果需要再接入真正 LIWC 或开源心理词典。

## 3. Agent 总体架构

建议将系统设计为 8 个 agent / module。它们不一定都是独立模型，可以是同一个 LLM 在不同 prompt 和工具约束下执行，也可以逐步替换成分类器、检索器或微调模型。

```text
User manuscript context + reviewer comments
        |
        v
[1] Review Understanding Agent
        |
        v
[2] Concern / Risk Classifier
        |
        v
[3] Emotion-Stance-Tone Analyzer
        |
        v
[4] Case Retrieval Agent
        |
        v
[5] Evidence Planner
        |
        v
[6] Rebuttal Drafting Assistant
        |
        v
[7] Tone and Structure Editor
        |
        v
[8] Integrity / Overclaim Checker
        |
        v
Traceable rebuttal plan + draft + warnings + provenance
```

## 4. Agent 详细设计

### 4.1 Review Understanding Agent

目标：把 reviewer comment 从自然语言批评转成结构化关切。

输入：

- reviewer comment；
- paper title / abstract / field metadata；
- 可选：当前 manuscript section、figure/table、author response 历史片段。

输出：

```json
{
  "concern_summary": "...",
  "explicit_requests": ["..."],
  "implicit_concerns": ["..."],
  "target_object": "method / experiment / claim / figure / writing / statistics",
  "severity": "minor / moderate / major / blocking",
  "uncertainty": "low / medium / high"
}
```

训练/标注信号：

- 当前已有：`concern_type_gold` / heuristic concern type；
- 需要新增：explicit_request、implicit_concern、severity、target_object。

禁止行为：

- 不能把 reviewer 的建议过度解释成作者必须执行的实验；
- 不能忽略 reviewer 的隐含风险点；
- 不能把语言润色问题误判成科学有效性问题。

### 4.2 Concern / Risk Classifier

目标：判断 reviewer comment 影响哪类论文风险。

建议风险类型：

| risk_type                | 含义                                |
| ------------------------ | ----------------------------------- |
| comparative_validity     | baseline、prior work、对比不足      |
| external_validity        | 泛化范围、外部验证、人群/数据域迁移 |
| reproducibility          | 代码、数据、参数、协议可复现        |
| statistical_validity     | 统计检验、显著性、样本量、不确定性  |
| mechanistic_validity     | 机制、消融、因果解释不足            |
| communication_clarity    | 图表、文字、结构、定义不清          |
| design_validity          | 实验设计、控制组、流程合理性        |
| responsible_research     | 数据偏差、伦理、隐私、安全          |
| theoretical_validity     | 理论假设、数学证明、概念有效性      |
| contribution_positioning | novelty、定位、相关工作             |

输出：

```json
{
  "concern_type": "generalization_scope",
  "risk_type": "external_validity",
  "risk_rationale": "...",
  "decision_relevance": "low / medium / high",
  "recommended_strategy_candidates": [
    "add_new_analysis",
    "narrow_claim_scope",
    "clarify_existing_evidence"
  ]
}
```

训练侧：

- 短期：用 45 条 model-confirmed subset 做 sanity check；
- 中期：从 9858 条 demo-ready pairs 中抽 300-500 条做 LLM-assisted label，再人工抽查；
- 长期：训练一个 lightweight classifier 或 embedding classifier。

### 4.3 Emotion-Stance-Tone Analyzer

目标：实现 PDF 里说的“情绪维度架构”，但保持学术场景克制。它不是模拟真实情感，而是识别语言中的姿态、压力和沟通风险。

输入：

- reviewer comment；
- author draft 或历史 author response；
- 可选：editor decision letter。

输出：

```json
{
  "reviewer_stance": "skeptical / constructive / blocking / confused / adversarial",
  "reviewer_pressure": "low / medium / high",
  "author_response_tone": "respectful / neutral / defensive / dismissive / over_apologetic",
  "sycophancy_risk": "low / medium / high",
  "overconfidence_risk": "low / medium / high",
  "recommended_tone_action": "soften / be_more_specific / acknowledge_then_answer / narrow_disagreement"
}
```

为什么它重要：

- PDF 提醒了“训练模型变温暖可能降低准确性并增加谄媚”；
- rebuttal 场景中，过度温暖可能导致无原则让步；
- 过度强硬会破坏学术合作信号；
- 所以系统需要做 tone calibration，而不是单纯“更礼貌”。

训练侧：

- 先用 LLM rubric 标注 tone / stance / sycophancy_risk；
- 人工抽查 100 条；
- 不把该标签作为硬 gold，先作为弱监督和评估维度。

### 4.4 Case Retrieval Agent

目标：从 v2709 中检索与当前 reviewer concern 相似的历史 Nature rebuttal 案例。

输入：

```json
{
  "concern_summary": "...",
  "concern_type": "...",
  "risk_type": "...",
  "target_object": "...",
  "paper_field": "...",
  "decision_signal": "optional"
}
```

输出：

```json
{
  "retrieved_cases": [
    {
      "pair_id": "...",
      "paper_id": "...",
      "doi": "...",
      "concern_type": "...",
      "response_strategy": "...",
      "review_context_preview": "...",
      "author_response_preview": "...",
      "source_json_path": "...",
      "source_offsets": {}
    }
  ],
  "retrieval_method": "hybrid_bm25_concern_strategy",
  "top_k": 5
}
```

当前已有基础：

- P1 最好方法：`hybrid_bm25_concern_strategy`；
- model-confirmed 45 条上 joint@5 约 0.7556；
- workflow prototype 中 joint@5 约 0.7778。

后续升级：

1. BM25 + concern filter；
2. 加 embedding retrieval；
3. 加 reranker；
4. 加 decision-aware filter；
5. 加 field/journal/year stratification。

### 4.5 Evidence Planner

目标：把“怎么回复”转化为“需要什么证据支撑”。

输出：

```json
{
  "recommended_strategy": "add_new_analysis",
  "evidence_needed": [
    {
      "type": "statistical_test",
      "description": "...",
      "required_artifact": "figure/table/supplement/method paragraph",
      "status": "available / missing / author_must_confirm"
    }
  ],
  "claim_scope_action": "keep / narrow / remove / defer",
  "manuscript_change_plan": [
    {
      "location": "Methods / Results / Supplement / Response only",
      "change_type": "clarification / new analysis / new experiment / limitation",
      "human_confirmation_required": true
    }
  ]
}
```

关键原则：

- 不能建议作者声称已经做了未完成实验；
- 不能自动编造数据、p 值、图号、引用；
- 对无法验证的内容必须标记 `author_must_confirm`。

### 4.6 Rebuttal Drafting Assistant

目标：生成结构化草稿，不生成不可审计的最终文本。

输出建议采用分段结构：

```json
{
  "draft_outline": [
    {
      "section": "acknowledgement",
      "text": "We thank the reviewer for raising this important point..."
    },
    {
      "section": "direct_answer",
      "text": "The main issue concerns..."
    },
    {
      "section": "evidence",
      "text": "To address this, the authors should cite or add..."
    },
    {
      "section": "manuscript_change",
      "text": "The response should specify the exact revised section..."
    },
    {
      "section": "scope_or_limitation",
      "text": "If the evidence is incomplete, narrow the claim..."
    }
  ],
  "placeholders_requiring_author_input": ["exact figure number", "new analysis result"],
  "not_final_response": true
}
```

训练侧：

- 不建议一开始微调“最终回复生成模型”；
- 应先训练/评估 outline generation、strategy selection、evidence planning；
- 最终 draft 可以由强 LLM + 严格 schema + integrity checker 完成。

### 4.7 Tone and Structure Editor

目标：把草稿变成学术上更合适的沟通结构。

检查项：

- 是否先承认 reviewer 关切，再给证据；
- 是否把反驳写得过硬；
- 是否把让步写得过度；
- 是否每一段都有明确功能；
- 是否避免“we have fully addressed”等过度绝对表达；
- 是否避免空泛感谢和没有证据的套话。

输出：

```json
{
  "tone_revision_actions": ["soften_disagreement", "add_specific_evidence_anchor"],
  "structure_score": 4,
  "tone_score": 4,
  "revised_outline": []
}
```

### 4.8 Integrity / Overclaim Checker

目标：作为独立慢思维纠偏层，专门阻止系统胡说或过度承诺。

必须检查：

| 检查项                 | 说明                           |
| ---------------------- | ------------------------------ |
| fabricated_evidence    | 是否编造实验、数据、引用、图表 |
| unsupported_commitment | 是否承诺作者未确认的修改       |
| overclaim              | 是否超过证据范围               |
| sycophancy             | 是否过度迎合 reviewer          |
| dismissiveness         | 是否轻视 reviewer 关切         |
| missing_provenance     | 是否缺少历史案例或输入证据来源 |
| uncertainty_hidden     | 是否隐藏不确定性               |

输出：

```json
{
  "integrity_pass": false,
  "issues": [
    {
      "type": "unsupported_commitment",
      "span": "...",
      "reason": "...",
      "required_fix": "replace with author_must_confirm placeholder"
    }
  ],
  "allowed_to_show_user": false
}
```

## 5. 训练侧总体路线

当前数据量和标签质量决定了：**不要一开始做大模型端到端微调**。更合理的训练路线是“知识库 + 弱监督标签 + 小模型/分类器 + RAG-agent + 小批量评估”。

### 5.1 当前可用训练/评估资产

| 数据资产                   |        数量 | 当前用途                      | 风险                             |
| -------------------------- | ----------: | ----------------------------- | -------------------------------- |
| v2709 主库                 | 2709 papers | provenance source、知识库源   | 字段不完全一致                   |
| core full-chain papers     |         339 | decision-aware case retrieval | 不是所有 pair 都对齐             |
| heuristic demo-ready pairs |        9858 | retrieval pool、弱监督        | 非人工 gold                      |
| model-confirmed subset     |          45 | 小评测集                      | model-confirmed，不是 human gold |
| unresolved cases           |           5 | error analysis                | 需要人工或更强复核               |

### 5.2 标签体系

建议把标签拆成 5 层，不要混在一个大 label 里。

#### A. Concern 标签

```text
baseline_comparison
generalization_scope
reproducibility_reporting
statistics_significance
ablation_mechanism
clarity_presentation
experimental_design
dataset_bias_ethics_safety
theoretical_validity
novelty_positioning
```

#### B. Risk 标签

```text
comparative_validity
external_validity
reproducibility
statistical_validity
mechanistic_validity
communication_clarity
design_validity
responsible_research
theoretical_validity
contribution_positioning
```

#### C. Strategy 标签

```text
acknowledge_and_fix
clarify_existing_evidence
add_new_experiment
add_new_analysis
narrow_claim_scope
contest_reviewer_premise
defer_future_work
justify_method_choice
reframe_contribution
editorial_only_change
```

#### D. Evidence 标签

```text
existing_result
new_experiment
new_analysis
statistical_test
code_or_data_availability
citation_or_prior_work
figure_or_table_revision
text_clarification
limitation_statement
author_confirmation_required
```

#### E. Tone / Stance / Commitment 标签

```text
reviewer_stance
reviewer_pressure
author_tone
confidence_calibration
commitment_level
sycophancy_risk
overclaim_risk
collaboration_signal
```

### 5.3 训练任务优先级

| 优先级 | 任务                        | 为什么先做                    |
| -----: | --------------------------- | ----------------------------- |
|     P0 | concern/risk classification | 决定后续检索和策略            |
|     P1 | strategy retrieval/ranking  | 当前已有 baseline，可快速提升 |
|     P2 | evidence planning           | 直接决定系统是否可靠          |
|     P3 | tone/stance classification  | 对应 PDF 的情绪维度架构       |
|     P4 | outline generation          | 比最终全文生成更可控          |
|     P5 | integrity checking          | 最关键的安全和可信模块        |
|     P6 | final draft generation      | 最后做，且必须有人确认        |

## 6. 模型训练与评估路线

### Phase A：标签扩展和清洗

目标：把 45 条 model-confirmed subset 扩展成 300-500 条高质量训练/验证 seed。

做法：

1. 从 `heuristic_rebuttal_pairs_demo_ready.jsonl` 分层抽样；
2. 按 concern_type、strategy、journal、year、full-chain/response-only 分层；
3. 用 DeepSeek/GPT 风格模型做第一轮结构化标签；
4. 对低置信、冲突、offset 不可恢复样本进入人工或二次模型复核；
5. 输出 `model_confirmed_v2_300` 或 `weak_gold_seed_500`。

验收标准：

- 每条都有 source path 和 offset；
- 每条都有 concern/risk/strategy/evidence/tone 标签；
- 至少 80% 样本可恢复原文；
- 明确标注 `label_source=model_assisted`，不能称 human gold。

### Phase B：分类器训练

目标：训练轻量模型或 prompt classifier，服务 agent 内部决策。

候选方法：

| 方法                             | 用途                      |
| -------------------------------- | ------------------------- |
| zero-shot LLM                    | 早期强 baseline           |
| few-shot LLM                     | 小样本稳定输出            |
| embedding + kNN                  | concern/strategy 快速分类 |
| logistic regression / linear SVM | 可解释 baseline           |
| small transformer fine-tuning    | 后续可选，不是第一步      |

先训练/比较：

- concern_type classifier；
- risk_type classifier；
- response_strategy classifier；
- tone/stance classifier。

指标：

- accuracy；
- macro-F1；
- per-class F1；
- calibration / abstention rate；
- error category。

### Phase C：Retrieval/Reranking 训练

目标：让 case retrieval 不只是 BM25，而能找出真正有用的历史案例。

训练样本构造：

- query：reviewer comment + concern/risk；
- positive：同 strategy / 同 concern / 高相似 response 的历史 pair；
- hard negative：同词汇但不同 strategy 或不同 risk 的 pair。

方法：

1. 当前 BM25/hybrid 作为 baseline；
2. 加 embedding retrieval；
3. 用 cross-encoder 或 LLM reranker 做 small-batch rerank；
4. 输出 top-k with provenance。

指标：

- strategy hit@5；
- concern hit@5；
- joint hit@5；
- MRR；
- retrieval usefulness human rating；
- provenance recoverability。

### Phase D：Evidence Planner 训练

目标：从 reviewer concern 和历史案例中预测“需要什么证据”。

监督信号：

- author response 中是否出现 experiment / analysis / clarification / limitation；
- strategy label；
- model-assisted evidence_type；
- manuscript change markers；
- decision-aware full-chain 子集中的 outcome signal。

输出不应是自然语言大段文本，而应是 schema：

```json
{
  "evidence_actions": [],
  "required_author_inputs": [],
  "claim_scope_action": "...",
  "risk_if_missing": "..."
}
```

评估：

- evidence_type accuracy / F1；
- required_author_input recall；
- overclaim prevention；
- human usefulness。

### Phase E：Workflow 训练/优化

目标：优化 agent 的完整流程，不追求单模型端到端。

比较系统：

| 系统                  | 说明                                  |
| --------------------- | ------------------------------------- |
| vanilla_llm           | 直接给 reviewer comment，让模型写回复 |
| retrieval_only        | 检索案例后直接生成                    |
| workflow_no_tone      | 去掉情绪/语气分析                     |
| workflow_no_integrity | 去掉完整性检查                        |
| workflow_full         | 完整 cognitive-layer workflow         |

评估维度：

- concern coverage；
- evidence grounding；
- specificity；
- tone appropriateness；
- overclaim risk；
- unsupported commitment；
- retrieval support；
- human preference。

## 7. 当前 workflow 与目标架构的差距

当前已有 `rebuttal_workflow.py` 已经包含：

- Review Understanding Agent；
- Concern/Risk Classifier；
- Case Retrieval Agent；
- Evidence Planner；
- Rebuttal Drafting Assistant；
- Tone and Structure Editor；
- Integrity / Overclaim Checker；
- provenance trace。

但当前版本仍偏规则化和原型化，主要差距是：

| 模块                 | 当前状态                      | 需要补强                                       |
| -------------------- | ----------------------------- | ---------------------------------------------- |
| review understanding | 基于已有 label 和文本 preview | 加 explicit/implicit concern extraction        |
| risk classifier      | concern 到 risk 的静态映射    | 引入模型判断和置信度                           |
| tone analyzer        | 只有简单 tone guidance        | 独立建模 stance、sycophancy、overconfidence    |
| case retrieval       | hybrid BM25 可用              | 加 embedding/reranker/decision-aware retrieval |
| evidence planner     | 模板化                        | 训练 evidence_type 和 required_author_input    |
| drafting             | outline 生成                  | 强制 schema、placeholder、禁止最终承诺         |
| integrity checker    | 规则检查                      | 加 span-level issue detection                  |
| evaluation           | 45 条小集                     | 做正式小批量对比评测                           |

## 8. 推荐的系统输出形态

不要直接输出一封完整 rebuttal。推荐输出如下结构：

```json
{
  "review_understanding": {},
  "risk_assessment": {},
  "tone_stance_analysis": {},
  "retrieved_cases": [],
  "evidence_plan": {},
  "rebuttal_outline": {},
  "draft_paragraphs": [],
  "integrity_warnings": [],
  "author_questions": [],
  "provenance": {},
  "notices": [
    "This is an assistant-generated plan and requires author confirmation.",
    "No experiment, analysis, citation, or manuscript change should be claimed unless verified by the authors."
  ]
}
```

这样更符合系统论文/知识库论文的定位：可追溯、可评估、可控制，而不是一个不可解释的文本生成器。

## 9. 下一步执行顺序

### Step 1：补齐 agent schema

产物：

- `AgentTraceSchema`；
- `ConcernRiskSchema`；
- `ToneStanceSchema`；
- `EvidencePlanSchema`；/
- `IntegrityCheckSchema`。

目标：让每个 agent 的输入输出可保存、可测试、可评估。

### Step 2：生成 100-200 条扩展 model-assisted training seed

产物：

- `data/training/author_rebuttal_agent/v2709/seed_200.jsonl`；
- 每条包含 concern/risk/strategy/evidence/tone/provenance。

目标：支撑分类器、retrieval rerank 和 evidence planner。

### Step 3：做正式小批量对比评测

比较：

- `vanilla_llm`；
- `retrieval_only`；
- `workflow_no_tone`；
- `workflow_no_integrity`；
- `workflow_full`。

产物：

- per-case side-by-side JSONL/CSV；
- aggregate metrics；
- 中文报告。

### Step 4：训练或实现第一批可替换模块

优先顺序：

1. concern/risk classifier；
2. strategy retriever/reranker；
3. tone/stance analyzer；
4. evidence planner；
5. integrity checker。

不建议优先训练 final rebuttal generator。

### Step 5：形成论文级 claim ledger

可以主张：

- 我们构建了一个基于 Nature 公开审稿互动的可追溯 rebuttal knowledge base；
- 我们提出了 cognitive-layer Author Rebuttal Assistant workflow；
- 小批量评测显示 workflow 比直接 LLM 生成更可追溯、更少过度承诺、更能覆盖 reviewer concern。

暂时不能强主张：

- 系统已经超越人类作者；
- 数据标签是人工金标；
- retrieval 或 agent 在大规模真实场景中已经验证；
- 系统能预测编辑决定或保证接收。

## 10. 最关键的设计原则

1. `v2709` 是知识库基础，不是直接可用的全量 gold training set。
2. 先做可追溯 workflow，再做模型微调。
3. 先训练/评估分类、检索、证据规划和完整性检查，再考虑最终文本生成。
4. 情绪维度要落到 tone、stance、confidence、commitment、sycophancy risk，不做空泛“共情”。
5. agent 必须保持 assistant 定位，不替作者承诺、不替 reviewer 判断、不编造证据。
6. 每条建议必须能回溯到 reviewer comment、历史案例、source path、offset 或作者确认字段。
7. 论文贡献应强调“认知层 + 知识库 + 可评估 workflow”，而不是只强调“LLM 写得更好”。
