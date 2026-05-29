# PDF-derived Design Lenses

## 定位

本文件把 `2026.5.15.pdf` 和 `2026.5.23.pdf` 的跨学科分析落到 NatureReview-Interact 的非训练系统设计中。它不是单一技术清单，也不是训练或微调计划，而是一个可记录、可追溯、可评估的解释框架。

## 2026.5.15.pdf 给出的设计线索

| Lens | PDF 来源 | 系统含义 | 必须保留的边界 |
|---|---|---|---|
| 默会知识 | `2026.5.15.pdf` | 审稿意见背后常有专家共同体的判断、可信度预期和领域标准；系统只能学习这些判断在公开文本中的痕迹。 | 不声称 AI 真懂默会知识，不推断 reviewer 真实心理。 |
| 制度依赖 | `2026.5.15.pdf` | 作者回应受到期刊、审稿制度、发表压力、共同体规范影响；系统应帮助作者辨认制度信号。 | 不预测接收率，不把礼貌或让步写成制度服从。 |
| 行动者网络 | `2026.5.15.pdf` | review interaction 不是两个人的文本对话，还涉及 manuscript、figure、dataset、code、benchmark、supplement、editor signal 等行动者。 | 只记录公开文本中的可观察对齐关系，不还原真实社会因果。 |

## 2026.5.23.pdf 给出的设计线索

| Lens | PDF 来源 | 系统含义 | 必须保留的边界 |
|---|---|---|---|
| 快思维 / 慢思维 | `2026.5.23.pdf` | 作者和 LLM 都可能快速防御、快速生成或快速迎合；系统必须先理解、再质询、再证据规划、再输出。 | 不一步生成 final rebuttal，不把流畅文本当成充分回应。 |
| 情绪和语气校准 | `2026.5.23.pdf` | 情绪维度应转成学术互动姿态：defensiveness、sycophancy risk、commitment level、uncertainty handling。 | 不诊断情绪，不做共情表演，不用温和语气替代证据。 |
| LIWC / GPT 心理文本分析启发 | `2026.5.23.pdf` | 可借鉴心理文本分析关注语气、确定性、承诺和互动姿态，但系统输出必须可审计。 | 不把心理分析写成医学或人格判断。 |

## 系统落点

每条 workflow trace 都必须包含以下 lens map：

1. `tacit_knowledge_boundary`
2. `institutional_dependence`
3. `actor_network_alignment`
4. `fast_slow_cognitive_correction`
5. `emotion_tone_commitment_calibration`
6. `author_agency_gate`

每个 lens 都必须给出 `source_pdf`、`observable_trace`、`system_action`、`boundary` 和 `evaluation_question`。

## 明确排除

- 不是单一技术清单。
- 不是训练或微调。
- 不是 RAG-only。
- 不是自动代写 rebuttal。
- 不是接收率预测。
