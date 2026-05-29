# Review Interaction Unit Schema

## 最小单位

一条 unit 表示一个可回溯的审稿互动片段：

```text
reviewer concern -> risk interpretation -> institutional signal -> author response move -> evidence action -> author positioning -> tone / commitment -> optional editor signal
```

## 必需字段

| 字段 | 含义 | 来源 |
|---|---|---|
| unit_id | 稳定 ID | generated |
| paper_id | paper 级 ID | source |
| pair_id | 原 pair ID，如有 | source/generated |
| source_url | 来源 URL | source |
| doi | DOI，如有 | source |
| review_text | reviewer comment span | source |
| response_text | author response span | source |
| review_offset | reviewer text offset | source / alignment |
| response_offset | response text offset | source / alignment |
| concern_type | concern taxonomy | heuristic / model / human |
| risk_type | risk taxonomy | heuristic / model / human |
| institutional_signal | 制度压力、期刊边界、共同体期待的可观察信号 | model / human |
| evidence_action | evidence action taxonomy | heuristic / model / human |
| author_positioning | 作者在坚持、让步、解释、反驳之间的位置 | model / human |
| response_strategy | response strategy taxonomy | heuristic / model / human |
| tone_commitment | tone and commitment taxonomy | model / human |
| editor_signal | decision signal，如有 | source / inferred |
| actor_links | 本条互动涉及的行动者和非人类对象 | source / inferred / model |
| provenance | URL/hash/offset/source file | source |
| label_source | heuristic/model_assisted/human_confirmed/mixed | generated |

## 核心原则

schema 不声称 AI 拥有人类默会知识，只保存公开文本中的可观察痕迹和对应 provenance。
