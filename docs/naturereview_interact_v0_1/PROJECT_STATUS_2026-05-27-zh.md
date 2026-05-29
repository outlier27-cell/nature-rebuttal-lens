# NatureReview-Interact 项目状态

更新时间：2026-05-27

## 当前一句话

本项目已经从爬取阶段转向把 v2709 公开同行评审数据转化为可检索、可评估、可追溯、负责任开源的 Review Interaction Agent。

## 当前已确认资产

| 资产 | 数量 / 路径 | 状态 |
|---|---:|---|
| v2709 主库 | 2709 records | verified |
| core full-chain papers | 339 | verified |
| response-only papers | 1400 | verified |
| review-only input papers | 860 | verified |
| editor decision-only papers | 42 | verified |
| demo-ready pairs | 9858 | heuristic |
| clean heuristic pairs | 11311 | heuristic |
| all heuristic pairs | 21978 | heuristic |
| demo-ready cases | 738 | heuristic |
| model-revised mini seed | 50 rows, 45 usable | model-assisted |
| workflow traces | 45 | prototype |

## 当前不能声称的内容

- 不能声称已有人工金标。
- 不能声称 agent 已经被真实作者或审稿专家验证。
- 不能声称模型真正掌握默会知识。
- 不能声称系统能预测接收率。
- 不能声称当前 workflow 已经是最终产品。

## 已有 baseline

- P1 best concern@5: `bm25_concern_filter`
- P1 best strategy@5: `hybrid_bm25_concern_strategy`
- workflow strategy_hit_at_5_rate: `0.8666666666666667`
- workflow joint_hit_at_5_rate: `0.7777777777777778`
- workflow integrity_pass_rate: `1.0`

## 本轮执行输出目录

- `docs/naturereview_interact_v0_1/`
- `data/processed/schemas/`
- `data/processed/taxonomies/`
- `data/processed/review_interaction_kb/v1/`
- `data/evaluation/seed_set/v1/`
- `data/evaluation/retrieval_v2/`
- `data/evaluation/workflow_v2/`
- `data/evaluation/eval_protocol_v1/`
