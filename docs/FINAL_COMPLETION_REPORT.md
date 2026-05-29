# 多 Agent 系统完成报告

日期：2026-05-28

## 当前结论

NatureReview-Interact 已经具备一个可运行的 v3 真多 Agent 工作流入口：

```powershell
$env:PYTHONPATH='src'
$env:PEER_REVIEW_API_BASE_URL='https://xh.v1api.cc'
$env:PEER_REVIEW_API_MODEL='deepseek-v3'
$env:PEER_REVIEW_API_KEY='YOUR_KEY'
python -m peer_review_skills.cli.main run-naturereview-multi-agent --limit 1
```

该入口只读取当前 v0.1 正式 KB、retrieval v2 和 taxonomy 文件，并输出到：

```text
data/evaluation/workflow_v3/
```

## 已实现内容

1. 9 个独立 LLM agent。
2. 结构化 agent message bus。
3. 依赖感知的 orchestrator，不再把有上下游依赖的 agent 当成并行格式化函数。
4. 与 v0.1 正式数据目录对齐的 workflow integration。
5. OpenAI-compatible / DeepSeek client 兼容。
6. taxonomy alias 映射。
7. fail-fast 错误处理，避免半成功 trace 被误认为完整工作流。
8. 跨学科 lens 层：默会知识边界、制度依赖、行动者网络、快慢思维校正、情绪-语气-承诺校准、作者主体性门控。
9. integrity / adequacy checker，保留 responsible-use warnings。
10. refinement 流程：带原始上下文和 feedback 修订指定 agent，重跑依赖它的下游 agent，再做 integrity recheck。

## 工作流顺序

```text
ReviewerUnderstandingAgent
  -> TacitConcernInterpreterAgent
  -> InstitutionalSignalInterpreterAgent
  -> EvidenceActionPlannerAgent
  -> AuthorPositioningAgent
  -> ToneCommitmentCalibratorAgent
  -> ActorNetworkMapperAgent
  -> CrossDisciplinaryLensInterpreterAgent
  -> IntegrityAdequacyCheckerAgent
```

默认不开 refinement 时，每条 interaction unit 是 9 次 LLM 调用、8 个依赖感知执行步骤。

## 当前 smoke test 证据

小批量真实 API smoke run 已经能产生：

```json
{
  "total_traces": 1,
  "total_llm_calls": 9,
  "input_interaction_units": 245,
  "input_retrieval_predictions": 100
}
```

这只证明链路可运行，不等于证明质量提升。质量提升需要单独的人类或专家评估。

## 边界

本系统不是：

- final rebuttal generator；
- acceptance predictor；
- human gold benchmark；
- reviewer/editor/author 的替代品；
- 声称读懂审稿人真实心理的系统；
- 声称多 Agent 自动更好的系统。

本系统是：

- 基于 Nature 公开审稿互动案例的 author rebuttal assistant workflow；
- model-assisted、可追溯、可评估的研究框架；
- 用跨学科 lens 帮助作者理解、组织和检查回应的系统。

最终完成状态以 `UPGRADE.md`、`docs/architecture/true-multi-agent-design.md` 和测试验证命令为准。
