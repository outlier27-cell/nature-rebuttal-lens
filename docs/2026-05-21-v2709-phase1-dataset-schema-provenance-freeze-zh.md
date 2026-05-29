# v2709 Phase 1 数据固化、Schema 与 Provenance 方案

> 日期：2026-05-21
> 当前阶段：`evidence_started`
> 当前目标：停止默认继续爬取，把现有 v2709 数据固化为 Author Rebuttal / Peer Review Assistant 可检索、可评估、可追溯的知识库输入。

## 1. 执行结论

当前项目应进入 Phase 1：**数据审计和 schema 固化**。

本阶段不做三件事：

1. 不继续默认扩展爬虫。
2. 不把启发式 pair 当人工金标。
3. 不写论文正文或强 novelty claim。

本阶段要完成四件事：

1. 固化 v2709 数据口径。
2. 明确每类 JSONL 文件的合法用途。
3. 冻结后续知识库需要的最小 schema。
4. 设计 100-200 条抽样校验，用来判断 heuristic pairs 是否足以进入 retrieval baseline 和弱监督流程。

## 2. 当前数据资产

### 2.1 官方正式主库

| 项 | 路径 / 数量 |
|---|---|
| 官方 index | `scraped_data/20_curated/final_nature_science_peer_review_corpus_index.json` |
| 官方 JSON 目录 | `scraped_data/20_curated/final_nature_science_peer_review_corpus/` |
| paper records | `2709` |
| reviewer report blocks | `32276` |
| papers with author response | `1804` |
| papers with decision letter | `393` |
| papers with both response and decision | `351` |
| quality high / medium | `2649 / 60` |

官方 JSON 顶层字段已观察到：

```text
abstract
ai_relevance_score
asset_probe
comments
doi
failure_reason
is_nature_main_journal
journal
keywords
peer_review
prereviews
scraped_at
source_files
status
success
title
url
year
```

`peer_review` 下已观察到：

```text
decision_letter
reviewer_reports[]
author_response
```

说明：字段存在性以实际 JSON 为准；不同 paper 可能缺少 `author_response` 或 `decision_letter`。

### 2.2 Author Rebuttal MVP 包

路径：

```text
data/processed/author_rebuttal_mvp/v2709/
```

核心文件：

| 文件 | 数量 / 用途 | 当前定位 |
|---|---:|---|
| `paper_manifest.jsonl` | `2709` | 全量 paper manifest 和 MVP tier |
| `core_full_chain_papers.jsonl` | `339` | 高质量 response + decision 子集 |
| `response_only_papers.jsonl` | `1400` | 高质量 review + response 子集 |
| `review_only_input_papers.jsonl` | `860` | 只能做输入 prompt，不做 rebuttal supervision |
| `editor_decision_only_papers.jsonl` | `42` | 可做 editor decision 建模，不做 author response gold |
| `heuristic_rebuttal_pairs_all.jsonl` | `21978` | 所有启发式窗口 pair |
| `heuristic_rebuttal_pairs_clean.jsonl` | `11311` | `confidence >= 0.70` 且 strategy 已知 |
| `heuristic_rebuttal_pairs_demo_ready.jsonl` | `9858` | concern 和 strategy 均已知的 demo/retrieval 候选 |
| `retrieval_examples.jsonl` | `9858` | compact retrieval examples |
| `demo_ready_cases.jsonl` | `738` | paper-level demo cases，每篇最多捆绑 8 条 pair |
| `summary.json` | 1 | 机器可读统计 |

关键口径：

- `351` 是官方主库中有 author response 和 decision letter 的 paper 数。
- `339` 是 MVP 包中 high-quality full-chain subset。
- `9858` 是 demo-ready heuristic pairs，不是人工金标。
- `1739` 是用于 pair extraction 的 A/B 高质量 source papers。

## 3. 数据用途分层

| 数据池 | 可以做 | 不可以做 |
|---|---|---|
| 官方 v2709 JSON | provenance source、全文恢复、审计、重新抽取 | 直接假设所有字段完整 |
| `paper_manifest.jsonl` | split、stratification、tier/filter、统计 | 当 interaction-level 标注 |
| `core_full_chain_papers.jsonl` | decision-aware case retrieval、case study、full-chain demo | 大规模 outcome 因果结论 |
| `response_only_papers.jsonl` | retrieval pool、strategy induction、weak supervision | decision-aware evaluation |
| `review_only_input_papers.jsonl` | 用户输入模拟、concern extraction 输入 | author response 监督 |
| `editor_decision_only_papers.jsonl` | editor signal 探索 | author response strategy learning |
| `heuristic_rebuttal_pairs_*` | retrieval candidates、demo、弱监督、抽样校验池 | gold benchmark |
| `retrieval_examples.jsonl` | MVP retrieval baseline 的候选库 | 直接报告为人工标注数据 |
| `demo_ready_cases.jsonl` | 端到端 demo、case-level provenance 检查 | 代替完整 benchmark |
| 旧 `data/processed/interaction_units` | 原型参考、schema 参考 | 官方 v2709 最终监督数据 |

## 4. 当前已发现的数据质量风险

### 4.1 启发式窗口错配

`retrieval_examples.jsonl` 和 pair 文件来自 marker/window heuristic。抽样时已经看到部分 pair 可能存在 `reviewer_concern` 与 `author_rebuttal` 窗口错位或方向反转的问题。

处理策略：

- `heuristic_rebuttal_pairs_demo_ready.jsonl` 只能作为 retrieval/demo/weak supervision 候选。
- P0 benchmark 必须先抽样校验。
- 任何论文中关于 pair-level 准确性的 claim 必须等人工或强模型复核后再写。

### 4.2 多轮审稿与 reviewer 对应关系不稳

Nature peer review 文档经常包含多轮 reviewer comments、author response、editor letter 和页面标记。单靠 marker window 可能无法稳定恢复：

- round boundary；
- reviewer identity；
- one-to-many concern-response；
- response 是否针对上一轮或同轮意见；
- editor decision 与 response 的因果顺序。

处理策略：

- Phase 1 只冻结 provenance 和最小可用 schema。
- Phase 2 再处理 taxonomy 与对齐校验。
- 对 full-chain decision-aware task 使用更保守子集。

### 4.3 许可与再分发风险

当前数据来自 Nature 系列公开 peer review 材料，但论文和数据集发布前必须核查：

- Nature 公开 peer review 文本的许可边界；
- 是否可再分发全文；
- 是否只能发布 metadata、offset、derived labels 或 retrieval index；
- 是否存在作者、审稿人、编辑相关隐私或署名风险。

当前建议：默认内部使用全文；对外发布时优先发布 metadata、schema、hash、offset、derived labels 和脚本，不默认发布原始全文。

## 5. Phase 1 Frozen Schema 草案

以下是知识库最小 schema，不是立即实现代码。字段名优先贴合现有文件，后续实现时再做 dataclass / JSON Schema。

### 5.1 `PaperRecord`

```json
{
  "paper_id": "10_1038_s41592-025-02707-1",
  "doi": "10.1038/s41592-025-02707-1",
  "title": "...",
  "journal": "Nature Methods",
  "year": 2025,
  "journal_family": "nature_subjournal",
  "quality": "high",
  "interaction_level": "full_chain",
  "mvp_tier": "A1_full_chain_structured",
  "reviewer_report_count": 27,
  "has_response": true,
  "has_decision": true,
  "author_response_len": 155072,
  "decision_letter_len": 279,
  "raw_json_path": "scraped_data/20_curated/final_nature_science_peer_review_corpus/10_1038_s41592-025-02707-1.json"
}
```

必需字段：

- `paper_id`
- `doi`
- `title`
- `journal`
- `year`
- `journal_family`
- `interaction_level`
- `mvp_tier`
- `raw_json_path`

### 5.2 `RebuttalPairCandidate`

```json
{
  "pair_id": "10_1038_s41592-025-02707-1:heuristic_pair:00003",
  "paper_id": "10_1038_s41592-025-02707-1",
  "doi": "10.1038/s41592-025-02707-1",
  "journal": "Nature Methods",
  "year": 2025,
  "mvp_tier": "A1_full_chain_structured",
  "interaction_level": "full_chain",
  "has_decision": true,
  "review_context": "...",
  "author_response": "...",
  "heuristic_concern_type": "generalization_scope",
  "heuristic_response_strategy": "add_new_experiment",
  "pair_confidence": 0.85,
  "context_truncated": false,
  "response_truncated": true,
  "source_json_path": "scraped_data/20_curated/final_nature_science_peer_review_corpus/10_1038_s41592-025-02707-1.json",
  "source_field": "/peer_review/author_response",
  "source_offsets": {
    "context_start": 53832,
    "context_end": 54426,
    "response_start": 54436,
    "response_end": 59788
  },
  "extraction_method": "official_v2709_response_marker_window_v1"
}
```

必需字段：

- `pair_id`
- `paper_id`
- `review_context`
- `author_response`
- `source_json_path`
- `source_field`
- `source_offsets`
- `extraction_method`

Phase 1 规则：

- `heuristic_concern_type` 和 `heuristic_response_strategy` 要明确标为 heuristic。
- `pair_confidence` 是启发式置信度，不是人工准确率。
- `context_truncated` 或 `response_truncated` 为 true 时，评测必须回源恢复全文或标记不可用于 gold。

### 5.3 `StrategyCase`

面向 retrieval/agent 的案例单元。

```json
{
  "case_id": "case:10_1038_s41592-025-02707-1:00003",
  "pair_id": "10_1038_s41592-025-02707-1:heuristic_pair:00003",
  "paper_id": "10_1038_s41592-025-02707-1",
  "concern": {
    "text": "...",
    "type": "generalization_scope",
    "risk_type": "external_validity",
    "severity": "unknown"
  },
  "response": {
    "text": "...",
    "strategy": "add_new_experiment",
    "evidence_type": "new_experiment",
    "stance": "acknowledge_and_address",
    "commitment": "completed_revision"
  },
  "decision_signal": {
    "has_decision": true,
    "decision_text_available": true,
    "decision_label": "unknown"
  },
  "provenance": {
    "source_json_path": "...",
    "source_field": "/peer_review/author_response",
    "source_offsets": {
      "context_start": 53832,
      "context_end": 54426,
      "response_start": 54436,
      "response_end": 59788
    },
    "extraction_method": "official_v2709_response_marker_window_v1",
    "validation_status": "unverified"
  }
}
```

说明：

- `risk_type`、`severity`、`stance`、`commitment` 当前多数没有人工金标，Phase 1 只能定义字段。
- `validation_status` 初始为 `unverified`，人工校验后改为 `verified` / `rejected` / `needs_review`。

### 5.4 `ValidatedPairLabel`

抽样校验产物。

```json
{
  "pair_id": "...",
  "annotator_id": "A1",
  "alignment_correct": true,
  "concern_type_correct": true,
  "strategy_correct": false,
  "corrected_concern_type": "baseline_comparison",
  "corrected_response_strategy": "add_new_analysis",
  "offset_recoverable": true,
  "unsafe_or_overclaiming_response": false,
  "notes": "strategy includes both new analysis and clarification; dominant strategy is add_new_analysis",
  "created_at": "2026-05-21"
}
```

## 6. Taxonomy 冻结口径

### 6.1 Concern taxonomy v1

当前文件：

```text
data/processed/taxonomies/concern_taxonomy.v1.json
```

当前 labels：

- `ablation_mechanism`
- `baseline_comparison`
- `clarity_presentation`
- `dataset_bias_ethics_safety`
- `experimental_design`
- `generalization_scope`
- `novelty_positioning`
- `reproducibility_reporting`
- `statistics_significance`
- `theoretical_validity`

Phase 1 决策：

- v1 先冻结为候选 taxonomy。
- 人工校验时必须允许 `unknown`、`multi_label`、`wrong_span`。
- 不把 `unknown` 当错误；要统计 unknown 来源。

### 6.2 Response strategy taxonomy v1

当前文件：

```text
data/processed/taxonomies/response_strategy_taxonomy.v1.json
```

当前 labels：

- `acknowledge_and_fix`
- `add_new_analysis`
- `add_new_experiment`
- `clarify_existing_evidence`
- `contest_reviewer_premise`
- `defer_future_work`
- `editorial_only_change`
- `justify_method_choice`
- `narrow_claim_scope`
- `reframe_contribution`

Phase 1 决策：

- v1 先冻结为候选 taxonomy。
- 人工校验时必须允许 response 同时包含多个策略，但需要标 dominant strategy。
- `contest_reviewer_premise` 样本少，后续可能需要过采样。

## 7. Provenance Policy

每条用于 retrieval、agent 输出示例、评测样本或论文案例的记录，必须满足以下条件：

1. 有 `paper_id` 或 `doi`。
2. 有 `source_json_path`。
3. 有 `source_field` 或可映射到官方 JSON 的 JSON pointer。
4. 有 `source_offsets` 或对应 review unit / author unit 的 source trace。
5. 能回源恢复原始上下文。
6. 输出给用户或写入论文时必须保留来源层级，不得只给模型生成解释。

验证规则：

| 检查项 | 方法 | 通过标准 |
|---|---|---|
| 文件存在 | `Test-Path source_json_path` | 100% |
| source field 存在 | 读取 JSON pointer | 100% |
| offset 合法 | start/end 为整数且 start < end | 100% |
| offset 可恢复 | 用 offsets 切片原文并与存储文本近似匹配 | 抽样通过率需报告 |
| pair 对齐 | 人工判断 concern-response 是否对应 | 抽样通过率需报告 |
| label 正确 | 人工判断 concern/strategy label | 抽样通过率需报告 |

## 8. 抽样校验设计

### 8.1 样本规模

建议第一轮抽样 `150` 条 pair：

- `100` 条来自 `heuristic_rebuttal_pairs_demo_ready.jsonl`
- `30` 条来自 `heuristic_rebuttal_pairs_clean.jsonl` 中 concern unknown 或边界模糊样本
- `20` 条来自 full-chain decision-aware cases

如果人力不足，最低可先做 `100` 条，但必须覆盖 full-chain、response-only、不同 concern type 和不同 journal family。

### 8.2 分层维度

| 维度 | 最低覆盖 |
|---|---|
| journal family | `nature_communications`、`communications_series`、`nature_subjournal`、`nature_main` |
| interaction level | `full_chain`、`review+response` |
| mvp tier | `A1/A2/B1/B2` 尽量覆盖 |
| concern type | 每个 v1 label 至少 5 条，样本不足则记录 |
| response strategy | 每个 v1 label 至少 5 条，样本不足则记录 |
| confidence bin | `0.7`、`0.8`、低置信边界样本 |
| truncation | 包含 `response_truncated=true` 的样本，用于检查是否需要回源 |

### 8.3 标注字段

每条样本至少标：

- `alignment_correct`
- `alignment_error_type`
- `concern_type_gold`
- `concern_type_is_multi_label`
- `response_strategy_gold`
- `response_strategy_secondary`
- `evidence_type`
- `unsafe_or_overclaiming_response`
- `offset_recoverable`
- `usable_for_retrieval`
- `usable_for_evaluation`
- `notes`

建议 `alignment_error_type` 枚举：

- `correct`
- `wrong_concern_window`
- `wrong_response_window`
- `reversed_context_response`
- `too_broad_context`
- `multi_issue_response`
- `no_direct_answer`
- `offset_error`
- `unclear`

## 9. Phase 1 验收标准

Phase 1 完成必须满足：

1. `.codex.md` 明确当前主线不是继续爬取。
2. 有本文件作为 dataset/schema/provenance freeze note。
3. `summary.json`、`README.md`、官方 audit 报告中的关键数量一致。
4. 关键字段和合法用途写清楚。
5. 有抽样校验方案。
6. 有明确禁止事项：heuristic 不等于 gold，旧 interaction_units 不等于官方 v2709 supervision。

Phase 1 未完成前，不建议进入：

- 大规模 baseline 性能报告；
- paper introduction / related work 正文；
- 强 novelty claim；
- 对外 dataset release。

## 10. 下一步

推荐紧接着做：

1. 生成抽样校验 JSONL/CSV。
2. 对 100-200 条 pair 做人工或强模型辅助校验。
3. 统计 alignment correctness、label correctness、offset recoverability。
4. 根据结果决定是否需要重新抽取 pair 或改进 segmentation/alignment。
5. 然后进入 `academic-research-suite -> ars/deep-research` 的 source-grounded literature review。
