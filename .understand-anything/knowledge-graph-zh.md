# Nature RebuttalLens 中文知识图谱摘要

由 `understand-anything:understand --full --language zh` 目标流程生成，主图文件为 `.understand-anything/knowledge-graph.json`。

## 项目定位

基于 Nature 透明同行评审互动案例的 manuscript-aware、跨学科 Author Rebuttal Assistant workflow。系统把审稿意见、作者回应、文本/Markdown/LaTeX/PDF/DOCX/DOC 原稿证据、证据动作、语气/承诺、编辑信号和 Responsible Use 组织成可记录、可追溯、可评估的多智能体流程。

## 图谱统计

- 节点数：441
- 边数：473
- 架构层：6
- 导览步骤：6
- 节点类型：{'file': 71, 'document': 23, 'config': 3, 'class': 54, 'function': 287, 'concept': 3}
- 边类型：{'contains': 341, 'imports': 126, 'documents': 3, 'implements': 2, 'validates': 1}

## 架构层

- **公开入口与命令行层**：负责 package metadata、CLI 子命令、README 首页说明、示例入口和用户可见运行方式。（11 个文件级节点）
- **Nature RebuttalLens 多智能体层**：实现 manuscript-aware 的 12-agent workflow，包括审稿理解、隐性风险、证据定位、案例解释、回应规划、跨学科镜头与完整性检查。（11 个文件级节点）
- **数据处理与知识库构建层**：把 Nature 公开审稿互动数据加工为 normalized papers、review/response units、alignment、taxonomy、skill cards、KB 和 release-safe artifacts。（30 个文件级节点）
- **模型 API、评测与发布门禁层**：封装 OpenAI-compatible API、handoff/review、retrieval baseline、simulation、diagnostics、judge、readiness 和 release validation。（21 个文件级节点）
- **研究文档、伦理边界与发布治理层**：记录跨学科研究框架、数据边界、Responsible Use、agent card、evaluation protocol、系统流程图和发布审计。（21 个文件级节点）
- **测试与回归保护层**：覆盖 acceptance、multi-agent、RebuttalLens workflow、README release surface、文档可读性、API 边界和格式支持。（3 个文件级节点）

## 推荐阅读路径

1. **从项目定位开始**：先阅读 README、open-source plan 和 workflow 文档，理解项目不是普通 RAG 或自动代写，而是审稿互动学习与可追踪 assistant workflow。
2. **理解用户入口**：查看 pyproject console scripts 和 CLI main，理解用户如何运行 run-rebuttal-lens 以及 v0.1 build/validate 命令。
3. **追踪 12-agent 主流程**：从 rebuttal_lens_workflow 进入，沿 manuscript context、review understanding、case retrieval、evidence planning、tone calibration、cross-disciplinary lens 和 integrity gate 阅读。
4. **理解数据到知识库的构建链**：阅读 normalize、segment、annotate、align、taxonomy、execution build 模块，理解 v2709 案例如何转成 release-safe schema、taxonomy、KB、evaluation artifacts。
5. **检查模型 API 和安全边界**：查看 OpenAI-compatible client、responsible-use 文档和 limitation 文档，确认外部模型调用、API key、confidential manuscript 和 unsupported commitment 的边界。
6. **用测试理解发布门禁**：最后阅读 tests，确认 README release surface、agent workflow、v0.1 acceptance、中文文档可读性和 API 边界都有回归保护。
