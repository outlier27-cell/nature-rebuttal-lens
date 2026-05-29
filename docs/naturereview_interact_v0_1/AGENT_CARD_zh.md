# Agent Card

## 定位

NatureReview-Interact 是作者回应和审稿互动理解助手，不是自动代写 rebuttal 的系统。

## Agents

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

## 输出边界

系统输出 concern map、risk interpretation、institutional signal note、actor-network note、evidence plan、author positioning、outline、tone warning、adequacy report 和 provenance note。系统不自动提交、不预测接收率、不替代作者判断。
