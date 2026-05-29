# v2709 Data Card

## 数据来源

Nature 系列公开同行评审相关页面和公开文件。

## 数据用途

- 审稿互动结构研究
- review concern / author response strategy 分析
- tacit concern / institutional signal / evidence action 标注研究
- retrieval baseline
- agent workflow trace evaluation

## 不适合用途

- 自动代写完整 rebuttal 并直接提交
- 接收率预测
- 对 reviewer 或 editor 的个体画像
- 训练不带 provenance 的黑箱生成器
- 声称模型拥有真实人类默会知识

## 当前金标状态

当前没有人工金标。当前 v0.1 默认使用 API 模型复核标签，属于 API 替代人工复核的 model-assisted seed；所有 heuristic 和 model-assisted 标签只能作为候选标签、检索样本或 sanity evaluation 输入，不能作为最终 benchmark gold label。

## 标签状态

| 标签类型 | 含义 | 可用于 |
|---|---|---|
| heuristic | 规则或弱监督生成 | 候选检索、粗粒度分析 |
| model-assisted | API 模型辅助复核 | 小规模 sanity evaluation |
| human-confirmed | 人工确认 | 正式 benchmark |

## 当前版本

- v2709 主库：2709 records
- demo-ready pairs：9858
- 本轮 seed candidates：见 `data/evaluation/seed_set/v1/`
- API 替代人工复核：200 条 seed request 已由 deepseek-v3 复核，结果仍是 model-assisted，不是 human gold。
