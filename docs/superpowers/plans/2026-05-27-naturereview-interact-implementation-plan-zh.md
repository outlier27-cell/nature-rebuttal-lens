# NatureReview-Interact Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 基于 `docs/FINAL-2026-05-26-nature-review-interaction-agent-open-source-plan-zh.md`，把当前 v2709 数据、已有评测雏形和跨学科框架推进为一个可开源、可追溯、可评估的 Nature Review Interaction Agent 项目。

**Architecture:** 项目采用“数据证据层 -> 跨学科操作化层 -> 互动知识库 -> 检索与评测层 -> 多智能体辅助层 -> 开源治理层”的分层架构。核心不是训练一个直接代写 rebuttal 的模型，而是从 Nature 公开同行评审链中学习 `reviewer concern -> tacit / explicit risk -> institutional pressure -> evidence action -> author positioning -> tone / commitment -> editor signal` 的互动结构，并把默会知识、制度压力、行动者网络和认知慢思维转成可标注、可检索、可评估的对象。

**Tech Stack:** Python 标准库为主；现有 `src/peer_review_skills` 包；JSONL / CSV / Markdown 作为可审计产物；OpenAI-compatible API 用于模型辅助标注和 outline sanity check；BM25 / lexical baseline 作为第一阶段检索评测；后续可加入 embeddings、轻量分类器和本地 demo。

---

## 0. 当前项目状态

本计划不是从零开始。当前 repo 已经具备以下基础：

| 模块 | 当前已有内容 | 可靠性判断 |
|---|---|---|
| 原始主库 | v2709，当前最终主库记录数为 2709 | 已确认，但不是每条都适合训练或评测 |
| MVP 数据包 | `data/processed/author_rebuttal_mvp/v2709/` | 可作为当前工作起点 |
| review-response pairs | `heuristic_rebuttal_pairs_demo_ready.jsonl` 约 9858 条 | heuristic，可用于检索和候选构建，不是金标 |
| model-revised mini seed | 50 条经 DeepSeek 辅助修订，其中 45 条可用 | model-assisted candidate，仍不是 human gold |
| P0 baseline | concern / strategy 基础指标已生成 | 可作为 sanity baseline |
| P1 retrieval baseline | BM25、concern filter、hybrid baseline 已生成 | 可作为 retrieval baseline v1 |
| workflow prototype | 45 条 trace，`integrity_pass_rate=1.0`，`joint_hit_at_5_rate=0.7778` | 可记录、可追溯的 prototype，但评测规模很小 |
| 跨学科最终方案 | `docs/FINAL-2026-05-26-nature-review-interaction-agent-open-source-plan-zh.md` | 当前理念和研究定位的主文档 |

关键约束：

- 不默认继续爬虫。
- 不把 heuristic label 或 model-assisted label 称为 human gold。
- 不开源或再分发可能有版权风险的全文，优先开源 schema、taxonomy、derived metadata、评测协议和 prompt/rubric。
- 系统定位为 assistant，不替代作者、审稿人或编辑，不预测接收率，不编造实验、数据、引用或承诺。

---

## 1. 总体实施路线

### Phase A：项目资产冻结与证据台账

目标：把“我们现在到底有什么”固定下来，防止后续工程、论文和 README 使用不一致的数字或概念。

产物：

- `docs/PROJECT_STATUS_2026-05-27-zh.md`
- `docs/CLAIM_LEDGER_zh.md`
- `docs/DATA_CARD_zh.md`
- `docs/RESPONSIBLE_USE_zh.md`

验收标准：

- 所有关键数字都能回溯到 `summary.json`、audit report 或 evaluation summary。
- 所有结论都标注状态：`verified`、`supported_by_heuristic`、`model_assisted`、`planned`、`speculative`、`remove_or_soften`。
- 文档明确区分 v2709 主库、MVP pairs、mini seed、workflow traces。

### Phase B：Review Interaction Unit schema 固化

目标：把跨学科框架落到稳定 schema，而不是停留在概念层。

产物：

- `docs/SCHEMA_REVIEW_INTERACTION_UNIT_zh.md`
- `docs/CROSS_DISCIPLINARY_ANNOTATION_GUIDE_zh.md`
- `data/processed/schemas/review_interaction_unit.schema.json`
- `data/processed/taxonomies/tacit_concern_taxonomy.v1.json`
- `data/processed/taxonomies/institutional_signal_taxonomy.v1.json`
- `data/processed/taxonomies/evidence_action_taxonomy.v1.json`
- `data/processed/taxonomies/author_positioning_taxonomy.v1.json`
- `data/processed/taxonomies/tone_commitment_taxonomy.v1.json`
- `data/processed/taxonomies/editor_signal_taxonomy.v1.json`

验收标准：

- 每条 interaction unit 至少包含 provenance、review text span、response text span、concern type、risk type、institutional signal、evidence action、author positioning、response strategy、tone / commitment、actor links、label source。
- schema 明确哪些字段来自原始数据，哪些字段来自规则，哪些字段来自模型辅助，哪些字段需要人工确认。
- offset recoverability 能在抽样中通过。
- `CROSS_DISCIPLINARY_ANNOTATION_GUIDE_zh.md` 必须给出默会知识、制度压力、行动者网络、作者定位和情绪姿态的可观察文本证据，避免把跨学科概念写成无法验证的口号。

### Phase C：小规模可信 seed set

目标：先做 100-200 条高质量 seed，而不是盲目扩到全部 9858 条。

产物：

- `data/evaluation/seed_set/v1/seed_candidates_200.jsonl`
- `data/evaluation/seed_set/v1/seed_model_reviewed_200.jsonl`
- `data/evaluation/seed_set/v1/seed_human_confirmation_template.csv`
- `data/evaluation/seed_set/v1/seed_report.md`

验收标准：

- 覆盖主要 concern 类型：clarity、experimental design、statistics、generalization、reproducibility、novelty、baseline、ablation、ethics。
- 每类至少 10 条可用样本，无法达到则在报告中说明原因。
- 每条 seed 都有 provenance、alignment status、label source、model rationale、human confirmation slot。

### Phase D：知识库与检索 baseline v2

目标：让系统不只是“找相似文本”，而是按互动结构检索案例。

产物：

- `data/processed/review_interaction_kb/v1/interaction_units.jsonl`
- `data/processed/review_interaction_kb/v1/case_index.jsonl`
- `data/processed/review_interaction_kb/v1/actor_network_cases.jsonl`
- `docs/ACTOR_NETWORK_CASE_MODEL_zh.md`
- `data/evaluation/retrieval_v2/retrieval_v2_report.md`
- `data/evaluation/retrieval_v2/retrieval_v2_summary.json`

验收标准：

- 支持按 concern、risk、institutional signal、actor links、evidence action、strategy、tone、decision signal 过滤或 rerank。
- 与 P1 baseline 对比至少报告：strategy R@1/R@3/R@5、concern@5、joint@5、case diversity、provenance completeness。
- 明确哪些提升来自标签过滤，哪些来自文本相似度。
- `actor_network_cases.jsonl` 必须能表示 reviewer、author、editor、manuscript、figure、dataset、code、benchmark、supplement、journal policy 等行动者如何在一个 case 中被重新对齐。

### Phase E：多智能体 workflow v2

目标：把最终方案中的跨学科 agent 角色落成可记录、可追溯、可评估的 workflow。

产物：

- `docs/AGENT_CARD_zh.md`
- `docs/WORKFLOW_SPEC_zh.md`
- `docs/COGNITIVE_TRACE_SPEC_zh.md`
- `data/evaluation/workflow_v2/workflow_traces.jsonl`
- `data/evaluation/workflow_v2/workflow_report.md`

验收标准：

- 每次运行保留完整 trace：输入、检索案例、agent intermediate outputs、最终建议、integrity checks、provenance。
- 输出不是直接代写完整 rebuttal，而是 concern map、risk interpretation、institutional positioning、actor-network note、evidence plan、author positioning、outline、tone warning、adequacy report。
- trace 必须显式记录慢思维链条：understand -> question -> evidence-plan -> position -> tone-calibrate -> commitment-check -> integrity-check -> output。
- 每个 agent 都有禁止行为清单。

### Phase F：自动评测 + 人工评估协议

目标：把项目从 demo 变成可发表研究计划。

产物：

- `docs/EVALUATION_PROTOCOL_zh.md`
- `docs/CROSS_DISCIPLINARY_EVALUATION_RUBRIC_zh.md`
- `data/evaluation/eval_protocol_v1/rubric.json`
- `data/evaluation/eval_protocol_v1/cross_disciplinary_rubric.json`
- `data/evaluation/eval_protocol_v1/human_eval_sheet.csv`
- `data/evaluation/eval_protocol_v1/automatic_metrics_report.md`

验收标准：

- 至少定义 7 个任务：concern extraction、risk classification、strategy retrieval、evidence recommendation、outline generation、tone/structure revision、decision-aware case retrieval。
- 每个任务都有输入、输出、自动指标、人工指标、baseline、失败模式。
- 至少定义 4 个跨学科评估维度：tacit concern interpretation、institutional positioning、actor-network alignment、cognitive trace quality。
- 人工评估不要求立刻完成，但表格和 rubric 必须可以直接使用。

### Phase G：开源发布包

目标：先开源框架、schema、派生数据和评测协议，再决定是否开源更多数据。

产物：

- `README.md`
- `docs/OPEN_SOURCE_RELEASE_PLAN_zh.md`
- `docs/DATA_RELEASE_BOUNDARY_zh.md`
- `docs/MODEL_AND_AGENT_LIMITATIONS_zh.md`
- `LICENSE` 或 license decision note

验收标准：

- README 第一屏明确项目不是代写工具。
- 数据边界明确：哪些可开源、哪些只给 URL / DOI / hash / offset、哪些不能默认再分发。
- API key、Bearer token、个人路径和敏感日志不进入开源文件。

### Phase H：论文与研究验证路线

目标：准备后续投稿，而不是现在直接写完整论文正文。

产物：

- `docs/PAPER_PLAN_zh.md`
- `docs/LITERATURE_MATRIX_zh.md`
- `docs/EXPERIMENT_PLAN_zh.md`
- `docs/REVIEWER_RISK_REGISTER_zh.md`

验收标准：

- 论文主线聚焦“从透明同行评审中学习科学回应的默会结构与证据结构”。
- 文献矩阵覆盖 peer review AI、rebuttal generation、RAG scholarly documents、LLM agents、AI governance、STS / tacit knowledge。
- 所有贡献主张都能在 claim ledger 中找到证据需求。

---

## 2. 建议文件结构

新增或重点维护以下文件：

```text
docs/
  PROJECT_STATUS_2026-05-27-zh.md
  CLAIM_LEDGER_zh.md
  DATA_CARD_zh.md
  RESPONSIBLE_USE_zh.md
  SCHEMA_REVIEW_INTERACTION_UNIT_zh.md
  CROSS_DISCIPLINARY_ANNOTATION_GUIDE_zh.md
  ACTOR_NETWORK_CASE_MODEL_zh.md
  AGENT_CARD_zh.md
  WORKFLOW_SPEC_zh.md
  COGNITIVE_TRACE_SPEC_zh.md
  EVALUATION_PROTOCOL_zh.md
  CROSS_DISCIPLINARY_EVALUATION_RUBRIC_zh.md
  OPEN_SOURCE_RELEASE_PLAN_zh.md
  DATA_RELEASE_BOUNDARY_zh.md
  MODEL_AND_AGENT_LIMITATIONS_zh.md
  PAPER_PLAN_zh.md
  LITERATURE_MATRIX_zh.md
  EXPERIMENT_PLAN_zh.md
  REVIEWER_RISK_REGISTER_zh.md

data/processed/
  schemas/
    review_interaction_unit.schema.json
  taxonomies/
    tacit_concern_taxonomy.v1.json
    institutional_signal_taxonomy.v1.json
    evidence_action_taxonomy.v1.json
    author_positioning_taxonomy.v1.json
    tone_commitment_taxonomy.v1.json
    editor_signal_taxonomy.v1.json
  review_interaction_kb/v1/
    interaction_units.jsonl
    case_index.jsonl
    actor_network_cases.jsonl
    kb_summary.json
    README.md

data/evaluation/
  seed_set/v1/
    seed_candidates_200.jsonl
    seed_model_reviewed_200.jsonl
    seed_human_confirmation_template.csv
    seed_report.md
  retrieval_v2/
    retrieval_v2_summary.json
    retrieval_v2_report.md
    predictions.jsonl
  workflow_v2/
    workflow_traces.jsonl
    workflow_summary.json
    workflow_report.md
  eval_protocol_v1/
    rubric.json
    cross_disciplinary_rubric.json
    human_eval_sheet.csv
    automatic_metrics_report.md
```

现有代码优先复用：

| 现有文件 | 后续作用 |
|---|---|
| `src/peer_review_skills/schemas/interaction_unit.py` | schema 固化基础 |
| `src/peer_review_skills/evaluation/phase1_pair_sampler.py` | seed 抽样基础 |
| `src/peer_review_skills/evaluation/phase1_mini_gold_revision.py` | 模型辅助复核基础 |
| `src/peer_review_skills/evaluation/p1_retrieval_baselines.py` | retrieval v2 的 baseline 对照 |
| `src/peer_review_skills/evaluation/rebuttal_workflow.py` | workflow v2 的原型基础 |
| `src/peer_review_skills/agents/orchestrator.py` | 多 agent 编排基础 |
| `src/peer_review_skills/api/openai_compatible.py` | DeepSeek / OpenAI-compatible API 调用基础 |

---

## 3. 任务清单

### Task 1: 冻结项目状态与证据台账

**Files:**
- Create: `docs/PROJECT_STATUS_2026-05-27-zh.md`
- Create: `docs/CLAIM_LEDGER_zh.md`
- Read: `data/processed/author_rebuttal_mvp/v2709/summary.json`
- Read: `data/analysis/final_framework_data_audit_v2709/v2709_final_framework_data_audit.md`
- Read: `data/evaluation/p1_retrieval_baselines/v2709_model_revised/p1_retrieval_summary.json`
- Read: `data/evaluation/author_rebuttal_workflow/v2709_model_revised/workflow_summary.json`

- [ ] **Step 1: 汇总当前资产**

Run:

```powershell
Get-Content data\processed\author_rebuttal_mvp\v2709\summary.json -Encoding UTF8
Get-Content data\analysis\final_framework_data_audit_v2709\v2709_final_framework_data_audit.md -Encoding UTF8
Get-Content data\evaluation\p1_retrieval_baselines\v2709_model_revised\p1_retrieval_summary.json -Encoding UTF8
Get-Content data\evaluation\author_rebuttal_workflow\v2709_model_revised\workflow_summary.json -Encoding UTF8
```

Expected:

```text
能看到 v2709 数量、MVP pairs 数量、P1 retrieval 指标、workflow trace 指标。
```

- [ ] **Step 2: 写项目状态文档**

`docs/PROJECT_STATUS_2026-05-27-zh.md` 必须包含：

```markdown
# NatureReview-Interact 项目状态

## 当前一句话
本项目已经从爬取阶段转向把 v2709 公开同行评审数据转化为可检索、可评估、可追溯、负责任开源的 Review Interaction Agent。

## 当前已确认资产

| 资产 | 数量 / 路径 | 状态 |
|---|---:|---|
| v2709 主库 | 2709 records | verified |
| demo-ready pairs | 9858 | heuristic |
| clean heuristic pairs | 11311 | heuristic |
| all heuristic pairs | 21978 | heuristic |
| model-revised mini seed | 50 rows, 45 usable | model-assisted |
| workflow traces | 45 | prototype |

## 当前不能声称的内容

- 不能声称已有人工金标。
- 不能声称 agent 已经被真实作者或审稿专家验证。
- 不能声称模型真正掌握默会知识。
- 不能声称系统能预测接收率。
```

- [ ] **Step 3: 写 claim ledger**

`docs/CLAIM_LEDGER_zh.md` 必须包含表格：

```markdown
| Claim | Evidence needed | Current artifact | Verification status | Risk |
|---|---|---|---|---|
| v2709 包含 2709 条公开同行评审相关记录 | 主库 index / summary | `summary.json` / corpus index | verified | 需保持版本一致 |
| 约 9858 条 demo-ready pair 可用于候选检索 | pair extraction summary | `heuristic_rebuttal_pairs_demo_ready.jsonl` | supported_by_heuristic | 不是人工金标 |
| Nature rebuttal 中大量回应涉及图表、补充材料、分析和实验动作 | keyword proxy audit | `v2709_final_framework_data_audit.md` | supported_by_heuristic | keyword proxy 可能误判 |
| 当前 workflow 已能记录 45 条可追溯 trace | workflow summary | `workflow_summary.json` | model_assisted | 样本小，未人工评估 |
| 本项目可研究默会知识的文本痕迹 | taxonomy + examples + literature | planned | speculative until annotation | 不能声称 AI 真懂默会知识 |
```

- [ ] **Step 4: 验收**

Run:

```powershell
Select-String -Path docs\PROJECT_STATUS_2026-05-27-zh.md,docs\CLAIM_LEDGER_zh.md -Pattern "human gold|人工金标|model-assisted|heuristic|verified"
```

Expected:

```text
文档能明确区分 heuristic、model-assisted 和 verified。
```

### Task 2: 数据卡与负责任使用边界

**Files:**
- Create: `docs/DATA_CARD_zh.md`
- Create: `docs/RESPONSIBLE_USE_zh.md`
- Create: `docs/DATA_RELEASE_BOUNDARY_zh.md`

- [ ] **Step 1: 写 Data Card**

`docs/DATA_CARD_zh.md` 必须包含：

```markdown
# v2709 Data Card

## 数据来源
Nature 系列公开同行评审相关页面和公开文件。

## 数据用途
- 审稿互动结构研究
- review concern / author response strategy 分析
- retrieval baseline
- agent workflow trace evaluation

## 不适合用途
- 自动代写完整 rebuttal 并直接提交
- 接收率预测
- 对 reviewer 或 editor 的个体画像
- 训练不带 provenance 的黑箱生成器

## 标签状态
| 标签类型 | 含义 | 可用于 |
|---|---|---|
| heuristic | 规则或弱监督生成 | 候选检索、粗粒度分析 |
| model-assisted | API 模型辅助复核 | 小规模 sanity evaluation |
| human-confirmed | 人工确认 | 正式 benchmark |
```

- [ ] **Step 2: 写 Responsible Use**

`docs/RESPONSIBLE_USE_zh.md` 必须包含禁止行为：

```markdown
# Responsible Use

本项目禁止或不支持：

- 上传 confidential manuscript 到外部 API。
- 使用系统预测论文接收概率。
- 使用系统生成未验证实验、数据、引用或承诺。
- 使用系统替代作者、审稿人或编辑的判断。
- 使用系统操纵 reviewer 或规避真实科学问题。

系统输出必须被定位为：

- concern map
- evidence planning aid
- writing organization aid
- integrity warning
- provenance-grounded case reference
```

- [ ] **Step 3: 写 Data Release Boundary**

`docs/DATA_RELEASE_BOUNDARY_zh.md` 必须包含：

```markdown
# Data Release Boundary

优先开源：
- schema
- taxonomy
- derived metadata
- source URL / DOI / hash / offset
- model-assisted label sample
- evaluation protocol
- prompt rubrics
- baseline scripts

谨慎处理：
- reviewer report 原文
- author response 原文
- editor decision letter 全文

默认不发布：
- 任何非公开审稿材料
- API key
- private logs
- 无 provenance 的全文聚合包
```

- [ ] **Step 4: 验收**

Run:

```powershell
Select-String -Path docs\DATA_CARD_zh.md,docs\RESPONSIBLE_USE_zh.md,docs\DATA_RELEASE_BOUNDARY_zh.md -Pattern "接收率|confidential|API key|provenance|heuristic|model-assisted"
```

Expected:

```text
关键边界词全部出现，且没有把 model-assisted 写成人工金标。
```

### Task 3: 固化 Review Interaction Unit schema

**Files:**
- Create: `docs/SCHEMA_REVIEW_INTERACTION_UNIT_zh.md`
- Create: `data/processed/schemas/review_interaction_unit.schema.json`
- Modify or compare: `src/peer_review_skills/schemas/interaction_unit.py`

- [ ] **Step 1: 检查现有 schema**

Run:

```powershell
Get-Content src\peer_review_skills\schemas\interaction_unit.py -Encoding UTF8
Get-Content src\peer_review_skills\schemas\annotation.py -Encoding UTF8
```

Expected:

```text
能看到当前 interaction unit 和 annotation 字段定义。
```

- [ ] **Step 2: 写中文 schema 文档**

`docs/SCHEMA_REVIEW_INTERACTION_UNIT_zh.md` 必须定义：

```markdown
# Review Interaction Unit Schema

## 最小单位
一条 unit 表示一个可回溯的审稿互动片段：

reviewer concern -> risk interpretation -> author response move -> evidence action -> tone / commitment -> optional editor signal

## 必需字段
| 字段 | 含义 | 来源 |
|---|---|---|
| unit_id | 稳定 ID | generated |
| paper_id | paper 级 ID | source |
| source_url | 来源 URL | source |
| doi | DOI，如有 | source |
| review_round | 审稿轮次，如可识别 | source / inferred |
| reviewer_id | reviewer 标识，如可识别 | source / inferred |
| review_text | reviewer comment span | source |
| response_text | author response span | source |
| review_offset | reviewer text offset | source / alignment |
| response_offset | response text offset | source / alignment |
| concern_type | concern taxonomy | heuristic / model / human |
| risk_type | risk taxonomy | heuristic / model / human |
| institutional_signal | 制度压力、期刊边界、共同体期待的可观察信号 | model / human |
| evidence_action | evidence action taxonomy | heuristic / model / human |
| author_positioning | 作者在坚持、让步、解释、反驳之间的位置 | model / human |
| response_strategy | response strategy taxonomy | heuristic / model / human |
| tone_commitment | tone and commitment taxonomy | model / human |
| editor_signal | decision signal，如有 | source / inferred |
| actor_links | 本条互动涉及的行动者和非人类对象 | source / inferred / model |
| provenance | URL/hash/offset/source file | source |
| label_source | heuristic/model_assisted/human_confirmed | generated |
```

- [ ] **Step 3: 写 JSON schema**

`data/processed/schemas/review_interaction_unit.schema.json` 必须至少包含字段：

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "title": "ReviewInteractionUnit",
  "type": "object",
  "required": [
    "unit_id",
    "paper_id",
    "review_text",
    "response_text",
    "concern_type",
    "response_strategy",
    "provenance",
    "label_source"
  ],
  "properties": {
    "unit_id": { "type": "string" },
    "paper_id": { "type": "string" },
    "source_url": { "type": ["string", "null"] },
    "doi": { "type": ["string", "null"] },
    "review_round": { "type": ["string", "integer", "null"] },
    "reviewer_id": { "type": ["string", "null"] },
    "review_text": { "type": "string" },
    "response_text": { "type": "string" },
    "review_offset": {
      "type": ["object", "null"],
      "properties": {
        "start": { "type": "integer" },
        "end": { "type": "integer" }
      }
    },
    "response_offset": {
      "type": ["object", "null"],
      "properties": {
        "start": { "type": "integer" },
        "end": { "type": "integer" }
      }
    },
    "concern_type": { "type": "string" },
    "risk_type": { "type": ["string", "null"] },
    "institutional_signal": { "type": ["string", "null"] },
    "evidence_action": { "type": ["string", "null"] },
    "author_positioning": { "type": ["string", "null"] },
    "response_strategy": { "type": "string" },
    "tone_commitment": { "type": ["object", "null"] },
    "editor_signal": { "type": ["object", "null"] },
    "actor_links": {
      "type": "array",
      "items": {
        "type": "object",
        "required": ["actor_type", "evidence"],
        "properties": {
          "actor_type": {
            "type": "string",
            "enum": ["reviewer", "author", "editor", "manuscript", "figure", "table", "dataset", "code", "benchmark", "supplement", "journal_policy", "ai_agent", "other"]
          },
          "actor_id": { "type": ["string", "null"] },
          "role_in_interaction": { "type": ["string", "null"] },
          "evidence": { "type": "string" }
        }
      }
    },
    "provenance": {
      "type": "object",
      "required": ["source_file", "source_hash"],
      "properties": {
        "source_file": { "type": "string" },
        "source_hash": { "type": "string" },
        "url": { "type": ["string", "null"] },
        "offset_recoverable": { "type": ["boolean", "null"] }
      }
    },
    "label_source": {
      "type": "string",
      "enum": ["heuristic", "model_assisted", "human_confirmed", "mixed"]
    }
  }
}
```

- [ ] **Step 4: 验收 JSON**

Run:

```powershell
python -m json.tool data\processed\schemas\review_interaction_unit.schema.json > $null
```

Expected:

```text
命令无错误退出。
```

### Task 4: 扩展 taxonomy 到跨学科标签

**Files:**
- Create: `data/processed/taxonomies/tacit_concern_taxonomy.v1.json`
- Create: `data/processed/taxonomies/institutional_signal_taxonomy.v1.json`
- Create: `data/processed/taxonomies/evidence_action_taxonomy.v1.json`
- Create: `data/processed/taxonomies/author_positioning_taxonomy.v1.json`
- Create: `data/processed/taxonomies/tone_commitment_taxonomy.v1.json`
- Create: `data/processed/taxonomies/editor_signal_taxonomy.v1.json`
- Create: `docs/TAXONOMY_GUIDE_zh.md`

- [ ] **Step 1: 检查现有 taxonomy**

Run:

```powershell
Get-Content data\processed\taxonomies\concern_taxonomy.v1.json -Encoding UTF8
Get-Content data\processed\taxonomies\response_strategy_taxonomy.v1.json -Encoding UTF8
Get-Content data\processed\taxonomies\skill_taxonomy.v1.json -Encoding UTF8
```

Expected:

```text
能看到当前 concern、response strategy 和 skill taxonomy。
```

- [ ] **Step 2: 定义 tacit concern taxonomy**

类别必须包含：

```json
[
  "credibility_trust",
  "novelty_positioning",
  "community_standard_fit",
  "evidence_chain_stability",
  "methodological_maturity",
  "scope_and_claim_boundary",
  "reproducibility_expectation",
  "ethical_or_social_risk",
  "presentation_as_epistemic_signal",
  "unknown"
]
```

- [ ] **Step 3: 定义 institutional signal taxonomy**

类别必须包含：

```json
[
  "journal_scope_fit",
  "community_norm_expectation",
  "editorial_risk_control",
  "reviewer_authority_pressure",
  "replicability_norm",
  "transparency_norm",
  "novelty_threshold",
  "ethical_acceptability",
  "presentation_standard",
  "unknown"
]
```

- [ ] **Step 4: 定义 evidence action taxonomy**

类别必须包含：

```json
[
  "new_experiment",
  "new_analysis",
  "new_baseline_or_comparison",
  "statistical_test_or_uncertainty",
  "figure_table_revision",
  "supplementary_material_revision",
  "code_data_availability",
  "method_clarification",
  "claim_narrowing",
  "limitation_discussion",
  "literature_repositioning",
  "no_new_evidence_explanation_only",
  "future_work_commitment",
  "unknown"
]
```

- [ ] **Step 5: 定义 author positioning taxonomy**

类别必须包含：

```json
[
  "accept_and_revise",
  "clarify_without_new_work",
  "justify_existing_choice",
  "partially_concede",
  "respectfully_disagree",
  "narrow_claim",
  "defer_to_future_work",
  "translate_to_editorial_signal",
  "unknown"
]
```

- [ ] **Step 6: 定义 tone / commitment taxonomy**

维度必须包含：

```json
{
  "tone": ["cooperative", "defensive", "assertive", "apologetic", "neutral", "unknown"],
  "commitment_level": ["completed_change", "promised_change", "clarification_only", "declined_with_reason", "future_work", "unknown"],
  "risk_flags": ["overclaim", "unsupported_commitment", "sycophancy", "excessive_defensiveness", "uncertainty_hiding", "none"]
}
```

- [ ] **Step 7: 定义 editor signal taxonomy**

类别必须包含：

```json
[
  "acceptance_signal",
  "minor_revision_signal",
  "major_revision_signal",
  "unresolved_core_concern",
  "request_for_clarification",
  "scope_or_journal_fit_signal",
  "editorial_process_signal",
  "not_available",
  "unknown"
]
```

- [ ] **Step 8: 验收**

Run:

```powershell
Get-ChildItem data\processed\taxonomies\*.json | ForEach-Object { python -m json.tool $_.FullName > $null }
```

Expected:

```text
所有 taxonomy JSON 都可解析。
```

### Task 4.5: 跨学科标注指南

**Files:**
- Create: `docs/CROSS_DISCIPLINARY_ANNOTATION_GUIDE_zh.md`
- Read: `docs/FINAL-2026-05-26-nature-review-interaction-agent-open-source-plan-zh.md`
- Read: `data/analysis/pdf_2026_05_15/extracted_text.txt`
- Read: `data/analysis/pdf_2026_05_23/extracted_text.txt`
- Read: `data/processed/taxonomies/tacit_concern_taxonomy.v1.json`
- Read: `data/processed/taxonomies/institutional_signal_taxonomy.v1.json`
- Read: `data/processed/taxonomies/author_positioning_taxonomy.v1.json`

- [ ] **Step 1: 读取跨学科来源**

Run:

```powershell
Get-Content docs\FINAL-2026-05-26-nature-review-interaction-agent-open-source-plan-zh.md -Encoding UTF8
Get-Content data\analysis\pdf_2026_05_15\extracted_text.txt -Encoding UTF8 -TotalCount 120
Get-Content data\analysis\pdf_2026_05_23\extracted_text.txt -Encoding UTF8 -TotalCount 120
```

Expected:

```text
能看到最终方案、2026.5.15 PDF 的默会知识/制度分析，以及 2026.5.23 PDF 的认知/情绪分析。
```

- [ ] **Step 2: 写标注总原则**

`docs/CROSS_DISCIPLINARY_ANNOTATION_GUIDE_zh.md` 必须包含：

```markdown
# Cross-disciplinary Annotation Guide

## 总原则

本项目不标注 reviewer 的真实心理，也不声称 AI 真正掌握默会知识。我们只标注公开文本中可观察的互动痕迹。

每个跨学科标签必须满足三个条件：

1. 有原文证据：reviewer comment、author response 或 editor decision 中能找到支持片段。
2. 有互动功能：该标签解释了 concern、response 或 decision signal 的关系。
3. 可被反驳：另一个标注者可以根据同一文本不同意该标签。
```

- [ ] **Step 3: 定义 tacit concern 标注规则**

必须包含如下表格：

```markdown
| 标签 | 可观察证据 | 不应标注的情况 |
|---|---|---|
| credibility_trust | reviewer 质疑结果是否可靠、claim 是否被数据支撑、实验是否足以支撑结论 | 只是要求改错别字或补格式 |
| community_standard_fit | reviewer 要求常见 baseline、标准 benchmark、领域通用报告方式 | 只是任意要求更多实验 |
| evidence_chain_stability | reviewer 指出图表、统计、补充材料、方法描述之间链条不稳 | 单纯说写得不清楚但不影响证据链 |
| presentation_as_epistemic_signal | reviewer 把图表、表达或结构问题当作可信度问题 | 纯语言润色 |
```

- [ ] **Step 4: 定义 institutional signal 标注规则**

必须包含：

```markdown
| 标签 | 可观察证据 | 解释边界 |
|---|---|---|
| journal_scope_fit | editor/reviewer 关注工作是否适合期刊范围、影响力或 novelty threshold | 不能推断真实编辑偏好 |
| reviewer_authority_pressure | author response 显示明显让步、道歉、顺从审稿权威 | 不能把礼貌语气一律当成权力压力 |
| transparency_norm | 要求 code/data、材料、可复现细节 | 应与具体 reproducibility evidence 区分 |
| editorial_risk_control | editor 强调 unresolved concern、additional revision、remaining issue | 不等同于接收率预测 |
```

- [ ] **Step 5: 定义 author positioning 标注规则**

必须包含：

```markdown
| 标签 | 含义 | 示例性证据 |
|---|---|---|
| accept_and_revise | 作者接受意见并完成修改 | "We have added..." |
| clarify_without_new_work | 作者解释已有内容，不新增实验 | "We clarify that..." |
| justify_existing_choice | 作者为原方法选择辩护 | "We chose this because..." |
| partially_concede | 部分接受，部分保留原立场 | "While we agree..., we note..." |
| respectfully_disagree | 明确但礼貌地反驳 reviewer premise | "We respectfully disagree..." |
| narrow_claim | 缩小 claim 或增加限制 | "We have toned down..." |
| defer_to_future_work | 承认重要但放到未来工作 | "We leave this to future work..." |
```

- [ ] **Step 6: 定义行动者网络标注规则**

必须包含：

```markdown
## Actor Links

actor_links 用于记录一条互动中被调动的行动者和非人类对象。常见 actor_type：

- reviewer
- author
- editor
- manuscript
- figure
- table
- dataset
- code
- benchmark
- supplement
- journal_policy
- ai_agent

标注时必须记录 `role_in_interaction`，例如：

- figure: 被 reviewer 质疑为证据不足的载体；
- supplement: 作者用来承载新增分析；
- code: 作者用来回应 reproducibility concern；
- editor: 将多个 unresolved concern 压缩为 revision signal。
```

- [ ] **Step 7: 定义认知/情绪标注边界**

必须包含：

```markdown
## Cognitive and Tone Boundary

本项目不诊断作者或 reviewer 的情绪状态，只标注文本中的互动姿态：

- defensive tone: 文本过度防御，可能削弱合作姿态；
- sycophancy risk: 无证据地迎合 reviewer 或承诺无法完成的修改；
- uncertainty hiding: 回避不确定性或把弱证据写成强结论；
- confidence calibration: 明确说明证据强度、限制和可验证承诺。
```

- [ ] **Step 8: 验收**

Run:

```powershell
Select-String -Path docs\CROSS_DISCIPLINARY_ANNOTATION_GUIDE_zh.md -Pattern "不标注 reviewer 的真实心理|可观察|institutional signal|author positioning|actor_links|sycophancy"
```

Expected:

```text
标注指南明确把跨学科概念转成可观察文本证据，并写清楚不能推断真实心理。
```

### Task 5: 构建 100-200 条 seed set v1

**Files:**
- Create: `data/evaluation/seed_set/v1/seed_candidates_200.jsonl`
- Create: `data/evaluation/seed_set/v1/seed_candidates_200.csv`
- Create: `data/evaluation/seed_set/v1/seed_report.md`
- Reuse: `data/processed/author_rebuttal_mvp/v2709/heuristic_rebuttal_pairs_demo_ready.jsonl`

- [ ] **Step 1: 基于现有 sampler 生成候选**

优先复用现有脚本。如果 CLI 已支持类似任务，优先用 CLI；否则扩展 `phase1_pair_sampler.py`。

Run:

```powershell
python -m peer_review_skills.cli.main --help
python -m peer_review_skills.evaluation.phase1_pair_sampler --help
```

Expected:

```text
能看到现有抽样入口；如果没有 CLI 参数，记录需要补充的参数名。
```

- [ ] **Step 2: 抽样策略**

抽样必须满足：

```text
1. 从 demo-ready pairs 中抽取。
2. 每个主要 concern type 尽量均衡。
3. 优先选择 offset recoverable、review/response 长度适中、alignment confidence 高的样本。
4. 避免同一 paper 过度重复。
5. 输出 JSONL 和 CSV 两种格式。
```

- [ ] **Step 3: seed report 必须包含**

`data/evaluation/seed_set/v1/seed_report.md` 必须包含：

```markdown
# Seed Set v1 Report

## Input
- source file
- candidate count
- sampling date

## Output
- selected count
- paper count
- concern distribution
- strategy distribution
- label source

## Known limitations
- not human gold
- may contain alignment errors
- model review required before benchmark use
```

- [ ] **Step 4: 验收**

Run:

```powershell
Get-Content data\evaluation\seed_set\v1\seed_candidates_200.jsonl -TotalCount 3
(Get-Content data\evaluation\seed_set\v1\seed_candidates_200.jsonl).Count
```

Expected:

```text
文件存在，数量在 100 到 200 之间，字段包含 pair_id、paper_id、review_text、response_text、concern_type、response_strategy、provenance。
```

### Task 6: 使用 DeepSeek-compatible API 做 seed model review

**Files:**
- Create: `data/evaluation/seed_set/v1/seed_model_reviewed_200.jsonl`
- Create: `data/evaluation/seed_set/v1/seed_model_reviewed_200.csv`
- Create: `data/evaluation/seed_set/v1/seed_human_confirmation_template.csv`
- Create: `data/evaluation/seed_set/v1/model_review_report.md`
- Reuse: `src/peer_review_skills/evaluation/phase1_mini_gold_revision.py`

- [ ] **Step 1: 环境变量方式提供 API key**

不要把 API key 写入任何脚本或输出文件。

Run:

```powershell
$env:OPENAI_COMPATIBLE_BASE_URL="https://xh.v1api.cc/v1"
$env:OPENAI_COMPATIBLE_MODEL="deepseek-v3"
$env:OPENAI_COMPATIBLE_API_KEY="<set in shell only>"
```

Expected:

```text
API key 只存在当前 shell 环境变量中，不进入 git、日志和 markdown。
```

- [ ] **Step 2: 模型复核字段**

每条模型复核必须输出：

```json
{
  "alignment_correct": "yes|needs_review|no",
  "usable_for_retrieval": "yes|no",
  "usable_for_evaluation": "yes|no",
  "revised_concern_type": "...",
  "revised_tacit_concern": "...",
  "revised_risk_type": "...",
  "revised_response_strategy": "...",
  "revised_evidence_action": "...",
  "tone_commitment": {
    "tone": "...",
    "commitment_level": "...",
    "risk_flags": []
  },
  "rationale": "short explanation"
}
```

- [ ] **Step 3: 生成 human confirmation template**

CSV 必须包含人工确认列：

```text
human_alignment_confirmed
human_concern_type
human_tacit_concern
human_risk_type
human_response_strategy
human_evidence_action
human_tone
human_commitment_level
human_notes
```

- [ ] **Step 4: 验收**

Run:

```powershell
Get-Content data\evaluation\seed_set\v1\model_review_report.md -Encoding UTF8
Select-String -Path data\evaluation\seed_set\v1\model_review_report.md -Pattern "not human gold|model-assisted|human confirmation"
```

Expected:

```text
报告明确声明这是 model-assisted，不是 human gold。
```

### Task 7: 构建 Review Interaction KB v1

**Files:**
- Create: `data/processed/review_interaction_kb/v1/interaction_units.jsonl`
- Create: `data/processed/review_interaction_kb/v1/case_index.jsonl`
- Create: `data/processed/review_interaction_kb/v1/actor_network_cases.jsonl`
- Create: `data/processed/review_interaction_kb/v1/kb_summary.json`
- Create: `data/processed/review_interaction_kb/v1/README.md`
- Create: `docs/ACTOR_NETWORK_CASE_MODEL_zh.md`
- Potential modify: `src/peer_review_skills/indexing/review_unit_index.py`

- [ ] **Step 1: 定义 KB 输入优先级**

KB v1 输入优先级：

```text
1. seed_model_reviewed_200 中 usable_for_retrieval=yes 的样本。
2. model-revised mini seed 45 条。
3. heuristic demo-ready pairs，用 label_source=heuristic 标记。
```

- [ ] **Step 2: 输出 interaction_units.jsonl**

每条 unit 必须兼容 `review_interaction_unit.schema.json`。

- [ ] **Step 3: 输出 case_index.jsonl**

每条 case index 必须包含：

```json
{
  "case_id": "string",
  "paper_id": "string",
  "unit_ids": ["..."],
  "available_chain": {
    "has_review": true,
    "has_response": true,
    "has_editor_decision": false
  },
  "actor_links": [
    {
      "actor_type": "figure",
      "role_in_interaction": "evidence carrier questioned by reviewer",
      "evidence": "reviewer asks to revise or clarify Figure 2"
    }
  ],
  "top_concern_types": [],
  "top_institutional_signals": [],
  "top_evidence_actions": [],
  "source_url": null,
  "provenance_status": "complete|partial|unknown"
}
```

- [ ] **Step 4: 输出 actor_network_cases.jsonl**

`actor_network_cases.jsonl` 用于把最终方案中的行动者网络理论落成可检索 case。每条必须包含：

```json
{
  "case_id": "string",
  "paper_id": "string",
  "unit_ids": ["..."],
  "actors": [
    {
      "actor_type": "reviewer",
      "role": "raises concern",
      "text_evidence": "short quote or span reference"
    },
    {
      "actor_type": "author",
      "role": "reframes claim and commits revision",
      "text_evidence": "short quote or span reference"
    },
    {
      "actor_type": "figure",
      "role": "becomes revised evidence carrier",
      "text_evidence": "Figure/Table/Supplement mention"
    }
  ],
  "interaction_translation": {
    "reviewer_concern": "string",
    "scientific_risk": "string",
    "institutional_signal": "string",
    "evidence_action": "string",
    "author_positioning": "string",
    "editor_readable_resolution": "string|null"
  },
  "provenance": {
    "source_file": "string",
    "source_hash": "string",
    "unit_offsets": []
  }
}
```

- [ ] **Step 5: 写 Actor Network Case Model 文档**

`docs/ACTOR_NETWORK_CASE_MODEL_zh.md` 必须包含：

```markdown
# Actor Network Case Model

本模型用于把行动者网络理论转成可检索 case，而不是声称还原真实社会因果。

## 核心思想

一条 rebuttal interaction 不只是 reviewer 和 author 的两人对话，而是多个行动者被重新对齐的过程：

reviewer concern -> manuscript / figure / dataset / code / benchmark -> author response -> editor-readable resolution signal

## 必须记录

- human actors: reviewer, author, editor
- non-human actors: manuscript, figure, table, dataset, code, benchmark, supplement, journal policy
- translation: reviewer concern 如何被作者转译成 evidence action 和 response wording
- provenance: 每个 actor link 都必须能回到原文证据
```

- [ ] **Step 6: 验收**

Run:

```powershell
Get-Content data\processed\review_interaction_kb\v1\kb_summary.json -Encoding UTF8
Get-Content data\processed\review_interaction_kb\v1\interaction_units.jsonl -TotalCount 1
Get-Content data\processed\review_interaction_kb\v1\actor_network_cases.jsonl -TotalCount 1
Select-String -Path docs\ACTOR_NETWORK_CASE_MODEL_zh.md -Pattern "行动者网络|non-human actors|translation|provenance"
```

Expected:

```text
summary 记录 unit_count、case_count、actor_network_case_count、label_source_counts、provenance_complete_rate。
```

### Task 8: Retrieval baseline v2

**Files:**
- Create: `data/evaluation/retrieval_v2/retrieval_v2_summary.json`
- Create: `data/evaluation/retrieval_v2/retrieval_v2_report.md`
- Create: `data/evaluation/retrieval_v2/predictions.jsonl`
- Potential modify: `src/peer_review_skills/evaluation/p1_retrieval_baselines.py`

- [ ] **Step 1: 固定 query set 和 retrieval pool**

Query set：

```text
seed_model_reviewed_200 中 usable_for_evaluation=yes 的样本。
```

Retrieval pool：

```text
Review Interaction KB v1 中除自身以外的 units。
```

- [ ] **Step 2: baseline 方法**

至少实现或复用这些方法：

```text
1. lexical cosine
2. BM25
3. concern filter + BM25
4. concern + risk filter + BM25
5. hybrid concern/risk/strategy rerank
```

- [ ] **Step 3: 指标**

必须报告：

```text
strategy_recall_at_1
strategy_recall_at_3
strategy_recall_at_5
concern_match_at_5
risk_match_at_5
joint_strategy_concern_at_5
joint_strategy_risk_at_5
average_distinct_paper_count
average_distinct_strategy_count
provenance_complete_rate_in_top5
```

- [ ] **Step 4: 验收**

Run:

```powershell
Get-Content data\evaluation\retrieval_v2\retrieval_v2_summary.json -Encoding UTF8
Get-Content data\evaluation\retrieval_v2\retrieval_v2_report.md -Encoding UTF8
```

Expected:

```text
报告含 P1 baseline 对照，并明确样本规模、label status 和局限。
```

### Task 9: Agent workflow v2 spec

**Files:**
- Create: `docs/AGENT_CARD_zh.md`
- Create: `docs/WORKFLOW_SPEC_zh.md`
- Create: `docs/COGNITIVE_TRACE_SPEC_zh.md`
- Potential modify: `src/peer_review_skills/evaluation/rebuttal_workflow.py`
- Potential modify: `src/peer_review_skills/agents/orchestrator.py`

- [ ] **Step 1: 写 Agent Card**

`docs/AGENT_CARD_zh.md` 必须包含 agent 列表：

```markdown
| Agent | 输入 | 输出 | 访问字段 | 禁止行为 |
|---|---|---|---|---|
| Reviewer Understanding Agent | review text | concern map | review_text, concern taxonomy | 不猜测 reviewer 身份 |
| Tacit Concern Interpreter | concern map | tacit/risk interpretation | tacit taxonomy, examples | 不声称读懂真实心理 |
| Institutional Signal Interpreter | concern + decision context | institutional signal note | institutional taxonomy, editor signal taxonomy | 不预测接收率，不推断编辑真实意图 |
| Evidence Action Planner | risk interpretation | evidence plan | evidence taxonomy, retrieved cases | 不编造实验或数据 |
| Author Positioning Agent | evidence plan | stance options | strategy taxonomy | 不建议无原则迎合 |
| Tone and Commitment Calibrator | draft/outline | tone warnings | tone taxonomy | 不鼓励过度承诺 |
| Actor-Network Mapper | concern + response + retrieved cases | actor alignment note | actor_links, case_index | 不声称还原真实因果，只记录文本中可观察关系 |
| Integrity and Adequacy Checker | full plan | adequacy report | provenance, retrieved cases | 不放过无证据 claim |
| Editor Signal Reader | case bundle | decision-risk note | editor signal taxonomy | 不预测接收率 |
| Ethics and Governance Agent | full trace | responsible-use warnings | policy docs | 不绕过数据和伦理边界 |
```

- [ ] **Step 2: 写 Workflow Spec**

`docs/WORKFLOW_SPEC_zh.md` 必须定义输出结构：

```json
{
  "concern_map": [],
  "risk_interpretation": [],
  "institutional_signal_note": [],
  "actor_network_note": [],
  "retrieved_cases": [],
  "evidence_action_plan": [],
  "author_positioning": [],
  "rebuttal_outline": [],
  "tone_commitment_warnings": [],
  "adequacy_report": [],
  "editor_signal_note": [],
  "provenance_notes": [],
  "responsible_use_warnings": []
}
```

- [ ] **Step 3: 写 Cognitive Trace Spec**

`docs/COGNITIVE_TRACE_SPEC_zh.md` 必须包含：

```markdown
# Cognitive Trace Spec

本项目的 workflow 不能一步生成 rebuttal。每条 trace 必须显式记录慢思维链条：

| Stage | 目的 | 必须输出 | 禁止行为 |
|---|---|---|---|
| understand | 拆解 reviewer 明说的 concern | concern_map | 不急着生成回复 |
| question | 识别不确定、隐含风险和可能误解 | risk_interpretation, uncertainty_notes | 不把 reviewer premise 自动当真 |
| evidence_plan | 把风险转成证据或修订动作 | evidence_action_plan | 不编造实验、数据、引用 |
| position | 帮作者选择坚持、让步、解释或反驳的位置 | author_positioning | 不无原则迎合 |
| tone_calibrate | 校准合作语气和承诺边界 | tone_commitment_warnings | 不把温暖语气当成充分回应 |
| commitment_check | 检查承诺是否可验证、可完成 | unsupported_commitment_flags | 不承诺无法完成的修改 |
| integrity_check | 检查 provenance、overclaim、adequacy | adequacy_report | 不输出无证据 claim |
| output | 生成结构化建议或 outline | final_structured_output | 不自动提交、不预测接收率 |
```

- [ ] **Step 4: 验收**

Run:

```powershell
Select-String -Path docs\AGENT_CARD_zh.md,docs\WORKFLOW_SPEC_zh.md,docs\COGNITIVE_TRACE_SPEC_zh.md -Pattern "不编造|不预测接收率|provenance|adequacy|tone|understand|question|evidence_plan|commitment_check"
```

Expected:

```text
关键禁止行为、跨学科 agent 和慢思维 trace 字段全部出现。
```

### Task 10: 运行 workflow v2 小批量 trace

**Files:**
- Create: `data/evaluation/workflow_v2/workflow_traces.jsonl`
- Create: `data/evaluation/workflow_v2/workflow_summary.json`
- Create: `data/evaluation/workflow_v2/workflow_report.md`
- Reuse: `src/peer_review_skills/evaluation/rebuttal_workflow.py`

- [ ] **Step 1: 输入规模**

先运行 30-50 条，不直接全量。

```text
query source: seed_model_reviewed_200 usable_for_evaluation=yes
retrieval source: review_interaction_kb/v1
model: deepseek-v3 for optional outline only
```

- [ ] **Step 2: trace 必须记录**

每条 trace 包含：

```json
{
  "query_unit_id": "...",
  "input_review_text": "...",
  "cognitive_trace": {
    "understand": {
      "concern_map": []
    },
    "question": {
      "risk_interpretation": [],
      "uncertainty_notes": []
    },
    "evidence_plan": {
      "evidence_action_plan": []
    },
    "position": {
      "author_positioning": []
    },
    "tone_calibrate": {
      "tone_commitment_warnings": []
    },
    "commitment_check": {
      "unsupported_commitment_flags": []
    },
    "integrity_check": {
      "adequacy_report": [],
      "provenance_checks": []
    },
    "output": {
      "final_structured_output": []
    }
  },
  "institutional_signal_note": [],
  "actor_network_note": [],
  "retrieval_method": "...",
  "retrieved_case_ids": [],
  "outline": [],
  "integrity_checks": [],
  "provenance": [],
  "errors": []
}
```

- [ ] **Step 3: workflow report 必须包含**

```markdown
# Workflow v2 Report

## Input
## Agent steps
## Retrieval metrics
## Integrity checks
## Cognitive trace quality
## Institutional positioning
## Actor-network alignment
## Failure cases
## Difference from direct rebuttal generation
## Limitations
```

- [ ] **Step 4: 验收**

Run:

```powershell
Get-Content data\evaluation\workflow_v2\workflow_summary.json -Encoding UTF8
Select-String -Path data\evaluation\workflow_v2\workflow_report.md -Pattern "not a final rebuttal-writing system|trace|provenance|integrity"
```

Expected:

```text
workflow v2 报告明确这是可追溯辅助工作流，不是最终代写系统。
```

### Task 11: Evaluation protocol v1

**Files:**
- Create: `docs/EVALUATION_PROTOCOL_zh.md`
- Create: `docs/CROSS_DISCIPLINARY_EVALUATION_RUBRIC_zh.md`
- Create: `data/evaluation/eval_protocol_v1/rubric.json`
- Create: `data/evaluation/eval_protocol_v1/cross_disciplinary_rubric.json`
- Create: `data/evaluation/eval_protocol_v1/human_eval_sheet.csv`

- [ ] **Step 1: 任务定义**

`docs/EVALUATION_PROTOCOL_zh.md` 必须包含 7 个任务：

```markdown
1. Review concern extraction
2. Risk point classification
3. Author response strategy retrieval
4. Evidence recommendation
5. Rebuttal outline generation
6. Tone / structure revision
7. Decision-aware case retrieval
8. Tacit concern interpretation
9. Institutional positioning assessment
10. Actor-network case retrieval
11. Cognitive trace quality assessment
```

- [ ] **Step 2: 每个任务必须包含**

```markdown
## Task Name
- Input
- Output
- Supervision signal
- Automatic metrics
- Human evaluation metrics
- Baselines
- Failure modes
```

- [ ] **Step 3: rubric 维度**

`rubric.json` 必须包含：

```json
{
  "dimensions": [
    "concern_correctness",
    "risk_interpretation_quality",
    "evidence_groundedness",
    "case_relevance",
    "tone_calibration",
    "commitment_safety",
    "adequacy_of_response",
    "provenance_traceability",
    "responsible_use_compliance",
    "tacit_concern_interpretation",
    "institutional_positioning_quality",
    "actor_network_alignment",
    "cognitive_trace_quality"
  ],
  "scale": [1, 2, 3, 4, 5]
}
```

- [ ] **Step 4: 写跨学科评估 rubric**

`docs/CROSS_DISCIPLINARY_EVALUATION_RUBRIC_zh.md` 必须包含：

```markdown
# Cross-disciplinary Evaluation Rubric

## 1. Tacit Concern Interpretation

评分问题：系统是否基于文本证据识别了 reviewer concern 背后的可信度、领域标准、证据链或 claim 边界问题？

1 分：只复述 reviewer 原话。
3 分：能识别显性风险，但缺少文本证据或边界说明。
5 分：能给出可观察证据、解释边界，并避免声称读懂 reviewer 心理。

## 2. Institutional Positioning

评分问题：系统是否识别了期刊范围、共同体标准、透明性规范、editorial risk control 等制度信号？

1 分：完全忽略制度语境。
3 分：提到制度压力，但没有说明和 response strategy 的关系。
5 分：能把制度信号转成作者可执行的回应位置，同时不预测接收率。

## 3. Actor-network Alignment

评分问题：系统是否记录了 manuscript、figure、dataset、code、benchmark、supplement、editor signal 等行动者如何被重新对齐？

1 分：只输出文本回复建议。
3 分：提到证据对象，但没有说明互动功能。
5 分：明确说明哪些行动者承担了证据、修订、透明性或编辑可读信号的作用。

## 4. Cognitive Trace Quality

评分问题：系统是否按 understand -> question -> evidence_plan -> position -> tone_calibrate -> commitment_check -> integrity_check -> output 的顺序工作？

1 分：直接生成回复。
3 分：有部分中间步骤，但缺少承诺或 integrity 检查。
5 分：完整记录慢思维链条，并能解释每一步如何减少过度自信、迎合或编造风险。
```

`data/evaluation/eval_protocol_v1/cross_disciplinary_rubric.json` 必须包含：

```json
{
  "dimensions": [
    {
      "name": "tacit_concern_interpretation",
      "scale": [1, 2, 3, 4, 5],
      "anchor_1": "Only repeats the explicit reviewer comment.",
      "anchor_3": "Identifies an implicit risk but lacks clear evidence or boundary.",
      "anchor_5": "Grounds the tacit concern in observable text and avoids mind-reading claims."
    },
    {
      "name": "institutional_positioning_quality",
      "scale": [1, 2, 3, 4, 5],
      "anchor_1": "Ignores institutional context.",
      "anchor_3": "Mentions institutional pressure without linking it to author action.",
      "anchor_5": "Links institutional signals to responsible author positioning without acceptance prediction."
    },
    {
      "name": "actor_network_alignment",
      "scale": [1, 2, 3, 4, 5],
      "anchor_1": "Only suggests wording.",
      "anchor_3": "Mentions evidence objects without explaining their role.",
      "anchor_5": "Explains how human and non-human actors are realigned through evidence and response actions."
    },
    {
      "name": "cognitive_trace_quality",
      "scale": [1, 2, 3, 4, 5],
      "anchor_1": "Directly generates a reply.",
      "anchor_3": "Includes partial intermediate reasoning but misses commitment or integrity checks.",
      "anchor_5": "Records the full slow-thinking chain and shows how it reduces overconfidence, sycophancy, and fabrication risk."
    }
  ]
}
```

- [ ] **Step 5: 验收**

Run:

```powershell
python -m json.tool data\evaluation\eval_protocol_v1\rubric.json > $null
python -m json.tool data\evaluation\eval_protocol_v1\cross_disciplinary_rubric.json > $null
Get-Content docs\EVALUATION_PROTOCOL_zh.md -Encoding UTF8
Select-String -Path docs\CROSS_DISCIPLINARY_EVALUATION_RUBRIC_zh.md -Pattern "Tacit Concern|Institutional Positioning|Actor-network|Cognitive Trace|不预测接收率"
```

Expected:

```text
评测协议可直接交给人工评估者或后续 experiment agent 使用，并且能评价跨学科价值是否真正进入系统输出。
```

### Task 12: 开源 README 与发布计划

**Files:**
- Create or Modify: `README.md`
- Create: `docs/OPEN_SOURCE_RELEASE_PLAN_zh.md`
- Create: `docs/MODEL_AND_AGENT_LIMITATIONS_zh.md`

- [ ] **Step 1: README 第一屏**

`README.md` 开头必须说明：

```markdown
# NatureReview-Interact

NatureReview-Interact is an open research framework for studying and assisting scientific review interactions from transparent peer review data.

It is not:
- an automatic rebuttal-writing service;
- an acceptance-probability predictor;
- a replacement for authors, reviewers, or editors;
- a tool for uploading confidential manuscripts to external AI services.
```

- [ ] **Step 2: 中文发布计划**

`docs/OPEN_SOURCE_RELEASE_PLAN_zh.md` 必须包含：

```markdown
## Release v0.1
- conceptual framework
- schema
- taxonomy
- data card
- responsible use
- seed sample metadata
- evaluation protocol
- baseline reports

## Release v0.2
- KB builder
- retrieval baseline v2
- workflow v2 traces

## Release v0.3
- demo interface
- expanded benchmark if human-confirmed labels exist
```

- [ ] **Step 3: limitations**

`docs/MODEL_AND_AGENT_LIMITATIONS_zh.md` 必须包含：

```markdown
- 模型不能真正拥有人类默会知识。
- 模型只能识别公开文本中的可观察痕迹。
- 当前 seed set 不是人工金标。
- 当前 workflow 没有经过真实作者用户研究。
- 任何实验、数据、引用和承诺必须由作者确认。
```

- [ ] **Step 4: 验收 secret scan**

Run:

```powershell
Select-String -Path README.md,docs\*.md -Pattern "sk-|Bearer|Authorization:" -SimpleMatch
```

Expected:

```text
没有任何 API key 或 Authorization token。
```

### Task 13: 论文计划与文献矩阵

**Files:**
- Create: `docs/PAPER_PLAN_zh.md`
- Create: `docs/LITERATURE_MATRIX_zh.md`
- Create: `docs/EXPERIMENT_PLAN_zh.md`
- Create: `docs/REVIEWER_RISK_REGISTER_zh.md`

- [ ] **Step 1: 论文主线**

`docs/PAPER_PLAN_zh.md` 的主问题：

```markdown
公开透明同行评审数据能否帮助我们学习科学审稿互动中的默会知识、制度压力、证据动作和语言姿态，并将这些规律转化为负责任的作者回应智能体？
```

贡献必须包含：

```markdown
1. 跨学科问题定义
2. Review Interaction Unit / Knowledge Base
3. Tacit Concern and Evidence Action Taxonomy
4. Cognitive-layer Multi-agent Workflow
5. Responsible Open-source Protocol
```

- [ ] **Step 2: 文献矩阵**

`docs/LITERATURE_MATRIX_zh.md` 必须包含类别：

```markdown
| 文献类别 | 要回答的问题 | 关键词 | 需要比较的 prior work | 我们的差异 |
|---|---|---|---|---|
| Peer review NLP / assistance | AI 如何辅助审稿？ | peer review, review feedback agent | Review Feedback Agent, Reviewer2 | 我们面向 author-review-editor interaction |
| Rebuttal generation | 如何生成或规划 rebuttal？ | rebuttal generation, response letter | Paper2Rebuttal, DRPG, RebuttalAgent | 我们强调证据动作和制度互动 |
| RAG over scholarly documents | 如何基于案例检索？ | scholarly RAG, citation-grounded generation | scholarly QA / RAG systems | 我们检索 interaction unit |
| LLM agents | 多 agent 如何拆解任务？ | LLM agent, workflow, planning | agent review systems | 我们设置责任边界和 integrity guard |
| STS / tacit knowledge | 默会知识如何进入审稿？ | tacit knowledge, peer review sociology | Polanyi, Collins, ANT | 我们只学习文本痕迹 |
| AI governance | 如何限制误用？ | AI disclosure, peer review policy | Nature, COPE, WAME, ICML policies | 我们内置 open-source boundary |
```

- [ ] **Step 3: 实验计划**

`docs/EXPERIMENT_PLAN_zh.md` 必须包含：

```markdown
Phase 1: Data audit and schema freeze
Phase 2: Seed set and taxonomy validation
Phase 3: Retrieval baseline v2
Phase 4: Agent workflow v2
Phase 5: Automatic and human evaluation
Phase 6: Ablation and error analysis
```

- [ ] **Step 4: reviewer risk register**

`docs/REVIEWER_RISK_REGISTER_zh.md` 必须包含最强反方意见：

```markdown
| Reviewer concern | Why it matters | Response strategy | Evidence needed |
|---|---|---|---|
| AI cannot learn tacit knowledge | 核心概念可能被攻击 | 改称 observable traces of tacit judgment | taxonomy examples + annotation |
| Labels are not gold | 评测可信度风险 | 明确 label status，补人工确认 | human eval sheet |
| Dataset copyright risk | 开源风险 | 发布 derived metadata and offsets | data release boundary |
| This is just RAG | 创新性风险 | 强调 interaction unit + cognitive layer | ablation vs RAG |
| Agent may encourage manipulation | 伦理风险 | responsible use and no acceptance prediction | governance doc |
```

- [ ] **Step 5: 验收**

Run:

```powershell
Select-String -Path docs\PAPER_PLAN_zh.md,docs\LITERATURE_MATRIX_zh.md,docs\REVIEWER_RISK_REGISTER_zh.md -Pattern "tacit|默会|evidence action|responsible|RAG|human"
```

Expected:

```text
论文计划同时体现技术、跨学科和治理价值。
```

---

## 4. 执行顺序建议

优先顺序：

1. Task 1-2：先固定状态、claim、data card、responsible use。
2. Task 3-4.5：固化 schema、taxonomy 和跨学科标注指南。
3. Task 5-6：扩展 100-200 条 seed，并做模型辅助复核。
4. Task 7-8：构建 KB v1、actor-network cases 和 retrieval baseline v2。
5. Task 9-10：写 agent spec、cognitive trace spec，并跑 workflow v2 小批量 trace。
6. Task 11：建立正式 evaluation protocol 和跨学科评估 rubric。
7. Task 12：准备开源发布包。
8. Task 13：准备论文计划、文献矩阵和 reviewer risk register。

不建议现在做：

- 继续大规模爬虫。
- 直接训练大模型。
- 直接发布全文数据包。
- 直接把 workflow 当作最终产品。
- 直接写完整论文正文。

---

## 5. 里程碑

| Milestone | 完成条件 | 预期价值 |
|---|---|---|
| M1: Project freeze | 状态文档、claim ledger、data card 完成 | 项目口径统一 |
| M2: Schema freeze | RIU schema + taxonomy + cross-disciplinary annotation guide 完成 | 数据可长期维护，跨学科概念可操作化 |
| M3: Seed v1 | 100-200 条 model-assisted seed 完成 | 支撑初步评测 |
| M4: KB v1 | interaction KB + case index + actor-network cases 完成 | 支撑结构化检索和行动者网络分析 |
| M5: Retrieval v2 | baseline report 完成 | 有可比较指标 |
| M6: Workflow v2 | 30-50 条完整 cognitive trace 完成 | 有可展示 agent，并能体现慢思维工作流 |
| M7: Evaluation protocol | rubric + cross-disciplinary rubric + human sheet 完成 | 可进入正式评估 |
| M8: Open-source v0.1 | README + governance docs 完成 | 可公开展示 |
| M9: Paper package | paper plan + lit matrix + risk register 完成 | 可进入论文写作 |

---

## 6. 当前最推荐的下一步

下一步应先执行 **Task 1-2**。

原因：

- 当前已有很多数据和报告，但口径分散。
- 在继续扩 seed、做 KB 或跑 workflow 前，必须先固定哪些 claim 已验证，哪些只是 heuristic 或 model-assisted。
- 这一步会直接服务 README、开源边界和论文贡献，不会浪费。

完成 Task 1-2 后，再执行 Task 3-4.5 固化 schema、taxonomy 和跨学科标注指南。只有 schema 和标注边界都稳了，后续 seed、KB、retrieval、agent trace 才不会反复返工，也不会把跨学科价值压扁成普通标签工程。

---

## 7. 完成定义

本实施计划完成时，项目应达到以下状态：

- 有清晰的跨学科定位，不再被误解为普通 rebuttal generator。
- 有稳定 Review Interaction Unit schema。
- 有跨学科标注指南，可以把默会知识、制度压力、行动者网络、作者定位和情绪姿态转成可观察文本证据。
- 有 100-200 条可审计、可人工确认的 seed set。
- 有可检索的 Review Interaction KB v1，并包含 actor-network case representation。
- 有 retrieval baseline v2 和 workflow v2 小批量 cognitive trace。
- 有 evaluation protocol 和 cross-disciplinary rubric，可进入自动 + 人工评估。
- 有 data card、agent card、responsible use、data release boundary。
- 有开源 README 和论文计划。

此时项目可以进入两个方向：

1. **开源 v0.1 发布**：发布框架、schema、taxonomy、派生元数据、评测协议和 baseline。
2. **研究论文推进**：基于 KB、seed set、retrieval baseline、workflow trace 和人工评估准备论文。
