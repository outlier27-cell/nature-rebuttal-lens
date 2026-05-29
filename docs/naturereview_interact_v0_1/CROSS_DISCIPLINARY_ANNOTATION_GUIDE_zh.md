# Cross-disciplinary Annotation Guide

## 总原则

本项目不标注 reviewer 的真实心理，也不声称 AI 真正掌握默会知识。我们只标注公开文本中可观察的互动痕迹。

每个跨学科标签必须满足三个条件：

1. 有原文证据：reviewer comment、author response 或 editor decision 中能找到支持片段。
2. 有互动功能：该标签解释了 concern、response 或 decision signal 的关系。
3. 可被反驳：另一个标注者可以根据同一文本不同意该标签。

## Tacit Concern

| 标签 | 可观察证据 | 不应标注的情况 |
|---|---|---|
| credibility_trust | reviewer 质疑结果是否可靠、claim 是否被数据支撑、实验是否足以支撑结论 | 只是要求改错别字或补格式 |
| community_standard_fit | reviewer 要求常见 baseline、标准 benchmark、领域通用报告方式 | 只是任意要求更多实验 |
| evidence_chain_stability | reviewer 指出图表、统计、补充材料、方法描述之间链条不稳 | 单纯说写得不清楚但不影响证据链 |
| presentation_as_epistemic_signal | reviewer 把图表、表达或结构问题当作可信度问题 | 纯语言润色 |

## Institutional Signal

| 标签 | 可观察证据 | 解释边界 |
|---|---|---|
| journal_scope_fit | editor/reviewer 关注工作是否适合期刊范围、影响力或 novelty threshold | 不能推断真实编辑偏好 |
| reviewer_authority_pressure | author response 显示明显让步、道歉、顺从审稿权威 | 不能把礼貌语气一律当成权力压力 |
| transparency_norm | 要求 code/data、材料、可复现细节 | 应与具体 reproducibility evidence 区分 |
| editorial_risk_control | editor 强调 unresolved concern、additional revision、remaining issue | 不等同于接收率预测 |

## Author Positioning

| 标签 | 含义 | 示例性证据 |
|---|---|---|
| accept_and_revise | 作者接受意见并完成修改 | "We have added..." |
| clarify_without_new_work | 作者解释已有内容，不新增实验 | "We clarify that..." |
| justify_existing_choice | 作者为原方法选择辩护 | "We chose this because..." |
| partially_concede | 部分接受，部分保留原立场 | "While we agree..., we note..." |
| respectfully_disagree | 明确但礼貌地反驳 reviewer premise | "We respectfully disagree..." |
| narrow_claim | 缩小 claim 或增加限制 | "We have toned down..." |
| defer_to_future_work | 承认重要但放到未来工作 | "We leave this to future work..." |

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

## Cognitive and Tone Boundary

本项目不诊断作者或 reviewer 的情绪状态，只标注文本中的互动姿态：

- defensive tone: 文本过度防御，可能削弱合作姿态；
- sycophancy risk: 无证据地迎合 reviewer 或承诺无法完成的修改；
- uncertainty hiding: 回避不确定性或把弱证据写成强结论；
- confidence calibration: 明确说明证据强度、限制和可验证承诺。
