# Nature RebuttalLens 发布前最终升级审计

更新时间：2026-06-05
工作分支：`feature/nature-response-schema-refactor`

## 1. 目标

本轮升级目标是把 Nature RebuttalLens 从“可运行的多智能体 rebuttal 分析器”提升到“可发布、可审计、带明确作者决策边界的 manuscript-aware rebuttal planning 系统”。

验收标准：

- 真实 OpenAI-compatible DeepSeek API 可以跑完整流程。
- DAG、reviewer committee、strategy tournament、final report 可以在同一次运行中协同工作。
- final report 不是最终投稿文本，而是可审计 response package。
- 每条 reviewer concern 都要尽量带有 severity、category、proposed_action、readiness、risk_level、missing_author_input、evidence_anchor。
- 高风险作者决策不得被系统记忆或替代承诺。
- trace 与 final report 必须显式展示 memory ethics boundary。
- DeepSeek provider 的真实 JSON 漂移必须被 normalizer 吸收。
- README、补丁文档、Understand 图谱和真实运行报告必须能说明当前系统架构。
- 全量测试、编译、NatureReview validation、密钥扫描和产物完整性检查通过。

非目标：

- 不训练模型，不微调模型。
- 不把 retrieved cases 当作稿件证据。
- 不生成可直接提交的最终 rebuttal。
- 不替作者决定新实验、新分析、claim narrowing、limitation admission 或 future work commitment。

## 2. 系统盘点

主要模块：

- `src/peer_review_skills/agents/rebuttal_lens_workflow.py`：工作流入口，支持 layered 与 DAG 两条路径。
- `src/peer_review_skills/agents/rebuttal_lens_graph.py`：DAG 节点与依赖图。
- `src/peer_review_skills/agents/committee_agents.py`：methodology / claim / tone reviewer committee。
- `src/peer_review_skills/agents/strategy_tournament.py`：策略候选与 meta planner。
- `src/peer_review_skills/agents/response_package.py`：Nature-compatible response package schema。
- `src/peer_review_skills/agents/final_report.py`：最终 JSON/Markdown 作者报告。
- `src/peer_review_skills/agents/base.py`：agent JSON 解析和 provider output normalizer。
- `src/peer_review_skills/cli/main.py`：公开 CLI 参数。
- `README.md`：发布说明。
- `docs/REBUTTAL_LENS_MEMORY_ETHICS_PATCH_zh.md`：记忆伦理补丁说明。

测试层：

- `tests/test_response_package.py`
- `tests/test_rebuttal_lens_workflow.py`
- `tests/test_rebuttal_lens_committee_strategy.py`
- `tests/test_multi_agent.py`
- 全量 pytest 共 138 个测试。

## 3. 外部参考与吸收方式

| 来源 | 借鉴点 | 当前落地 |
| --- | --- | --- |
| `捍卫智能体记忆的伦理纯粹性.pdf` | 证成大于结论、决策权记忆归零、不可替代表达承诺、不可篡改审计痕迹、标注记忆边界 | `memory_ethics_boundary`、`--reset-memory`、`decision_deferred`、`memory_decision_boundary` |
| `Yuan1z0825/nature-skills/skills/nature-response` | reviewer comment ID、action label、readiness gate、QA checklist | `response_package.py` 的 action/readiness/risk/schema 字段 |
| `Yuan1z0825/nature-skills/skills/nature-reviewer` | 不虚构 reviewer 身份，只使用不同 emphasis | `committee_agents.py` 的 methodology / claim / tone committee |
| `Yuan1z0825/nature-skills/skills/nature-data` | FAIR、repository、identifier、license、metadata check | `data_availability_check` |
| `Yuan1z0825/nature-skills/skills/nature-citation` | 引用不能仅靠标题相关就作为证据 | `citation_support_check` |
| `Galaxy-Dawn/claude-scholar/skills/review-response` | Accept / Defend / Clarify / Experiment 策略库 | `strategy_tournament.py`，但套上 evidence gate 与 author confirmation |

## 4. 已实施升级

### 4.1 Response Package Schema

状态：已完成。

实现内容：

- 新增 Nature-compatible action labels。
- 新增 readiness 状态 `decision_deferred`。
- 增加 severity、category、risk_level、missing_author_input、evidence_anchor。
- 增加每条 card 的 `memory_decision_boundary`。
- 高风险且需要作者确认的动作进入 `decision_deferred`，而不是被普通 `needs_author_input` 吞掉。

覆盖测试：

- `tests/test_response_package.py`
- `tests/test_rebuttal_lens_workflow.py::test_final_report_uses_decision_deferred_for_unconfirmed_high_risk_actions`

### 4.2 记忆伦理边界

状态：已完成。

实现内容：

- trace 增加 `memory_ethics_boundary`。
- final report 增加 `memory_ethics_boundary`。
- README 增加 Memory Ethics Boundary 小节。
- CLI 增加 `--reset-memory`。
- `--reset-memory` 被写入 workflow config 并反映到 trace/report。

边界规则：

- `justification_memory_not_conclusion_memory = true`
- `cross_run_strategy_memory_used = false`
- `author_decisions_reset_each_run = true`
- `per_item_author_confirmation_required = true`
- `trace_bound_to_output = true`

### 4.2.1 Active Forgetting Runtime

状态：已进入实施计划并完成代码落地。

本轮 memory-ethics 升级把“遗忘使记忆成为记忆”转成 runtime 证据：

- `memory_passport` 记录保留与遗忘的 memory classes。
- `forgetting_ledger` 记录每个被遗忘 memory class 及其伦理理由。
- `irreversible_forgetting_statement` 声明被遗忘的 author decisions、strategy preferences、final wording 不能从 checkpoints、cache、retrieved cases 或旧 final reports 中重构。
- `--memory-policy strict` 为 contamination-sensitive runs 扩大遗忘范围。
- `--forget-scope` 允许用户为单次运行显式增加要遗忘的 memory class。
- 跨运行回归测试验证上一轮作者选择 A 不会成为下一轮默认答案。
- Markdown 报告包含中文伦理解释：“遗忘不是能力损失，而是保护作者主体性的边界。”

这让 RebuttalLens 不会把过去作者选择悄悄转成未来默认策略。

### 4.3 DAG / Committee / Strategy Tournament 高配路径

状态：已完成。

实现内容：

- DAG 路径支持可选 committee 和 strategy tournament 节点。
- committee 使用 methodology、claim calibration、tone interaction 三种 emphasis。
- strategy tournament 输出候选策略，meta planner 选择保守主策略。
- 真实 DeepSeek v3 运行验证 11 层 DAG、19 节点、18 次 LLM 调用、0 错误。

### 4.4 DeepSeek Provider Drift 硬化

状态：已完成。

实现内容：

- `base.py`：结构化 `reasoning` dict/list 归一化为 JSON string。
- `strategy_tournament.py`：补齐缺失 `strategy_id`，兼容扁平候选结构，不把 numeric feasibility 转成 required_actions。
- `strategy_tournament.py`：兼容 dict rejection_reasons 与 object list author questions。
- `specialized_agents_part2.py`：允许合法 fast thinking / slow thinking evidence-check 标签，增加否定语境识别。
- `final_report.py`：从 dict question 中提取 question/text/description/required_artifact，避免 Markdown 中出现 Python dict 字符串。

### 4.5 发布文档与知识图谱

状态：已完成。

新增/更新产物：

- `README.md`：新增 Memory Ethics Boundary。
- `docs/REBUTTAL_LENS_MEMORY_ETHICS_PATCH_zh.md`：记忆伦理补丁说明。
- `.understand-anything/knowledge-graph.json`：代码结构图谱，28 节点、30 边。
- `.understand-anything/memory-ethics-knowledge-graph.json`：记忆伦理知识图谱，21 节点、26 边。
- `data/evaluation/rebuttal_lens_deepseek_full_20260605_v3/DEEPSEEK_V3_FULL_RUN_REPORT_zh.md`：真实 DeepSeek v3 完整运行报告。

## 5. 真实运行证据

运行命令使用：

- `deepseek-v3`
- `https://xh.v1api.cc`
- `--workflow-engine dag`
- `--enable-committee`
- `--enable-strategy-tournament`
- `--reset-memory`

输出目录：

`data/evaluation/rebuttal_lens_deepseek_full_20260605_v3`

运行结果：

- `total_llm_calls = 18`
- `levels_executed = 11`
- `graph_node_count = 19`
- `nodes_executed = 19`
- `message_bus_count = 18`
- `error_count = 0`
- `package_readiness = needs_author_input`
- `response_package_gate_issues = []`
- `unsafe_claims = []`
- `provenance_checks = 2`
- `memory_ethics_boundary.reset_memory_requested = true`

结论：示例最终为 `needs_author_input` 是正确结果，因为系统识别到 alternative split robustness evidence 缺失，不能替作者承诺已解决。

## 6. 验证日志

| 命令/检查 | 结果 | 说明 |
| --- | --- | --- |
| DeepSeek v3 full DAG run | PASS | 18 LLM calls，11 DAG levels，0 errors |
| artifact integrity check | PASS | summary/trace/final report JSON 可解析，Markdown UTF-8 中文正常 |
| Understand graph validation | PASS | 两个图谱节点唯一、边不悬空、layer/tour 引用存在 |
| `git diff --check` | PASS | 仅 CRLF warning，无 whitespace error |
| `python -m compileall -q src tests` | PASS | 编译通过 |
| `python -m pytest -q --basetemp=C:\tmp\rl_pytest_deepseek_v3_final` | PASS | 138 passed in 10.27s |
| `python -m peer_review_skills.cli.main validate-naturereview-v01` | PASS | validation PASS，关键计数正常 |
| secret scan | PASS | 无真实 key 写入；测试 fixture 的 fake Bearer token 已白名单区分 |
| README/docs/final_report mojibake scan | PASS | UTF-8 读取无 replacement char 和常见 mojibake marker |

## 7. 回滚策略

如需回滚本轮核心行为：

- 移除 `--reset-memory` CLI 参数。
- 从 trace/final report 移除 `memory_ethics_boundary`。
- 从 response package 移除 `decision_deferred` 和 `memory_decision_boundary`。
- 回退 DeepSeek normalizer 补丁。

不建议回滚，因为这些补丁都是发布边界、安全性和真实 provider 兼容性相关。

## 8. 剩余风险

- 当前真实 API 示例只有 1 条 reviewer concern，不能覆盖所有复杂多 reviewer 场景。
- DAG 模式当前审计主干是 `execution_trace` 和 `message_bus`，不是 `checkpoints/` 目录；这是当前设计，需要在文档中讲清楚。
- 用户曾在聊天中暴露 API key；仓库未写入该 key，但发布前应轮换平台 key。
- `.understand-anything/`、`docs/`、`UPGRADE.md`、DeepSeek demo 输出目录当前被 `.gitignore` 忽略；如果需要把这些作为发布材料提交，需要调整忽略策略或单独归档。

## 9. 完成清单

- [x] 真实 DeepSeek API 完整流程跑通。
- [x] DAG + committee + strategy tournament 高配路径跑通。
- [x] response package schema 完成。
- [x] decision_deferred 完成。
- [x] memory ethics boundary 完成。
- [x] --reset-memory 完成。
- [x] DeepSeek provider drift normalizer 完成。
- [x] README 与记忆伦理补丁文档完成。
- [x] Understand 代码图谱完成。
- [x] Understand 记忆伦理知识图谱完成。
- [x] 真实运行报告完成。
- [x] 全量测试、编译、validation、密钥扫描完成。
- [ ] 如需提交 GitHub，先确认是否提交被忽略的 docs / UPGRADE / .understand-anything / demo artifacts。
