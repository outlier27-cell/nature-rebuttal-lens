# Workflow Spec

## Output Contract

```json
{
  "concern_map": [],
  "risk_interpretation": [],
  "institutional_signal_note": [],
  "actor_network_note": [],
  "retrieved_cases": [],
  "evidence_action_plan": [],
  "author_positioning": [],
  "rebuttal_outline": [],
  "tone_commitment_warnings": [],
  "adequacy_report": [],
  "editor_signal_note": [],
  "provenance_notes": [],
  "responsible_use_warnings": []
}
```

## Required Cognitive Trace

每次运行必须保留：

```text
understand -> question -> evidence_plan -> position -> tone_calibrate -> commitment_check -> integrity_check -> output
```

## Trace Requirements

- 每个 retrieved case 必须有 provenance。
- 每个 evidence action 必须对应 reviewer concern 或 author response evidence。
- 每个 commitment warning 必须说明是否存在 overclaim、unsupported_commitment、sycophancy、excessive_defensiveness 或 uncertainty_hiding。
- 输出不是 final rebuttal，不直接提交，不预测接收率。
