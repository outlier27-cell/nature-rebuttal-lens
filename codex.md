# Nature RebuttalLens 项目总览

更新时间：2026-05-29
项目目录：`C:\Users\wancy\Desktop\nature-comment`

## 一句话

Nature RebuttalLens 是一个基于 Nature 系列公开同行评审互动案例的跨学科、可追溯、可评估 Author Rebuttal Assistant workflow。它不是爬虫项目、不是训练微调项目、不是 RAG-only 系统、不是自动代写 rebuttal 的工具。

它的核心目标是帮助作者理解 reviewer comment 背后的显性关切、隐含风险、制度信号、证据缺口、语气承诺和作者主体性边界，并用 Nature 历史案例作为有 provenance 的有限类比。

## 当前最终工作流

```text
manuscript context
  -> manuscript evidence map
  -> reviewer concern map
  -> tacit / explicit risk
  -> institutional signal
  -> bounded Nature case analogy
  -> evidence action plan
  -> author positioning
  -> tone / commitment calibration
  -> actor network map
  -> cross-disciplinary lens trace
  -> integrity / adequacy / author confirmation gate
```

## 12 个 Agent

1. ManuscriptContextExtractorAgent：整理原稿 section 和证据边界。
2. ManuscriptEvidenceLocatorAgent：定位原文证据、缺口和不确定点。
3. ReviewerUnderstandingAgent：拆解 reviewer 明面请求。
4. TacitConcernInterpreterAgent：解释可观察文本中的隐含风险，不读心。
5. InstitutionalSignalInterpreterAgent：识别透明性、共同体标准、编辑可读性等制度信号。
6. CaseRetrievalInterpreterAgent：把 Nature 历史案例解释为有限类比，不当作规则。
7. EvidenceActionPlannerAgent：规划证据动作，要求作者确认。
8. AuthorPositioningAgent：给出回应姿态选项。
9. ToneCommitmentCalibratorAgent：校准语气、承诺强度和 overclaim 风险。
10. ActorNetworkMapperAgent：记录 reviewer、author、dataset、figure、table、code、supplement 等行动者如何承载证据。
11. CrossDisciplinaryLensInterpreterAgent：输出默会知识边界、制度依赖、行动者网络、快慢思维校正、情绪-语气-承诺校准、作者主体性门控。
12. IntegrityAdequacyCheckerAgent：最终检查 provenance、作者确认、越界承诺、接收率预测和最终代写风险。

## 当前数据基础

当前主数据版本仍来自 v2709 Nature 系列公开同行评审记录。v0.1 知识库已整理出：

| 项目 | 数量 |
|---|---:|
| seed candidates | 200 |
| model-assisted seed records | 200 |
| interaction units | 245 |
| case index | 199 |
| actor-network cases | 199 |
| retrieval predictions | 100 |
| workflow traces | 50 |
| simulation traces | 50 |
| cross-disciplinary lens traces | 50 |
| API handoff requests | 200 |

这些标签是 `model_assisted`，不是 human gold。

## 常用命令

运行 Nature RebuttalLens 示例：

```powershell
$env:PYTHONPATH='src'
$env:PEER_REVIEW_API_BASE_URL='https://xh.v1api.cc'
$env:PEER_REVIEW_API_MODEL='deepseek-v3'
$env:PEER_REVIEW_API_KEY='YOUR_KEY'
python -m peer_review_skills.cli.main run-rebuttal-lens `
  --review-file examples/rebuttal_lens/reviewer_comment.txt `
  --manuscript-file examples/rebuttal_lens/manuscript_excerpt.md `
  --response-file examples/rebuttal_lens/author_draft_response.txt `
  --output-dir data/evaluation/rebuttal_lens_demo
```

验证 v0.1 artifacts：

```powershell
$env:PYTHONPATH='src'; python -m peer_review_skills.cli.main validate-naturereview-v01
```

运行测试：

```powershell
$env:PYTHONPATH='src'; python -m pytest -q
```

编译检查：

```powershell
$env:PYTHONPATH='src'; python -m compileall -q src tests
```

## 边界

- 不生成可直接提交的最终 rebuttal。
- 不预测接收率。
- 不编造实验、数据、引用或原文证据。
- 不把 Nature 历史案例当作固定规则。
- 不鼓励把 confidential manuscript 上传到不受控 API。
- 所有新增实验、分析、数据、引用和承诺都必须由作者确认。

## GitHub 发布状态

本地已初始化 git 仓库。当前环境没有 `gh` CLI，尚不能直接把仓库关联到 GitHub Project。需要后续提供 GitHub 远端仓库地址或安装并登录 `gh` 后再执行 push / project item 关联。
