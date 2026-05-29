# Author Rebuttal / Peer Review Assistant 研究计划

> 版本：2026-05-20
> 项目阶段：从数据扩展转向知识库、评测任务与智能体工作流设计
> 数据起点：Nature 系列公开同行评审数据 v2709
> 工作目录：`C:\Users\wancy\Desktop\nature-comment`

## 0. 项目一句话目标

本项目旨在基于 Nature 系列公开同行评审数据，构建一个 Author Rebuttal / Peer Review Assistant 系统。系统需要理解审稿意见、作者回复和编辑决策之间的互动关系，识别审稿人的真实关切与风险点，总结作者常用的有效回应策略，并基于真实历史案例辅助作者组织 rebuttal、补充证据、调整语气和回应结构。

项目重点已经从继续爬取数据，转向把现有 v2709 数据转化为可检索、可评估、可用于智能体工作流的审稿互动知识库。除非后续论证明确说明现有数据不足，否则不应默认继续做爬虫或扩展数据抓取。

---

## 1. Intake and Stage Detection

### 1.1 当前阶段判断

当前项目处于 `evidence_started` 阶段。

理由如下：

- 已有正式数据版本 v2709。
- 已有数据审计报告、数据总结和导出数据包。
- 已有 schema、taxonomy、处理流水线和部分实验产物。
- 已经生成 Author Rebuttal MVP 数据包。
- 还没有完成文献定位、正式实验设计、人工评估、baseline 对比和论文 claim ledger。

因此，当前不是 `raw_idea`，也不是 `draft_started`。最准确的定位是：已经有数据和原型基础，但还没有形成可投稿论文的研究设计闭环。

### 1.2 已有材料

| 类别 | 当前材料 | 状态 |
|---|---|---|
| 正式主库 | `scraped_data/20_curated/final_nature_science_peer_review_corpus_index.json` | 已有，v2709 |
| 正式逐篇 JSON | `scraped_data/20_curated/final_nature_science_peer_review_corpus/` | 已有 |
| 导出数据包 | `extend_nature_science/` | 已同步到 v2709 |
| 数据集中文总结 | `extend_nature_science/数据集完整总结.md` | 已更新 |
| 数据审计报告 | `data/evaluation/reports/data_audit_report.md` | 已有 |
| Author Rebuttal 数据审核 | `data/evaluation/reports/author_rebuttal_mvp_data_audit.md` | 已生成 |
| MVP 数据包 | `data/processed/author_rebuttal_mvp/v2709/` | 已生成 |
| concern taxonomy | `data/processed/taxonomies/concern_taxonomy.v1.json` | 已有 |
| response strategy taxonomy | `data/processed/taxonomies/response_strategy_taxonomy.v1.json` | 已有 |
| interaction schema | `src/peer_review_skills/schemas/interaction_unit.py` | 已有 |
| 旧 interaction 产物 | `data/processed/interaction_units/interaction_units.jsonl` | 可参考，但不应作为最终 v2709 官方监督数据 |
| skill cards | `data/processed/skill_cards/mvp/` | 已有，需重新基于 v2709 审核 |
| readiness 报告 | `data/evaluation/reports/system_readiness_report.md` | 已有 |

### 1.3 当前关键数据规模

来自 v2709 和 MVP 数据包的已核查数字：

| 指标 | 数值 |
|---|---:|
| 正式论文记录 | 2709 |
| 含 author response 的论文 | 1804 |
| 同时含 author response 和 decision letter 的论文 | 351 |
| 高质量 rebuttal 相关论文级案例 | 1739 |
| 高质量 full-chain 案例 | 339 |
| 高质量 response-only rebuttal 案例 | 1400 |
| review-only 输入池 | 860 |
| editor decision-only 池 | 42 |
| heuristic rebuttal pairs | 21978 |
| clean heuristic pairs | 11311 |
| demo-ready pairs | 9858 |
| demo-ready paper cases | 738 |

### 1.4 缺失材料

| 缺失项 | 当前状态 | 影响 |
|---|---|---|
| source-grounded literature review | planned | 不能强写 novelty claim |
| 数据许可和再分发策略核查 | planned | 影响 dataset release 和论文伦理部分 |
| v2709 schema freeze | partially supported | 影响复现实验和知识库稳定性 |
| 人工标注 / 人工校验子集 | planned | 影响 taxonomy 和 pair extraction 可信度 |
| retrieval baseline | planned | 影响系统论文实证贡献 |
| agent workflow prototype | planned | 影响 MVP 可演示性 |
| automatic + human evaluation | planned | 影响可投稿性 |
| ablation / error analysis | planned | 影响方法贡献可信度 |
| 目标 venue 定位 | planned | 影响写作风格和贡献组合 |

### 1.5 当前最优先任务

当前最优先任务不是继续爬虫，而是按以下顺序推进：

1. **Knowledge base construction**：冻结 v2709 schema，形成可追溯、可检索的 review-response-decision 知识库。
2. **Retrieval / evaluation design**：把系统转化为可评估任务，而不是只做 demo。
3. **Agent workflow design**：在知识库和评测任务明确后，设计 Author Rebuttal Assistant 多智能体流程。
4. **Paper framing**：在文献定位和实验计划之后，确定论文主线和贡献表述。

### 1.6 Idea-to-Paper 质量门

本计划按 `$idea-to-paper-pipeline` 的硬门槛执行。任何后续写作、实验或系统实现都必须保留从 claim 到 evidence 的可追溯链路：

`idea -> RQ -> prior work -> method -> evidence -> claims -> manuscript -> critique -> revision`

当前阶段的硬门槛如下：

1. **不写论文正文**：在完成 source-grounded literature review 和 experiment plan 前，不进入 introduction / related work 正文写作。
2. **不强写 novelty claim**：所有“首次”“最大”“优于已有系统”等表述，在文献矩阵完成前一律标记为 `planned` 或 `unverified`。
3. **不把 heuristic 当 gold**：`heuristic_rebuttal_pairs_*` 只能作为候选训练/检索资源，不能作为人工金标或最终监督标签。
4. **不把 demo 当评测**：系统贡献必须至少包含 retrieval baseline、agent workflow baseline 和 integrity / overclaim 检查。
5. **不让传播超过证据**：后续 slide、demo、项目页或论文摘要必须显式说明数据许可、heuristic alignment 和 assistant 边界。

---

## 2. RQ Brief

### 2.1 主研究问题

如何将 Nature 系列公开同行评审材料转化为一个可追溯、可检索、可评估的审稿互动知识库，并基于该知识库构建辅助作者理解审稿关切、检索历史回应策略、规划证据补充和组织 rebuttal 的 Author Rebuttal / Peer Review Assistant？

### 2.2 子研究问题

1. 公开 peer review 文档中的 reviewer concern、author response strategy 和 editor decision signal 能否被结构化为可复用的知识单元？
2. 基于真实历史案例的 retrieval 是否能帮助系统为新的审稿意见推荐更合适的回应策略和证据补充方向？
3. 多智能体 workflow 是否能将 review understanding、risk classification、case retrieval、evidence planning、tone editing 和 integrity checking 串成一个可评估的 author rebuttal assistance 流程？
4. 如何设计自动评估和人工评估，使系统不是只生成流畅 rebuttal，而是保持 evidence-grounded、provenance-aware、不过度承诺？

### 2.3 目标领域

本项目位于以下交叉领域：

- AI for peer review
- author rebuttal assistance
- scientific communication
- scientific writing support
- LLM agent workflow
- retrieval-augmented generation over scholarly documents
- evidence-grounded academic assistance

### 2.4 目标论文类型

推荐定位为：**混合型系统论文 + 知识库论文 + 评测论文**。

不建议单独定位为纯 dataset paper。原因是项目已有数据并非来自全新发布机制，而是对公开 peer review 材料的结构化利用。最有潜力的贡献不是“又爬了一个数据集”，而是：

- 如何把公开审稿材料转成审稿互动知识库；
- 如何设计 review concern / response strategy / decision-aware retrieval 任务；
- 如何基于真实案例构建 Author Rebuttal Assistant workflow；
- 如何控制 evidence grounding 和 overclaim 风险。

### 2.5 In Scope

- Nature 系列公开同行评审材料 v2709。
- review concern extraction。
- risk point classification。
- author response strategy modeling。
- review-response alignment。
- evidence recommendation。
- retrieval-grounded rebuttal planning。
- decision-aware case retrieval。
- provenance-aware assistant workflow。
- automatic + human evaluation。

### 2.6 Out of Scope

- 默认继续爬取更多数据。
- 自动替作者生成不可验证的实验承诺。
- 伪造实验、数据、引用或修改承诺。
- 替代审稿人、编辑或作者做最终学术判断。
- 判断论文是否应该接收。
- 未经许可核查就公开再分发完整原始 peer review 文本。
- 将系统定位为操纵审稿过程的工具。

---

## 3. FINER Assessment

### 3.1 Feasible

**评估：pass with risk**

已有 v2709 数据足以支撑初步论文贡献：

- `2709` 篇正式记录；
- `1804` 篇有 author response；
- `351` 篇同时有 author response 和 decision letter；
- `1739` 篇高质量 rebuttal 相关论文级案例；
- `9858` 条 demo-ready pairs；
- `738` 个 demo-ready paper cases。

可行性风险主要在于：

- 当前 `heuristic_rebuttal_pairs_*` 是启发式抽取，不是人工金标。
- 旧 `data/processed/interaction_units` 可参考，但不应直接作为官方 v2709 监督数据。
- 需要建立小规模人工验证集，确认 concern/strategy/alignment 质量。

### 3.2 Interesting

**评估：pass**

作者 rebuttal 是高频、高成本、高风险的学术写作任务。现有 LLM 可以生成回复，但容易出现：

- 回应不对齐审稿人真实关切；
- 过度礼貌但缺少实质修改；
- 编造实验或承诺；
- 缺少历史案例支撑；
- 难以区分 reviewer concern、editor risk 和 author action。

因此，用真实历史 peer review 互动案例构建 assistant 有明确实践价值。

### 3.3 Novel

**评估：risk**

潜在新意包括：

- 使用 Nature 系列公开同行评审材料，而不是只依赖 OpenReview 或会议评审数据；
- 建模 reviewer concern、author response 和 editor decision 的互动关系；
- 强调 provenance-aware response strategy retrieval；
- 把 rebuttal assistant 定位为 evidence planner 和 integrity checker，而非单纯文本生成器。

但这些 novelty claim 必须通过 literature review 验证。目前只能标记为 `planned` 或 `unverified`，不能直接写成论文结论。

### 3.4 Ethical

**评估：risk**

需要重点处理：

- 公开同行评审数据的版权、许可、再分发边界；
- 审稿人和作者文本虽然公开，但仍可能有上下文敏感性；
- 系统可能被误用为“策略化迎合审稿人”的工具；
- LLM 可能编造实验、伪造修改承诺或过度承诺；
- 自动 rebuttal 可能削弱作者对学术责任的承担。

治理定位必须明确：

> 系统是 assistant，不是 author、reviewer 或 editor 的替代品。

### 3.5 Relevant

**评估：pass**

项目与以下活跃问题直接相关：

- AI for science；
- peer review assistance；
- scientific writing support；
- RAG over scholarly documents；
- LLM agents for academic workflows；
- responsible AI in scholarly communication。

### 3.6 最大失败风险

最大风险不是数据规模不足，而是论文贡献被质疑为：

- “只是把公开数据做了简单抽取”；
- “只是一个 RAG demo”；
- “没有可靠评估”；
- “生成 rebuttal 有伦理风险”。

规避方式：

- 把贡献主线放在知识库 schema、任务定义、provenance、评估和 integrity checking；
- 不夸大生成能力；
- 用 baseline、ablation 和人工评估证明系统各模块的作用；
- 明确 assistant 边界。

---

## 4. Contribution Framing

### 4.1 路线 A：审稿互动知识库 / Dataset Paper

**核心想法**

构建 Nature peer review interaction knowledge base，将 paper、reviewer report、author response、editor decision、concern、strategy 和 provenance 结构化。

**可能贡献**

1. v2709 Nature peer review interaction corpus。
2. review-response-decision schema。
3. concern / response strategy taxonomy。
4. 数据统计、覆盖分析和局限性。

**优点**

- 与现有数据最贴合。
- 不依赖复杂 agent 效果。
- 可以较快形成可复现数据资产。
- 适合后续所有系统和实验。

**缺点**

- 纯 dataset paper 可能创新性不足。
- 数据再分发风险较高。
- 需要清楚证明区别于 OpenReview、PeerRead 等已有数据。
- 如果不能公开全文，只能发布 metadata/schema/splits，贡献表达会受限。

### 4.2 路线 B：Author Rebuttal Assistant / RAG-agent 系统论文

**核心想法**

构建一个基于真实历史 peer review 案例的 RAG-agent 系统，输入审稿意见，输出 concern/risk、相似案例、证据补充建议、rebuttal outline、tone revision 和 integrity warnings。

**可能贡献**

1. 一个可运行的 Author Rebuttal Assistant。
2. RAG + multi-agent workflow。
3. 对比 vanilla LLM、template-only、retrieval-only baseline。
4. 人工评估系统输出的 helpfulness、grounding、specificity 和 safety。

**优点**

- 应用价值强。
- 容易展示。
- 与项目最终目标一致。

**缺点**

- 如果没有强评估，容易被认为只是 demo。
- agent 设计需要证明必要性。
- 生成式系统有 hallucination 和 overclaim 风险。

### 4.3 路线 C：审稿关切与回应策略的实证分析 + Assistant Workflow

**核心想法**

先基于 v2709 分析 reviewer concern、author strategy、evidence request、decision signal 的分布和组合，再基于这些实证发现设计 provenance-aware Author Rebuttal Assistant。

**可能贡献**

1. 审稿互动知识库。
2. concern / strategy / risk 的实证分析。
3. retrieval-grounded assistant workflow。
4. evidence-grounded 与 integrity-aware evaluation。

**优点**

- 数据、分析、系统三者能形成完整链条。
- 不完全依赖生成质量。
- 更适合将 scientific communication 理论融入 AI 系统。
- 可以避免“纯数据集不够新”和“纯 demo 不够严谨”的问题。

**缺点**

- 工作量更大。
- 需要清晰控制 claim 强度。
- 需要人工验证 taxonomy 和 retrieval 质量。

### 4.4 推荐路线

推荐采用 **路线 C：审稿关切与回应策略的实证分析 + provenance-aware Author Rebuttal Assistant workflow**。

原因：

- v2709 数据已经足以支撑实证分析和系统设计。
- 项目已有 `1739` 篇高质量 rebuttal 相关案例和 `9858` 条 demo-ready pairs。
- full-chain 子集可以支持 decision-aware case retrieval。
- 论文贡献可以同时覆盖数据、方法、系统和评估。
- 伦理上更稳：系统不是自动写 rebuttal，而是帮助作者理解、检索、规划和检查。

推荐论文主线：

> We construct a provenance-aware peer review interaction knowledge base from Nature transparent peer review materials and study how review concerns, author response strategies, and editorial decision signals can support retrieval-grounded author rebuttal assistance.

### 4.5 最小可投稿版本

路线 C 容易膨胀为“大而全”的系统工程，因此本文的最小可投稿版本必须收束为三项核心贡献：

1. **数据与知识库贡献**：基于 v2709 构建 provenance-aware peer review interaction knowledge base，明确 paper、review comment、author response、decision signal、strategy case 的 schema、来源和限制。
2. **任务与评测贡献**：定义并评估 review concern extraction / response strategy retrieval / rebuttal outline generation with integrity checking 三个核心任务。
3. **系统工作流贡献**：构建一个 retrieval-grounded、provenance-aware、带 overclaim checker 的 Author Rebuttal Assistant workflow，并与 vanilla LLM、retrieval-only、no-integrity-checker baseline 对比。

增强贡献可作为扩展实验或 case study，而不是第一版论文的阻塞项：

- decision-aware retrieval；
- tone / structure revision；
- full multi-agent ablation；
- skill-card induction；
- editor decision signal 的细粒度因果分析。

若时间或标注资源不足，第一版论文应优先保证前三个核心贡献完整闭环，而不是追求七个任务全部做完。

### 4.6 贡献强度控制

后续论文写作中应避免以下强 claim：

- “系统显著提高 rebuttal 质量”，除非完成受控人工评估。
- “历史策略导致论文接收”，除非有严格因果识别；当前只能说 “associated with decision signals”。
- “Nature v2709 是最大 author rebuttal 数据集”，除非 literature review 和 corpus comparison 已验证。
- “模型理解审稿人真实意图”，更稳妥表述是 “infers concern and risk categories from reviewer text”。

推荐默认表述：

- “provenance-aware case retrieval” 而不是 “automatic rebuttal generation”；
- “assistant for planning and checking responses” 而不是 “AI author”；
- “decision-aware exploratory analysis” 而不是 “decision-causal strategy discovery”。

---

## 5. Literature Positioning Plan

本阶段不写泛泛综述，只定义文献检索矩阵。所有 novelty claim 在完成检索前均标记为 `unverified`。

### 5.1 Peer Review NLP / Peer Review Assistance

**要回答的问题**

- 已有工作如何建模 peer review？
- 是否已有 review quality、helpfulness、recommendation、meta-review、review summarization 等任务？
- 这些任务是否处理 author response？

**关键词**

- peer review NLP
- peer review assistance
- review quality prediction
- meta-review generation
- scientific peer review dataset
- reviewer comment classification

**需要比较的 prior work / baseline**

- OpenReview 数据相关工作；
- PeerRead 相关工作；
- ICLR / NeurIPS review modeling；
- review helpfulness / review quality prediction；
- meta-review generation。

### 5.2 Rebuttal Generation / Response-to-Reviewer Modeling

**要回答的问题**

- 是否已有 reviewer comment -> author response generation 任务？
- 数据来源是什么？
- 是否考虑 evidence grounding 和 response commitment？
- 是否区分 acknowledge、add experiment、clarify、contest、defer？

**关键词**

- rebuttal generation
- response to reviewers
- author response generation
- scientific revision response
- reviewer comment response modeling

**需要比较的 baseline**

- vanilla LLM response generation；
- template-based response；
- retrieval-augmented response；
- instruction-tuned scientific writing models。

### 5.3 Scientific Claim Verification / Evidence-Grounded Writing

**要回答的问题**

- 如何防止模型编造实验、引用和证据？
- 何种 grounding 机制适合 scholarly writing？
- 如何检测 unsupported claims？

**关键词**

- scientific claim verification
- evidence-grounded generation
- citation-grounded generation
- factuality in scientific writing
- hallucination in scholarly writing

**需要比较的 baseline**

- claim verification systems；
- citation-grounded generation；
- fact-checking over scientific text；
- unsupported claim detection。

### 5.4 RAG over Scholarly Documents

**要回答的问题**

- scholarly RAG 如何处理长文档、metadata、provenance 和 citation？
- case-based retrieval 如何评估？
- dense retrieval、BM25、hybrid retrieval 在 scientific text 上如何比较？

**关键词**

- retrieval augmented generation scholarly documents
- scientific RAG
- case-based reasoning
- dense retrieval scientific text
- hybrid retrieval academic papers

**需要比较的 baseline**

- BM25；
- dense embedding retrieval；
- hybrid retrieval；
- reranking；
- metadata-aware retrieval。

### 5.5 LLM Agents for Academic Research Workflows

**要回答的问题**

- LLM agents 如何拆分 academic workflow？
- 多智能体相对单一 prompt 是否有可证明收益？
- 如何做 integrity checking？

**关键词**

- LLM agents academic writing
- research agents
- multi-agent scientific workflow
- AI research assistant
- scholarly writing assistant

**需要比较的 baseline**

- single-agent prompt；
- retrieval-only pipeline；
- multi-agent workflow；
- planner-checker architecture。

### 5.6 Peer Review Corpora: OpenReview / Nature / Transparent Review

**要回答的问题**

- 现有 peer review corpora 包含哪些字段？
- 是否有 author responses 和 editor decisions？
- 数据许可和再分发方式是什么？
- Nature transparent peer review 与 OpenReview 数据有什么差异？

**关键词**

- OpenReview dataset
- PeerRead
- transparent peer review dataset
- Nature peer review files
- peer review corpus
- reviewer report author response dataset

### 5.7 Literature Matrix Skeleton

| Source Category | Problem | Method to Inspect | Data / Benchmark to Inspect | Question to Answer | Limitation to Check | Relation to This Project | Verification |
|---|---|---|---|---|---|---|---|
| OpenReview / PeerRead peer review modeling papers | peer review text understanding | classification, summarization, quality prediction, meta-review generation | OpenReview, PeerRead, ICLR-style reviews | Do they model reviewer concern, author response, or only review text? | May lack author response and editor decision links | Defines nearest peer-review NLP baselines | unverified |
| Review quality / helpfulness prediction papers | reviewer comment usefulness and severity | supervised classifiers, LLM classifiers, rubric-based scoring | conference peer reviews | Can their labels inform risk point classification? | Quality/helpfulness is not the same as rebuttal usefulness | Potential baseline for concern/risk classification | unverified |
| Rebuttal / response-to-reviewer modeling papers | author response generation or revision response | sequence generation, instruction tuning, retrieval augmentation | reviewer comment + author response datasets | What supervision and safety constraints are used? | May optimize fluent response rather than grounded commitment | Closest task family for Author Rebuttal Assistant | unverified |
| Scientific RAG and evidence-grounded writing papers | grounded scholarly generation | BM25, dense retrieval, hybrid retrieval, reranking, citation grounding | scholarly documents, claims, citations | Which retrieval design best supports provenance-aware writing? | RAG can retrieve irrelevant or unsupported evidence | Baseline and design source for case retrieval | unverified |
| LLM academic agent workflow papers | multi-step research or writing assistance | planner-checker, multi-agent workflow, tool-using agents | academic writing / research tasks | Do agent decompositions improve quality over single-prompt systems? | Agent complexity may not improve results | Baseline for modular assistant workflow | unverified |
| Transparent peer review corpus / publisher data papers | public peer review dataset construction | data curation, schema design, licensing analysis | publisher peer review files, OpenReview, journal data | What can be redistributed and what schema fields are standard? | Licensing and ethical constraints may limit release | Positions v2709 knowledge base contribution | unverified |

---

## 6. Knowledge Base Design

### 6.1 设计目标

知识库必须满足四个要求：

1. **可检索**：能根据新的 reviewer concern 找到相似历史案例。
2. **可评估**：每个任务有输入、输出、标签、baseline 和指标。
3. **可追溯**：每条策略都能回溯到真实历史案例。
4. **可用于 agent workflow**：不同 agent 可以访问明确字段，而不是读取杂乱全文。

### 6.2 最小数据单元

推荐层级如下：

1. `paper`
2. `review_round`
3. `reviewer_report`
4. `review_comment`
5. `author_response`
6. `review_response_pair`
7. `editor_decision`
8. `strategy_case`

其中 MVP 最关键的是：

> `review_response_pair`: reviewer concern + aligned author response + strategy labels + provenance

### 6.2.1 与现有 `InteractionUnit` 的对齐原则

当前仓库已有 `src/peer_review_skills/schemas/interaction_unit.py`，其中已经定义了：

- `interaction_id`
- `paper_id`
- `round_id`
- `reviewer_id`
- `review_span_text`
- `author_response_text`
- `alignment_method`
- `alignment_confidence`
- `alignment_status`
- `source_trace`
- `concern_type`
- `concern_claim`
- `evidence_request`
- `reviewer_sentiment`
- `reviewer_severity`
- `author_strategy`
- `author_action`
- `response_stance`
- `response_outcome`

因此，后续 schema freeze 不应另起一套互不兼容的标准。建议采用两层设计：

1. **`InteractionUnit` 作为底层对齐单元**：保留现有字段，用于 review span 与 author response span 的配对、标签和 source trace。
2. **新增 `StrategyCase` / `RebuttalCase` 作为上层检索单元**：在 `InteractionUnit` 基础上聚合检索文本、策略解释、decision signal、risk type、commitment、tone、provenance 和 human validation status。

这样既能复用现有代码，又能支持 assistant workflow 所需的更高层语义字段。

### 6.3 Paper Schema 草案

```json
{
  "paper_id": "10_1038_s41592-025-02707-1",
  "doi": "10.1038/s41592-025-02707-1",
  "title": "A visual-omics foundation model to bridge histopathology with spatial transcriptomics",
  "journal": "Nature Methods",
  "journal_family": "nature_subjournal",
  "year": 2025,
  "quality": "high",
  "interaction_level": "full_chain",
  "has_reviewer_reports": true,
  "has_author_response": true,
  "has_decision_letter": true,
  "reviewer_report_count": 27,
  "author_response_len": 155072,
  "decision_letter_len": 279,
  "source_json_path": "scraped_data/20_curated/final_nature_science_peer_review_corpus/10_1038_s41592-025-02707-1.json"
}
```

### 6.4 ReviewResponsePair Schema 草案

```json
{
  "pair_id": "string",
  "paper_id": "string",
  "doi": "string",
  "round_id": "round_1|round_2|round_unknown",
  "reviewer_id": "reviewer_1|reviewer_2|reviewer_unknown",
  "review_comment": {
    "text": "string",
    "concern_type": "baseline_comparison",
    "risk_type": "insufficient_evidence",
    "severity": "minor|moderate|major|blocking|unknown",
    "evidence_request": "experiment|analysis|data|code|clarification|statistics|unknown"
  },
  "author_response": {
    "text": "string",
    "strategy": "add_new_experiment",
    "stance": "agree|partial|disagree|neutral",
    "commitment": "performed|promised|clarified|declined|deferred|unknown",
    "evidence_type": ["new_experiment", "new_analysis"],
    "tone": "deferential|assertive|neutral|corrective"
  },
  "editor_decision_signal": {
    "available": true,
    "decision_text": "string",
    "decision_stage": "revision|accept|reject|unknown",
    "signal": "positive|conditional|negative|unknown"
  },
  "alignment": {
    "status": "matched|ambiguous|missing_response|unsupported",
    "confidence": 0.82,
    "method": "heuristic|model|human"
  },
  "provenance": {
    "source_json_path": "string",
    "json_pointer": "/peer_review/author_response",
    "source_offsets": {
      "review_start": 0,
      "review_end": 100,
      "response_start": 200,
      "response_end": 500
    },
    "extraction_method": "official_v2709_response_marker_window_v1"
  }
}
```

### 6.5 需要表示的核心语义字段

| 字段 | 说明 | 当前状态 | Schema 层级 |
|---|---|---|
| `concern_type` | 审稿关切类型 | 已有 taxonomy v1 | `InteractionUnit` |
| `concern_claim` | 审稿意见中的核心主张或要求 | 已有 schema 字段，需 v2709 重跑/校验 | `InteractionUnit` |
| `evidence_request` | reviewer 要求的证据类型 | 已有 schema 字段 | `InteractionUnit` |
| `reviewer_severity` | 审稿意见严重程度 | 已有 schema 字段 | `InteractionUnit` |
| `author_strategy` | 作者回应策略 | 已有 taxonomy v1 | `InteractionUnit` |
| `response_stance` | 作者回应立场 | 已有 schema 字段 | `InteractionUnit` |
| `response_outcome` | 回应是否 addressed / contested / deferred 等 | 已有 schema 字段 | `InteractionUnit` |
| `risk_type` | 对论文接收或可信度的风险 | planned | `StrategyCase` |
| `evidence_type` | 回复实际使用或建议补充的证据 | planned | `StrategyCase` |
| `tone` | 回复语气 | planned | `StrategyCase` |
| `commitment` | 作者是否承诺修改、补实验、补分析 | planned | `StrategyCase` |
| `decision_signal` | 编辑决策信号 | partially available, needs parsing | `StrategyCase` / paper-level |
| `alignment_status` | review 与 response 是否匹配 | 现有旧流水线可参考，v2709 需重跑或校验 | `InteractionUnit` |
| `provenance` | 回溯原文位置 | v2709 MVP 数据包已有 source path 和 offsets | both |

### 6.6 多轮审稿处理

需要保留：

- `round_id`
- `reviewer_id`
- `comment_id`
- `response_id`
- `decision_id`
- `pair_confidence`

如果自动无法判断轮次，应保留 `round_unknown`，不能丢弃记录。多轮审稿的重点不是强行完美切分，而是让系统知道哪些判断是确定的、哪些是不确定的。

### 6.7 Provenance 规则

每个策略案例必须能追溯到：

- DOI；
- journal；
- year；
- source JSON path；
- source field；
- source offsets；
- extraction method；
- confidence；
- human/model/rule validation status。

没有 provenance 的案例不能进入正式 assistant retrieval。

### 6.8 数据质量与发布分层

计划中的“高质量”“clean”“demo-ready”必须在论文和数据说明中显式定义，避免被误读为人工金标。

推荐发布/使用分层：

| 层级 | 用途 | 允许 claim | 禁止 claim |
|---|---|---|---|
| raw v2709 paper records | 数据审计、统计、重新抽取 | 正式主库规模与字段覆盖 | interaction-level 标签正确 |
| heuristic pairs all | 候选池、召回分析 | 可作为弱监督候选 | 金标配对、最终评估 |
| clean heuristic pairs | 检索候选、人工抽样池 | 规则过滤后的高置信候选 | 人工验证质量 |
| demo-ready pairs | demo、初步 retrieval prototype | 可演示的 provenance-linked case | 可投稿性能结论 |
| human-validated subset | retrieval/eval/test set | 可作为评测基准 | 覆盖所有领域/期刊 |

第一版论文至少需要一个 human-validated subset。建议从 full-chain、response-only 和 hard negative 中分层抽样，标注 concern relevance、strategy relevance、alignment correctness 和 unsafe commitment。

---

## 7. Task and Evaluation Design

### 7.0 第一版任务优先级

七个任务都合理，但第一版论文不应把所有任务都作为核心实验。推荐优先级如下：

| 优先级 | 任务 | 第一版定位 |
|---|---|---|
| P0 | Review Concern Extraction | 核心任务 |
| P0 | Author Response Strategy Retrieval | 核心任务 |
| P0 | Rebuttal Outline Generation with Integrity Checking | 核心任务 |
| P1 | Risk Point Classification | 支撑任务，可并入 concern extraction |
| P1 | Evidence Recommendation | 支撑任务，可作为 rebuttal outline 的中间输出 |
| P2 | Decision-Aware Case Retrieval | 扩展任务或 case study |
| P2 | Tone / Structure Revision | 扩展任务或 demo 功能 |

P0 任务必须有 baseline、自动指标、人工评估和 error analysis。P1/P2 任务可以先作为模块输出或消融条件，不必全部独立成完整 benchmark。

### 7.1 Task 1: Review Concern Extraction

**输入**

- reviewer comment；
- paper metadata；
- optional surrounding report context。

**输出**

- concern summary；
- concern type；
- evidence request。

**可用监督信号**

- concern taxonomy v1；
- heuristic labels；
- 人工标注子集。

**自动指标**

- accuracy；
- macro-F1；
- label-wise F1；
- summary faithfulness score。

**人工评估**

- 是否抓住主要关切；
- 是否遗漏隐含风险；
- 是否误把礼貌表达当成主问题。

**baseline**

- keyword rule；
- zero-shot LLM；
- few-shot LLM；
- fine-tuned classifier。

**失败模式**

- 把多个 concern 合并成一个；
- 将 minor presentation 问题误判为 major scientific risk；
- 忽略 reviewer 的隐含证据要求。

### 7.2 Task 2: Risk Point Classification

**输入**

- reviewer concern；
- concern type；
- paper metadata。

**输出**

- risk type；
- severity；
- risk rationale。

**可用监督信号**

- reviewer severity；
- decision signal；
- 人工标注。

**自动指标**

- macro-F1；
- calibration error；
- severity ordering accuracy。

**人工评估**

- 风险是否合理；
- 是否过度推断；
- 是否明确区分 scientific risk 和 presentation risk。

**baseline**

- rule-based severity；
- LLM classifier；
- concern-type prior baseline。

**失败模式**

- 所有问题都判为 high risk；
- 忽略 editor decision context；
- 把 reviewer opinion 当作事实。

### 7.3 Task 3: Author Response Strategy Retrieval

**输入**

- new reviewer concern；
- concern type；
- evidence request；
- optional journal/domain metadata。

**输出**

- ranked historical review-response pairs；
- recommended response strategies；
- provenance。

**可用监督信号**

- v2709 retrieval examples；
- pair confidence；
- human relevance labels。

**自动指标**

- Recall@k；
- MRR；
- nDCG；
- label match；
- metadata-aware retrieval score。

**人工评估**

- 案例是否真正相关；
- 策略是否可迁移；
- 是否有误导性相似。

**baseline**

- BM25；
- dense retrieval；
- hybrid retrieval；
- reranking；
- random same-label retrieval。

**失败模式**

- 表面词相似但策略不适用；
- 检索结果缺少 provenance；
- 过度偏向 Nature Communications。

### 7.4 Task 4: Evidence Recommendation

**输入**

- concern；
- retrieved cases；
- author-provided constraints。

**输出**

- evidence action plan；
- evidence type；
- feasibility warning。

**可用监督信号**

- author strategy labels；
- evidence cues；
- historical response actions。

**自动指标**

- evidence type F1；
- action label accuracy；
- unsupported commitment detection rate。

**人工评估**

- 建议是否可执行；
- 是否符合审稿关切；
- 是否避免承诺无法完成的实验。

**baseline**

- taxonomy mapping；
- vanilla LLM；
- retrieval-only examples。

**失败模式**

- 建议补做不现实实验；
- 把历史案例中的实验当成当前论文事实；
- 给出模糊建议。

### 7.5 Task 5: Rebuttal Outline Generation

**输入**

- reviewer concern；
- concern/risk labels；
- retrieved examples；
- author-provided facts。

**输出**

- structured rebuttal outline。

**可用监督信号**

- historical author responses；
- strategy templates；
- human rubric。

**自动指标**

- structure coverage；
- grounding score；
- unsupported claim count；
- citation/provenance coverage。

**人工评估**

- 是否完整；
- 是否具体；
- 是否礼貌但不空泛；
- 是否符合作者提供证据。

**baseline**

- vanilla LLM；
- template-only；
- retrieval-only；
- RAG without integrity checker。

**失败模式**

- 生成流畅但空泛；
- 编造实验；
- 忽视 reviewer 的核心请求；
- 过度让步或过度反驳。

### 7.6 Task 6: Tone / Structure Revision

**输入**

- draft rebuttal；
- concern type；
- intended stance。

**输出**

- revised response；
- tone warnings；
- structure suggestions。

**可用监督信号**

- historical tone patterns；
- human preference labels。

**自动指标**

- rubric-based LLM judge score；
- unsupported content preservation；
- factual consistency check。

**人工评估**

- 礼貌性；
- 清晰度；
- 具体性；
- 学术沟通适切性。

**baseline**

- grammar rewrite；
- vanilla LLM rewrite；
- template rewrite。

**失败模式**

- 改写后改变事实；
- 过度谄媚；
- 削弱关键科学立场。

### 7.7 Task 7: Decision-Aware Case Retrieval

**输入**

- concern；
- optional editor decision context；
- desired evidence type。

**输出**

- similar cases with decision signals。

**可用监督信号**

- full-chain cases；
- decision letter text；
- editor signal parser。

**自动指标**

- decision-signal match；
- Recall@k；
- nDCG；
- case utility score。

**人工评估**

- 案例是否对当前编辑风险有帮助；
- 是否正确解释 decision signal。

**baseline**

- non-decision retrieval；
- same concern retrieval；
- same journal retrieval。

**失败模式**

- 将接收结果误读为策略因果；
- 忽略编辑信号模糊性；
- 过度泛化个案。

---

## 8. Agent Workflow Design

### 8.1 Review Understanding Agent

**输入**

- reviewer comment；
- optional reviewer report context；
- paper metadata。

**输出**

- concise concern summary；
- explicit request；
- implicit risk；
- uncertainty notes。

**可调用工具**

- concern taxonomy；
- text segmenter；
- retrieval over similar comments。

**需要访问的知识库字段**

- `review_comment.text`
- `paper.title`
- `journal`
- `year`
- `concern_type`
- `evidence_request`

**禁止行为**

- 不得判断作者一定错误；
- 不得添加原文没有的实验事实；
- 不得把 reviewer opinion 当作 verified fact。

### 8.2 Concern / Risk Classifier

**输入**

- concern summary；
- review comment；
- paper metadata。

**输出**

- concern type；
- risk type；
- severity；
- evidence request；
- confidence。

**可调用工具**

- taxonomy classifier；
- severity rubric；
- decision-signal lookup。

**需要访问字段**

- concern taxonomy；
- reviewer severity；
- interaction metadata。

**禁止行为**

- 不得把所有 concern 都判成 major；
- 不得基于 journal prestige 推断风险；
- 不得输出没有置信度的强判断。

### 8.3 Case Retrieval Agent

**输入**

- concern type；
- concern text；
- evidence request；
- risk type；
- optional domain metadata。

**输出**

- top-k historical cases；
- response strategies；
- provenance；
- retrieval rationale。

**可调用工具**

- BM25；
- dense retrieval；
- hybrid retrieval；
- metadata filters；
- reranker。

**需要访问字段**

- `retrieval_examples.jsonl`
- `demo_ready_cases.jsonl`
- `concern_type`
- `author_strategy`
- `source_json_path`
- `source_offsets`

**禁止行为**

- 不得返回无 provenance 的案例；
- 不得隐藏低置信度；
- 不得把历史案例当作当前论文事实。

### 8.4 Evidence Planner

**输入**

- concern；
- retrieved cases；
- author-provided constraints。

**输出**

- evidence plan；
- possible actions；
- feasibility warnings；
- unsupported commitment warnings。

**可调用工具**

- response strategy taxonomy；
- evidence type classifier；
- integrity checker。

**需要访问字段**

- `author_strategy`
- `evidence_type`
- `commitment`
- `response_outcome`
- historical examples。

**禁止行为**

- 不得建议作者声称已完成未完成实验；
- 不得伪造数据；
- 不得伪造引用；
- 不得承诺作者未授权的修改。

### 8.5 Rebuttal Drafting Assistant

**输入**

- reviewer concern；
- evidence plan；
- author-provided facts；
- retrieved examples。

**输出**

- rebuttal outline；
- optional draft paragraphs；
- required evidence checklist。

**可调用工具**

- retrieval examples；
- tone templates；
- claim ledger。

**需要访问字段**

- concern summary；
- response strategy；
- historical response；
- provenance。

**禁止行为**

- 不得生成“we performed X”除非作者明确提供 X 已完成；
- 不得把 retrieval case 的实验复制成当前论文实验；
- 不得替作者做学术承诺。

### 8.6 Tone and Structure Editor

**输入**

- draft rebuttal；
- target stance；
- concern type。

**输出**

- revised tone；
- structure suggestions；
- clarity warnings。

**可调用工具**

- tone rubric；
- historical examples；
- unsupported claim detector。

**需要访问字段**

- author response examples；
- stance；
- strategy；
- tone labels。

**禁止行为**

- 不得改变事实内容；
- 不得将拒绝改成承诺；
- 不得过度弱化作者立场。

### 8.7 Integrity / Overclaim Checker

**输入**

- draft rebuttal；
- evidence plan；
- author-provided facts；
- source constraints。

**输出**

- unsupported claims；
- missing evidence；
- unsafe commitments；
- suggested softening。

**可调用工具**

- claim ledger；
- provenance checker；
- commitment classifier。

**需要访问字段**

- source provenance；
- author evidence；
- generated claims；
- retrieved examples。

**禁止行为**

- 不得放过无证据承诺；
- 不得把历史案例当当前论文证据；
- 不得把不确定内容改写成确定结论。

---

## 9. Claim Ledger Skeleton

| Claim | Evidence Needed | v2709 Artifact | Verification Status | Risk |
|---|---|---|---|---|
| v2709 足以支撑 Author Rebuttal Assistant 的初步知识库构建 | 数据规模、response/full-chain 数量、字段审计 | `summary.json`, `author_rebuttal_mvp_data_audit.md` | supported | 数据质量需要抽样人工验证 |
| Nature peer review 数据可被结构化为 review-response-decision 知识单元 | schema、pair extraction、provenance | `paper_manifest.jsonl`, `retrieval_examples.jsonl`, schema files | supported | pair extraction 目前是 heuristic |
| 历史 author responses 可归纳为 response strategy taxonomy | taxonomy、pair labels、examples | `response_strategy_taxonomy.v1.json`, `retrieval_examples.jsonl` | supported | taxonomy 需要人工一致性评估 |
| full-chain cases 可用于 decision-aware retrieval | full-chain subset、decision letter fields | `core_full_chain_papers.jsonl` | supported | decision signal 需要更细解析 |
| retrieval-grounded assistant 比 vanilla LLM 更可追溯 | retrieval baseline vs LLM baseline | planned experiment | planned | 效果未必更强，但 provenance 应更强 |
| integrity checker 可降低 unsupported rebuttal commitments | checker outputs + human eval | planned prototype/eval | planned | 需要对照实验 |
| 系统应作为 assistant 而非 author/reviewer/editor 替代品 | workflow constraints、ethics analysis、UI wording | design docs and rubric | supported/planned | 需要在论文和系统中持续声明 |
| 本项目相对已有 peer review corpora 有新颖性 | source-grounded literature review | literature matrix | planned | 当前不能强写 novelty claim |

### 9.1 当前不能强写的 claim

以下 claim 目前应标记为 `remove_or_soften` 或 `planned`：

- “系统显著提高 rebuttal 质量。”
- “系统优于所有现有 peer review assistant。”
- “Nature v2709 是目前最大的 author rebuttal 数据集。”
- “历史案例中的策略导致了论文接收。”
- “模型能自动判断审稿人真实意图。”

这些都需要实验、文献检索或更强证据。

---

## 10. Experiment / Validation Plan

### Phase 1: 数据审计和 Schema 固化

**目标**

将 v2709 和 Author Rebuttal MVP 数据包固化为可复现实验输入。

**产物**

- dataset card；
- frozen schema；
- train/dev/test 或 retrieval/eval split；
- provenance policy；
- sample inspection report。

**验收标准**

- 每个字段有定义；
- 每条 pair 可回溯；
- 抽样 source offsets 可恢复原文；
- A/B/C/D/E tier 定义固定；
- 数据许可风险列入 limitations。

**风险**

- 公开文本再分发许可不清；
- heuristic pair 错配；
- marker-based extraction 对部分期刊不稳。

**下一步**

抽样人工校验 100-200 条 pairs。

### Phase 2: Concern / Strategy Taxonomy 标注或弱监督构建

**目标**

稳定 concern taxonomy 和 response strategy taxonomy。

**产物**

- taxonomy v1.1；
- human-labeled validation subset；
- inter-annotator agreement；
- unknown 类别分析。

**验收标准**

- 每个 label 有定义、正例、反例；
- 标注一致性可报告；
- unknown 类别比例得到解释或下降；
- label 能支持 retrieval 和 agent workflow。

**风险**

- taxonomy 太工程化，学术解释不足；
- label 之间边界模糊；
- 单条 response 同时包含多个策略。

### Phase 3: Retrieval Baseline

**目标**

验证历史案例检索是否能找到对新 reviewer concern 有用的 response strategy cases。

**产物**

- BM25 baseline；
- dense retrieval baseline；
- hybrid retrieval baseline；
- reranker baseline；
- retrieval evaluation set。

**验收标准**

- 有 Recall@k、MRR、nDCG；
- 有 human relevance score；
- 按 concern type 分析性能；
- 报告失败案例。

**风险**

- 文本相似不等于策略相似；
- dense embedding 偏向领域词而非审稿逻辑；
- full-chain 子集分布偏向非 Nature Communications。

### Phase 4: Agent Workflow Prototype

**目标**

构建一个可记录、可追溯、可评估的 Author Rebuttal Assistant workflow。

**产物**

- agent input/output logs；
- per-agent JSON outputs；
- generated rebuttal outline；
- integrity warnings；
- provenance-linked retrieved cases。

**验收标准**

- 每条建议有来源；
- 不生成无证据实验承诺；
- integrity checker 能拦截 unsupported claims；
- 与 baseline 可比较。

**风险**

- agent 数量增加但效果不超过简单 RAG；
- 输出变长但不可用；
- 人工评估成本较高。

### Phase 5: Automatic + Human Evaluation

**目标**

评估系统是否真的有助于作者理解和组织 rebuttal。

**产物**

- automatic metrics report；
- human evaluation rubric；
- pairwise comparison；
- error analysis samples。

**验收标准**

- 至少比较 vanilla LLM、retrieval-only、agent workflow；
- 人工评分覆盖 usefulness、specificity、grounding、integrity、tone；
- 报告统计显著性或置信区间；
- 报告伦理和失败模式。

**建议实验条件**

| 条件 | 说明 | 用途 |
|---|---|---|
| Vanilla LLM | 只给 reviewer comment 和通用 rebuttal 指令 | 测量无知识库时的自然生成质量 |
| Template-only | 使用固定 rebuttal 结构模板，不检索历史案例 | 测量结构化提示的贡献 |
| Retrieval-only | 返回相似历史案例和策略，不生成完整 outline | 测量知识库与检索本身的贡献 |
| RAG draft | 检索案例后直接生成 rebuttal outline | 测量普通 RAG 能力 |
| Agent workflow | concern -> retrieval -> evidence plan -> outline -> integrity check | 测量完整工作流贡献 |
| No-integrity-checker ablation | 去掉 overclaim / unsupported commitment 检查 | 测量安全与证据约束贡献 |

**人工评估协议草案**

第一版建议采用 blind pairwise + rubric 混合评估：

- 样本：从 human-validated subset 中抽取 80-120 条 reviewer concern，覆盖 full-chain / response-only、不同 concern type、不同期刊族。
- 评估者：至少 2 名有论文投稿或审稿经验的研究者；如果资源允许，加入 1 名领域外 scientific writing evaluator。
- 盲评：隐藏系统条件名称，随机展示两个或多个候选输出。
- 评分维度：usefulness、specificity、grounding/provenance、integrity/safety、tone appropriateness、actionability。
- 额外记录：是否出现 fabricated experiment、unsupported promise、misread concern、irrelevant retrieved case。
- 一致性：报告 Cohen's kappa / Krippendorff's alpha 或至少报告 disagreement rate 与 adjudication policy。
- 统计：对 pairwise preference 报告置信区间；对 Likert score 报告均值、标准差和 bootstrap CI。

**输出必须保留的证据链**

每个被评估样本应保存：

- input reviewer comment；
- retrieved case IDs；
- provenance；
- intermediate concern/risk labels；
- generated outline；
- integrity checker warnings；
- final evaluated output；
- evaluator scores。

**风险**

- 自动指标和真实有用性相关性弱；
- human eval 主观性强；
- 需要控制 evaluator blind condition。

### Phase 6: Ablation and Error Analysis

**目标**

证明哪些模块有贡献，哪些失败模式需要限制。

**产物**

- no retrieval ablation；
- no integrity checker ablation；
- no decision signal ablation；
- no taxonomy ablation；
- error taxonomy；
- limitations section。

**验收标准**

- 每个模块贡献有数据支持；
- 对无提升模块降低 claim；
- 错误案例可复现；
- limitations 与实验结果一致。

**风险**

- ablation 差异小；
- assistant workflow 主要收益来自 retrieval 而非 agent；
- 需要软化系统贡献。

### Phase 7: Paper Claim Gate

**目标**

在写论文正文前，把实验结果、数据审计和文献定位映射到 claim ledger，决定哪些 claim 可以写进论文，哪些必须软化或删除。

**产物**

- updated claim ledger；
- CER argument map；
- table/figure plan；
- limitations checklist；
- ethics and governance statement draft。

**验收标准**

- 每个主 claim 都能追溯到数据审计、实验结果或已验证文献；
- 每个实验图表都有对应的命令、输入 split 和输出文件；
- 每个 novelty claim 都能在 literature matrix 中定位；
- 每个 assistant 能力 claim 都有 baseline 或 ablation 支撑；
- limitations 不只写伦理风险，也写数据偏差、heuristic alignment、期刊分布和人工评估边界。

---

## 11. Recommended Next Skills and Order

### 11.1 推荐顺序

#### Step 1: `academic-research-suite -> ars/deep-research` in `lit-review` mode

**目的**

做 source-grounded literature review。

**原因**

当前 novelty、closest baselines 和 target venue 仍未验证。不能在没有文献矩阵的情况下写强贡献。

**预期产物**

- literature matrix；
- closest baselines；
- gap analysis；
- verified / unverified novelty claims。

**建议提示词**

```text
Use academic-research-suite -> ars/deep-research in lit-review mode.

Topic:
Author Rebuttal / Peer Review Assistant based on Nature transparent peer review data.

Focus:
peer review NLP, response-to-reviewer modeling, scientific RAG, evidence-grounded scholarly writing, LLM academic agents, transparent peer review corpora.

Output:
source-grounded literature matrix, closest baselines, corpus comparison, verified/unverified novelty claims, and risks for positioning v2709 as a provenance-aware review-response-decision knowledge base.

Do not write manuscript prose. Mark all uncertain novelty claims as unverified.
```

#### Step 2: `academic-research-suite -> ars/experiment-agent` in `plan` mode

**目的**

把 Phase 1-6 转为可执行实验计划。

**原因**

现在已有数据包，但还需要明确 split、baseline、metrics、人工评估协议和验收标准。

**预期产物**

- experiment plan；
- evaluation protocol；
- ablation plan；
- reproducibility checklist。

**建议提示词**

```text
Use academic-research-suite -> ars/experiment-agent in plan mode.

Input:
docs/2026-05-20-author-rebuttal-assistant-v2709-research-plan-zh.md
data/processed/author_rebuttal_mvp/v2709/
src/peer_review_skills/schemas/interaction_unit.py

Goal:
Convert the research plan into an executable experiment protocol for P0 tasks:
1. Review Concern Extraction
2. Author Response Strategy Retrieval
3. Rebuttal Outline Generation with Integrity Checking

Output:
dataset split plan, human-validated subset plan, baselines, metrics, ablations, human evaluation protocol, reproducibility checklist, and stopping criteria.
```

#### Step 2.5: 本地 schema freeze / knowledge base implementation planning

**目的**

把 `InteractionUnit`、`StrategyCase`、`RebuttalCase`、retrieval examples 和 provenance policy 固化为工程任务。

**原因**

文献综述和实验计划可以并行推进，但所有实验都依赖稳定 schema。不能等到写论文时才发现 pair、case、decision signal 和 provenance 字段不一致。

**预期产物**

- schema freeze note；
- migration plan from current v2709 MVP files；
- validation script checklist；
- sample audit protocol；
- no-gold-label warning in dataset card。

#### Step 3: `academic-research-suite -> ars/academic-paper` in `outline-only` or `plan` mode

**目的**

在 RQ、文献定位和实验计划稳定后，写论文大纲。

**原因**

目前还不应该写正文。应先形成 argument map 和 section outline。

**预期产物**

- title candidates；
- abstract skeleton；
- contribution bullets；
- section outline；
- figures/tables plan。

**进入条件**

- literature matrix 完成；
- P0 experiment plan 完成；
- schema freeze note 完成；
- claim ledger 至少区分 `supported` / `planned` / `remove_or_soften`。

#### Step 4: `academic-research-suite -> ars/academic-paper-reviewer`

**目的**

在 research plan 或初稿形成后做模拟评审。

**原因**

当前还没有实验结果和论文大纲，不适合过早模拟评审。

**预期产物**

- novelty critique；
- methodology critique；
- ethics critique；
- revision roadmap。

**进入条件**

- 已有 paper outline 或 4-6 页 extended abstract；
- 已有初步实验结果或明确标记为 planned 的 experiment table；
- 已有 limitations 和 ethics 边界。

### 11.2 当前不建议做的事

- 不建议继续默认爬虫。
- 不建议直接写 introduction。
- 不建议直接做 UI。
- 不建议把 heuristic pairs 当作 gold labels。
- 不建议声称系统已经优于 baseline。
- 不建议同时把七个任务都作为第一版论文核心实验。
- 不建议把 decision signal 解释为 strategy 的因果效果。
- 不建议公开再分发完整原始文本前跳过许可核查。

### 11.3 建议停止点

本计划当前建议采用：

> 路线 C：审稿关切与回应策略的实证分析 + provenance-aware Author Rebuttal Assistant workflow。

下一步应先做 `ars/deep-research` 文献定位，确认已有工作、baseline 和 novelty gap。确认后再进入实验设计阶段。

同时，工程侧可以并行推进 schema freeze 和 human-validated subset 设计，但不得先写论文正文或系统宣传文案。

### 11.4 下一轮最小执行清单

为了把本计划转成可执行工作，下一轮建议只启动以下 5 件事：

1. 生成 source-grounded literature matrix。
2. 写 `StrategyCase` / `RebuttalCase` schema freeze note。
3. 设计 100-200 条 human-validated subset 抽样与标注协议。
4. 实现或规划 P0 retrieval baseline，不扩展到全部 P1/P2 任务。
5. 更新 claim ledger，把所有 novelty 和 performance claim 保持在 `planned`，直到文献和实验完成。
