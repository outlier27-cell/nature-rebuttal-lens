# Actor Network Case Model

本模型用于把行动者网络理论转成可检索 case，而不是声称还原真实社会因果。

## 核心思想

一条 rebuttal interaction 不只是 reviewer 和 author 的两人对话，而是多个行动者被重新对齐的过程：

```text
reviewer concern -> manuscript / figure / dataset / code / benchmark -> author response -> editor-readable resolution signal
```

## 必须记录

- human actors: reviewer, author, editor
- non-human actors: manuscript, figure, table, dataset, code, benchmark, supplement, journal policy
- translation: reviewer concern 如何被作者转译成 evidence action 和 response wording
- provenance: 每个 actor link 都必须能回到原文证据

## 边界

actor-network case 只表示公开文本中的可观察关系，不声称发现真实因果机制、隐藏审稿讨论或编辑真实心理。
