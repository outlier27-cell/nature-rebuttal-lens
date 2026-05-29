# 从 Nature 审稿互动中学习出来的 Agent / Model 框架

> 日期：2026-05-26
> 目的：修正前一版“案例检索助手”思路，明确本项目真正要做的是：从 Nature 公开审稿互动案例中学习审稿、回应、编辑决策之间的互动规律，并基于这些规律构建能够自动参与审稿互动的 agent / model。
> 核心转向：数据不是最终产品，也不是简单 case library；数据是训练和归纳“审稿互动能力”的经验来源。

## 1. 先明确真正目标

我们不是要做一个只会“查相似案例”的 RAG 工具。

我们真正要做的是：

> 从 Nature 系列公开同行评审数据中学习 reviewer concern、author rebuttal、revision action、tone、evidence use、editorial signal 之间的规律，训练或构建一个能够理解审稿意见、判断真实风险、选择回应策略、规划证据、生成回复并自我校正的审稿互动 agent。

换句话说，v2709 数据的作用是：

- 不是简单拿来展示案例；
- 不是只作为检索库；
- 而是作为一种“审稿互动经验数据”，让模型学到 Nature 审稿过程里反复出现的模式。

这些模式包括：

1. reviewer 通常怎样表达不同类型的担忧；
2. 哪些 reviewer concern 是轻微表达问题，哪些是重大科学风险；
3. 作者面对不同 concern 通常采用什么 response strategy；
4. 什么情况下作者补实验、补分析、补引用、改图、改文字、缩小 claim；
5. 什么语气更像成熟的学术回应；
6. 哪些回复容易过度承诺或没有真正回答问题；
7. editor decision 和 reviewer concern / author response 之间有哪些可观察信号。

## 2. 前一版方向哪里偏了

前一版把重点放在：

```text
reviewer comment -> 检索相似 Nature 案例 -> 给作者参考 -> 生成回复计划
```

这个方向可用，但它只是产品表层。

更深层应该是：

```text
Nature 审稿互动数据
  -> 学习审稿互动结构
  -> 学习 concern/risk/strategy/evidence/tone/decision 的映射
  -> 形成策略模型和可训练任务
  -> agent 自动进行审稿互动推理
```

所以 retrieval 只是其中一个能力，不是系统的核心定义。

真正核心应该是一个 **learned interaction model**：

```text
P(response_strategy, evidence_action, tone, claim_scope | reviewer_concern, paper_context, decision_signal)
```

也就是：给定审稿意见和论文上下文，模型要能判断应该怎么回应、需要什么证据、语气如何、是否要缩小 claim、哪些地方必须作者确认。

## 3. 从数据中应该学习什么

### 3.1 学 reviewer concern

模型要学会 reviewer 关切的不同层级：

| 层级 | 例子 | 要学到的能力 |
|---|---|---|
| 表层请求 | “Please clarify Figure 2.” | 识别显性要求 |
| 隐含风险 | 图 2 不清可能说明证据链不清 | 识别真实担忧 |
| 科学风险 | 样本量、统计、baseline、泛化不足 | 判断风险类型 |
| 编辑风险 | 如果不回应，可能影响 revision outcome | 判断严重程度 |

输出不是简单分类，而是：

```json
{
  "atomic_concern": "...",
  "surface_request": "...",
  "implicit_risk": "...",
  "risk_type": "...",
  "severity": "...",
  "decision_relevance": "..."
}
```

### 3.2 学 author response strategy

从 author response 中学习策略：

| 策略 | 含义 |
|---|---|
| acknowledge_and_fix | 承认问题并修改 |
| clarify_existing_evidence | 澄清已有证据 |
| add_new_experiment | 新增实验 |
| add_new_analysis | 新增分析 |
| narrow_claim_scope | 缩小 claim |
| contest_reviewer_premise | 礼貌反驳 reviewer 前提 |
| defer_future_work | 承认为未来工作 |
| justify_method_choice | 解释方法选择 |
| reframe_contribution | 重新定位贡献 |
| editorial_only_change | 只做表达或图表修改 |

这里要学的是映射关系：

```text
reviewer concern type + severity + paper context
    -> likely successful response strategy
```

不是简单背诵历史案例。

### 3.3 学 evidence action

这是最重要的训练目标之一。

模型需要学会 reviewer concern 到 evidence action 的映射：

| reviewer concern | 常见 evidence action |
|---|---|
| 泛化性不足 | 新 dataset / cohort / domain validation，或缩小 claim |
| baseline 不足 | 增加 baseline comparison 或解释 prior work 差异 |
| 统计质疑 | 补充统计检验、置信区间、敏感性分析 |
| 机制不足 | ablation、mechanism analysis、feature importance |
| 可复现性不足 | code、data、protocol、parameter、supplement |
| 表达不清 | 改图、改 legend、改 wording、补定义 |
| novelty 不清 | 加 related work、重写 contribution framing |

这个能力决定 agent 是不是“懂审稿互动”，而不是只会写漂亮话。

### 3.4 学 tone / stance / commitment

这部分来自 `2026.5.23.pdf` 的启发，但要理性落地。

模型不需要真的“有情绪”，但要学会学术互动中的姿态：

| 维度 | 要学的内容 |
|---|---|
| reviewer stance | reviewer 是质疑、困惑、建议、强要求还是阻断性批评 |
| author stance | 作者是承认、解释、反驳、让步还是重构 |
| confidence | 回复是否过度自信或过度不确定 |
| commitment | 作者是否承诺了实验、分析、修改或未来工作 |
| collaboration signal | 是否体现理解 reviewer 关切并愿意合作 |
| defensiveness | 是否显得在逃避或对抗 |
| sycophancy | 是否过度迎合 reviewer，导致无原则承诺 |

这就是 PDF 里“情绪维度架构”的可训练版本。

### 3.5 学 editor / decision signal

如果有 decision letter，模型可以学习：

```text
reviewer concern + author response + editor decision
```

之间的可观察关系。

注意：不能声称因果，不能说“这样回复一定会接收”。

可以学习的是：

- 哪些 concern 在 editor letter 中被强调；
- 哪些 response strategy 常出现在 full-chain 成功修订案例中；
- 哪些风险类型更可能被 editor 视为 major issue；
- 什么样的 response 没有真正解决 reviewer concern。

这部分可以形成：

```json
{
  "decision_signal": "minor_revision / major_revision / accept_after_revision / reject_or_unknown",
  "editor_emphasis": ["..."],
  "unresolved_concerns": ["..."],
  "response_adequacy_signal": "strong / partial / weak / unknown"
}
```

## 4. 总体模型框架

建议把系统分成三层：

```text
Layer 1: Interaction Knowledge Extraction
Layer 2: Learned Interaction Models
Layer 3: Review Interaction Agent
```

### 4.1 Layer 1：Interaction Knowledge Extraction

目标：把 v2709 中的原始 peer review 文件变成可训练的 interaction units。

输入：

- reviewer reports；
- author response；
- decision letter；
- paper metadata；
- source offsets。

输出：

```json
{
  "unit_id": "...",
  "review_comment": "...",
  "atomic_concern": "...",
  "author_response_span": "...",
  "response_strategy": "...",
  "evidence_action": "...",
  "tone_stance": {},
  "decision_signal": {},
  "provenance": {}
}
```

这层主要解决：

- 拆分；
- 对齐；
- 标注；
- offset recoverability；
- label confidence。

### 4.2 Layer 2：Learned Interaction Models

目标：从 interaction units 中学习模式。

这里可以有多个小模型，而不是一个大而全的黑盒模型。

#### Model A：Concern Understanding Model

输入：

```text
reviewer comment + paper title/abstract
```

输出：

```text
atomic concerns + risk type + severity + implicit concern
```

训练信号：

- heuristic concern type；
- model-assisted label；
- later human-confirmed subset。

#### Model B：Strategy Selection Model

输入：

```text
atomic concern + risk type + paper context
```

输出：

```text
response strategy distribution
```

例如：

```json
{
  "add_new_analysis": 0.42,
  "clarify_existing_evidence": 0.31,
  "narrow_claim_scope": 0.19
}
```

#### Model C：Evidence Action Model

输入：

```text
concern + selected strategy + paper context
```

输出：

```text
needed evidence / revision action / author confirmation
```

这是 agent 最关键的能力。

#### Model D：Tone and Commitment Model

输入：

```text
reviewer comment + draft response
```

输出：

```text
tone risk + commitment type + overclaim risk + sycophancy risk
```

#### Model E：Response Adequacy Model

输入：

```text
reviewer concern + author response + evidence action
```

输出：

```text
does_response_address_concern: full / partial / weak / no
```

这个模型可以用于自动评估和 agent 自我修正。

### 4.3 Layer 3：Review Interaction Agent

目标：使用 learned models 自动执行审稿互动。

输入：

```text
reviewer comments + manuscript context + author constraints
```

输出：

```text
rebuttal plan + evidence plan + response draft + revision suggestions + self-check report
```

Agent 的执行流程：

```text
1. 解析 reviewer comments
2. 拆成 atomic concerns
3. 对每个 concern 预测 risk/severity
4. 选择 response strategy
5. 预测需要的 evidence action
6. 向作者索取必要确认
7. 生成 response plan
8. 生成 draft
9. 检查 response adequacy
10. 检查 tone/commitment/overclaim
11. 输出最终可审阅版本
```

## 5. Agent 应该“自动”到什么程度

这里要分清楚：

| 能自动 | 不能自动 |
|---|---|
| 自动理解 reviewer concern | 自动决定真实实验结果 |
| 自动判断风险类型 | 自动编造新实验 |
| 自动推荐策略 | 自动承诺作者会做什么 |
| 自动规划需要证据 | 自动替作者确认 manuscript change |
| 自动生成草稿 | 自动提交 rebuttal |
| 自动检查 overclaim | 自动保证编辑接受 |

所以它是自动进行“审稿互动推理”，不是自动替作者完成科学事实。

## 6. 训练任务设计

### Task 1：Atomic Concern Extraction

输入：

```text
reviewer comment
```

输出：

```json
[
  {
    "atomic_concern": "...",
    "surface_request": "...",
    "implicit_risk": "..."
  }
]
```

用途：

- reviewer understanding；
- 后续所有模型的入口。

### Task 2：Concern Risk Classification

输入：

```text
atomic concern + paper metadata
```

输出：

```text
risk_type + severity + decision_relevance
```

### Task 3：Strategy Prediction

输入：

```text
concern + risk_type + optional paper context
```

输出：

```text
response_strategy distribution
```

### Task 4：Evidence Action Prediction

输入：

```text
concern + risk_type + selected strategy
```

输出：

```text
evidence_action + required_author_confirmation
```

### Task 5：Response Adequacy Scoring

输入：

```text
reviewer concern + author response
```

输出：

```text
full / partial / weak / no
```

### Task 6：Tone and Commitment Calibration

输入：

```text
reviewer concern + draft response
```

输出：

```text
tone risk + commitment risk + overclaim risk
```

### Task 7：Decision-aware Interaction Modeling

输入：

```text
concern + response + editor decision
```

输出：

```text
observable decision signal / unresolved concern / response adequacy
```

限制：

- 只做 signal modeling；
- 不做“接收率预测”的强 claim。

## 7. 训练数据如何从 v2709 来

### 7.1 当前数据能支持什么

当前已有：

- 2709 paper records；
- 339 full-chain papers；
- 1400 response-only papers；
- 9858 demo-ready heuristic pairs；
- 45 model-confirmed subset。

可以支持：

- concern taxonomy 初步学习；
- strategy taxonomy 初步学习；
- evidence action 弱监督；
- tone/commitment 弱监督；
- retrieval/reranking；
- 小批量 workflow evaluation。

### 7.2 当前数据不能直接支持什么

不能直接支持：

- 大规模 human gold training；
- 可靠接收率预测；
- causal claim；
- 完整多轮审稿因果链；
- final rebuttal generator 的高质量监督训练。

### 7.3 推荐构建数据集

建议下一步构建：

```text
data/training/review_interaction_model/v2709/interaction_seed_200.jsonl
```

每条包含：

```json
{
  "unit_id": "...",
  "review_comment": "...",
  "atomic_concerns": [],
  "risk_type": "...",
  "severity": "...",
  "author_response_span": "...",
  "response_strategy": "...",
  "evidence_action": "...",
  "tone_stance": {},
  "commitment_level": "...",
  "response_adequacy": "...",
  "decision_signal": {},
  "source_offsets": {},
  "label_source": "model_assisted",
  "needs_human_review": true
}
```

## 8. Agent 的“特别能力”应该是什么

这个项目的特别之处，不应该是“会写得流畅”。

应该是以下 6 个能力：

### 8.1 Reviewer Intent Reading

能看出 reviewer 表面说“clarify”，背后可能是在质疑：

- 证据链；
- 方法合理性；
- claim 过度；
- generalization；
- statistical validity。

### 8.2 Strategy Selection

能判断面对不同 concern 应该：

- 承认并修改；
- 澄清已有证据；
- 新增分析；
- 新增实验；
- 缩小 claim；
- 礼貌反驳；
- 放到 future work。

### 8.3 Evidence Discipline

能知道每种策略需要什么证据，不能空口说。

### 8.4 Tone Calibration

能避免：

- 防御性太强；
- 过度迎合；
- 过度自信；
- 含糊逃避。

### 8.5 Response Adequacy Self-check

能判断自己的回复是否真的回答了 reviewer concern。

### 8.6 Editorial Signal Awareness

能识别哪些问题更可能是 editor 关心的 major risk。

## 9. 推荐的模型实现路径

### Phase 1：规则 + LLM 标注

先不用训练复杂模型。

做：

- 用 DeepSeek/GPT 风格模型给 100-200 条 pair 标注；
- 输出结构化 JSON；
- 检查 offset recoverability；
- 建立 interaction schema。

### Phase 2：小模型 baseline

训练/比较：

- TF-IDF / BM25 + linear classifier；
- embedding + kNN；
- few-shot LLM classifier；
- small transformer fine-tuning。

任务：

- risk classification；
- strategy prediction；
- evidence action prediction。

### Phase 3：策略模型 + 检索增强

不是简单 retrieval，而是：

```text
learned strategy predictor + retrieved historical pattern + evidence planner
```

模型先预测策略，再用历史案例校准。

### Phase 4：Agent workflow

把模型接进 agent：

```text
Concern Understanding Model
  -> Strategy Selection Model
  -> Evidence Action Model
  -> Draft Generator
  -> Adequacy Evaluator
  -> Integrity/Tone Checker
```

### Phase 5：自动互动模拟

模拟一个审稿互动过程：

```text
Reviewer Agent: 给出审稿意见
Author Rebuttal Agent: 生成回应
Editor Signal Agent: 判断是否仍有 unresolved concerns
Author Agent: 修订回应
```

这里才是真正的“自动审稿互动 agent”。

注意：Reviewer Agent 和 Editor Signal Agent 不是为了替代人类，而是为了训练和评估 rebuttal agent。

## 10. 和普通 RAG Assistant 的区别

| 普通 RAG assistant | 我们要做的 interaction agent |
|---|---|
| 查相似案例 | 学习 concern-response-decision 规律 |
| 把案例塞给 LLM | 训练策略选择和证据规划能力 |
| 输出一段回复 | 输出互动推理、证据计划、回复和自检 |
| 主要靠 prompt | 有可训练任务和模型模块 |
| 评价生成质量 | 评价 concern coverage、adequacy、strategy、evidence、tone |
| 没有编辑信号 | 使用 full-chain 子集学习 editor signal |

## 11. 最终系统蓝图

```text
Nature v2709 Review Interaction Data
        |
        v
Interaction Unit Builder
        |
        v
Learned Interaction Models
  - Concern Understanding
  - Risk Classification
  - Strategy Selection
  - Evidence Action Prediction
  - Tone/Commitment Calibration
  - Response Adequacy Scoring
        |
        v
Review Interaction Agent
  - understands reviewer
  - predicts risk
  - selects strategy
  - plans evidence
  - asks author confirmations
  - drafts response
  - checks adequacy and integrity
        |
        v
Automatic Review Interaction Simulation
  - reviewer agent
  - rebuttal agent
  - editor signal agent
  - revision loop
```

## 12. 下一步最应该做什么

下一步应该做的是：

1. **定义 interaction unit schema。**
   这是训练 agent/model 的基础。

2. **从 v2709 抽 100-200 条，构建 `interaction_seed_200.jsonl`。**
   不只是 review-response pair，要标注 atomic concern、risk、strategy、evidence action、tone、adequacy、decision signal。

3. **先训练/评估三个核心模型。**
   - Concern/Risk Model；
   - Strategy Selection Model；
   - Evidence Action Model。

4. **再做 agent workflow。**
   把这些 learned models 接成自动互动 agent。

5. **最后做 reviewer-author-editor simulation。**
   用模拟互动测试 agent 是否真的学到了审稿互动能力。

## 13. 一句话修正版

我们不是在用 Nature 数据做一个“案例检索回复助手”。

我们是在用 Nature 公开同行评审数据学习一种 **审稿互动策略模型**：

> 它要学会 reviewer 在担心什么、作者通常怎样有效回应、什么证据动作支撑什么策略、什么语气和承诺是合适的、哪些问题会成为编辑层面的风险；然后把这些学到的规律组装成一个能够自动进行审稿互动推理和回应生成的 agent。
