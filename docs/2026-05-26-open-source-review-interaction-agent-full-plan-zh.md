# Nature Review Interaction Agent 开源研究方案

> 日期：2026-05-26
> 当前目标：先形成一个可以开源的研究型项目方案，而不是立即进入具体工程实现。
> 核心输入：`v2709` Nature 系列公开同行评审数据、已有 MVP 数据包、现有小批量评测结果、`2026.5.23.pdf` 的人文/认知分析、外部 peer review / rebuttal / RAG / AI governance 相关工作。
> 项目定位：从 Nature 公开审稿互动数据中学习审稿意见、作者回应、证据动作、语气策略和编辑信号之间的规律，构建一个可解释、可追溯、可评估、可开源的 Review Interaction Agent 研究框架。

## 1. 总体结论

本项目不应该定位为“Nature 案例检索助手”，也不应该定位为“自动帮作者写 rebuttal 的文本生成器”。

更准确的定位是：

> 一个基于 Nature 公开同行评审互动案例的 **Review Interaction Learning + Agent Framework**。
> 它从历史审稿互动中学习 reviewer concern、author strategy、evidence action、tone / stance、commitment、editorial signal 之间的规律，再把这些规律组织成一个能够自动进行审稿互动推理的 agent。

这个 agent 的核心能力不是“写得像人”，而是：

1. 看懂 reviewer 表层意见背后的真实风险；
2. 判断 concern 是表达问题、方法问题、证据问题、统计问题、泛化问题、伦理问题还是贡献定位问题；
3. 选择合理的 author response strategy；
4. 规划需要的 evidence action；
5. 校准回应语气和承诺强度；
6. 识别回复是否真正解决 reviewer concern；
7. 保持可追溯、可审计和可开源复现。

## 2. 当前数据基础

当前项目已有 `v2709` 数据，主要资产如下：

| 数据资产 | 数量 | 当前作用 |
|---|---:|---|
| paper records | 2709 | Nature 公开审稿互动主语料 |
| core full-chain papers | 339 | reviewer-author-editor 可观察互动链 |
| response-only papers | 1400 | author response strategy 学习 |
| review-only input papers | 860 | reviewer concern extraction 输入 |
| heuristic rebuttal pairs all | 21978 | 原始候选 pair |
| heuristic rebuttal pairs clean | 11311 | 弱监督候选 |
| demo-ready pairs | 9858 | 初始检索、模式归纳、seed 构建 |
| demo-ready cases | 738 | paper-level case bundle |
| model-confirmed subset | 45 | 小批量评测和 sanity check |

这些数据足够支持：

- 构建审稿互动知识库；
- 归纳 concern / strategy / evidence / tone taxonomy；
- 建立弱监督训练任务；
- 做小规模 model-assisted evaluation；
- 开源 schema、派生标签、评测协议和 agent 框架。

这些数据暂时不足以支持：

- 声称模型已经学到所有 Nature 审稿规律；
- 大规模 human gold benchmark；
- 可靠接收率预测；
- causal claim；
- 直接训练高质量 final rebuttal generator；
- 发布完整原始全文作为开放数据集。

## 3. `2026.5.23.pdf` 给项目的核心启发

这份 PDF 的价值不在于给出工程模块，而在于从人文和认知角度提醒我们：审稿互动不是纯文本生成问题。

### 3.1 双系统理论：快反应与慢纠偏

审稿互动中存在类似“快思维”和“慢思维”的张力：

| 场景 | 快反应风险 | 慢纠偏需求 |
|---|---|---|
| 作者收到批评 | 防御、反驳、情绪化 | 重新理解 reviewer 真实关切 |
| LLM 直接生成回复 | 流畅但空泛 | 证据、策略、承诺逐项检查 |
| reviewer 表达模糊 | 表层理解 | 推断隐含科学风险 |
| 作者想快速过关 | 过度承诺 | 检查是否真的有实验/分析支持 |

所以 agent 不能只有 drafting model，而应该有一个“先反应、再校准、再证据约束、再完整性检查”的认知层。

### 3.2 情绪维度：不是共情表演，而是学术互动姿态

PDF 强调情绪、隐藏心理状态、语言线索和合作性改变。落到本项目里，不能简单做“更温暖的回复”，因为外部研究已经提示过度温暖可能降低准确性并增加 sycophancy。

因此我们要建模的是：

- reviewer stance；
- reviewer pressure；
- author stance；
- confidence calibration；
- commitment level；
- defensiveness；
- sycophancy risk；
- collaboration signal。

这不是让 agent 假装有人类情感，而是让它识别学术互动中的语气风险和策略姿态。

### 3.3 认知层架构：把 LLM 放进可审计流程

PDF 中的 cognitive layer 思路应转化为本项目的核心架构：

```text
LLM 负责语言理解和生成
认知层负责：
  - concern decomposition
  - risk judgment
  - strategy selection
  - evidence planning
  - tone calibration
  - adequacy checking
  - integrity checking
  - provenance logging
```

这意味着我们应该开源的不只是 prompt，而是一套可解释的审稿互动建模框架。

## 4. 外部相关工作与可借鉴点

### 4.1 Peer review 数据集

代表工作：

- PeerRead：早期 peer review 数据集，连接 paper、review 和 decision。
- NLPeer：统一多来源 peer review 数据表示，强调 metadata、ethics、versioning。
- MOPRD：multidisciplinary open peer review dataset，包含 manuscript versions、review comments、author rebuttal letters、editorial decisions。
- Re2：full-stage peer review 数据，关注 multi-turn rebuttal discussions、score changes、final decisions。

对我们的启发：

- 数据集不能只放文本，要有结构化 interaction unit；
- 必须区分 paper-level、comment-level、response-level、decision-level；
- 必须保留 provenance；
- 需要明确许可和再分发边界；
- 我们的差异是 Nature transparent peer review，不是 OpenReview/会议 rebuttal。

### 4.2 Rebuttal generation / response modeling

代表工作：

- Paper2Rebuttal / RebuttalAgent：强调 reviewer intent、evidence-centric planning 和 inspectable response plan。
- DRPG：Decompose、Retrieve、Plan、Generate，说明 rebuttal 不应直接一步生成。
- Theory-of-Mind RebuttalAgent：尝试建模 reviewer mental state 和 strategic persuasion。
- Author-in-the-Loop / REspGen / REspEval：强调作者拥有模型没有的 domain expertise 和 author-only information。
- DEFEND：指出直接 LLM rebuttal 在事实正确性和 targeted refutation 上容易失败，segment-wise 和 author-in-the-loop 更可靠。
- RbtAct：用 rebuttal 来识别 actionable review feedback，强调 review segment 到 response/action 的映射。

对我们的启发：

- reviewer comment 要拆成 atomic concern；
- response 生成前要先生成 response plan；
- 需要明确 evidence action；
- 作者确认是必要环节；
- 评价不能只看流畅度，要看 concern coverage、faithfulness、input utilization、strategy coherence 和 discourse quality；
- Theory-of-Mind 思路可以借鉴，但不能过度声称知道 reviewer 真实心理，只能输出可审计的 stance / pressure / uncertainty。

### 4.3 RAG、事实核查和科学证据

代表工作：

- RAG：把生成和外部知识检索结合，适合知识密集任务。
- PaperQA：面向科学文献的 retrieval-augmented agent，需要检索、综合和引用证据。
- Self-RAG：retrieve、generate、critique 的自我反思流程。
- SciFact / FEVER：claim verification 和 evidence retrieval 任务范式。
- FActScore：把长文本拆成 atomic facts，再判断每个事实是否被来源支持。

对我们的启发：

- 检索不是目的，而是证据约束的一部分；
- 回复中的 factual claim 应拆成 atomic claims；
- 每个 claim 应标记 supported / unsupported / needs_author_confirmation；
- overclaim 和 unsupported commitment 应成为核心评估项；
- agent 要有 critique / self-check 步骤。

### 4.4 Peer review assistance 与 AI governance

代表工作和政策：

- Review Feedback Agent：在真实 peer review 环境中用 LLM 给 reviewer 提供 clarity、specificity、actionability 反馈。
- OpenReviewer：面向 scientific review generation 的专用模型。
- Nature / Springer Nature AI policy：reviewers 不应把未发表稿件上传到外部生成式 AI 工具，AI 使用需要透明和合规。
- ICML 2026 policy：允许作者用 LLM 辅助写作，但禁止 reviewer 上传 manuscript 到 LLM，并要求披露 AI use；也开始关注 prompt injection 等问题。
- COPE / WAME 等出版伦理讨论：AI 可以辅助，但不能替代责任主体。

对我们的启发：

- 开源项目必须明确 responsible use；
- 不应鼓励用户上传未公开稿件到不受控 API；
- assistant 不能替代作者、审稿人、编辑；
- reviewer-side simulation 可以用于研究和评估，但不能伪装成真实 peer review；
- 开源文档必须包含 AI use disclosure、data ethics、license boundary。

## 5. 我们应该开源什么

考虑 Nature 数据许可和伦理边界，开源项目不应默认发布完整原始 peer review 全文。

更合适的开源范围：

### 5.1 可以优先开源

- project overview；
- schema；
- taxonomy；
- extraction pipeline 描述；
- derived metadata；
- source URL / DOI / hash；
- source offsets；
- model-assisted labels；
- evaluation protocol；
- small manually/model-confirmed examples；
- agent framework；
- prompts / rubrics；
- baseline scripts；
- report templates；
- responsible use policy。

### 5.2 谨慎开源

- author response 长文本；
- reviewer report 长文本；
- decision letter 全文；
- 可反推出个人身份的内容；
- 可能受版权约束的原文再分发。

### 5.3 不建议开源或默认禁用

- 未公开 manuscript；
- confidential review material；
- 用户上传的真实未发表论文；
- 自动提交 rebuttal 功能；
- 号称预测接收率或操纵 reviewer 的模块。

## 6. 从数据中要学习的核心对象

### 6.1 Concern

模型要学 reviewer 在担心什么。

```json
{
  "surface_request": "Please clarify the control experiment.",
  "atomic_concern": "The control condition is insufficiently described.",
  "implicit_risk": "The causal claim may not be supported without a clear control.",
  "risk_type": "design_validity",
  "severity": "major",
  "decision_relevance": "high"
}
```

### 6.2 Strategy

模型要学作者应该如何回应。

```json
{
  "response_strategy": "add_new_analysis",
  "strategy_rationale": "The reviewer challenges robustness rather than wording.",
  "alternative_strategies": ["clarify_existing_evidence", "narrow_claim_scope"]
}
```

### 6.3 Evidence Action

模型要学什么策略需要什么证据。

```json
{
  "evidence_action": "statistical_sensitivity_analysis",
  "required_artifacts": ["supplementary_table", "methods_detail"],
  "author_confirmation_required": true
}
```

### 6.4 Tone / Stance / Commitment

模型要学学术互动姿态。

```json
{
  "reviewer_stance": "skeptical",
  "author_stance": "acknowledge_then_clarify",
  "confidence_calibration": "calibrated",
  "commitment_level": "completed_revision",
  "sycophancy_risk": "low",
  "defensiveness_risk": "low"
}
```

### 6.5 Response Adequacy

模型要学回复是否真的解决问题。

```json
{
  "adequacy": "partial",
  "unresolved_concern": "The response explains the rationale but does not provide additional validation.",
  "needed_follow_up": "Either add validation or narrow the claim."
}
```

### 6.6 Editorial Signal

模型要学可观察编辑信号。

```json
{
  "editorial_signal": "major_revision_emphasis",
  "editor_emphasized_risks": ["external_validity", "statistical_validity"],
  "observable_outcome": "revision_requested",
  "causal_claim_allowed": false
}
```

## 7. 最终 Agent 框架

建议把最终系统设计为 5 个能力层，而不是一开始拆成过多子 agent。

```text
Layer 1: Interaction Understanding
Layer 2: Strategy and Evidence Learning
Layer 3: Rebuttal Planning
Layer 4: Response Generation and Calibration
Layer 5: Simulation and Evaluation
```

### 7.1 Layer 1：Interaction Understanding

目标：

- 拆解 reviewer comment；
- 识别 atomic concerns；
- 判断 risk type、severity、implicit risk；
- 建立 reviewer concern map。

对应模型：

- Concern Understanding Model；
- Risk Classification Model。

### 7.2 Layer 2：Strategy and Evidence Learning

目标：

- 学习 concern -> strategy；
- 学习 strategy -> evidence action；
- 学习 author response 里的实际 revision behavior；
- 学习不同 risk 对应的常见处理方式。

对应模型：

- Strategy Selection Model；
- Evidence Action Model；
- Response Adequacy Model。

### 7.3 Layer 3：Rebuttal Planning

目标：

- 不是直接写回复；
- 而是生成可检查的 rebuttal plan。

输出：

```json
{
  "concern_map": [],
  "strategy_plan": [],
  "evidence_plan": [],
  "author_confirmation_questions": [],
  "risk_if_unaddressed": []
}
```

### 7.4 Layer 4：Response Generation and Calibration

目标：

- 基于 plan 生成结构化草稿；
- 校准 tone、confidence、commitment；
- 检查 overclaim、unsupported evidence、defensiveness、sycophancy。

对应模型/模块：

- Draft Generator；
- Tone and Commitment Calibrator；
- Integrity Checker。

### 7.5 Layer 5：Simulation and Evaluation

目标：

- 用 agent simulation 测试系统是否真的学到互动能力；
- 不把 simulation 当真实 peer review；
- 而是作为研究评估环境。

模拟角色：

```text
Reviewer Agent:
  生成或复述 reviewer concern，检查回复是否 addressed。

Author Rebuttal Agent:
  理解 concern，规划策略，生成回复。

Editor Signal Agent:
  判断是否仍有 unresolved concern，给出 revision pressure signal。
```

## 8. 推荐研究问题

主研究问题：

> Can open transparent peer review data be used to learn structured interaction patterns that improve evidence-grounded, strategy-aware, and integrity-preserving author rebuttal assistance?

中文表述：

> 公开透明同行评审数据是否可以用于学习结构化审稿互动规律，从而提升作者回应系统在证据约束、策略选择和学术完整性方面的能力？

子问题：

1. Nature 公开审稿互动中 reviewer concern、author strategy、evidence action 和 editor signal 是否存在可归纳的结构模式？
2. 从这些模式中学习出来的策略模型，是否比直接 LLM 生成更能覆盖 reviewer concern？
3. evidence action modeling 是否能降低 unsupported commitment 和 overclaim 风险？
4. tone / stance / commitment calibration 是否能改善 rebuttal 的学术互动质量？
5. 开源时如何在研究可复现性、版权边界、隐私保护和负责任使用之间取得平衡？

## 9. 论文与开源贡献定位

推荐贡献路线：

### Contribution 1：Nature Review Interaction Schema

贡献：

- 定义 reviewer-author-editor interaction unit；
- 给出 concern、risk、strategy、evidence、tone、adequacy、decision signal taxonomy；
- 提供 derived metadata 和 provenance。

价值：

- 为后续 peer review NLP 和 rebuttal agent 提供结构化基础。

### Contribution 2：Interaction Learning Tasks

贡献：

- atomic concern extraction；
- risk classification；
- strategy prediction；
- evidence action prediction；
- response adequacy scoring；
- tone / commitment calibration；
- decision-aware signal modeling。

价值：

- 把 rebuttal assistance 从 demo 变成可评估任务。

### Contribution 3：Review Interaction Agent Framework

贡献：

- 基于 learned interaction models 的 agent；
- 不只是 case retrieval；
- 不只是 final text generation；
- 强调 strategy、evidence、tone、integrity。

价值：

- 给 open-source academic agent 提供可复现框架。

### Contribution 4：Responsible Open-Source Release

贡献：

- 开源 schema、labels、evaluation、prompts、baseline；
- 避免默认再分发受版权约束的全文；
- 明确 AI use policy 和 responsible use。

价值：

- 让项目可用、可复现，同时降低伦理和版权风险。

## 10. 评价体系

不要只评价 BLEU/ROUGE 或“写得像不像”。

建议评价：

| 维度 | 问题 |
|---|---|
| concern coverage | 是否覆盖 reviewer 的核心关切 |
| risk accuracy | 是否正确判断风险类型和严重程度 |
| strategy appropriateness | 策略是否适合该 concern |
| evidence grounding | 是否有足够证据支撑 |
| actionability | 是否给出可执行修改建议 |
| response adequacy | 是否真正回答 reviewer |
| tone calibration | 是否克制、专业、非防御、非讨好 |
| commitment safety | 是否避免未经确认的承诺 |
| overclaim prevention | 是否避免超过证据 |
| provenance | 是否能追溯到数据、case、offset 或 author confirmation |

## 11. 开源版本的边界

### 11.1 MVP 开源版本应该包含

```text
README
project motivation
data card
model card / agent card
schema
taxonomy
derived labels sample
evaluation protocol
baseline results
responsible use policy
AI disclosure template
license notes
```

### 11.2 README 应该明确

- 本项目是研究工具，不是论文接收率提升工具；
- 不应上传 confidential manuscript 到不受控 API；
- 不应让 AI 替代作者、审稿人或编辑；
- 生成内容需要作者确认；
- 所有 evidence、experiment、analysis、citation 必须真实存在；
- 数据来自公开 transparent peer review 文件，但原文再分发有边界。

## 12. 最推荐的阶段路线

先不进入具体实现，但研究路线可以这样定：

### Stage 1：Open-Source Research Framing

产物：

- project README；
- data card；
- ethics / responsible use statement；
- schema draft；
- taxonomy draft。

目标：

- 让别人知道这个项目不是爬虫，不是自动代写，而是 review interaction learning。

### Stage 2：Interaction Unit Definition

产物：

- `ReviewInteractionUnit` schema；
- concern/risk/strategy/evidence/tone/adequacy/decision signal 定义；
- provenance 规则。

目标：

- 统一后续数据、模型、agent、评测。

### Stage 3：Seed Dataset

产物：

- 100-200 条 model-assisted seed；
- 明确 label_source；
- 明确 needs_human_review；
- 明确 offset recoverability。

目标：

- 从案例转向可学习样本。

### Stage 4：Learning Tasks and Baselines

产物：

- concern/risk baseline；
- strategy prediction baseline；
- evidence action baseline；
- response adequacy baseline。

目标：

- 证明数据可以学到东西。

### Stage 5：Agent Framework

产物：

- learned interaction model 驱动的 agent；
- plan-first rebuttal workflow；
- tone/integrity gate；
- simulation environment。

目标：

- 证明 agent 可以进行审稿互动推理，而不只是检索案例。

## 13. 风险和反方意见

### 13.1 最大方法风险

风险：

- Nature 公开 peer review 文件不完整；
- heuristic pair 可能错配；
- author response 不一定对应单个 reviewer concern；
- editor decision 未必完整反映内部判断；
- model-assisted labels 不是 human gold。

应对：

- 所有 claims 保守；
- 用 provenance 和 offset；
- 区分 heuristic / model-assisted / human-confirmed；
- 不做 causal claim；
- 从小批量人工/模型复核开始。

### 13.2 最大伦理风险

风险：

- 被误用为自动 rebuttal 代写；
- 被误用来操纵 reviewer；
- 上传未公开 manuscript 到外部 API；
- 再分发受版权约束的 peer review 原文；
- 模型编造实验或承诺。

应对：

- 开源时加入 responsible use；
- 默认输出 plan 和 warnings，不直接输出 final submission；
- 明确 author confirmation；
- 不默认再分发全文；
- integrity checker 必须成为核心模块。

### 13.3 最大论文风险

风险：

- 贡献看起来像普通 RAG；
- 数据标签不够强；
- 评测规模太小；
- 外部工作已有 rebuttal generation agent。

应对：

- 强调 learned review interaction，不是 RAG；
- 强调 Nature transparent peer review，不是 OpenReview；
- 强调 evidence action 和 adequacy，不是文本生成；
- 强调开源 schema + task + responsible release；
- 强调人文/认知层：tone、commitment、overclaim、slow correction。

## 14. 最终推荐定位

项目名称可以考虑：

```text
NatureReview-Interact
Nature Rebuttal Interaction Agent
OpenReview Interaction Learning for Rebuttal Assistance
Review2Rebuttal Interaction Framework
```

最推荐的论文/开源标题方向：

> Learning Review-Response Interaction Patterns from Transparent Peer Review for Evidence-Grounded Rebuttal Assistance

中文：

> 从透明同行评审中学习审稿-回应互动模式：面向证据约束作者回复辅助的开源框架

## 15. 一句话总方案

本项目最好的方向是：

> 先把 v2709 Nature 公开同行评审数据转化为结构化 review interaction units，再从中学习 reviewer concern、author strategy、evidence action、tone / commitment 和 editor signal 的映射规律，最后开源一个以 learned interaction models 为核心、具备 rebuttal planning、response generation、adequacy checking 和 integrity guard 的 Review Interaction Agent 框架。

这比“案例检索助手”更有研究价值，也比“自动写 rebuttal”更安全、更可解释、更适合开源。
