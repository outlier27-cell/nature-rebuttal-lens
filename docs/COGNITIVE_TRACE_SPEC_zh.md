# Cognitive Trace Spec

本项目的 workflow 不能一步生成 rebuttal。每条 trace 必须显式记录慢思维链条：

| Stage | 目的 | 必须输出 | 禁止行为 |
|---|---|---|---|
| understand | 拆解 reviewer 明说的 concern | concern_map | 不急着生成回复 |
| question | 识别不确定、隐含风险和可能误解 | risk_interpretation, uncertainty_notes | 不把 reviewer premise 自动当真 |
| evidence_plan | 把风险转成证据或修订动作 | evidence_action_plan | 不编造实验、数据、引用 |
| position | 帮作者选择坚持、让步、解释或反驳的位置 | author_positioning | 不无原则迎合 |
| tone_calibrate | 校准合作语气和承诺边界 | tone_commitment_warnings | 不把温暖语气当成充分回应 |
| commitment_check | 检查承诺是否可验证、可完成 | unsupported_commitment_flags | 不承诺无法完成的修改 |
| integrity_check | 检查 provenance、overclaim、adequacy | adequacy_report | 不输出无证据 claim |
| output | 生成结构化建议或 outline | final_structured_output | 不自动提交、不预测接收率 |
