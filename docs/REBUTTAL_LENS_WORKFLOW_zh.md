# Nature RebuttalLens 最终版工作流说明

Nature RebuttalLens 是从 NatureReview-Interact 升级出来的 manuscript-aware Author Rebuttal Assistant。它不是 final rebuttal generator，也不是接收率预测器；它的目标是把 reviewer comment、作者原稿、Nature 公开审稿互动案例、证据动作、语气承诺和跨学科解释整合成可追溯、可评估的工作流。

## 输入

- reviewer comment
- manuscript 文本、Markdown 或 LaTeX 摘要
- author draft response，可选
- editor letter，可选
- retrieved Nature cases，可选

当前开源实现只默认解析文本、Markdown 和 LaTeX 类文本。PDF / DOCX 可以后续接入显式 parser，但系统不能在解析失败时假装看过原文。

## 12 个 agent

1. ManuscriptContextExtractorAgent：整理原稿 section 和可用证据边界。
2. ManuscriptEvidenceLocatorAgent：定位 reviewer concern 在原文中的支持、缺口或不确定点。
3. ReviewerUnderstandingAgent：拆解 reviewer 明面请求。
4. TacitConcernInterpreterAgent：解释可观察文本中的隐含风险，不推断私人心理。
5. InstitutionalSignalInterpreterAgent：识别透明性、共同体标准、编辑可读性等制度信号。
6. CaseRetrievalInterpreterAgent：把 Nature 历史案例解释为有限类比，不当作规则。
7. EvidenceActionPlannerAgent：规划证据动作，并要求作者确认。
8. AuthorPositioningAgent：给出回应姿态选项。
9. ToneCommitmentCalibratorAgent：校准语气、承诺强度和 overclaim 风险。
10. ActorNetworkMapperAgent：记录 reviewer、author、dataset、figure、table、code、supplement 等行动者如何承载证据。
11. CrossDisciplinaryLensInterpreterAgent：输出默会知识边界、制度依赖、行动者网络、快慢思维校正、情绪-语气-承诺校准、作者主体性门控。
12. IntegrityAdequacyCheckerAgent：最终检查 provenance、作者确认、越界承诺、接收率预测和最终代写风险。

## 输出

Nature RebuttalLens 输出 `rebuttal_lens_trace.json`，包含：

- manuscript context
- manuscript evidence map
- concern map
- tacit risk interpretation
- institutional signal
- Nature case interpretation
- evidence action plan
- author positioning
- tone / commitment warnings
- actor network note
- cross-disciplinary lens trace
- integrity and adequacy report

## 边界

- 不生成可直接提交的最终 rebuttal。
- 不预测接收率。
- 不编造实验、数据、引用或原文证据。
- 不把 Nature 历史案例当作固定规则。
- 所有新增实验、分析、数据、引用和承诺都必须由作者确认。
