# Claim Ledger

| Claim | Evidence needed | Current artifact | Verification status | Risk |
|---|---|---|---|---|
| v2709 包含 2709 条公开同行评审相关记录 | 主库 index / summary | `data/processed/author_rebuttal_mvp/v2709/summary.json` | verified | 需保持版本一致 |
| 约 9858 条 demo-ready pair 可用于候选检索 | pair extraction summary | `heuristic_rebuttal_pairs_demo_ready.jsonl` | supported_by_heuristic | 不是人工金标 |
| Nature rebuttal 中大量回应涉及图表、补充材料、分析和实验动作 | v2709 corpus audit | `data/analysis/final_framework_data_audit_v2709/v2709_final_framework_data_audit.md` | supported_by_corpus_audit | derived signal 可能误判 |
| 当前 workflow 已能记录 45 条可追溯 trace | workflow summary | `data/evaluation/author_rebuttal_workflow/v2709_model_revised/workflow_summary.json` | model_assisted | 样本小，未人工评估 |
| 本项目可研究默会知识的文本痕迹 | taxonomy + examples + literature | `docs/CROSS_DISCIPLINARY_ANNOTATION_GUIDE_zh.md` | planned | 不能声称 AI 真懂默会知识 |
| 行动者网络可转成 case representation | actor links + case model | `docs/ACTOR_NETWORK_CASE_MODEL_zh.md` | planned | 只能表示公开文本中的可观察关系 |
| 慢思维 workflow 可以降低直接生成风险 | cognitive trace + integrity checks | `docs/COGNITIVE_TRACE_SPEC_zh.md` | planned | 需要后续实证评估 |
