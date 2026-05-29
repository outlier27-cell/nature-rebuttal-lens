# Training and Learning Design

## 目标

本项目的训练侧目标不是直接训练 final rebuttal generator，而是把 Nature 公开审稿互动案例转成可学习、可替换、可评估的中间能力。核心是学习审稿互动结构，而不是学习代写一封完整回复。

## Interaction Learning Targets

| Target | 学到什么 | 当前监督信号 | 主要风险 |
|---|---|---|---|
| concern understanding | reviewer 明确提出什么问题 | concern_type, review_text | 多问题评论被压成单一标签 |
| tacit risk interpretation | 明确意见背后的可观察风险 | tacit_concern, risk_type | 误读 reviewer 心理 |
| institutional positioning | 期刊、共同体、透明性等制度信号 | institutional_signal | 误写成接收率预测 |
| strategy selection | concern 对应的回应策略 | response_strategy | 把策略标签泄露给检索排序 |
| evidence action planning | 哪类证据动作能回应风险 | evidence_action, actor_links | 编造实验、数据或引用 |
| author positioning | 作者应坚持、让步、解释还是缩小 claim | author_positioning | 无原则迎合或过度防御 |
| tone / commitment calibration | 语气、承诺强度和不确定性边界 | tone_commitment | sycophancy 或 unsupported commitment |
| response adequacy | 回应是否真正覆盖 concern | retrieved cases + adequacy rubric | 只看流畅度不看解决度 |

## Trainable / Replaceable Modules

| Module | v0.1 实现 | 后续可训练方向 | 不建议做法 |
|---|---|---|---|
| Concern Classifier | taxonomy + model-assisted labels | lightweight classifier / prompt classifier | 直接用最终回复质量反推 concern |
| Risk Interpreter | tacit taxonomy + model-assisted labels | classifier with evidence quote constraint | 声称读取 reviewer hidden intent |
| Strategy Selector | retrieval target + label distribution | strategy prediction / reranker | 在 retrieval ranking 中使用 query strategy label |
| Evidence Planner | evidence_action + actor_links | action planner with feasibility flags | 推荐作者不存在的实验或数据 |
| Tone Calibrator | tone_commitment labels | unsupported commitment detector | 把礼貌当成充分回应 |
| Adequacy Checker | workflow trace + rubric | response adequacy scorer | 只评估语言流畅度 |
| Integrity Checker | provenance checks + author-confirmation gates | atomic claim support checker | 允许无来源事实或承诺 |

## model-assisted training seed

当前导出位置：

```text
data/training/author_rebuttal_agent/v2709/model_assisted_training_seed_200.jsonl
data/training/author_rebuttal_agent/v2709/training_seed_summary.json
```

每条训练样本包含：

- input: review_text, response_text, title, journal, year
- targets: concern_type, risk_type, tacit_concern, institutional_signal, response_strategy, evidence_action, author_positioning, tone_commitment, actor_links, response_adequacy
- learning_tasks: concern_extraction, risk_classification, strategy_prediction, evidence_action_prediction, author_positioning_prediction, tone_commitment_calibration, unsupported_commitment_detection, response_adequacy_scoring, decision_aware_case_retrieval
- provenance: source_file, source_hash, offset_recoverable, review_offset, response_offset
- safety_boundaries: no acceptance prediction, no fabricated evidence, no confidential manuscript upload, author confirmation required

## 当前 v0.1 的训练边界

- 当前数据可以支持 model-assisted sanity training/evaluation seed。
- 当前数据可以支持 retrieval/reranker、分类器、证据规划、tone/commitment checker 的原型实验。
- 当前数据不能支撑 human gold benchmark、接收率预测、端到端高质量 final rebuttal generator 微调。
- API 替代人工复核可以作为 v0.1 默认流程，但必须标注 model-assisted，不得写成人工金标。

## 推荐实验顺序

1. 固化 taxonomy 和训练 seed contract。
2. 比较 concern/risk/strategy/evidence 的 historical local baseline、retrieval baseline、LLM zero-shot。
3. 做 retrieval/reranker，但禁止使用 query response_strategy label 参与排序。
4. 做 response adequacy 和 unsupported commitment 检查。
5. 将模块接入 workflow trace，比较 direct LLM、RAG-only、cognitive workflow 三类路线。
6. 只有在出现 human gold benchmark 后，才声明正式监督评测结论。
