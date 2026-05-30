# Nature RebuttalLens 完整工作示例

本文用仓库内置示例说明 Nature RebuttalLens 如何从输入一步一步生成可审计输出。它不是最终 rebuttal 生成器，而是一个 manuscript-aware、跨学科、可追踪的作者回应辅助工作流。

## 1. 输入文件

示例输入位于 `examples/rebuttal_lens/`：

- `reviewer_comment.txt`：审稿人意见。
- `manuscript_excerpt.md`：作者提供的 manuscript 摘录。
- `author_draft_response.txt`：作者已有草稿回应，可为空。
- `retrieved_cases.json`：检索到的 Nature 透明同行评审案例，可为空。

运行命令：

```powershell
$env:PYTHONPATH="src"
$env:PEER_REVIEW_API_BASE_URL="https://xh.v1api.cc"
$env:PEER_REVIEW_API_KEY="YOUR_KEY"
$env:PEER_REVIEW_API_MODEL="deepseek-v3"

python -m peer_review_skills.cli.main run-rebuttal-lens `
  --review-file examples/rebuttal_lens/reviewer_comment.txt `
  --manuscript-file examples/rebuttal_lens/manuscript_excerpt.md `
  --response-file examples/rebuttal_lens/author_draft_response.txt `
  --retrieved-cases-file examples/rebuttal_lens/retrieved_cases.json `
  --output-dir data/evaluation/rebuttal_lens_demo
```

如果没有设置 `PEER_REVIEW_API_KEY`，CLI 会直接报出缺失配置，不会进入半执行状态。

## 2. 输入预处理

CLI 读取文件后调用 `run_rebuttal_lens_workflow()`。

第一步是构造 `unit`：

- `review_text` 保存审稿意见。
- `response_text` 保存作者草稿。
- `editor_text` 保存可选编辑信。
- `manuscript_context` 保存 manuscript 模式、分节、字符数、证据边界。
- `unit_id` 默认是 `rebuttal_lens_user_case`，也可以由配置覆盖。

manuscript 支持文本、Markdown、LaTeX-like 文本、PDF、DOCX 和需要 LibreOffice 转换的 DOC。当前 PDF/DOCX 主要做文本抽取，不做 OCR、图像理解或复杂表格解析。

## 3. 模型与配置

工作流从 `config/multi_agent_config.yaml` 读取 12 个 agent 的配置。每个 agent 可配置：

- `model`
- `temperature`
- `max_retries`

这些配置会进入 agent 实例。前端 manuscript agent 和后端 9 个专业 agent 都按 agent id 解析运行参数。这样可以把复杂 agent 放到更强模型，把简单 agent 放到更低成本模型。

## 4. 12 个 Agent 的执行顺序

RebuttalLens 按层执行，每一层输出会进入后续 agent。

### Layer 0: Manuscript Context

`manuscript_context_extractor`

作用：

- 总结作者提供的 manuscript context。
- 标明哪些 section 可作为证据来源。
- 记录输入限制，例如只提供了片段、缺少图表、缺少补充材料。

输出会进入 reviewer understanding、tacit concern、manuscript evidence 等后续步骤。

### Layer 1: Review Understanding

`reviewer_understanding_agent`

作用：

- 提取审稿人明确提出的问题。
- 把问题映射到 concern taxonomy。
- 只根据审稿文本做判断，不声称知道审稿人真实心理。

### Layer 1: Tacit Concern Interpretation

`tacit_concern_interpreter`

作用：

- 从可观察文本中解释潜在风险。
- 输出 tacit concern 和 risk interpretation。
- 明确边界：这只是文本迹象，不是对审稿人动机的读取。

### Layer 1: Manuscript Evidence

`manuscript_evidence_locator`

作用：

- 把 reviewer concern 回连到 manuscript section。
- 判断证据状态：supported、partially_supported、missing、uncertain。
- 记录 gap 和作者需要确认的问题。

长 manuscript 会先按 review relevance 选择最多 12 个 section，并记录截断元数据，避免只看前几节导致漏掉后文关键证据。

### Layer 2: Institutional Signal

`institutional_signal_interpreter`

作用：

- 解释 journal/editor-facing 信号。
- 例如透明度、方法充分性、可复现性、领域规范。
- 不预测接收概率。

### Layer 2: Case Retrieval Interpretation

`case_retrieval_interpreter`

作用：

- 把 retrieved Nature cases 解释为有边界的历史类比。
- 输出哪些策略可以迁移，哪些不能迁移。
- 明确案例不是规则，也不是结果预测。

### Layer 2: Evidence Action Planning

`evidence_action_planner`

作用：

- 综合 concern、risk、manuscript evidence 和 retrieved cases。
- 给出证据行动计划，例如补充说明、补充分析、修订图表、提供代码或数据。
- 每个行动都要求作者确认，不允许发明实验、数据、引用或承诺。

### Layer 3: Author Positioning

`author_positioning_agent`

作用：

- 给出作者回应 stance。
- 例如承认并修正、澄清已有证据、合理防守、请求边界化解释。
- 不强迫作者让步。

### Layer 3: Tone & Commitment

`tone_commitment_calibrator`

作用：

- 检查语气和承诺是否安全。
- 标记 defensive tone、unsupported commitment、overclaim、过度让步等风险。
- 不把语气替代证据。

### Layer 4: Actor Network

`actor_network_mapper`

作用：

- 映射证据载体：作者、审稿人、编辑、图表、数据集、代码、补充材料、引用。
- 判断哪些 actor 承载了证据、信号或承诺。
- 避免把复杂同行评审简化成单一社会因果。

### Layer 4: Cross-Disciplinary Lenses

`cross_disciplinary_lens_interpreter`

作用：

用 6 个跨学科 lens 解释当前交互：

- 默会知识边界
- 制度依赖
- 行动者网络对齐
- 快慢思维校正
- 情绪-语气-承诺校准
- 作者主体性门控

每个 lens 都输出：

- 可观察迹象
- 系统动作
- 边界
- 可评估问题

### Layer 5: Integrity

`integrity_adequacy_checker`

作用：

- 对所有 agent 输出做最终完整性检查。
- 检查 provenance、adequacy、safety、responsible-use boundary 和 author agency。
- 输出 responsible use warnings 和 issues。

## 5. Checkpoint 与失败追踪

工作流每执行完一层，就写入 checkpoint：

```text
data/evaluation/rebuttal_lens_demo/checkpoints/
```

如果第 3 个或更晚 agent 调用失败，系统会写出：

```text
data/evaluation/rebuttal_lens_demo/rebuttal_lens_failure_trace.json
```

失败 trace 包含已经完成的 message bus、execution trace 和 summary，但不会写入 API key。

## 6. 最终输出

成功执行后写出两个主要文件：

```text
data/evaluation/rebuttal_lens_demo/rebuttal_lens_trace.json
data/evaluation/rebuttal_lens_demo/rebuttal_lens_summary.json
```

`rebuttal_lens_trace.json` 包含：

- `trace_id`
- `query_unit_id`
- `agent_intermediate_outputs`
- `message_bus`
- `execution_trace`
- `execution_metadata`
- `manuscript_context`
- `responsible_use_boundary`

`rebuttal_lens_summary.json` 包含：

- 系统名
- workflow version
- 总 trace 数
- 总 LLM call 数
- manuscript mode
- trace 文件路径
- 脱敏后的 config

## 7. 如何判断这个系统真的 work

可以用以下证据判断：

- 每个 agent 都独立构造 prompt 并调用模型 client。
- 每个 agent 都有结构化 JSON 输出校验。
- 上游输出进入下游输入，不只是生成描述性文本。
- checkpoint 和 failure trace 能记录执行状态。
- CLI 缺少 API key 时明确失败，不会伪造结果。
- 测试覆盖 manuscript loading、agent schema、checkpoint、failure trace、CLI、配置和公开文档边界。

推荐验证命令：

```powershell
$env:PYTHONPATH="src"
python -m pytest -q
python -m compileall -q src tests
python -m peer_review_skills.cli.main validate-naturereview-v01
python -m pip install --dry-run -e .
```

这些命令验证的是本地代码、结构、文档和 release artifacts。真实 API 调用还需要有效的 `PEER_REVIEW_API_KEY`。

## 8. 当前边界

Nature RebuttalLens 当前仍有明确边界：

- 不生成最终可提交 rebuttal。
- 不预测 acceptance probability。
- 不读取审稿人私人心理。
- 不发明实验、数据、图表、引用或承诺。
- 不建议未经授权上传 confidential manuscript。
- RebuttalLens 主流程当前不支持自动 refinement；如开启会 fail fast。

因此，系统的定位是作者思考、组织、检查和追踪回应策略的辅助工具，而不是替代作者、审稿人或编辑判断的自动决策系统。
