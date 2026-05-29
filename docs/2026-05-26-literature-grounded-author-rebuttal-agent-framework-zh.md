# Author Rebuttal Assistant 最完整框架思路

> 日期：2026-05-26
> 目的：判断当前 agent 设计是否基于 v2709 数据和现有工作形成，并补充一个更完整、但不过度复杂的框架。
> 结论：当前 `docs/2026-05-26-agent-and-training-design-from-2026-05-23-pdf-zh.md` 的方向是合理的，但它更像“基于 PDF 启发 + 项目数据现状”的设计草案；还不能说已经是充分吸收外部工作的最终框架。本文件补上外部相关工作、可借鉴点和我们自己的完整框架。

## 1. 对现有文档的判断

现有文档不是凭空想出来的，它确实和我们现在的数据状态匹配：

- `v2709` 主库有 2709 篇 paper 记录；
- MVP 包里有 1739 篇可用于 pair extraction 的 source papers；
- 有 9858 条 demo-ready heuristic rebuttal pairs；
- 有 45 条 model-confirmed 小评测集；
- 已经跑过 P1 retrieval baseline；
- 已经有一个可记录、可追溯的 workflow prototype。

所以文档里强调的几个方向是有数据基础的：

1. **不继续默认爬虫，而是先把 v2709 变成知识库。**
2. **不直接训练最终回复生成模型，而是先做 concern、risk、strategy、evidence、tone、integrity。**
3. **不把 heuristic pair 当人工 gold，而是作为 retrieval、weak supervision 和 prototype 数据。**
4. **必须保留 provenance，因为当前 pair 是从原始 peer review file 中抽出来的，必须能回溯 source path 和 offset。**

但现有文档还不够完整：

- 它对外部相关工作引用不足；
- 它还没有明确说明我们和 OpenReview/ICLR rebuttal 数据工作的差异；
- 它把 agent 拆得比较细，后续实现时可以简化；
- tone / stance / emotion 设计主要来自 PDF 启发，目前还不是 v2709 已验证标签；
- 当前数据还不能支撑“模型训练已经成熟”或“agent 有正式效果提升”的强结论。

更准确地说：现有文档是一个**合理的 agent 设计草案**，但还需要变成一个**文献对齐、数据约束清楚、评估路径明确的完整研究框架**。

## 2. 外部相关工作给我们的启发

### 2.1 Peer review 数据集方向

相关工作：

- [PeerRead](https://aclanthology.org/N18-1149/) 是较早的公开 peer review 数据集，包含 paper drafts、accept/reject decisions 和 expert reviews。
- [NLPeer](https://arxiv.org/abs/2211.06651) 强调 ethically sourced multi-domain peer review corpus、统一数据表示、metadata 和 versioning。
- [MOPRD](https://arxiv.org/abs/2212.04972) 是 multidisciplinary open peer review dataset，覆盖 metadata、多个 manuscript versions、review comments、meta-reviews、author rebuttal letters 和 editorial decisions。
- [Re2](https://arxiv.org/abs/2505.07920) 明确把 full-stage peer review 和 multi-turn rebuttal discussions 建成数据集，强调 review、rebuttal、discussion、score changes 和 final decisions。

可借鉴点：

- 我们不能只存文本，要存 metadata、版本、round、reviewer、response、decision、offset、source path。
- 最小单元不能只用 paper，应该至少有 `paper -> round -> reviewer comment -> concern -> author response span -> evidence/action -> decision signal`。
- 外部数据多来自 OpenReview/会议体系，我们的差异在于 Nature 系列公开同行评审文件，领域更偏自然科学、生命科学、跨学科，且包含 journal editorial process。

对我们框架的影响：

- 我们应该把 v2709 定位为 **Nature transparent peer review interaction knowledge base**，不是普通 review dataset。
- 知识库的核心卖点是真实 Nature reviewer-author-editor 互动链，而不是单纯更大规模。

### 2.2 Author rebuttal / response generation 方向

相关工作：

- [Paper2Rebuttal / RebuttalAgent](https://arxiv.org/abs/2601.14171) 明确指出 rebuttal 不应直接做 text generation，而应拆成 reviewer intent 对齐、evidence-centric planning、inspectable response plan 和 drafting。
- [DRPG](https://arxiv.org/abs/2601.18081) 把学术 rebuttal 拆成 Decompose、Retrieve、Plan、Generate 四步，和我们希望做的 concern decomposition、case retrieval、strategy planning 高度一致。
- [Dancing in Chains / ToM RebuttalAgent](https://arxiv.org/abs/2601.15715) 从 Theory of Mind 角度建模 reviewer mental state，再形成策略和回复。这与 `2026.5.23.pdf` 中“识别隐藏心理状态、语言线索、情绪和合作性改变”的出发点最接近，但我们需要把它落成可审计的 stance/tone/risk 标签，而不是不可验证的心理猜测。
- [Author-in-the-Loop Response Generation / REspGen / REspEval](https://arxiv.org/abs/2602.11173) 强调作者有 domain expertise、author-only information 和 response strategies，系统必须把作者意图纳入生成与评价。
- [DEFEND](https://arxiv.org/abs/2603.27360) 发现直接 LLM rebuttal 在 factual correctness 和 targeted refutation 上表现差，segment-wise generation 和 author-in-the-loop 更可靠。
- [RbtAct](https://arxiv.org/abs/2603.09723) 把 rebuttal 当作 actionable review feedback 的监督信号，用 review segment 到 rebuttal segment 的映射来学习什么样的评论真的促成作者行动。

可借鉴点：

- reviewer comment 要拆成 atomic concerns；
- 每个 concern 都要有对应 response strategy；
- rebuttal 生成前必须先有 response plan；
- 作者必须在关键节点确认：是否真的做了实验、是否有结果、是否愿意缩小 claim；
- evaluation 不能只看文本流畅度，要看 coverage、faithfulness、strategic coherence、input utilization 和 discourse quality。
- 对 reviewer 心理状态和语气的建模要保持克制，输出应是可检查的 `reviewer_stance`、`pressure`、`uncertainty`，而不是断言 reviewer 的真实动机。

对我们框架的影响：

- 我们应该把系统叫 **Author Rebuttal Assistant**，不是自动 rebuttal writer。
- 最核心输出不是最终回复，而是 `concern map + strategy plan + evidence plan + draft + warnings + provenance`。
- 训练侧优先做 alignment、classification、retrieval、planning，不优先做端到端生成。

### 2.3 Peer review assistance / reviewer feedback 方向

相关工作：

- [Review Feedback Agent](https://www.nature.com/articles/s42256-026-01188-x) 在 ICLR 2025 进行大规模随机实验，使用多个 LLM 给 reviewer 提供反馈，目标是提高 review clarity、specificity 和 actionability。
- [OpenReviewer](https://arxiv.org/abs/2412.11948) 是面向 scientific paper review generation 的专用模型，展示了结构化 review template 和 domain-specific fine-tuning 的价值。

可借鉴点：

- clarity、specificity、actionability 是 peer review/rebuttal 系统的关键评价维度；
- 多模型或多模块反馈可以改善审稿文本质量；
- 但是 review generation 和 rebuttal assistance 是不同任务：reviewer 侧要找问题，author 侧要理解问题、组织证据和回应。

对我们框架的影响：

- 我们的评价指标应包括 actionability 和 specificity；
- 但不要把系统做成“替 reviewer 审稿”，而是让作者更好理解和回应 reviewer。

### 2.4 RAG、科学证据和事实核查方向

相关工作：

- [RAG](https://arxiv.org/abs/2005.11401) 的基本思想是把生成模型和外部知识检索结合，适合知识密集任务。
- [PaperQA](https://arxiv.org/abs/2312.07559) 展示了面向 scientific literature 的 retrieval-augmented agent，需要检索、综合和引用全文证据。
- [Self-RAG](https://arxiv.org/abs/2310.11511) 强调 retrieve、generate、critique 的自反流程。
- [SciFact](https://www.aclweb.org/anthology/2020.emnlp-main.609.pdf) 和 [FEVER](https://arxiv.org/abs/1803.05355) 提供了 evidence retrieval + claim verification 的任务范式。
- [FActScore](https://arxiv.org/abs/2305.14251) 把长文本生成拆成 atomic facts，再检查每个 atomic fact 是否被可靠知识源支持。

可借鉴点：

- rebuttal draft 里的每个事实性陈述都应该能找到依据；
- 可以把生成内容拆成 atomic claims，再逐条验证；
- RAG 不是只把 top-k 文档塞给模型，而是要有检索、重排、引用、核查、失败处理；
- 对 reviewer concern 的回应要能显示“这个建议来自哪条历史案例、哪段原文、哪种策略”。

对我们框架的影响：

- 我们的 Integrity Checker 应该借鉴 FActScore/SciFact：把 draft 中的 claim 拆出来，再判断 supported / unsupported / needs_author_confirmation。
- Case Retrieval Agent 不只是找相似文本，还要找相似 concern、相似 strategy、相似 evidence action。

### 2.5 Nature transparent peer review 数据来源

相关工作/政策：

- Nature Communications 从 2016 年开始让作者选择公开 reviewer comments 和 author responses，2022 年宣布对所有符合条件的研究论文公开这些 exchanges。
- Nature Portfolio peer review policy 明确 transparent peer review 文件可能包含 reviewer comments、author rebuttal letters，以及部分 editorial decision letters。
- Nature reviewer guide 强调 review 应关注 novelty、claim convincingness、further evidence、overselling、method detail、statistical soundness 和 ethical concerns。

可借鉴点：

- Nature 的 reviewer guide 可以直接变成我们的 risk taxonomy 来源；
- transparent peer review file 是很强的数据资产，但也不是完整编辑过程，可能缺少 confidential comments 和 editor 内部讨论；
- 对外发布时要保守处理全文再分发问题，优先发布 metadata、hash、offset、derived labels 和脚本。

对我们框架的影响：

- 我们的 risk taxonomy 不应凭空设计，可以和 Nature reviewer guide 对齐；
- 论文里不能声称“完整还原编辑决策”，只能说“基于公开 peer review file 的可观察互动链”。

## 3. 我们自己的完整框架

我们最终应该设计一个 **Nature Rebuttal Knowledge Base + Author Rebuttal Assistant Workflow**。

一句话：

> 基于 Nature 系列公开同行评审文件，把 reviewer comment、author response 和 editor decision 中可观察的互动关系结构化成可检索知识库，并构建一个 evidence-grounded、author-in-the-loop、可追溯、可评估的 rebuttal assistant，帮助作者理解审稿关切、规划回应策略、补充证据、校准语气，并避免编造和过度承诺。

## 4. 数据层框架

### 4.1 数据来源

当前以 `v2709` 为基准：

| 数据 | 当前数量 | 用途 |
|---|---:|---|
| paper records | 2709 | 主语料和 provenance |
| core full-chain papers | 339 | review-response-decision case |
| response-only papers | 1400 | review-response strategy learning |
| review-only input papers | 860 | reviewer concern extraction 输入 |
| heuristic pairs all | 21978 | 原始 pair pool |
| heuristic pairs clean | 11311 | 弱监督和检索候选 |
| demo-ready pairs | 9858 | retrieval/demo pool |
| demo-ready cases | 738 | paper-level demo |
| model-confirmed subset | 45 | 小批量评测集 |

### 4.2 最小知识单元

不要只用 paper 作为最小单位。建议采用 6 层结构：

```text
Paper
  -> Review Round
    -> Reviewer Comment
      -> Atomic Concern
        -> Author Response Span
          -> Evidence / Revision Action
            -> Decision Signal
```

### 4.3 核心字段

每条 `RebuttalInteractionUnit` 至少包含：

```json
{
  "unit_id": "...",
  "paper_id": "...",
  "doi": "...",
  "journal": "...",
  "year": 2025,
  "round_id": "unknown_or_detected",
  "reviewer_id": "reviewer_1_or_unknown",
  "review_comment": "...",
  "atomic_concern": "...",
  "concern_type": "...",
  "risk_type": "...",
  "author_response_span": "...",
  "response_strategy": "...",
  "evidence_type": "...",
  "tone_stance": {
    "reviewer_stance": "...",
    "author_tone": "...",
    "confidence": "...",
    "commitment_level": "..."
  },
  "decision_signal": {
    "has_decision": true,
    "decision_text_preview": "...",
    "observable_outcome": "accepted_after_revision_or_unknown"
  },
  "provenance": {
    "source_json_path": "...",
    "source_field": "...",
    "source_offsets": {},
    "extraction_method": "...",
    "label_source": "heuristic_or_model_assisted_or_human"
  }
}
```

## 5. Agent 工作流框架

为了不过度复杂，建议先保留 6 个主模块，而不是一开始拆成十几个 agent。

```text
输入：reviewer comments + manuscript context + optional author notes

1. Concern Mapper
   拆分 reviewer comment，抽取 atomic concerns、显性要求和隐含风险。

2. Risk and Strategy Planner
   判断每个 concern 属于哪类风险，并给出候选回应策略。

3. Nature Case Retriever
   从 v2709 知识库中检索相似 concern、相似 strategy、相似 evidence action 的历史案例。

4. Evidence and Revision Planner
   明确需要什么证据、哪些内容作者必须确认、哪些 claim 应该缩小。

5. Rebuttal Composer
   生成结构化 outline 和 draft paragraphs，不直接宣称为最终回复。

6. Integrity and Tone Gate
   检查事实依据、过度承诺、过度迎合、防御性语气、缺失 provenance。

输出：traceable rebuttal plan + draft + warnings + retrieved cases + author questions
```

### 5.1 Concern Mapper

输入：

- reviewer comment；
- manuscript title/abstract；
- 可选 manuscript section。

输出：

- atomic concerns；
- concern_type；
- reviewer explicit request；
- implicit risk；
- severity；
- target object。

关键点：

- 一个长 review comment 可能包含多个 concern；
- 一个 concern 可能需要多个 response actions；
- 不要把所有问题都当成“补实验”。

### 5.2 Risk and Strategy Planner

输入：

- atomic concerns；
- manuscript metadata；
- 可选 decision letter。

输出：

- risk_type；
- strategy_candidates；
- decision_relevance；
- rationale。

推荐 risk taxonomy：

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

推荐 strategy taxonomy：

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

### 5.3 Nature Case Retriever

输入：

- concern summary；
- concern_type；
- risk_type；
- strategy candidate；
- journal/field metadata。

检索方式：

1. 先用当前已验证较好的 `hybrid_bm25_concern_strategy`；
2. 再加入 embedding retrieval；
3. 再做 reranker；
4. 对 full-chain 子集加入 decision-aware filter。

输出：

- top-k similar cases；
- 每个 case 的 reviewer concern；
- author response strategy；
- evidence action；
- source path 和 offset；
- 是否同领域、同 journal family、同 risk type。

### 5.4 Evidence and Revision Planner

输入：

- concern；
- retrieved cases；
- manuscript context；
- author notes。

输出：

- evidence_needed；
- manuscript_change_plan；
- author_must_confirm；
- unsupported_gap；
- claim_scope_action。

核心原则：

- 如果没有作者确认，不能写“we performed a new experiment”；
- 可以写“the authors should consider adding...”或用 placeholder；
- 对无法证明的地方，明确标记 `needs_author_confirmation`。

### 5.5 Rebuttal Composer

输入：

- concern map；
- strategy plan；
- evidence plan；
- retrieved examples；
- author confirmations。

输出：

- structured outline；
- response draft；
- placeholders；
- alternative phrasings。

推荐段落结构：

```text
1. Acknowledge reviewer concern
2. State direct answer
3. Provide evidence or planned revision
4. Specify manuscript change
5. Calibrate scope / limitation if needed
```

### 5.6 Integrity and Tone Gate

输入：

- draft；
- evidence plan；
- retrieved cases；
- source provenance；
- author confirmations。

输出：

- integrity_pass；
- unsupported claims；
- fabricated evidence risk；
- overclaim risk；
- sycophancy risk；
- defensive tone risk；
- missing provenance；
- required fixes。

这里的 tone 不是“更温暖”，而是“更准确、更克制、更合作”。

## 6. 训练侧框架

### 6.1 不建议现在做的事

现在不应该优先做：

- 大规模端到端 rebuttal generator 微调；
- 直接用 9858 条 heuristic pair 当 gold；
- 直接训练 outcome prediction；
- 声称系统能提高 Nature 接收率；
- 让 agent 自动承诺新增实验。

### 6.2 应该先做的事

训练侧建议分 5 步：

#### Step A：扩展 model-assisted seed

从 9858 条 demo-ready pairs 中分层抽 100-200 条，补充：

- atomic concern；
- risk type；
- response strategy；
- evidence type；
- tone/stance；
- commitment level；
- offset recoverability；
- label confidence。

输出：

```text
data/training/author_rebuttal_agent/v2709/seed_200.jsonl
```

#### Step B：训练/评估分类模块

先做轻量模型或 prompt classifier：

- concern classifier；
- risk classifier；
- strategy classifier；
- evidence type classifier；
- tone/stance classifier。

指标：

- accuracy；
- macro-F1；
- per-class F1；
- abstention rate；
- calibration。

#### Step C：训练/评估 retrieval/reranker

任务：

- 给一个 reviewer concern，检索最有用的 Nature 历史案例。

指标：

- concern hit@5；
- strategy hit@5；
- joint hit@5；
- MRR；
- provenance recoverability；
- human usefulness。

#### Step D：训练/评估 evidence planner

任务：

- 判断需要 existing evidence、new analysis、new experiment、citation、limitation、editorial change，还是 author confirmation。

指标：

- evidence type F1；
- unsupported commitment recall；
- author confirmation detection；
- overclaim prevention。

#### Step E：做小批量 workflow 对比评测

比较：

- vanilla LLM；
- retrieval only；
- workflow without integrity gate；
- workflow without author confirmation；
- full workflow。

评价：

- concern coverage；
- faithfulness；
- specificity；
- actionability；
- evidence grounding；
- tone appropriateness；
- overclaim risk；
- human preference。

## 7. 我们与已有工作的差异化

| 方向 | 别人在做什么 | 我们应该怎么做 |
|---|---|---|
| OpenReview rebuttal | 多集中在 ICLR/ACL/ML conference rebuttal | 聚焦 Nature 系列公开 peer review file |
| 自动生成 | 很多工作比较 direct generation vs structured generation | 明确做 assistant，不做自动替代作者 |
| 数据结构 | review-response 或 review-response-revision triplets | 加入 reviewer-author-editor 可观察互动链 |
| 证据 | 依赖 paper context 或外部检索 | 用 v2709 历史案例 + manuscript evidence + author confirmation |
| 评价 | coverage、faithfulness、discourse | 加 provenance recoverability、unsupported commitment、overclaim risk |
| 语气 | 礼貌/流畅度 | tone calibration，避免防御和过度迎合 |
| 贡献 | 单系统或单数据集 | Nature KB + RAG-agent workflow + evaluation framework |

## 8. 最终 MVP 形态

最终 MVP 不应该是一个聊天框直接说“我给你写好了”。

更合理的输出是：

```json
{
  "concern_map": [
    {
      "concern_id": "c1",
      "concern_summary": "...",
      "risk_type": "...",
      "severity": "...",
      "target_object": "..."
    }
  ],
  "retrieved_cases": [
    {
      "case_id": "...",
      "why_retrieved": "...",
      "historical_strategy": "...",
      "source": {
        "paper_id": "...",
        "source_json_path": "...",
        "offsets": {}
      }
    }
  ],
  "evidence_plan": [
    {
      "concern_id": "c1",
      "needed_evidence": "...",
      "status": "available_or_author_must_confirm",
      "risk_if_missing": "..."
    }
  ],
  "draft": {
    "outline": [],
    "paragraphs": [],
    "placeholders": []
  },
  "integrity_report": {
    "pass": false,
    "warnings": [],
    "required_author_confirmations": []
  }
}
```

## 9. 当前最该执行的下一步

下一步不是再扩爬虫，也不是直接做大模型训练。

最合理的顺序是：

1. **固化最终 agent schema。**
   把 concern map、retrieved case、evidence plan、draft、integrity report 的 JSON schema 定下来。

2. **从 v2709 扩展 100-200 条 training/evaluation seed。**
   用现有 API 模型做 model-assisted 标注，但保持 `label_source=model_assisted`。

3. **跑一个正式小批量 workflow comparison。**
   比较 vanilla LLM、retrieval only、no integrity、full workflow。

4. **把检索从 BM25/hybrid 升级到 embedding + reranker。**
   先不要追求复杂，先看 top-k case usefulness 是否提升。

5. **把 Integrity Checker 做成正式模块。**
   这是我们和“普通会写回复的 LLM”拉开差异的关键。

## 10. 最终研究主张应该怎么写

可以主张：

- 我们构建了一个基于 Nature transparent peer review files 的审稿互动知识库；
- 我们提出了一个 evidence-grounded、author-in-the-loop 的 Author Rebuttal Assistant 框架；
- 我们把 rebuttal assistance 拆成 concern mapping、case retrieval、evidence planning、drafting 和 integrity checking；
- 我们用 v2709 数据验证了小规模 retrieval 和 workflow 的可行性；
- 我们的框架比直接生成回复更可追溯、更可评估、更符合学术完整性要求。

暂时不能主张：

- 系统能自动写出最终可提交 rebuttal；
- 系统能替代作者或审稿人；
- 系统能预测或提高 Nature 接收率；
- 当前标签是人工 gold；
- 当前 tone / emotion 标签已经被充分验证。

## 11. 一句话总结

我们最终要做的不是“Nature rebuttal 自动生成器”，而是：

> 一个基于 Nature 真实公开审稿互动案例的、可检索、可追溯、可评估、作者参与确认的 rebuttal planning assistant。它先理解审稿关切，再检索历史案例，规划证据和修改，生成结构化草稿，并用完整性检查防止编造、过度承诺和语气失衡。
