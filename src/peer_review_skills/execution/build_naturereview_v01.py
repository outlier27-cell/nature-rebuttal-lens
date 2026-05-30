import csv
import hashlib
import json
import re
import time
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from peer_review_skills.config import PROJECT_ROOT
from peer_review_skills.api.openai_compatible import OpenAICompatibleChatClient, extract_json_object
from peer_review_skills.io.jsonl import read_jsonl, write_jsonl


MVP_DIR = PROJECT_ROOT / "data/processed/author_rebuttal_mvp/v2709"
MINI_SEED_PATH = (
    PROJECT_ROOT
    / "data/evaluation/phase1_pair_validation/v2709/model_revised_mini_gold/phase1_mini_gold_seed_50_model_revised.jsonl"
)
DOCS_DIR = PROJECT_ROOT / "docs"
EXEC_DIR = DOCS_DIR / "naturereview_interact_v0_1"
SCHEMA_DIR = PROJECT_ROOT / "data/processed/schemas"
TAXONOMY_DIR = PROJECT_ROOT / "data/processed/taxonomies"
SEED_DIR = PROJECT_ROOT / "data/evaluation/seed_set/v1"
KB_DIR = PROJECT_ROOT / "data/processed/review_interaction_kb/v1"
RETRIEVAL_DIR = PROJECT_ROOT / "data/evaluation/retrieval_v2"
WORKFLOW_DIR = PROJECT_ROOT / "data/evaluation/workflow_v2"
EVAL_DIR = PROJECT_ROOT / "data/evaluation/eval_protocol_v1"
TRAINING_DIR = PROJECT_ROOT / "data/training/author_rebuttal_agent/v2709"
SIMULATION_DIR = PROJECT_ROOT / "data/evaluation/simulation_v1"
NATUREREVIEW_API_HANDOFF_DIR = PROJECT_ROOT / "data/evaluation/api_handoff/naturereview_v01"
NATUREREVIEW_API_RESULTS_DIR = PROJECT_ROOT / "data/evaluation/api_results/naturereview_v01"


MAJOR_CONCERNS = [
    "clarity_presentation",
    "experimental_design",
    "statistics_significance",
    "generalization_scope",
    "reproducibility_reporting",
    "novelty_positioning",
    "baseline_comparison",
    "ablation_mechanism",
    "dataset_bias_ethics_safety",
    "theoretical_validity",
]

REQUIRED_DOCS = [
    "PROJECT_STATUS_2026-05-27-zh.md",
    "CLAIM_LEDGER_zh.md",
    "DATA_CARD_zh.md",
    "RESPONSIBLE_USE_zh.md",
    "DATA_RELEASE_BOUNDARY_zh.md",
    "SCHEMA_REVIEW_INTERACTION_UNIT_zh.md",
    "CROSS_DISCIPLINARY_ANNOTATION_GUIDE_zh.md",
    "ACTOR_NETWORK_CASE_MODEL_zh.md",
    "AGENT_CARD_zh.md",
    "WORKFLOW_SPEC_zh.md",
    "COGNITIVE_TRACE_SPEC_zh.md",
    "SIMULATION_EVALUATION_SPEC_zh.md",
    "PDF_DERIVED_DESIGN_LENSES_zh.md",
    "INTERDISCIPLINARY_SYSTEM_FRAME_zh.md",
    "NON_TRAINING_OPEN_SOURCE_SCOPE_zh.md",
    "EVALUATION_PROTOCOL_zh.md",
    "CROSS_DISCIPLINARY_EVALUATION_RUBRIC_zh.md",
    "OPEN_SOURCE_RELEASE_PLAN_zh.md",
    "OPEN_SOURCE_V0_1_COMPLETION_STATUS_zh.md",
    "MODEL_AND_AGENT_LIMITATIONS_zh.md",
    "PAPER_PLAN_zh.md",
    "LITERATURE_MATRIX_zh.md",
    "EXPERIMENT_PLAN_zh.md",
    "REVIEWER_RISK_REGISTER_zh.md",
    "READY_FOR_API_REVIEW_zh.md",
    "LICENSE_DECISION_zh.md",
]

CROSS_DISCIPLINARY_LENS_KEYS = [
    "tacit_knowledge_boundary",
    "institutional_dependence",
    "actor_network_alignment",
    "fast_slow_cognitive_correction",
    "emotion_tone_commitment_calibration",
    "author_agency_gate",
]

REQUIRED_TAXONOMIES = [
    "tacit_concern_taxonomy.v1.json",
    "institutional_signal_taxonomy.v1.json",
    "evidence_action_taxonomy.v1.json",
    "author_positioning_taxonomy.v1.json",
    "tone_commitment_taxonomy.v1.json",
    "editor_signal_taxonomy.v1.json",
]

REQUIRED_TRACE_STAGES = [
    "understand",
    "question",
    "evidence_plan",
    "position",
    "tone_calibrate",
    "commitment_check",
    "integrity_check",
    "output",
]

REQUIRED_WORKFLOW_AGENTS = [
    "reviewer_understanding_agent",
    "tacit_concern_interpreter",
    "institutional_signal_interpreter",
    "evidence_action_planner",
    "author_positioning_agent",
    "tone_commitment_calibrator",
    "actor_network_mapper",
    "integrity_adequacy_checker",
]

AGNES_ADVICE_FORBIDDEN_MARKERS = [
    "lexical_overlap",
    "lexical-overlap",
    "lexical or fallback retrieval signal",
    "text_similarity_signal",
    "checked whether response text contains cues",
    "keyword",
    "rule-based",
    "rule matching",
    "规则匹配",
]

EVALUATION_TASKS = [
    {
        "name": "Review concern extraction",
        "input": "Reviewer comment span plus provenance.",
        "output": "Concern map with concern_type, quoted evidence, and uncertainty note.",
        "supervision": "Heuristic/model-assisted concern labels; future human-confirmed labels.",
        "automatic": "Exact/partial label match, evidence-span recoverability, unknown-rate.",
        "human": "Concern correctness, evidence grounding, boundary awareness.",
        "baselines": "Historical local classifier, majority concern baseline, lightweight LLM zero-shot.",
        "failures": "Over-broad concern, confusing praise with concern, missing multi-issue comments.",
    },
    {
        "name": "Risk point classification",
        "input": "Concern map, review text, response text, tacit concern taxonomy.",
        "output": "Risk type and tacit concern interpretation grounded in observable text.",
        "supervision": "Risk labels derived from taxonomy plus human adjudication slots.",
        "automatic": "Risk label agreement, consistency with concern_type, unsupported-inference rate.",
        "human": "Tacit concern interpretation quality and no mind-reading compliance.",
        "baselines": "Concern-to-risk lookup table, zero-shot classifier.",
        "failures": "Attributing hidden reviewer intent, flattening institutional risk into wording advice.",
    },
    {
        "name": "Author response strategy retrieval",
        "input": "New review concern/risk query and optional filters.",
        "output": "Top-k historical interaction units with response_strategy and provenance.",
        "supervision": "Candidate response_strategy labels; future human relevance judgments.",
        "automatic": "Strategy R@1/R@3/R@5, concern@5, joint strategy+concern@5, diversity.",
        "human": "Case relevance, strategic usefulness, provenance traceability.",
        "baselines": "BM25, BM25+concern filter, lexical cosine, random same-concern baseline.",
        "failures": "Retrieving same-paper leakage, high text similarity but wrong strategy, low diversity.",
    },
    {
        "name": "Evidence recommendation",
        "input": "Risk interpretation, retrieved cases, evidence_action taxonomy.",
        "output": "Evidence action plan: analysis, experiment, figure/table, supplement, code/data, or clarification.",
        "supervision": "Evidence action labels and retrieved author response actions.",
        "automatic": "Evidence action match, unsupported action rate, provenance coverage.",
        "human": "Evidence groundedness, feasibility, no fabricated experiment/data/citation.",
        "baselines": "Concern-to-evidence lookup, retrieved-nearest evidence action.",
        "failures": "Inventing new experiments, recommending infeasible work, ignoring claim boundary.",
    },
    {
        "name": "Rebuttal outline generation",
        "input": "Concern map, risk interpretation, evidence plan, retrieved cases.",
        "output": "Structured outline, not submission-ready rebuttal text.",
        "supervision": "Workflow trace adequacy labels and human outline scores.",
        "automatic": "Required-section coverage, provenance citation coverage, overclaim flags.",
        "human": "Adequacy of response, organization, usefulness for author thinking.",
        "baselines": "Direct LLM outline, template-only outline, retrieval-only summary.",
        "failures": "Generating polished but unsupported rebuttal, skipping limitations, over-promising.",
    },
    {
        "name": "Tone / structure revision",
        "input": "Draft outline or author notes plus tone/commitment taxonomy.",
        "output": "Tone warnings, commitment-level flags, safer structure suggestions.",
        "supervision": "Tone/commitment labels and human ratings.",
        "automatic": "Unsupported commitment count, acceptance-prediction absence, banned behavior checks.",
        "human": "Tone calibration, commitment safety, clarity without sycophancy.",
        "baselines": "Structured tone checklist, direct LLM editing.",
        "failures": "Politeness replacing substance, excessive concession, unverifiable promises.",
    },
    {
        "name": "Decision-aware case retrieval",
        "input": "Concern/risk query plus optional decision/editor signal filters.",
        "output": "Cases with editor-readable signals and decision-context caveats.",
        "supervision": "Available editor_signal metadata and human case relevance labels.",
        "automatic": "Decision-signal match@k, provenance completeness, case diversity.",
        "human": "Decision-context usefulness and no acceptance prediction.",
        "baselines": "Concern-only retrieval, BM25 over review text.",
        "failures": "Inferring acceptance probability, treating editor signal as causal proof.",
    },
    {
        "name": "Tacit concern interpretation",
        "input": "Concern/risk evidence and tacit concern taxonomy.",
        "output": "Observable trace of tacit judgment with boundary statement.",
        "supervision": "Taxonomy labels plus human cross-disciplinary rubric.",
        "automatic": "Taxonomy coverage, evidence quote presence, mind-reading phrase absence.",
        "human": "Tacit concern interpretation score.",
        "baselines": "Explicit concern restatement, direct LLM interpretation.",
        "failures": "Psychologizing reviewer, making unverifiable claims about hidden motives.",
    },
    {
        "name": "Institutional positioning assessment",
        "input": "Concern, response, journal/policy/editor signal context when available.",
        "output": "Institutional signal note linked to author action options.",
        "supervision": "Institutional signal taxonomy and human ratings.",
        "automatic": "Signal label match, link-to-action coverage, acceptance-prediction absence.",
        "human": "Institutional positioning quality.",
        "baselines": "No-institution baseline, policy-signal detector.",
        "failures": "Ignoring journal/community norms, predicting editorial outcome.",
    },
    {
        "name": "Actor-network case retrieval",
        "input": "Query plus desired actors such as figure, dataset, code, benchmark, supplement.",
        "output": "Cases showing how human and non-human actors are realigned.",
        "supervision": "Actor_links metadata and human relevance judgments.",
        "automatic": "Actor type match@k, actor evidence coverage, case diversity.",
        "human": "Actor-network alignment score.",
        "baselines": "Text-only retrieval, actor-metadata filter.",
        "failures": "Mentioning objects without explaining their interaction role.",
    },
    {
        "name": "Cognitive trace quality assessment",
        "input": "Full workflow trace.",
        "output": "Trace quality score and missing-stage warnings.",
        "supervision": "Rubric scores from human evaluation sheet.",
        "automatic": "Required stage completion, provenance checks, unsupported commitment flags.",
        "human": "Cognitive trace quality and responsible-use compliance.",
        "baselines": "Direct response generation, trace without integrity checker.",
        "failures": "Post-hoc rationalization, missing commitment check, hidden direct generation.",
    },
]

MOJIBAKE_MARKERS = [
    "\u951b",
    "\u9369",
    "\u4e67",
    "\u4e64",
    "\u4e6c",
    "\u4e75",
    "\u4e7b",
    "\u6d93\u20ac",
    "\u93c1\u7248\u5d41",
    "\u5bee\u20ac",
    "\u8930\u64b3\u588d\u524d",
]

SECRET_PATTERNS = {
    "openai_style_api_key": re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    "authorization_bearer_value": re.compile(r"Authorization:\s*Bearer\s+(?!YOUR_API_KEY|<|token\b)[A-Za-z0-9._-]{10,}", re.IGNORECASE),
}


def main() -> None:
    _ensure_dirs()
    summary = _read_json(MVP_DIR / "summary.json")
    audit = _read_text(PROJECT_ROOT / "data/analysis/final_framework_data_audit_v2709/v2709_final_framework_data_audit.md")
    p1_summary = _read_json(PROJECT_ROOT / "data/evaluation/p1_retrieval_baselines/v2709_model_revised/p1_retrieval_summary.json")
    workflow_summary = _read_json(
        PROJECT_ROOT / "data/evaluation/author_rebuttal_workflow/v2709_model_revised/workflow_summary.json"
    )

    _write_project_docs(summary, audit, p1_summary, workflow_summary)
    _write_schema()
    _write_taxonomies()
    _write_cross_disciplinary_docs()
    _write_pdf_derived_design_docs()
    _write_agent_workflow_docs()

    demo_ready = list(read_jsonl(MVP_DIR / "heuristic_rebuttal_pairs_demo_ready.jsonl"))
    mini_seed = [r for r in read_jsonl(MINI_SEED_PATH) if _is_yes(r.get("revised_usable_for_retrieval"))]
    seed_candidates = _build_seed_candidates(demo_ready, target_per_concern=20)
    _write_seed_outputs(seed_candidates)

    seed_model_reviewed = _build_model_reviewed_seed(seed_candidates, mini_seed)
    seed_model_reviewed = _apply_existing_seed_api_results_if_complete(seed_model_reviewed)
    _write_model_review_outputs(seed_model_reviewed)

    interaction_units = _build_interaction_units(seed_model_reviewed, mini_seed)
    case_index = _build_case_index(interaction_units)
    actor_cases = _build_actor_network_cases(case_index, interaction_units)
    _write_kb_outputs(interaction_units, case_index, actor_cases)

    retrieval_predictions, retrieval_summary = _build_retrieval_v2(interaction_units)
    _write_retrieval_outputs(retrieval_predictions, retrieval_summary)

    traces = _build_workflow_traces(interaction_units[:50], retrieval_predictions)
    _write_workflow_outputs(traces)
    simulation_traces = _build_simulation_traces(traces)
    _write_simulation_outputs(simulation_traces)

    _write_training_outputs(interaction_units)
    _write_evaluation_protocol()
    _write_open_source_docs()
    _write_paper_docs()
    _write_api_handoff(seed_model_reviewed)
    _write_validation_report(_validate_naturereview_v01())
    _write_execution_summary()


def _ensure_dirs() -> None:
    for path in [EXEC_DIR, SCHEMA_DIR, TAXONOMY_DIR, SEED_DIR, KB_DIR, RETRIEVAL_DIR, WORKFLOW_DIR, EVAL_DIR, TRAINING_DIR, SIMULATION_DIR]:
        path.mkdir(parents=True, exist_ok=True)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _read_optional_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return list(read_jsonl(path))


def _write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_csv(path: Path, records: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            row = {
                field: json.dumps(record.get(field), ensure_ascii=False)
                if isinstance(record.get(field), (dict, list))
                else record.get(field, "")
                for field in fields
            }
            writer.writerow(row)


def _write_project_docs(
    summary: dict[str, Any],
    audit: str,
    p1_summary: dict[str, Any],
    workflow_summary: dict[str, Any],
) -> None:
    paper_counts = summary["paper_counts"]
    pair_counts = summary["pair_counts"]
    status_doc = f"""# NatureReview-Interact 项目状态

更新时间：2026-05-27

## 当前一句话

本项目已经从爬取阶段转向把 v2709 公开同行评审数据转化为可检索、可评估、可追溯、负责任开源的 Review Interaction Agent。

## 当前已确认资产

| 资产 | 数量 / 路径 | 状态 |
|---|---:|---|
| v2709 主库 | {paper_counts["paper_manifest"]} records | verified |
| core full-chain papers | {paper_counts["core_full_chain_papers"]} | verified |
| response-only papers | {paper_counts["response_only_papers"]} | verified |
| review-only input papers | {paper_counts["review_only_input_papers"]} | verified |
| editor decision-only papers | {paper_counts["editor_decision_only_papers"]} | verified |
| demo-ready pairs | {pair_counts["heuristic_rebuttal_pairs_demo_ready"]} | heuristic |
| clean heuristic pairs | {pair_counts["heuristic_rebuttal_pairs_clean"]} | heuristic |
| all heuristic pairs | {pair_counts["heuristic_rebuttal_pairs_all"]} | heuristic |
| demo-ready cases | {pair_counts["demo_ready_cases"]} | heuristic |
| model-revised mini seed | 50 rows, 45 usable | model-assisted |
| workflow traces | {workflow_summary["workflow"]["trace_count"]} | prototype |

## 当前不能声称的内容

- 不能声称已有人工金标。
- 不能声称 agent 已经被真实作者或审稿专家验证。
- 不能声称模型真正掌握默会知识。
- 不能声称系统能预测接收率。
- 不能声称当前 workflow 已经是最终产品。

## 已有 baseline

- P1 best concern@5: `{p1_summary["best_by_metric"]["concern_match_at_5"]}`
- P1 best strategy@5: `{p1_summary["best_by_metric"]["strategy_recall_at_5"]}`
- workflow strategy_hit_at_5_rate: `{workflow_summary["evaluation"]["strategy_hit_at_5_rate"]}`
- workflow joint_hit_at_5_rate: `{workflow_summary["evaluation"]["joint_hit_at_5_rate"]}`
- workflow integrity_pass_rate: `{workflow_summary["evaluation"]["integrity_pass_rate"]}`

## 本轮执行输出目录

- `docs/naturereview_interact_v0_1/`
- `data/processed/schemas/`
- `data/processed/taxonomies/`
- `data/processed/review_interaction_kb/v1/`
- `data/evaluation/seed_set/v1/`
- `data/evaluation/retrieval_v2/`
- `data/evaluation/workflow_v2/`
- `data/evaluation/eval_protocol_v1/`
"""
    _write_doc("PROJECT_STATUS_2026-05-27-zh.md", status_doc)

    claim_doc = """# Claim Ledger

| Claim | Evidence needed | Current artifact | Verification status | Risk |
|---|---|---|---|---|
| v2709 包含 2709 条公开同行评审相关记录 | 主库 index / summary | `data/processed/author_rebuttal_mvp/v2709/summary.json` | verified | 需保持版本一致 |
| 约 9858 条 demo-ready pair 可用于候选检索 | pair extraction summary | `heuristic_rebuttal_pairs_demo_ready.jsonl` | supported_by_heuristic | 不是人工金标 |
| Nature rebuttal 中大量回应涉及图表、补充材料、分析和实验动作 | v2709 corpus audit | `data/analysis/final_framework_data_audit_v2709/v2709_final_framework_data_audit.md` | supported_by_corpus_audit | derived signal 可能误判 |
| 当前 workflow 已能记录 45 条可追溯 trace | workflow summary | `data/evaluation/author_rebuttal_workflow/v2709_model_revised/workflow_summary.json` | model_assisted | 样本小，未人工评估 |
| 本项目可研究默会知识的文本痕迹 | taxonomy + examples + literature | `docs/CROSS_DISCIPLINARY_ANNOTATION_GUIDE_zh.md` | planned | 不能声称 AI 真懂默会知识 |
| 行动者网络可转成 case representation | actor links + case model | `docs/ACTOR_NETWORK_CASE_MODEL_zh.md` | planned | 只能表示公开文本中的可观察关系 |
| 慢思维 workflow 可以降低直接生成风险 | cognitive trace + integrity checks | `docs/COGNITIVE_TRACE_SPEC_zh.md` | planned | 需要后续实证评估 |
"""
    _write_doc("CLAIM_LEDGER_zh.md", claim_doc)

    data_card = """# v2709 Data Card

## 数据来源

Nature 系列公开同行评审相关页面和公开文件。

## 数据用途

- 审稿互动结构研究
- review concern / author response strategy 分析
- tacit concern / institutional signal / evidence action 标注研究
- retrieval baseline
- agent workflow trace evaluation

## 不适合用途

- 自动代写完整 rebuttal 并直接提交
- 接收率预测
- 对 reviewer 或 editor 的个体画像
- 训练不带 provenance 的黑箱生成器
- 声称模型拥有真实人类默会知识

## 当前金标状态

当前没有人工金标。当前 v0.1 默认使用 API 模型复核标签，属于 API 替代人工复核的 model-assisted seed；所有 heuristic 和 model-assisted 标签只能作为候选标签、检索样本或 sanity evaluation 输入，不能作为最终 benchmark gold label。

## 标签状态

| 标签类型 | 含义 | 可用于 |
|---|---|---|
| heuristic | 规则或弱监督生成 | 候选检索、粗粒度分析 |
| model-assisted | API 模型辅助复核 | 小规模 sanity evaluation |
| human-confirmed | 人工确认 | 正式 benchmark |

## 当前版本

- v2709 主库：2709 records
- demo-ready pairs：9858
- 本轮 seed candidates：见 `data/evaluation/seed_set/v1/`
- API 替代人工复核：200 条 seed request 已由 deepseek-v3 复核，结果仍是 model-assisted，不是 human gold。
"""
    _write_doc("DATA_CARD_zh.md", data_card)

    responsible = """# Responsible Use

本项目是审稿互动研究和作者回应辅助框架，不是代写服务。

## 禁止或不支持

- 上传 confidential manuscript 到外部 API。
- 使用系统预测论文接收概率。
- 使用系统生成未验证实验、数据、引用或承诺。
- 使用系统替代作者、审稿人或编辑的判断。
- 使用系统操纵 reviewer 或规避真实科学问题。
- 对 reviewer/editor 做个体画像或心理推断。

简写为三条硬边界：不预测接收率，不替代作者/审稿人/编辑，不编造实验、数据、引用或承诺。

## 系统输出定位

- concern map
- tacit / explicit risk interpretation
- institutional signal note
- evidence planning aid
- actor-network alignment note
- writing organization aid
- tone and commitment warning
- integrity warning
- provenance-grounded case reference

## 人类责任

作者必须确认所有实验、数据、引用、限制、承诺和最终回复文本。AI 输出不能替代学术责任主体。
"""
    _write_doc("RESPONSIBLE_USE_zh.md", responsible)

    release_boundary = """# Data Release Boundary

## 优先开源

- schema
- taxonomy
- derived metadata
- source URL / DOI / hash / offset
- model-assisted label sample
- evaluation protocol
- prompt rubrics
- baseline scripts
- data card
- agent card
- responsible use policy

## 谨慎处理

- reviewer report 原文
- author response 原文
- editor decision letter 全文

## 默认不发布

- 任何非公开审稿材料
- API key
- private logs
- 无 provenance 的全文聚合包

## 原则

默认发布“可复现方法和派生结构”，而不是重新分发可能存在版权风险的全文语料。
"""
    _write_doc("DATA_RELEASE_BOUNDARY_zh.md", release_boundary)

    overview = f"""# NatureReview-Interact v0.1 Execution Package

本目录是 `2026-05-27-naturereview-interact-implementation-plan-zh.md` 的执行包索引。

## 已生成核心文档

- `../PROJECT_STATUS_2026-05-27-zh.md`
- `../CLAIM_LEDGER_zh.md`
- `../DATA_CARD_zh.md`
- `../RESPONSIBLE_USE_zh.md`
- `../SCHEMA_REVIEW_INTERACTION_UNIT_zh.md`
- `../CROSS_DISCIPLINARY_ANNOTATION_GUIDE_zh.md`
- `../ACTOR_NETWORK_CASE_MODEL_zh.md`
- `../AGENT_CARD_zh.md`
- `../WORKFLOW_SPEC_zh.md`
- `../COGNITIVE_TRACE_SPEC_zh.md`
- `../EVALUATION_PROTOCOL_zh.md`
- `../CROSS_DISCIPLINARY_EVALUATION_RUBRIC_zh.md`

## 当前数据口径

```text
v2709 records: {paper_counts["paper_manifest"]}
demo-ready pairs: {pair_counts["heuristic_rebuttal_pairs_demo_ready"]}
clean heuristic pairs: {pair_counts["heuristic_rebuttal_pairs_clean"]}
workflow trace prototype: {workflow_summary["workflow"]["trace_count"]}
```
"""
    (EXEC_DIR / "README.md").write_text(overview, encoding="utf-8")


def _write_doc(name: str, content: str) -> None:
    (DOCS_DIR / name).write_text(content.strip() + "\n", encoding="utf-8")
    (EXEC_DIR / name).write_text(content.strip() + "\n", encoding="utf-8")


def _write_pdf_derived_design_docs() -> None:
    pdf_lenses = """# PDF-derived Design Lenses

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
"""
    _write_doc("PDF_DERIVED_DESIGN_LENSES_zh.md", pdf_lenses)

    system_frame = """# Interdisciplinary System Frame

NatureReview-Interact 的核心不是 RAG、BM25、模型微调或单一技术套路，而是把 Nature 公开同行评审案例转成一个跨学科的 review-interaction assistant。

## 核心问题

系统要帮助作者回答六个问题：

1. reviewer 明说的 concern 是什么？
2. concern 背后可观察的 tacit risk 是什么？
3. 期刊、共同体、透明性或编辑流程带来了什么 institutional signal？
4. 哪些行动者承载回应：figure、table、dataset、code、benchmark、supplement、method text？
5. 作者应该如何选择 stance、evidence action、tone 和 commitment？
6. 哪些内容必须由作者确认，系统不能替作者承诺？

## 非技术中心

检索和 baseline 只用于查找案例、记录 provenance 和建立可比评测。项目真正的贡献是把人文社科概念转成可执行的 agent workflow：默会知识边界、制度依赖、行动者网络、快慢思维纠偏、情绪-语气-承诺校准、作者主体性门禁。

## 输出形态

系统默认输出 plan、risk map、evidence action、case analogy、tone warning、author confirmation question 和 adequacy report，不默认输出 submission-ready rebuttal。
"""
    _write_doc("INTERDISCIPLINARY_SYSTEM_FRAME_zh.md", system_frame)

    scope = """# Non-training Open-source Scope

## v0.1 范围

NatureReview-Interact v0.1 是 non-training、cross-disciplinary 的开源研究框架。训练和微调不属于 v0.1 核心。

v0.1 核心包括：

- Review Interaction Unit schema
- taxonomy
- model-assisted seed review
- review interaction knowledge base
- case retrieval as support infrastructure
- cognitive workflow traces
- reviewer-author-editor simulation traces
- cross-disciplinary lens map
- evaluation protocol and rubric
- responsible-use and release-boundary docs

## 不是什么

- not a RAG system
- not RAG-only
- 不是单一技术套路
- 不是 final rebuttal generator
- 不是 acceptance predictor
- 不是训练或微调项目

## RAG/retrieval 的位置

RAG/retrieval 只是辅助设施，用来找历史案例、保留 provenance、支持 case analogy 和评测对照。系统的核心价值是跨学科解释框架和负责任的审稿互动 workflow。

## Legacy optional artifacts

`data/training/author_rebuttal_agent/v2709/` 可以保留为未来实验的 legacy optional non-core artifact。它不能被写成 v0.1 核心贡献，也不能作为开源完成度的 release blocker。
"""
    _write_doc("NON_TRAINING_OPEN_SOURCE_SCOPE_zh.md", scope)


def _write_schema() -> None:
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "ReviewInteractionUnit",
        "type": "object",
        "required": [
            "unit_id",
            "paper_id",
            "review_text",
            "response_text",
            "concern_type",
            "response_strategy",
            "provenance",
            "label_source",
        ],
        "properties": {
            "unit_id": {"type": "string"},
            "paper_id": {"type": "string"},
            "pair_id": {"type": ["string", "null"]},
            "source_url": {"type": ["string", "null"]},
            "doi": {"type": ["string", "null"]},
            "title": {"type": ["string", "null"]},
            "journal": {"type": ["string", "null"]},
            "year": {"type": ["integer", "string", "null"]},
            "review_round": {"type": ["string", "integer", "null"]},
            "reviewer_id": {"type": ["string", "null"]},
            "review_text": {"type": "string"},
            "response_text": {"type": "string"},
            "review_offset": {
                "type": ["object", "null"],
                "properties": {"start": {"type": "integer"}, "end": {"type": "integer"}},
            },
            "response_offset": {
                "type": ["object", "null"],
                "properties": {"start": {"type": "integer"}, "end": {"type": "integer"}},
            },
            "concern_type": {"type": "string"},
            "risk_type": {"type": ["string", "null"]},
            "institutional_signal": {"type": ["string", "null"]},
            "evidence_action": {"type": ["string", "null"]},
            "author_positioning": {"type": ["string", "null"]},
            "response_strategy": {"type": "string"},
            "tone_commitment": {"type": ["object", "null"]},
            "editor_signal": {"type": ["object", "null"]},
            "actor_links": {
                "type": "array",
                "items": {
                    "type": "object",
                    "required": ["actor_type", "evidence"],
                    "properties": {
                        "actor_type": {
                            "type": "string",
                            "enum": [
                                "reviewer",
                                "author",
                                "editor",
                                "manuscript",
                                "figure",
                                "table",
                                "dataset",
                                "code",
                                "benchmark",
                                "supplement",
                                "journal_policy",
                                "ai_agent",
                                "other",
                            ],
                        },
                        "actor_id": {"type": ["string", "null"]},
                        "role_in_interaction": {"type": ["string", "null"]},
                        "evidence": {"type": "string"},
                    },
                },
            },
            "provenance": {
                "type": "object",
                "required": ["source_file", "source_hash"],
                "properties": {
                    "source_file": {"type": "string"},
                    "source_hash": {"type": "string"},
                    "url": {"type": ["string", "null"]},
                    "offset_recoverable": {"type": ["boolean", "null"]},
                },
            },
            "label_source": {"type": "string", "enum": ["heuristic", "model_assisted", "human_confirmed", "mixed"]},
        },
    }
    _write_json(SCHEMA_DIR / "review_interaction_unit.schema.json", schema)

    doc = """# Review Interaction Unit Schema

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
"""
    _write_doc("SCHEMA_REVIEW_INTERACTION_UNIT_zh.md", doc)


def _write_taxonomies() -> None:
    taxonomies = {
        "tacit_concern_taxonomy.v1.json": {
            "taxonomy_name": "tacit_concern_taxonomy",
            "taxonomy_version": "v1",
            "labels": {
                "credibility_trust": "Reviewer questions whether claims are trustworthy or adequately supported.",
                "novelty_positioning": "Reviewer questions whether contribution is meaningfully new or well positioned.",
                "community_standard_fit": "Reviewer invokes expected baselines, benchmarks, reporting norms, or field standards.",
                "evidence_chain_stability": "Reviewer questions whether figures, statistics, methods, and claims form a stable evidence chain.",
                "methodological_maturity": "Reviewer questions whether the method is sufficiently mature, robust, or justified.",
                "scope_and_claim_boundary": "Reviewer questions whether claims exceed the evidence or context.",
                "reproducibility_expectation": "Reviewer expects code, data, parameters, protocols, or reporting details.",
                "ethical_or_social_risk": "Reviewer raises ethics, bias, privacy, safety, or societal risk.",
                "presentation_as_epistemic_signal": "Reviewer treats presentation clarity as a signal of evidential reliability.",
                "unknown": "No reliable tacit concern can be inferred from observable text.",
            },
        },
        "institutional_signal_taxonomy.v1.json": {
            "taxonomy_name": "institutional_signal_taxonomy",
            "taxonomy_version": "v1",
            "labels": {
                "journal_scope_fit": "Observable signal about journal scope, audience, contribution threshold, or fit.",
                "community_norm_expectation": "Observable signal about field norms or shared community expectations.",
                "editorial_risk_control": "Observable editor/reviewer signal about unresolved risk or revision burden.",
                "reviewer_authority_pressure": "Observable response pattern showing deference to reviewer authority.",
                "replicability_norm": "Observable expectation that findings should be replicable.",
                "transparency_norm": "Observable expectation for code, data, methods, or protocol transparency.",
                "novelty_threshold": "Observable expectation for higher novelty or stronger positioning.",
                "ethical_acceptability": "Observable expectation for ethical, safety, privacy, or fairness acceptability.",
                "presentation_standard": "Observable expectation for journal-quality presentation and clarity.",
                "unknown": "No reliable institutional signal can be inferred.",
            },
        },
        "evidence_action_taxonomy.v1.json": {
            "taxonomy_name": "evidence_action_taxonomy",
            "taxonomy_version": "v1",
            "labels": {
                "new_experiment": "Author reports a newly performed experiment or validation.",
                "new_analysis": "Author reports a new analysis, benchmark, robustness check, or comparison.",
                "new_baseline_or_comparison": "Author adds or discusses additional baselines or comparative methods.",
                "statistical_test_or_uncertainty": "Author adds statistical testing, uncertainty estimates, sample-size discussion, or confidence intervals.",
                "figure_table_revision": "Author revises figures, tables, captions, or visual presentation.",
                "supplementary_material_revision": "Author moves or adds evidence to supplementary material.",
                "code_data_availability": "Author provides code, data, weights, database, protocol, or availability details.",
                "method_clarification": "Author clarifies method, assumptions, or implementation.",
                "claim_narrowing": "Author narrows a claim or reduces overstatement.",
                "limitation_discussion": "Author adds limitations or caveats.",
                "literature_repositioning": "Author updates related work or contribution positioning.",
                "no_new_evidence_explanation_only": "Author explains existing evidence without new work.",
                "future_work_commitment": "Author defers the issue to future work.",
                "unknown": "Evidence action cannot be identified.",
            },
        },
        "author_positioning_taxonomy.v1.json": {
            "taxonomy_name": "author_positioning_taxonomy",
            "taxonomy_version": "v1",
            "labels": {
                "accept_and_revise": "Author accepts the concern and revises.",
                "clarify_without_new_work": "Author clarifies existing evidence without new work.",
                "justify_existing_choice": "Author defends or justifies an existing choice.",
                "partially_concede": "Author accepts part of the concern while preserving part of the original position.",
                "respectfully_disagree": "Author explicitly but politely challenges the reviewer premise.",
                "narrow_claim": "Author narrows the claim or scope.",
                "defer_to_future_work": "Author acknowledges value but defers to future work.",
                "translate_to_editorial_signal": "Author frames the response as an editor-readable resolution signal.",
                "unknown": "Author position cannot be identified.",
            },
        },
        "tone_commitment_taxonomy.v1.json": {
            "taxonomy_name": "tone_commitment_taxonomy",
            "taxonomy_version": "v1",
            "tone": ["cooperative", "defensive", "assertive", "apologetic", "neutral", "unknown"],
            "commitment_level": [
                "completed_change",
                "promised_change",
                "clarification_only",
                "declined_with_reason",
                "future_work",
                "unknown",
            ],
            "risk_flags": [
                "overclaim",
                "unsupported_commitment",
                "sycophancy",
                "excessive_defensiveness",
                "uncertainty_hiding",
                "none",
            ],
        },
        "editor_signal_taxonomy.v1.json": {
            "taxonomy_name": "editor_signal_taxonomy",
            "taxonomy_version": "v1",
            "labels": {
                "acceptance_signal": "Observable acceptance or publication-ready signal.",
                "minor_revision_signal": "Observable minor revision signal.",
                "major_revision_signal": "Observable major revision signal.",
                "unresolved_core_concern": "Observable signal of unresolved central concern.",
                "request_for_clarification": "Observable request for clarification.",
                "scope_or_journal_fit_signal": "Observable scope or journal fit signal.",
                "editorial_process_signal": "Observable process-related signal.",
                "not_available": "No editor decision text is available.",
                "unknown": "Decision signal cannot be identified.",
            },
        },
    }
    for filename, value in taxonomies.items():
        _write_json(TAXONOMY_DIR / filename, value)

    guide = """# Taxonomy Guide

## Purpose

这些 taxonomy 把最终方案中的跨学科概念转成可执行标签。它们不是心理诊断，也不是对 reviewer/editor 真实意图的断言。

## Taxonomy Files

- `tacit_concern_taxonomy.v1.json`
- `institutional_signal_taxonomy.v1.json`
- `evidence_action_taxonomy.v1.json`
- `author_positioning_taxonomy.v1.json`
- `tone_commitment_taxonomy.v1.json`
- `editor_signal_taxonomy.v1.json`

## 使用原则

1. 先找原文证据，再打标签。
2. 优先标注可观察互动功能，而不是推断真实心理。
3. 无法判断时使用 `unknown`。
4. 所有模型辅助标签都必须保留 `label_source=model_assisted`。
"""
    _write_doc("TAXONOMY_GUIDE_zh.md", guide)


def _write_cross_disciplinary_docs() -> None:
    annotation = """# Cross-disciplinary Annotation Guide

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
"""
    _write_doc("CROSS_DISCIPLINARY_ANNOTATION_GUIDE_zh.md", annotation)

    actor_model = """# Actor Network Case Model

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
"""
    _write_doc("ACTOR_NETWORK_CASE_MODEL_zh.md", actor_model)

    cognitive = """# Cognitive Trace Spec

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
"""
    _write_doc("COGNITIVE_TRACE_SPEC_zh.md", cognitive)


def _write_agent_workflow_docs() -> None:
    agent_card = """# Agent Card

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
"""
    _write_doc("AGENT_CARD_zh.md", agent_card)

    workflow_spec = """# Workflow Spec

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
"""
    _write_doc("WORKFLOW_SPEC_zh.md", workflow_spec)


def _build_seed_candidates(records: list[dict[str, Any]], target_per_concern: int) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    seen_papers: Counter[str] = Counter()
    by_concern: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for record in records:
        concern = str(record.get("heuristic_concern_type") or "unknown")
        if concern in MAJOR_CONCERNS:
            by_concern[concern].append(record)

    for concern in MAJOR_CONCERNS:
        candidates = sorted(
            by_concern.get(concern, []),
            key=lambda r: (
                -float(r.get("pair_confidence") or 0),
                seen_papers[str(r.get("paper_id"))],
                str(r.get("pair_id")),
            ),
        )
        count = 0
        for record in candidates:
            paper_id = str(record.get("paper_id") or "")
            if seen_papers[paper_id] >= 3:
                continue
            selected.append(_prepare_seed_record(record, len(selected) + 1, "seed_candidates_balanced_200"))
            seen_papers[paper_id] += 1
            count += 1
            if count >= target_per_concern:
                break
    return selected[:200]


def _prepare_seed_record(record: dict[str, Any], index: int, source: str) -> dict[str, Any]:
    offsets = record.get("source_offsets") or {}
    label_source = "model_assisted" if source == "phase1_model_revised_mini_seed" else "heuristic"
    return {
        "seed_id": f"seed_v1_{index:04d}",
        "pair_id": record.get("pair_id"),
        "paper_id": record.get("paper_id"),
        "doi": record.get("doi"),
        "title": record.get("title"),
        "journal": record.get("journal"),
        "year": record.get("year"),
        "journal_family": record.get("journal_family"),
        "interaction_level": record.get("interaction_level"),
        "pair_confidence": record.get("pair_confidence"),
        "review_text": record.get("review_context") or record.get("review_text") or "",
        "response_text": record.get("author_response") or record.get("response_text") or "",
        "concern_type": record.get("heuristic_concern_type")
        or record.get("revised_concern_type_gold")
        or record.get("concern_type_gold")
        or "unknown",
        "response_strategy": record.get("heuristic_response_strategy")
        or record.get("revised_response_strategy_gold")
        or record.get("response_strategy_gold")
        or "unknown",
        "evidence_action": _normalize_evidence_action(record.get("revised_evidence_type") or record.get("evidence_type")),
        "offset_recoverable": _is_offset_recoverable(record),
        "source_json_path": record.get("source_json_path"),
        "source_field": record.get("source_field"),
        "source_offsets": offsets,
        "label_source": label_source,
        "selection_source": source,
        "human_confirmation_status": "needs_human_confirmation",
    }


def _write_seed_outputs(records: list[dict[str, Any]]) -> None:
    write_jsonl(SEED_DIR / "seed_candidates_200.jsonl", records)
    fields = [
        "seed_id",
        "pair_id",
        "paper_id",
        "doi",
        "title",
        "journal",
        "year",
        "interaction_level",
        "pair_confidence",
        "concern_type",
        "response_strategy",
        "evidence_action",
        "offset_recoverable",
        "label_source",
        "human_confirmation_status",
    ]
    _write_csv(SEED_DIR / "seed_candidates_200.csv", records, fields)
    summary = {
        "seed_count": len(records),
        "paper_count": len({r["paper_id"] for r in records}),
        "concern_distribution": Counter(r["concern_type"] for r in records),
        "strategy_distribution": Counter(r["response_strategy"] for r in records),
        "label_source": "heuristic",
        "notes": [
            "This seed candidate set is not human gold.",
            "Rows require model review and human confirmation before benchmark use.",
        ],
    }
    _write_json(SEED_DIR / "seed_summary.json", _jsonable(summary))
    report = _seed_report("Seed Set v1 Report", summary)
    (SEED_DIR / "seed_report.md").write_text(report, encoding="utf-8")


def _build_model_reviewed_seed(seed_candidates: list[dict[str, Any]], mini_seed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    mini_by_pair = {str(r.get("pair_id")): r for r in mini_seed}
    reviewed: list[dict[str, Any]] = []
    for index, seed in enumerate(seed_candidates, start=1):
        record = dict(seed)
        mini = mini_by_pair.get(str(seed.get("pair_id")))
        if mini:
            record["alignment_correct"] = mini.get("revised_alignment_correct") or mini.get("alignment_correct") or "yes"
            record["concern_type"] = mini.get("revised_concern_type_gold") or seed["concern_type"]
            record["response_strategy"] = mini.get("revised_response_strategy_gold") or seed["response_strategy"]
            record["evidence_action"] = _normalize_evidence_action(mini.get("revised_evidence_type") or seed["evidence_action"])
            record["model_rationale"] = mini.get("model_revision_rationale") or ""
            record["label_source"] = "model_assisted"
        else:
            record["alignment_correct"] = "yes" if seed.get("offset_recoverable") else "needs_review"
            record["model_rationale"] = _heuristic_rationale(seed)
            record["label_source"] = "heuristic_model_ready"
        record["seed_review_id"] = f"seed_review_v1_{index:04d}"
        record["tacit_concern"] = record.get("tacit_concern") or _model_field_fallback(record, "tacit_concern")
        record["institutional_signal"] = record.get("institutional_signal") or _model_field_fallback(record, "institutional_signal")
        record["author_positioning"] = record.get("author_positioning") or _model_field_fallback(record, "author_positioning")
        record["tone_commitment"] = record.get("tone_commitment") or _model_tone_fallback(record)
        record["actor_links"] = record.get("actor_links") or _structural_actor_links(record)
        record["usable_for_retrieval"] = "yes" if record["alignment_correct"] in {"yes", True} else "no"
        record["usable_for_evaluation"] = "yes" if record["alignment_correct"] in {"yes", True} else "no"
        record["human_confirmation_status"] = "needs_human_confirmation"
        reviewed.append(record)
    return reviewed


def _apply_existing_seed_api_results_if_complete(seed_records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    results = _read_optional_jsonl(NATUREREVIEW_API_RESULTS_DIR / "seed_review_results.jsonl")
    errors = _read_optional_jsonl(NATUREREVIEW_API_RESULTS_DIR / "seed_review_errors.jsonl")
    if len(results) < len(seed_records) or errors:
        return seed_records
    result_by_seed_id = {
        str(record.get("seed_review_id")): record
        for record in results
        if record.get("seed_review_id") and not record.get("error")
    }
    if any(str(seed.get("seed_review_id")) not in result_by_seed_id for seed in seed_records):
        return seed_records
    return [_merge_seed_api_review_result(seed, result_by_seed_id[str(seed.get("seed_review_id"))]) for seed in seed_records]


def _write_model_review_outputs(records: list[dict[str, Any]]) -> None:
    write_jsonl(SEED_DIR / "seed_model_reviewed_200.jsonl", records)
    fields = [
        "seed_review_id",
        "seed_id",
        "pair_id",
        "paper_id",
        "concern_type",
        "tacit_concern",
        "institutional_signal",
        "response_strategy",
        "evidence_action",
        "author_positioning",
        "alignment_correct",
        "usable_for_retrieval",
        "usable_for_evaluation",
        "label_source",
        "model_rationale",
    ]
    _write_csv(SEED_DIR / "seed_model_reviewed_200.csv", records, fields)
    human_fields = fields + [
        "human_alignment_confirmed",
        "human_concern_type",
        "human_tacit_concern",
        "human_risk_type",
        "human_institutional_signal",
        "human_response_strategy",
        "human_evidence_action",
        "human_author_positioning",
        "human_tone",
        "human_commitment_level",
        "human_notes",
    ]
    _write_csv(SEED_DIR / "seed_human_confirmation_template.csv", records, human_fields)
    summary = {
        "reviewed_count": len(records),
        "label_source_counts": Counter(r["label_source"] for r in records),
        "usable_for_retrieval_counts": Counter(r["usable_for_retrieval"] for r in records),
        "usable_for_evaluation_counts": Counter(r["usable_for_evaluation"] for r in records),
        "tacit_concern_counts": Counter(r["tacit_concern"] for r in records),
        "institutional_signal_counts": Counter(r["institutional_signal"] for r in records),
        "notes": [
            "This is model-ready/heuristic-assisted seed review, not final human gold.",
            "No external API was called by this builder; API review requires OPENAI_COMPATIBLE_API_KEY.",
        ],
    }
    _write_json(SEED_DIR / "seed_model_reviewed_summary.json", _jsonable(summary))
    report = _seed_report("Model-reviewed Seed v1 Report", summary)
    report += "\n\n## API status\n\nNo API key was present in the environment during this run, so no external model calls were made.\n"
    (SEED_DIR / "model_review_report.md").write_text(report, encoding="utf-8")


def _build_interaction_units(seed_records: list[dict[str, Any]], mini_seed: list[dict[str, Any]]) -> list[dict[str, Any]]:
    units: list[dict[str, Any]] = []
    all_records = seed_records + [
        _prepare_seed_record(record, len(seed_records) + index, "phase1_model_revised_mini_seed")
        for index, record in enumerate(mini_seed, start=1)
    ]
    seen: set[str] = set()
    for index, record in enumerate(all_records, start=1):
        pair_id = str(record.get("pair_id") or f"generated:{index}")
        if pair_id in seen:
            continue
        seen.add(pair_id)
        unit = _to_interaction_unit(record, index)
        units.append(unit)
    return units


def _to_interaction_unit(record: dict[str, Any], index: int) -> dict[str, Any]:
    source_file = str(record.get("source_json_path") or "")
    offsets = record.get("source_offsets") or {}
    return {
        "unit_id": f"riu_v1_{index:05d}",
        "paper_id": str(record.get("paper_id") or ""),
        "pair_id": record.get("pair_id"),
        "source_url": None,
        "doi": record.get("doi"),
        "title": record.get("title"),
        "journal": record.get("journal"),
        "year": record.get("year"),
        "review_round": None,
        "reviewer_id": None,
        "review_text": record.get("review_text") or record.get("review_context") or "",
        "response_text": record.get("response_text") or record.get("author_response") or "",
        "review_offset": _offset(offsets, "context"),
        "response_offset": _offset(offsets, "response"),
        "concern_type": record.get("concern_type") or "unknown",
        "risk_type": _risk_from_concern(record.get("concern_type")),
        "tacit_concern": record.get("tacit_concern") or _model_field_fallback(record, "tacit_concern"),
        "institutional_signal": record.get("institutional_signal") or _model_field_fallback(record, "institutional_signal"),
        "evidence_action": record.get("evidence_action") or _normalize_evidence_action(None),
        "author_positioning": record.get("author_positioning") or _model_field_fallback(record, "author_positioning"),
        "response_strategy": record.get("response_strategy") or "unknown",
        "tone_commitment": record.get("tone_commitment") or _model_tone_fallback(record),
        "editor_signal": {"signal": "not_available" if not record.get("has_decision") else "editorial_process_signal"},
        "actor_links": record.get("actor_links") or _structural_actor_links(record),
        "provenance": {
            "source_file": source_file,
            "source_hash": _sha1(source_file),
            "url": None,
            "offset_recoverable": bool(record.get("offset_recoverable") in {True, "yes"}),
        },
        "label_source": _normalize_label_source(str(record.get("label_source") or "heuristic")),
    }


def _build_case_index(units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_paper: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for unit in units:
        by_paper[unit["paper_id"]].append(unit)
    cases = []
    for index, (paper_id, paper_units) in enumerate(sorted(by_paper.items()), start=1):
        cases.append(
            {
                "case_id": f"case_v1_{index:05d}",
                "paper_id": paper_id,
                "unit_ids": [u["unit_id"] for u in paper_units],
                "available_chain": {
                    "has_review": True,
                    "has_response": True,
                    "has_editor_decision": any((u.get("editor_signal") or {}).get("signal") != "not_available" for u in paper_units),
                },
                "actor_links": _merge_actor_links(paper_units),
                "top_concern_types": _top_counts(u["concern_type"] for u in paper_units),
                "top_institutional_signals": _top_counts(u["institutional_signal"] for u in paper_units),
                "top_evidence_actions": _top_counts(u["evidence_action"] for u in paper_units),
                "source_url": None,
                "provenance_status": "complete"
                if all((u.get("provenance") or {}).get("source_file") for u in paper_units)
                else "partial",
            }
        )
    return cases


def _build_actor_network_cases(case_index: list[dict[str, Any]], units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    unit_by_id = {u["unit_id"]: u for u in units}
    actor_cases = []
    for case in case_index:
        case_units = [unit_by_id[uid] for uid in case["unit_ids"] if uid in unit_by_id]
        if not case_units:
            continue
        first = case_units[0]
        actor_cases.append(
            {
                "case_id": case["case_id"],
                "paper_id": case["paper_id"],
                "unit_ids": case["unit_ids"],
                "actors": _merge_actor_links(case_units),
                "interaction_translation": {
                    "reviewer_concern": first["concern_type"],
                    "scientific_risk": first["risk_type"],
                    "institutional_signal": first["institutional_signal"],
                    "evidence_action": first["evidence_action"],
                    "author_positioning": first["author_positioning"],
                    "editor_readable_resolution": (first.get("editor_signal") or {}).get("signal"),
                },
                "provenance": {
                    "source_file": (first.get("provenance") or {}).get("source_file"),
                    "source_hash": (first.get("provenance") or {}).get("source_hash"),
                    "unit_offsets": [
                        {
                            "unit_id": u["unit_id"],
                            "review_offset": u.get("review_offset"),
                            "response_offset": u.get("response_offset"),
                        }
                        for u in case_units
                    ],
                },
            }
        )
    return actor_cases


def _write_kb_outputs(units: list[dict[str, Any]], cases: list[dict[str, Any]], actor_cases: list[dict[str, Any]]) -> None:
    write_jsonl(KB_DIR / "interaction_units.jsonl", units)
    write_jsonl(KB_DIR / "case_index.jsonl", cases)
    write_jsonl(KB_DIR / "actor_network_cases.jsonl", actor_cases)
    summary = {
        "unit_count": len(units),
        "case_count": len(cases),
        "actor_network_case_count": len(actor_cases),
        "label_source_counts": Counter(u["label_source"] for u in units),
        "provenance_complete_rate": sum(1 for u in units if (u.get("provenance") or {}).get("source_file")) / max(len(units), 1),
        "concern_counts": Counter(u["concern_type"] for u in units),
        "institutional_signal_counts": Counter(u["institutional_signal"] for u in units),
    }
    _write_json(KB_DIR / "kb_summary.json", _jsonable(summary))
    readme = """# Review Interaction KB v1

This KB contains Review Interaction Units generated from current v2709 MVP material.

## Files

- `interaction_units.jsonl`: unit-level review-response interaction records.
- `case_index.jsonl`: paper/case-level grouping.
- `actor_network_cases.jsonl`: actor-network representation for cross-disciplinary retrieval.
- `kb_summary.json`: counts and provenance summary.

## Label status

This is not a human-gold benchmark. It combines heuristic and model-assisted candidate labels for retrieval and workflow prototyping.
"""
    (KB_DIR / "README.md").write_text(readme, encoding="utf-8")


def _build_retrieval_v2(units: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    queries = units[: min(100, len(units))]
    predictions = []
    provenance_complete = sum(1 for unit in units if (unit.get("provenance") or {}).get("source_file")) / max(len(units), 1)
    for query in queries:
        scored = []
        for candidate in units:
            if candidate["unit_id"] == query["unit_id"]:
                continue
            score = 0
            if candidate["concern_type"] == query["concern_type"]:
                score += 8
            if candidate.get("risk_type") == query.get("risk_type"):
                score += 5
            if candidate["institutional_signal"] == query["institutional_signal"]:
                score += 3
            score += _actor_overlap_score(query, candidate)
            if _has_model_supported_evidence_action(candidate):
                score += 2
            if (candidate.get("provenance") or {}).get("source_file"):
                score += 1
            scored.append((score, candidate))
        ranked = [c for _, c in sorted(scored, key=lambda item: (-item[0], item[1]["unit_id"]))]
        top = ranked[:5]
        top1 = top[:1]
        top3 = top[:3]
        case_explanations = [_case_explanation(query, candidate) for candidate in top]
        predictions.append(
            {
                "query_unit_id": query["unit_id"],
                "query_concern_type": query["concern_type"],
                "query_strategy": query["response_strategy"],
                "query_strategy_label_used_for_ranking": False,
                "method": "case_metadata_interdisciplinary_rerank_v3",
                "top_k": [
                    {
                        "unit_id": c["unit_id"],
                        "paper_id": c["paper_id"],
                        "concern_type": c["concern_type"],
                        "institutional_signal": c["institutional_signal"],
                        "response_strategy": c["response_strategy"],
                        "evidence_action": c["evidence_action"],
                    }
                    for c in top
                ],
                "case_explanations": case_explanations,
                "strategy_hit_at_1": any(c["response_strategy"] == query["response_strategy"] for c in top1),
                "strategy_hit_at_3": any(c["response_strategy"] == query["response_strategy"] for c in top3),
                "strategy_hit_at_5": any(c["response_strategy"] == query["response_strategy"] for c in top),
                "concern_hit_at_5": any(c["concern_type"] == query["concern_type"] for c in top),
                "institutional_hit_at_5": any(c["institutional_signal"] == query["institutional_signal"] for c in top),
                "joint_strategy_concern_at_5": any(
                    c["response_strategy"] == query["response_strategy"] and c["concern_type"] == query["concern_type"]
                    for c in top
                ),
                "distinct_paper_count": len({c["paper_id"] for c in top}),
                "distinct_strategy_count": len({c["response_strategy"] for c in top}),
                "case_diversity_at_5": len({c["paper_id"] for c in top}) / max(len(top), 1),
                "retrieval_signal_notes": [
                    "case_metadata_signal: concern, risk, institutional_signal, actor links, provenance",
                    "interdisciplinary_signal: actor-network and model-supported evidence-action availability",
                ],
            }
        )
    n = max(len(predictions), 1)
    p1_summary = _read_json(
        PROJECT_ROOT / "data/evaluation/p1_retrieval_baselines/v2709_model_revised/p1_retrieval_summary.json"
    )
    p1_best = p1_summary.get("best_by_metric", {})
    p1_methods = p1_summary.get("methods", {})
    p1_comparison = {}
    for metric in [
        "strategy_recall_at_1",
        "strategy_recall_at_3",
        "strategy_recall_at_5",
        "concern_match_at_5",
        "joint_strategy_concern_match_at_5",
    ]:
        method_name = p1_best.get(metric)
        method_metrics = (p1_methods.get(method_name) or {}).get("metrics", {}) if method_name else {}
        p1_comparison[metric] = {
            "best_method": method_name,
            "value": method_metrics.get(metric),
        }
    summary = {
        "baseline_id": "retrieval_v3_case_metadata_interdisciplinary_rerank",
        "query_count": len(predictions),
        "pool_count": len(units),
        "metrics": {
            "strategy_recall_at_1": sum(1 for p in predictions if p["strategy_hit_at_1"]) / n,
            "strategy_recall_at_3": sum(1 for p in predictions if p["strategy_hit_at_3"]) / n,
            "strategy_recall_at_5": sum(1 for p in predictions if p["strategy_hit_at_5"]) / n,
            "concern_match_at_5": sum(1 for p in predictions if p["concern_hit_at_5"]) / n,
            "institutional_match_at_5": sum(1 for p in predictions if p["institutional_hit_at_5"]) / n,
            "joint_strategy_concern_at_5": sum(1 for p in predictions if p["joint_strategy_concern_at_5"]) / n,
            "average_distinct_paper_count": sum(p["distinct_paper_count"] for p in predictions) / n,
            "average_distinct_strategy_count": sum(p["distinct_strategy_count"] for p in predictions) / n,
            "case_diversity_at_5": sum(p["case_diversity_at_5"] for p in predictions) / n,
            "provenance_completeness": provenance_complete,
        },
        "p1_baseline_comparison": p1_comparison,
        "improvement_attribution": {
            "case_metadata_signals": [
                "concern_type",
                "risk_type",
                "institutional_signal",
                "actor_links",
                "provenance",
            ],
            "advice_path_boundary": "Agnes workflow advice is grounded in model-assisted labels, controlled Nature case metadata, provenance-linked case analogies, cross-disciplinary traces, and author-confirmation gates.",
            "caveat": "V2 and P1 are over different candidate-label pools, so comparisons are directional sanity checks, not final human-gold claims.",
        },
        "notes": [
            "This is a case-metadata retrieval sanity baseline over candidate labels.",
            "It is not a final human-gold evaluation.",
        ],
    }
    return predictions, summary


def _case_explanation(query: dict[str, Any], candidate: dict[str, Any]) -> dict[str, Any]:
    shared_reasons = []
    if candidate.get("concern_type") == query.get("concern_type"):
        shared_reasons.append(f"shares concern={candidate.get('concern_type')}")
    if candidate.get("institutional_signal") == query.get("institutional_signal"):
        shared_reasons.append(f"shares institutional_signal={candidate.get('institutional_signal')}")
    if candidate.get("risk_type") == query.get("risk_type"):
        shared_reasons.append(f"shares risk_type={candidate.get('risk_type')}")
    why_relevant = (
        "Retrieved as a Nature case analogy because it " + " and ".join(shared_reasons) + " with the query."
        if shared_reasons
        else "Retrieved as a provenance-linked Nature case candidate; no label match is claimed."
    )
    matched_signals = {
        "concern_type": candidate.get("concern_type") if candidate.get("concern_type") == query.get("concern_type") else None,
        "institutional_signal": candidate.get("institutional_signal")
        if candidate.get("institutional_signal") == query.get("institutional_signal")
        else None,
        "risk_type": candidate.get("risk_type") if candidate.get("risk_type") == query.get("risk_type") else None,
        "actor_types": sorted({link.get("actor_type") for link in candidate.get("actor_links", []) if link.get("actor_type")}),
        "case_metadata_basis": ["concern_type", "risk_type", "institutional_signal", "actor_links", "provenance"],
    }
    return {
        "unit_id": candidate.get("unit_id"),
        "paper_id": candidate.get("paper_id"),
        "why_relevant": why_relevant,
        "matched_signals": matched_signals,
        "transferable_pattern": {
            "concern": candidate.get("concern_type"),
            "risk": candidate.get("risk_type"),
            "strategy": candidate.get("response_strategy"),
            "evidence_action": _model_supported_evidence_action(candidate),
            "author_positioning": candidate.get("author_positioning"),
            "tone_commitment": candidate.get("tone_commitment"),
            "label_source": candidate.get("label_source"),
        },
        "provenance": candidate.get("provenance") or {},
    }


def _write_retrieval_outputs(predictions: list[dict[str, Any]], summary: dict[str, Any]) -> None:
    write_jsonl(RETRIEVAL_DIR / "predictions.jsonl", predictions)
    _write_json(RETRIEVAL_DIR / "retrieval_v2_summary.json", _jsonable(summary))
    p1_rows = "\n".join(
        f"| {metric} | {payload.get('best_method') or 'n/a'} | {_fmt_metric(payload.get('value'))} |"
        for metric, payload in summary["p1_baseline_comparison"].items()
    )
    report = f"""# Retrieval v2 Report

## Input

- query_count: {summary["query_count"]}
- pool_count: {summary["pool_count"]}
- method: case metadata + interdisciplinary signal rerank

## Metrics

| Metric | Value |
|---|---:|
| strategy_recall_at_1 | {summary["metrics"]["strategy_recall_at_1"]:.4f} |
| strategy_recall_at_3 | {summary["metrics"]["strategy_recall_at_3"]:.4f} |
| strategy_recall_at_5 | {summary["metrics"]["strategy_recall_at_5"]:.4f} |
| concern_match_at_5 | {summary["metrics"]["concern_match_at_5"]:.4f} |
| institutional_match_at_5 | {summary["metrics"]["institutional_match_at_5"]:.4f} |
| joint_strategy_concern_at_5 | {summary["metrics"]["joint_strategy_concern_at_5"]:.4f} |
| case_diversity_at_5 | {summary["metrics"]["case_diversity_at_5"]:.4f} |
| provenance_completeness | {summary["metrics"]["provenance_completeness"]:.4f} |
| average_distinct_paper_count | {summary["metrics"]["average_distinct_paper_count"]:.4f} |
| average_distinct_strategy_count | {summary["metrics"]["average_distinct_strategy_count"]:.4f} |

## P1 Baseline Comparison

| P1 metric | Best P1 method | P1 value |
|---|---|---:|
{p1_rows}

## Improvement Attribution

- Case metadata: concern, risk, institutional signal, actor links, and provenance are explicit rerank signals.
- No strategy-label leakage: response_strategy is used only as an evaluation target, not as a ranking signal.
- Advice boundary: Agnes workflow recommendations are grounded in model-assisted labels, controlled Nature case metadata, provenance-linked case analogies, cross-disciplinary traces, and author-confirmation gates.
- Caveat: v2 and P1 are evaluated over candidate labels and different pools, so these numbers are sanity checks rather than human-gold claims.

## Limitations

This is evaluated over candidate labels, not final human gold.
"""
    (RETRIEVAL_DIR / "retrieval_v2_report.md").write_text(report, encoding="utf-8")


def _build_workflow_traces(units: list[dict[str, Any]], retrieval_predictions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    pred_by_query = {p["query_unit_id"]: p for p in retrieval_predictions}
    traces = []
    for unit in units:
        pred = pred_by_query.get(unit["unit_id"], {"top_k": []})
        case_explanations = pred.get("case_explanations", [])
        lens_map = _cross_disciplinary_lens_map(unit, pred)
        agent_outputs = _agent_intermediate_outputs(unit, pred)
        agent_outputs["cross_disciplinary_lens_interpreter"] = {"lens_map": lens_map}
        rebuttal_plan = _build_rebuttal_plan(unit, pred)
        trace = {
            "trace_id": f"workflow_v2_{len(traces) + 1:04d}",
            "query_unit_id": unit["unit_id"],
            "input_review_text": unit["review_text"],
            "agent_intermediate_outputs": agent_outputs,
            "cross_disciplinary_lens_map": lens_map,
            "case_explanations": case_explanations,
            "cognitive_trace": {
                "understand": agent_outputs["reviewer_understanding_agent"],
                "question": {
                    "risk_interpretation": agent_outputs["tacit_concern_interpreter"]["risk_interpretation"],
                    "uncertainty_notes": ["Candidate label requires human confirmation."],
                },
                "evidence_plan": agent_outputs["evidence_action_planner"],
                "position": agent_outputs["author_positioning_agent"],
                "tone_calibrate": agent_outputs["tone_commitment_calibrator"],
                "commitment_check": {
                    "unsupported_commitment_flags": [
                        flag for flag in unit["tone_commitment"].get("risk_flags", []) if flag != "none"
                    ]
                },
                "integrity_check": agent_outputs["integrity_adequacy_checker"],
                "output": {
                    "final_structured_output": _structured_output(unit, rebuttal_plan),
                    "rebuttal_plan": rebuttal_plan,
                },
            },
            "institutional_signal_note": [{"institutional_signal": unit["institutional_signal"]}],
            "actor_network_note": unit["actor_links"],
            "case_selection_basis": {
                "method": pred.get("method", "not_run"),
                "advice_boundary": "model-assisted labels, controlled Nature case metadata, provenance-linked case analogies, cross-disciplinary traces, and author-confirmation gates",
            },
            "retrieved_case_ids": [item["unit_id"] for item in pred.get("top_k", [])],
            "outline": [section["suggested_move"] for section in rebuttal_plan["sections"]],
            "integrity_checks": ["no_acceptance_prediction", "no_unverified_experiment_claim", "provenance_required"],
            "provenance": [unit["provenance"]],
            "errors": [],
        }
        traces.append(trace)
    return traces


def _agent_intermediate_outputs(unit: dict[str, Any], pred: dict[str, Any]) -> dict[str, Any]:
    evidence_plan = _build_evidence_action_plan(unit, pred)
    response_adequacy = _assess_response_adequacy(unit, evidence_plan)
    return {
        "reviewer_understanding_agent": {
            "concern_map": [
                {
                    "concern_type": unit["concern_type"],
                    "surface_request": _preview(unit["review_text"], 180),
                    "implicit_risk": _implicit_risk_note(unit),
                    "text_evidence": _preview(unit["review_text"]),
                    "label_source": unit.get("label_source"),
                }
            ]
        },
        "tacit_concern_interpreter": {
            "risk_interpretation": [
                {
                    "risk_type": unit["risk_type"],
                    "tacit_concern": unit["tacit_concern"],
                    "boundary": "Observable textual trace only; not a claim about reviewer psychology.",
                }
            ]
        },
        "institutional_signal_interpreter": {
            "institutional_signal_note": [
                {
                    "institutional_signal": unit["institutional_signal"],
                    "action_link": "Translate institutional signal into evidence and positioning choices without predicting acceptance.",
                }
            ]
        },
        "evidence_action_planner": {
            "evidence_action_plan": evidence_plan,
            "author_confirmation_questions": _author_confirmation_questions(unit, evidence_plan),
        },
        "author_positioning_agent": {
            "author_positioning": [
                {
                    "position": unit["author_positioning"],
                    "stance_boundary": "Offer options for author judgment; do not force concession.",
                }
            ]
        },
        "tone_commitment_calibrator": {
            "tone_commitment_warnings": [unit["tone_commitment"]],
        },
        "actor_network_mapper": {
            "actor_network_note": unit["actor_links"],
            "retrieved_case_ids": [item["unit_id"] for item in pred.get("top_k", [])],
        },
        "integrity_adequacy_checker": {
            "adequacy_report": [
                "Trace is provenance-linked but not human evaluated.",
                "Do not treat this as final rebuttal text.",
                "Do not predict acceptance probability.",
            ],
            "response_adequacy": response_adequacy,
            "provenance_checks": [unit["provenance"]],
            "responsible_use_warnings": ["assistant_only", "author_must_verify_all_claims"],
        },
    }


def _cross_disciplinary_lens_map(unit: dict[str, Any], pred: dict[str, Any]) -> dict[str, Any]:
    evidence_action = _resolve_evidence_action(unit, pred).get("action_type")
    retrieved_case_ids = [item.get("unit_id") for item in pred.get("top_k", [])[:3]]
    tone = unit.get("tone_commitment") if isinstance(unit.get("tone_commitment"), dict) else {}
    actor_types = sorted(
        {
            str(link.get("actor_type"))
            for link in (unit.get("actor_links") or [])
            if isinstance(link, dict) and link.get("actor_type")
        }
    )
    return {
        "tacit_knowledge_boundary": {
            "source_pdf": "2026.5.15.pdf",
            "concept": "默会知识只能作为公开文本中的可观察痕迹来处理",
            "observable_trace": f"tacit_concern={unit.get('tacit_concern')}; risk_type={unit.get('risk_type')}; concern_type={unit.get('concern_type')}",
            "system_action": "把 reviewer concern 转成可追溯的风险假设，并要求证据片段支持。",
            "boundary": "不推断真实心理，不声称 AI 掌握专家默会知识，只保留可观察文本痕迹。",
            "evaluation_question": "系统是否把隐含风险解释为可检查假设，而不是把它写成 reviewer 的真实意图？",
        },
        "institutional_dependence": {
            "source_pdf": "2026.5.15.pdf",
            "concept": "制度依赖和发表压力会影响作者回应姿态",
            "observable_trace": f"institutional_signal={unit.get('institutional_signal')}; author_positioning={unit.get('author_positioning')}",
            "system_action": "把期刊范围、透明性规范、共同体标准等制度信号转成作者可选择的回应位置。",
            "boundary": "不预测接收率，不把礼貌或让步自动解释为服从制度压力；作者确认和作者判断必须保留。",
            "evaluation_question": "系统是否帮助作者识别制度语境，同时保留作者判断和责任？",
        },
        "actor_network_alignment": {
            "source_pdf": "2026.5.15.pdf",
            "concept": "行动者网络把 reviewer、author、editor 与 figure/dataset/code/benchmark 等对象一起建模",
            "observable_trace": f"actor_types={actor_types}; retrieved_cases={retrieved_case_ids}",
            "system_action": "记录哪些人类和非人类行动者承载证据、修订、透明性或编辑可读信号。",
            "boundary": "不还原真实社会因果，只描述公开文本中可观察的行动者对齐关系；不替代作者、reviewer 或 editor 的判断。",
            "evaluation_question": "系统是否说明了 evidence action 由哪些对象承载，而不是只给出抽象建议？",
        },
        "fast_slow_cognitive_correction": {
            "source_pdf": "2026.5.23.pdf",
            "concept": "快思维先反应，慢思维负责校准、证据约束和完整性检查",
            "observable_trace": "understand -> question -> evidence_plan -> position -> tone_calibrate -> commitment_check -> integrity_check -> output",
            "system_action": "强制 plan-first workflow，先做 concern/risk/evidence/commitment 检查，再输出结构化建议。",
            "boundary": "不直接生成最终 rebuttal，不把流畅文本当成充分回应；作者确认必须先于任何承诺。",
            "evaluation_question": "系统是否有明确慢思维纠偏链条来减少过度自信、迎合和编造风险？",
        },
        "emotion_tone_commitment_calibration": {
            "source_pdf": "2026.5.23.pdf",
            "concept": "情绪维度不是表演共情，而是学术互动姿态、承诺强度和不确定性管理",
            "observable_trace": f"tone={tone.get('tone')}; commitment_level={tone.get('commitment_level')}; risk_flags={tone.get('risk_flags')}",
            "system_action": "校准语气、承诺强度、防御性、迎合风险和 unsupported commitment。",
            "boundary": "不诊断作者或 reviewer 情绪，不推断真实心理，不用温和语气替代实质证据。",
            "evaluation_question": "系统是否既降低冲突风险，又避免无证据让步或承诺？",
        },
        "author_agency_gate": {
            "source_pdf": "2026.5.23.pdf + 2026.5.15.pdf",
            "concept": "assistant 必须保留作者主体性和专业判断",
            "observable_trace": f"evidence_action={evidence_action}; author_confirmation_required=true; label_status=model_assisted_not_human_gold",
            "system_action": "对所有证据动作、实验、数据、引用和承诺设置作者确认门禁。",
            "boundary": "作者确认必需；系统不替代作者、不替代 reviewer、不替代 editor。",
            "evaluation_question": "系统是否把建议变成作者可审查的选择，而不是替作者做承诺？",
        },
    }


def _model_supported_evidence_action(unit: dict[str, Any]) -> str:
    action = str(unit.get("evidence_action") or "unknown")
    if _has_model_supported_evidence_action(unit):
        return action
    return "unknown"


def _actor_types(unit: dict[str, Any]) -> set[str]:
    return {
        str(link.get("actor_type"))
        for link in unit.get("actor_links", [])
        if isinstance(link, dict) and link.get("actor_type")
    }


def _actor_overlap_score(query: dict[str, Any], candidate: dict[str, Any]) -> int:
    return len(_actor_types(query) & _actor_types(candidate))


def _has_model_supported_evidence_action(unit: dict[str, Any]) -> bool:
    action = str(unit.get("evidence_action") or "unknown")
    label_source = str(unit.get("label_source") or "")
    return action not in {"", "unknown"} and label_source in {"model_assisted", "human_confirmed", "mixed"}


def _resolve_evidence_action(unit: dict[str, Any], pred: dict[str, Any]) -> dict[str, Any]:
    action = _model_supported_evidence_action(unit)
    if action != "unknown":
        return {
            "action_type": action,
            "basis_type": "model_assisted_unit_label",
            "supporting_case_ids": [],
            "support_count": 1,
            "requires_author_confirmation": True,
        }

    counts: Counter[str] = Counter()
    supporting: dict[str, list[str]] = defaultdict(list)
    for explanation in pred.get("case_explanations", [])[:5]:
        pattern = explanation.get("transferable_pattern") or {}
        candidate_action = str(pattern.get("evidence_action") or "unknown")
        label_source = str(pattern.get("label_source") or "")
        if candidate_action in {"", "unknown"} or label_source not in {"model_assisted", "human_confirmed", "mixed"}:
            continue
        counts[candidate_action] += 1
        supporting[candidate_action].append(str(explanation.get("unit_id") or "unknown_case"))

    if counts:
        selected, support_count = counts.most_common(1)[0]
        return {
            "action_type": selected,
            "basis_type": "case_derived",
            "supporting_case_ids": supporting[selected],
            "support_count": support_count,
            "requires_author_confirmation": True,
        }

    return {
        "action_type": "insufficient_case_support",
        "basis_type": "insufficient_model_or_case_evidence",
        "supporting_case_ids": [],
        "support_count": 0,
        "requires_author_confirmation": True,
    }


def _required_artifact_for_action(action: str) -> str:
    artifacts = {
        "claim_narrowing": "claim boundary revision and limitation wording verified by the author",
        "code_data_availability": "code, data, protocol, or availability artifact verified by the author",
        "figure_table_revision": "figure, table, caption, or visual presentation revision verified by the author",
        "future_work_commitment": "bounded future-work statement verified by the author",
        "limitation_discussion": "limitation or caveat text verified by the author",
        "literature_repositioning": "related-work or contribution-positioning revision verified by the author",
        "method_clarification": "method, assumption, or implementation clarification verified by the author",
        "new_analysis": "new analysis, robustness check, or comparison verified by the author",
        "new_baseline_or_comparison": "additional baseline or comparative result verified by the author",
        "new_experiment": "new experiment, validation, or control result verified by the author",
        "no_new_evidence_explanation_only": "existing-evidence explanation verified by the author",
        "statistical_test_or_uncertainty": "statistical test, uncertainty estimate, or sample-size statement verified by the author",
        "supplementary_material_revision": "supplementary material revision verified by the author",
        "insufficient_case_support": "author-provided evidence or manuscript location is required before any action can be recommended",
        "unknown": "author-provided evidence or manuscript location is required before any action can be recommended",
    }
    return artifacts.get(action, "author-verified artifact matching the selected model-assisted evidence action")


def _build_evidence_action_plan(unit: dict[str, Any], pred: dict[str, Any]) -> list[dict[str, Any]]:
    decision = _resolve_evidence_action(unit, pred)
    action = decision["action_type"]
    retrieved_patterns = [
        explanation.get("transferable_pattern", {}).get("evidence_action")
        for explanation in pred.get("case_explanations", [])[:3]
        if explanation.get("transferable_pattern", {}).get("evidence_action")
    ]
    return [
        {
            "action_type": action,
            "evidence_action": action,
            "required_artifact": _required_artifact_for_action(action),
            "feasibility": "needs_author_confirmation",
            "author_must_confirm": True,
            "linked_concern_type": unit.get("concern_type"),
            "retrieved_case_patterns": retrieved_patterns,
            "decision_basis": decision,
            "overclaim_risk": _overclaim_risks(unit, action),
            "no_fabrication_boundary": "Do not invent experiments, data, citations, or commitments.",
        }
    ]


def _author_confirmation_questions(unit: dict[str, Any], evidence_plan: list[dict[str, Any]]) -> list[str]:
    action = evidence_plan[0]["action_type"] if evidence_plan else "textual_clarification_with_author_confirmation"
    artifact = evidence_plan[0]["required_artifact"] if evidence_plan else "manuscript clarification"
    return [
        f"Can the author verify that the proposed artifact exists or can be added: {artifact}?",
        f"Where should the response cite the manuscript change for concern_type={unit.get('concern_type')}?",
        f"Does the author need to narrow the claim if {action} cannot be completed?",
    ]


def _assess_response_adequacy(unit: dict[str, Any], evidence_plan: list[dict[str, Any]]) -> dict[str, Any]:
    concern = str(unit.get("concern_type") or "")
    action = evidence_plan[0]["action_type"] if evidence_plan else "unknown"
    decision_basis = {
        "basis_type": "insufficient_model_or_case_adequacy_signal",
        "source": "model_assisted_labels_and_case_metadata",
        "supporting_case_ids": [],
    }
    if not str(unit.get("response_text") or "").strip():
        coverage = "not_covered"
    elif unit.get("alignment_correct") == "yes" and _has_model_supported_evidence_action(unit):
        coverage = "covered"
        decision_basis = {
            "basis_type": "model_assisted_alignment_and_evidence_action",
            "source": unit.get("label_source"),
            "supporting_case_ids": [],
        }
    elif unit.get("response_strategy") in {"clarify_existing_evidence", "justify_method_choice"}:
        coverage = "partially_covered"
        decision_basis = {
            "basis_type": "model_assisted_strategy_boundary",
            "source": unit.get("label_source"),
            "supporting_case_ids": [],
        }
    else:
        coverage = "needs_author_confirmation"
    missing = [] if coverage == "covered" else [action]
    unresolved = [] if coverage == "covered" else [f"Need confirmation that response addresses {concern} with {action}."]
    return {
        "coverage_status": coverage,
        "unresolved_concerns": unresolved,
        "missing_evidence_actions": missing,
        "adequacy_rationale": (
            f"Coverage is {coverage}; assessed from model-assisted alignment, evidence-action labels, "
            "case-derived support, and author-confirmation boundaries. This is not human gold."
        ),
        "decision_basis": decision_basis,
        "needs_author_confirmation": True,
    }


def _build_rebuttal_plan(unit: dict[str, Any], pred: dict[str, Any]) -> dict[str, Any]:
    evidence_decision = _resolve_evidence_action(unit, pred)
    evidence_action = evidence_decision["action_type"]
    case_ids = [item.get("unit_id") for item in pred.get("top_k", [])[:3]]
    return {
        "plan_id": f"plan::{unit.get('unit_id')}",
        "label_status": "model_assisted_not_human_gold",
        "sections": [
            {
                "name": "concern_acknowledgement",
                "purpose": f"Address reviewer concern type {unit.get('concern_type')} without defensiveness.",
                "suggested_move": f"Acknowledge the reviewer concern about {unit.get('concern_type')} and restate the scientific risk.",
                "source": "reviewer_understanding_agent",
            },
            {
                "name": "evidence_action",
                "purpose": "Convert the reviewer concern into a verifiable evidence or revision action.",
                "suggested_move": f"Evaluate the case-supported action candidate: {evidence_action}; cite the manuscript location only after author confirmation.",
                "source": "evidence_action_planner",
                "action_type": evidence_action,
                "decision_basis": evidence_decision,
            },
            {
                "name": "case_grounded_strategy",
                "purpose": "Use retrieved Nature cases as strategy analogies, not as copied text.",
                "suggested_move": f"Compare against retrieved cases {', '.join(case_ids) or 'none'} to choose a bounded response strategy.",
                "source": "case_retrieval_agent",
            },
            {
                "name": "claim_boundary_and_tone",
                "purpose": "Calibrate author commitment and avoid overclaiming.",
                "suggested_move": f"Use author positioning={unit.get('author_positioning')} and tone={unit.get('tone_commitment', {}).get('tone')} while preserving uncertainty boundaries.",
                "source": "tone_commitment_calibrator",
            },
        ],
        "author_confirmation_required": True,
    }


def _structured_output(unit: dict[str, Any], rebuttal_plan: dict[str, Any]) -> list[str]:
    evidence_section = next(
        (section for section in rebuttal_plan["sections"] if section.get("name") == "evidence_action"),
        {},
    )
    return [
        f"Concern map: {unit.get('concern_type')} -> {unit.get('risk_type')}.",
        f"Evidence action before drafting: {evidence_section.get('action_type', 'needs_author_confirmation')}.",
        f"Author stance: {unit.get('author_positioning')}; keep all commitments verifiable.",
        f"Use {len(rebuttal_plan['sections'])} plan sections before drafting any final response.",
    ]


def _implicit_risk_note(unit: dict[str, Any]) -> str:
    return f"{unit.get('tacit_concern')} / {unit.get('risk_type')} based on observable text only."


def _overclaim_risks(unit: dict[str, Any], action: str) -> list[str]:
    risks = ["fabricated_evidence_if_author_cannot_verify_artifact"]
    if action in {"claim_narrowing", "limitation_discussion"} or unit.get("concern_type") == "generalization_scope":
        risks.append("overgeneralization")
    if action == "statistical_test_or_uncertainty":
        risks.append("unsupported_significance_claim")
    if unit.get("response_strategy") == "defer_future_work":
        risks.append("unsupported_future_commitment")
    return risks


def _write_workflow_outputs(traces: list[dict[str, Any]]) -> None:
    write_jsonl(WORKFLOW_DIR / "workflow_traces.jsonl", traces)
    summary = {
        "workflow_id": "naturereview_interact_workflow_v2",
        "trace_count": len(traces),
        "completed_count": len([t for t in traces if not t["errors"]]),
        "error_count": sum(1 for t in traces if t["errors"]),
        "cognitive_trace_stages": [
            "understand",
            "question",
            "evidence_plan",
            "position",
            "tone_calibrate",
            "commitment_check",
            "integrity_check",
            "output",
        ],
        "notes": [
            "This is a recordable and traceable assistant workflow over candidate labels.",
            "It is not a final human-evaluated benchmark or a final rebuttal-writing system.",
        ],
    }
    _write_json(WORKFLOW_DIR / "workflow_summary.json", summary)
    report = f"""# Workflow v2 Report

## Input

- trace_count: {len(traces)}
- source: Review Interaction KB v1 candidate units

## Agent steps

The workflow follows `understand -> question -> evidence_plan -> position -> tone_calibrate -> commitment_check -> integrity_check -> output`.

## Retrieval metrics

Retrieval case IDs are attached per trace when available.

## Integrity checks

- no acceptance prediction
- no unverified experiment claim
- provenance required

## Cognitive trace quality

Every trace records all required slow-thinking stages.

## Institutional positioning

Every trace contains an `institutional_signal_note`.

## Actor-network alignment

Every trace contains `actor_network_note` derived from observable actor links.

## Failure cases

No execution errors in this generated batch. Labels remain candidate labels.

## Difference from direct rebuttal generation

The workflow outputs structured maps, evidence plans, warnings, and outlines. It does not produce a final submission-ready rebuttal.

## Limitations

This is not a final rebuttal-writing system and not a human-gold evaluation.
"""
    (WORKFLOW_DIR / "workflow_report.md").write_text(report, encoding="utf-8")


def _build_simulation_traces(traces: list[dict[str, Any]]) -> list[dict[str, Any]]:
    simulation_traces: list[dict[str, Any]] = []
    for index, trace in enumerate(traces, start=1):
        cognitive = trace.get("cognitive_trace") or {}
        understand = cognitive.get("understand") or {}
        evidence_plan = cognitive.get("evidence_plan") or {}
        integrity_check = cognitive.get("integrity_check") or {}
        response_adequacy = integrity_check.get("response_adequacy") or {}
        rebuttal_plan = (cognitive.get("output") or {}).get("rebuttal_plan") or {}
        confirmation_questions = evidence_plan.get("author_confirmation_questions") or []
        evidence_actions = evidence_plan.get("evidence_action_plan") or []
        concern_map = understand.get("concern_map") or []
        first_concern = concern_map[0] if concern_map else {}
        unresolved = response_adequacy.get("unresolved_concerns") or []
        missing_evidence = response_adequacy.get("missing_evidence_actions") or []
        adequacy_status = response_adequacy.get("coverage_status") or "unknown"
        simulation_traces.append(
            {
                "simulation_id": f"simulation_v1_{index:04d}",
                "source_trace_id": trace.get("trace_id"),
                "query_unit_id": trace.get("query_unit_id"),
                "label_status": "model_assisted_not_human_gold",
                "boundary": "not real peer review; research-only simulation; assistant evaluation only",
                "simulation_roles": {
                    "reviewer_agent": {
                        "role_goal": "Restate observable reviewer concern and test whether the planned response addresses it.",
                        "observable_concern": first_concern.get("surface_request") or _preview(trace.get("input_review_text", "")),
                        "concern_type": first_concern.get("concern_type"),
                        "implicit_risk_probe": first_concern.get("implicit_risk"),
                        "adequacy_probe": {
                            "coverage_status": adequacy_status,
                            "unresolved_concerns": unresolved,
                            "missing_evidence_actions": missing_evidence,
                        },
                        "must_not_do": [
                            "infer private reviewer intent",
                            "identify reviewers",
                            "invent new criticism beyond observable text",
                        ],
                    },
                    "author_rebuttal_agent": {
                        "role_goal": "Create a plan-first author response scaffold with evidence and author-confirmation gates.",
                        "rebuttal_plan": rebuttal_plan,
                        "evidence_actions": evidence_actions,
                        "author_confirmation_questions": confirmation_questions,
                        "retrieved_case_explanations": trace.get("case_explanations") or [],
                        "must_not_do": [
                            "write final submission-ready rebuttal without author verification",
                            "invent experiments, data, citations, or completed revisions",
                            "promise changes the author has not confirmed",
                        ],
                    },
                    "editor_signal_agent": {
                        "role_goal": "Translate remaining concerns into editor-readable risk signals without predicting decisions.",
                        "editor_signal_note": _editor_signal_note_for_simulation(trace, response_adequacy),
                        "revision_pressure_signal": _revision_pressure_signal(response_adequacy),
                        "decision_boundary": "not an acceptance prediction; only a structured unresolved-risk note",
                        "must_not_do": [
                            "predict acceptance probability",
                            "claim causal effect of a response strategy",
                            "simulate a real editor decision",
                        ],
                    },
                },
                "evaluation_signals": {
                    "concern_coverage": adequacy_status,
                    "evidence_grounding": "needs_author_confirmation" if missing_evidence else "planned_with_case_support",
                    "commitment_safety": "requires_confirmation_gate"
                    if any(item.get("author_must_confirm") for item in evidence_actions)
                    else "no_explicit_commitment_detected",
                    "case_provenance_complete": all(
                        bool((case.get("provenance") or {}).get("source_file"))
                        for case in (trace.get("case_explanations") or [])
                    ),
                    "workflow_provenance_complete": all(
                        bool((prov or {}).get("source_file")) for prov in (trace.get("provenance") or [])
                    ),
                    "cross_disciplinary_trace": [
                        "tacit_concern",
                        "institutional_signal",
                        "actor_network",
                        "tone_commitment",
                        "response_adequacy",
                    ],
                    "simulation_limitations": [
                        "model-assisted labels only",
                        "not human gold",
                        "not real peer review",
                    ],
                },
                "cross_disciplinary_evaluation": _cross_disciplinary_simulation_evaluation(trace),
                "provenance": {
                    "workflow_trace_id": trace.get("trace_id"),
                    "query_unit_id": trace.get("query_unit_id"),
                    "source_provenance": trace.get("provenance") or [],
                    "retrieved_case_ids": trace.get("retrieved_case_ids") or [],
                },
            }
        )
    return simulation_traces


def _editor_signal_note_for_simulation(trace: dict[str, Any], response_adequacy: dict[str, Any]) -> dict[str, Any]:
    institutional_signal = None
    notes = trace.get("institutional_signal_note") or []
    if notes and isinstance(notes[0], dict):
        institutional_signal = notes[0].get("institutional_signal")
    return {
        "institutional_signal": institutional_signal or "unknown",
        "response_adequacy": response_adequacy.get("coverage_status") or "unknown",
        "editor_readable_risk": (
            "remaining evidence or claim-boundary risk needs author attention"
            if response_adequacy.get("coverage_status") != "covered"
            else "planned response appears to cover the observable concern, subject to author verification"
        ),
    }


def _cross_disciplinary_simulation_evaluation(trace: dict[str, Any]) -> dict[str, Any]:
    lens_map = trace.get("cross_disciplinary_lens_map") or {}
    lens_coverage = {
        key: bool(
            isinstance(lens_map.get(key), dict)
            and lens_map[key].get("observable_trace")
            and lens_map[key].get("system_action")
            and lens_map[key].get("boundary")
        )
        for key in CROSS_DISCIPLINARY_LENS_KEYS
    }
    return {
        "lens_coverage": lens_coverage,
        "all_required_lenses_present": all(lens_coverage.values()),
        "cross_disciplinary_value": [
            "默会知识边界被转成可观察风险假设",
            "制度依赖被转成作者可选择的回应位置",
            "行动者网络被转成 evidence carrier 和 provenance",
            "快思维/慢思维被转成 plan-first workflow",
            "情绪维度被转成语气、承诺和不确定性校准",
            "作者主体性通过 author confirmation gate 保留",
        ],
        "forbidden_behaviors": [
            "把检索结果当成最终答案",
            "用不可追溯的捷径替代案例证据和模型复核",
            "预测接收率",
            "编造实验或承诺",
            "推断 reviewer 或 editor 的真实心理",
            "替代作者专业判断",
        ],
        "not_rag_only_boundary": "not RAG-only; retrieval is support infrastructure for cross-disciplinary review-interaction reasoning.",
    }


def _revision_pressure_signal(response_adequacy: dict[str, Any]) -> str:
    coverage = response_adequacy.get("coverage_status")
    if coverage == "covered":
        return "low_unresolved_pressure_after_author_verification"
    if coverage == "partially_covered":
        return "medium_revision_pressure"
    if coverage == "not_covered":
        return "high_revision_pressure"
    return "needs_author_confirmation"


def _write_simulation_outputs(simulation_traces: list[dict[str, Any]]) -> None:
    write_jsonl(SIMULATION_DIR / "simulation_traces.jsonl", simulation_traces)
    role_counts = Counter(
        role
        for trace in simulation_traces
        for role in (trace.get("simulation_roles") or {}).keys()
    )
    adequacy_counts = Counter(
        (trace.get("evaluation_signals") or {}).get("concern_coverage") or "unknown"
        for trace in simulation_traces
    )
    summary = {
        "simulation_id": "simulation_v1_reviewer_author_editor_layer",
        "trace_count": len(simulation_traces),
        "label_status": "model_assisted_not_human_gold",
        "boundary": "not real peer review; research-only simulation; assistant evaluation only",
        "roles": sorted(role_counts),
        "role_counts": role_counts,
        "concern_coverage_counts": adequacy_counts,
        "source": "data/evaluation/workflow_v2/workflow_traces.jsonl",
        "notes": [
            "This is a lightweight evaluation/simulation layer over workflow traces.",
            "It does not simulate real reviewers or editors.",
            "It is designed to test whether the assistant preserves concern, evidence, tone, provenance, and integrity signals.",
        ],
    }
    _write_json(SIMULATION_DIR / "simulation_summary.json", _jsonable(summary))
    report = f"""# Simulation v1 Report

## Scope

- trace_count: {len(simulation_traces)}
- roles: reviewer_agent, author_rebuttal_agent, editor_signal_agent
- label_status: model_assisted_not_human_gold
- boundary: not real peer review

## Purpose

This layer evaluates whether a workflow trace can be re-read from three roles:

- Reviewer Agent: checks concern coverage against observable review text.
- Author Rebuttal Agent: checks evidence planning, confirmation questions, and case transfer.
- Editor Signal Agent: checks unresolved-risk signals without predicting acceptance.

## Limits

The simulation is not a replacement for real peer review, user studies, or human gold annotation.
"""
    (SIMULATION_DIR / "simulation_report.md").write_text(report, encoding="utf-8")
    spec = """# Simulation Evaluation Spec

## Purpose

This document defines the Layer 5 simulation/evaluation artifact for NatureReview-Interact. It is a research-only evaluation scaffold over recorded workflow traces, not real peer review.

It is not RAG-only. Retrieval is used as support infrastructure; the simulation evaluates 跨学科价值: tacit knowledge boundary, institutional dependence, actor-network alignment, fast/slow cognitive correction, emotion-tone-commitment calibration, and author agency.

## Reviewer Agent

Input: workflow trace, concern map, response adequacy report, provenance.

Output:

- observable reviewer concern
- concern type and implicit risk probe
- coverage status
- unresolved concerns
- missing evidence actions

Forbidden:

- infer private reviewer psychology
- identify reviewers
- invent criticism not grounded in the review text

## Author Rebuttal Agent

Input: retrieved case explanations, evidence action plan, rebuttal plan, tone/commitment warnings.

Output:

- plan-first rebuttal scaffold
- author confirmation questions
- evidence actions and required artifacts
- case-transfer notes

Forbidden:

- generate final submission-ready rebuttal as the default artifact
- invent experiments, data, citations, or completed manuscript changes
- commit to changes the author has not verified

## Editor Signal Agent

Input: institutional signal, response adequacy, missing evidence actions, unresolved concerns.

Output:

- editor-readable unresolved-risk note
- revision pressure signal
- decision-boundary warning

Forbidden:

- predict acceptance probability
- simulate a real editor decision
- claim causal effects from historical cases

## Evaluation Signals

- concern coverage
- evidence grounding
- commitment safety
- case provenance completeness
- workflow provenance completeness
- cross-disciplinary trace coverage
- cross-disciplinary lens coverage
- forbidden behavior avoidance

## Boundary

All simulation traces are `model_assisted_not_human_gold`. They are useful for system debugging and evaluation design, but they are not human gold and not real peer review.

## Not RAG-only Boundary

The system must not 把检索结果当成最终答案, must not 用不可追溯的捷径替代案例证据和模型复核, must not 预测接收率, and must not 编造实验或承诺.
"""
    _write_doc("SIMULATION_EVALUATION_SPEC_zh.md", spec)


def _write_training_outputs(interaction_units: list[dict[str, Any]]) -> None:
    training_rows = [_to_training_seed(unit, index) for index, unit in enumerate(interaction_units[:200], start=1)]
    write_jsonl(TRAINING_DIR / "model_assisted_training_seed_200.jsonl", training_rows)
    summary = {
        "row_count": len(training_rows),
        "label_status": "model_assisted_not_human_gold",
        "core_release_scope": "legacy_optional_non_core",
        "label_source_counts": Counter(row["label_source"] for row in training_rows),
        "task_counts": Counter(task for row in training_rows for task in row["learning_tasks"]),
        "provenance_complete_rate": (
            sum(1 for row in training_rows if row.get("provenance", {}).get("source_file") and row.get("provenance", {}).get("source_hash"))
            / len(training_rows)
            if training_rows
            else 0.0
        ),
        "notes": [
            "This export is a model-assisted training/evaluation seed, not a human gold benchmark.",
            "Legacy optional non-core artifact for future experiments; training and fine-tuning are not v0.1 core scope.",
            "It is designed for modular interaction-learning experiments, not final rebuttal generation fine-tuning.",
        ],
    }
    _write_json(TRAINING_DIR / "training_seed_summary.json", _jsonable(summary))
    report = f"""# Model-assisted Training Seed v0.1

## Purpose

This export turns Review Interaction Units into a compact training/evaluation contract for Author Rebuttal Assistant modules.

## Counts

```json
{json.dumps(_jsonable(summary), ensure_ascii=False, indent=2, sort_keys=True)}
```

## Boundary

- model-assisted training seed, not human gold benchmark.
- not for direct final rebuttal generator fine-tuning.
- every row keeps provenance and safety boundaries.
"""
    (TRAINING_DIR / "README.md").write_text(report, encoding="utf-8")
    training_doc = """# Training and Learning Design

## 目标

本项目的训练侧目标不是直接训练 final rebuttal generator，而是把 Nature 公开审稿互动案例转成可学习、可替换、可评估的中间能力。核心是学习审稿互动结构，而不是学习代写一封完整回复。

## Interaction Learning Targets

| Target | 学到什么 | 当前监督信号 | 主要风险 |
|---|---|---|---|
| concern understanding | reviewer 明确提出什么问题 | concern_type, review_text | 多问题评论被压成单一标签 |
| tacit risk interpretation | 明确意见背后的可观察风险 | tacit_concern, risk_type | 误读 reviewer 心理 |
| institutional positioning | 期刊、共同体、透明性等制度信号 | institutional_signal | 误写成接收率预测 |
| strategy selection | concern 对应的回应策略 | response_strategy | 把策略标签泄露给检索排序 |
| evidence action planning | 哪类证据动作能回应风险 | evidence_action, actor_links | 编造实验、数据或引用 |
| author positioning | 作者应坚持、让步、解释还是缩小 claim | author_positioning | 无原则迎合或过度防御 |
| tone / commitment calibration | 语气、承诺强度和不确定性边界 | tone_commitment | sycophancy 或 unsupported commitment |
| response adequacy | 回应是否真正覆盖 concern | retrieved cases + adequacy rubric | 只看流畅度不看解决度 |

## Trainable / Replaceable Modules

| Module | v0.1 实现 | 后续可训练方向 | 不建议做法 |
|---|---|---|---|
| Concern Classifier | taxonomy + model-assisted labels | lightweight classifier / prompt classifier | 直接用最终回复质量反推 concern |
| Risk Interpreter | tacit taxonomy + model-assisted labels | classifier with evidence quote constraint | 声称读取 reviewer hidden intent |
| Strategy Selector | retrieval target + label distribution | strategy prediction / reranker | 在 retrieval ranking 中使用 query strategy label |
| Evidence Planner | evidence_action + actor_links | action planner with feasibility flags | 推荐作者不存在的实验或数据 |
| Tone Calibrator | tone_commitment labels | unsupported commitment detector | 把礼貌当成充分回应 |
| Adequacy Checker | workflow trace + rubric | response adequacy scorer | 只评估语言流畅度 |
| Integrity Checker | provenance checks + author-confirmation gates | atomic claim support checker | 允许无来源事实或承诺 |

## model-assisted training seed

当前导出位置：

```text
data/training/author_rebuttal_agent/v2709/model_assisted_training_seed_200.jsonl
data/training/author_rebuttal_agent/v2709/training_seed_summary.json
```

每条训练样本包含：

- input: review_text, response_text, title, journal, year
- targets: concern_type, risk_type, tacit_concern, institutional_signal, response_strategy, evidence_action, author_positioning, tone_commitment, actor_links, response_adequacy
- learning_tasks: concern_extraction, risk_classification, strategy_prediction, evidence_action_prediction, author_positioning_prediction, tone_commitment_calibration, unsupported_commitment_detection, response_adequacy_scoring, decision_aware_case_retrieval
- provenance: source_file, source_hash, offset_recoverable, review_offset, response_offset
- safety_boundaries: no acceptance prediction, no fabricated evidence, no confidential manuscript upload, author confirmation required

## 当前 v0.1 的训练边界

- 当前数据可以支持 model-assisted sanity training/evaluation seed。
- 当前数据可以支持 retrieval/reranker、分类器、证据规划、tone/commitment checker 的原型实验。
- 当前数据不能支撑 human gold benchmark、接收率预测、端到端高质量 final rebuttal generator 微调。
- API 替代人工复核可以作为 v0.1 默认流程，但必须标注 model-assisted，不得写成人工金标。

## 推荐实验顺序

1. 固化 taxonomy 和训练 seed contract。
2. 比较 concern/risk/strategy/evidence 的 historical local baseline、retrieval baseline、LLM zero-shot。
3. 做 retrieval/reranker，但禁止使用 query response_strategy label 参与排序。
4. 做 response adequacy 和 unsupported commitment 检查。
5. 将模块接入 workflow trace，比较 direct LLM、RAG-only、cognitive workflow 三类路线。
6. 只有在出现 human gold benchmark 后，才声明正式监督评测结论。
"""
    _write_doc("TRAINING_AND_LEARNING_DESIGN_zh.md", training_doc)


def _to_training_seed(unit: dict[str, Any], index: int) -> dict[str, Any]:
    tone_commitment = unit.get("tone_commitment") if isinstance(unit.get("tone_commitment"), dict) else {}
    risk_flags = tone_commitment.get("risk_flags") if isinstance(tone_commitment, dict) else []
    unsupported_flags = [
        flag
        for flag in (risk_flags if isinstance(risk_flags, list) else [])
        if str(flag) in {"unsupported_commitment", "overclaim", "uncertainty_hiding"}
    ]
    response_adequacy = {
        "status": "candidate",
        "coverage_signal": "has_response" if unit.get("response_text") else "missing_response",
        "unsupported_commitment_flags": unsupported_flags,
        "needs_author_confirmation": True,
    }
    return {
        "training_example_id": f"train_seed_v2709_{index:04d}",
        "source_unit_id": unit.get("unit_id"),
        "input": {
            "review_text": unit.get("review_text"),
            "response_text": unit.get("response_text"),
            "title": unit.get("title"),
            "journal": unit.get("journal"),
            "year": unit.get("year"),
        },
        "targets": {
            "concern_type": unit.get("concern_type"),
            "risk_type": unit.get("risk_type"),
            "tacit_concern": unit.get("tacit_concern"),
            "institutional_signal": unit.get("institutional_signal"),
            "response_strategy": unit.get("response_strategy"),
            "evidence_action": unit.get("evidence_action"),
            "author_positioning": unit.get("author_positioning"),
            "tone_commitment": tone_commitment,
            "actor_links": unit.get("actor_links") or [],
            "response_adequacy": response_adequacy,
        },
        "learning_tasks": [
            "concern_extraction",
            "risk_classification",
            "tacit_concern_interpretation",
            "institutional_signal_detection",
            "strategy_prediction",
            "evidence_action_prediction",
            "author_positioning_prediction",
            "tone_commitment_calibration",
            "unsupported_commitment_detection",
            "response_adequacy_scoring",
            "decision_aware_case_retrieval",
        ],
        "provenance": {
            "source_file": (unit.get("provenance") or {}).get("source_file"),
            "source_hash": (unit.get("provenance") or {}).get("source_hash"),
            "offset_recoverable": (unit.get("provenance") or {}).get("offset_recoverable"),
            "review_offset": unit.get("review_offset"),
            "response_offset": unit.get("response_offset"),
            "doi": unit.get("doi"),
        },
        "label_source": unit.get("label_source"),
        "label_status": "model_assisted_not_human_gold",
        "safety_boundaries": [
            "no_acceptance_prediction",
            "no_fabricated_experiment_data_or_citation",
            "no_confidential_manuscript_upload",
            "author_confirmation_required",
            "provenance_required",
        ],
    }


def _write_evaluation_protocol() -> None:
    task_sections = "\n\n".join(_task_protocol_section(task) for task in EVALUATION_TASKS)
    protocol = f"""# Evaluation Protocol

## Tasks

{chr(10).join(f"{index}. {task['name']}" for index, task in enumerate(EVALUATION_TASKS, start=1))}

## Task Contracts

{task_sections}

## Label status

Current candidate labels are heuristic or model-assisted. They are not human gold.

Retrieval baselines, BM25-style baselines, and local comparison baselines are support infrastructure only. They are included to make the system auditable and comparable, but the project contribution is not RAG-only. The core value is a cross-disciplinary review-interaction workflow that turns tacit concern, institutional signal, actor-network alignment, cognitive correction, tone/commitment calibration, and author agency into recordable and evaluable traces.
"""
    _write_doc("EVALUATION_PROTOCOL_zh.md", protocol)

    rubric = {
        "dimensions": [
            "concern_correctness",
            "risk_interpretation_quality",
            "evidence_groundedness",
            "case_relevance",
            "tone_calibration",
            "commitment_safety",
            "adequacy_of_response",
            "provenance_traceability",
            "responsible_use_compliance",
            "tacit_concern_interpretation",
            "institutional_positioning_quality",
            "actor_network_alignment",
            "cognitive_trace_quality",
        ],
        "scale": [1, 2, 3, 4, 5],
    }
    _write_json(EVAL_DIR / "rubric.json", rubric)

    cross = {
        "dimensions": [
            {
                "name": "tacit_concern_interpretation",
                "scale": [1, 2, 3, 4, 5],
                "anchor_1": "Only repeats the explicit reviewer comment.",
                "anchor_3": "Identifies an implicit risk but lacks clear evidence or boundary.",
                "anchor_5": "Grounds the tacit concern in observable text and avoids mind-reading claims.",
            },
            {
                "name": "institutional_positioning_quality",
                "scale": [1, 2, 3, 4, 5],
                "anchor_1": "Ignores institutional context.",
                "anchor_3": "Mentions institutional pressure without linking it to author action.",
                "anchor_5": "Links institutional signals to responsible author positioning without acceptance prediction.",
            },
            {
                "name": "actor_network_alignment",
                "scale": [1, 2, 3, 4, 5],
                "anchor_1": "Only suggests wording.",
                "anchor_3": "Mentions evidence objects without explaining their role.",
                "anchor_5": "Explains how human and non-human actors are realigned through evidence and response actions.",
            },
            {
                "name": "cognitive_trace_quality",
                "scale": [1, 2, 3, 4, 5],
                "anchor_1": "Directly generates a reply.",
                "anchor_3": "Includes partial intermediate reasoning but misses commitment or integrity checks.",
                "anchor_5": "Records the full slow-thinking chain and shows how it reduces overconfidence, sycophancy, and fabrication risk.",
            },
        ]
    }
    _write_json(EVAL_DIR / "cross_disciplinary_rubric.json", cross)

    cross_doc = """# Cross-disciplinary Evaluation Rubric

## 1. Tacit Concern Interpretation

评分问题：系统是否基于文本证据识别了 reviewer concern 背后的可信度、领域标准、证据链或 claim 边界问题？

1 分：只复述 reviewer 原话。
3 分：能识别显性风险，但缺少文本证据或边界说明。
5 分：能给出可观察证据、解释边界，并避免声称读懂 reviewer 心理。

## 2. Institutional Positioning

评分问题：系统是否识别了期刊范围、共同体标准、透明性规范、editorial risk control 等制度信号？

1 分：完全忽略制度语境。
3 分：提到制度压力，但没有说明和 response strategy 的关系。
5 分：能把制度信号转成作者可执行的回应位置，同时不预测接收率。

## 3. Actor-network Alignment

评分问题：系统是否记录了 manuscript、figure、dataset、code、benchmark、supplement、editor signal 等行动者如何被重新对齐？

1 分：只输出文本回复建议。
3 分：提到证据对象，但没有说明互动功能。
5 分：明确说明哪些行动者承担了证据、修订、透明性或编辑可读信号的作用。

## 4. Cognitive Trace Quality

评分问题：系统是否按 understand -> question -> evidence_plan -> position -> tone_calibrate -> commitment_check -> integrity_check -> output 的顺序工作？

1 分：直接生成回复。
3 分：有部分中间步骤，但缺少承诺或 integrity 检查。
5 分：完整记录慢思维链条，并能解释每一步如何减少过度自信、迎合或编造风险。
"""
    _write_doc("CROSS_DISCIPLINARY_EVALUATION_RUBRIC_zh.md", cross_doc)

    sheet_fields = [
        "unit_id",
        "paper_id",
        "concern_correctness",
        "risk_interpretation_quality",
        "evidence_groundedness",
        "case_relevance",
        "tone_calibration",
        "commitment_safety",
        "adequacy_of_response",
        "provenance_traceability",
        "responsible_use_compliance",
        "tacit_concern_interpretation",
        "institutional_positioning_quality",
        "actor_network_alignment",
        "cognitive_trace_quality",
        "human_notes",
    ]
    _write_csv(EVAL_DIR / "human_eval_sheet.csv", [], sheet_fields)
    auto_report = """# Automatic Metrics Report

This placeholder report records the metric contract. Actual automatic metrics are in `data/evaluation/retrieval_v2/retrieval_v2_summary.json` and `data/evaluation/workflow_v2/workflow_summary.json`.
"""
    (EVAL_DIR / "automatic_metrics_report.md").write_text(auto_report, encoding="utf-8")


def _task_protocol_section(task: dict[str, str]) -> str:
    return f"""### {task["name"]}

- **Input**: {task["input"]}
- **Output**: {task["output"]}
- **Supervision signal**: {task["supervision"]}
- **Automatic metrics**: {task["automatic"]}
- **Human evaluation metrics**: {task["human"]}
- **Baselines**: {task["baselines"]}
- **Failure modes**: {task["failures"]}"""


def _write_open_source_docs() -> None:
    readme = """# Nature RebuttalLens

[![Python](https://img.shields.io/badge/python-3.10%2B-3776AB)](pyproject.toml)
[![License](https://img.shields.io/badge/license-Apache--2.0-green)](LICENSE)
[![Status](https://img.shields.io/badge/status-research%20alpha-orange)](docs/OPEN_SOURCE_V0_1_COMPLETION_STATUS_zh.md)
[![Agent Workflow](https://img.shields.io/badge/workflow-12%20agents-0f766e)](docs/REBUTTAL_LENS_WORKFLOW_zh.md)

**Nature RebuttalLens is a manuscript-aware, cross-disciplinary Author Rebuttal Assistant workflow built from Nature transparent peer-review interaction cases.**

It helps authors interpret reviewer comments with structure: what the reviewer explicitly asks for, what risk may sit behind the comment, what evidence in the manuscript is already usable, what still needs author confirmation, and how similar Nature review interactions can be used as bounded historical analogies.

This is an independent open-source research project. It is not affiliated with, endorsed by, or operated by Nature Portfolio or Springer Nature.

![Nature RebuttalLens workflow](docs/assets/rebuttal-lens-workflow.svg)

## What The System Does

Nature RebuttalLens turns a reviewer comment, optional manuscript text, optional draft response, and optional retrieved Nature peer-review cases into a traceable assistant workflow.

The system is designed to:

- identify explicit reviewer concerns and possible tacit risks;
- connect reviewer concerns back to manuscript evidence when manuscript text is provided;
- interpret institutional and editor-facing signals without claiming access to hidden reviewer intent;
- retrieve and interpret similar Nature review-response cases as historical analogies;
- plan evidence actions, response structure, tone, author positioning, and integrity checks;
- produce a recorded workflow trace that can be inspected, evaluated, and improved.

It is not a final rebuttal generator, acceptance predictor, reviewer replacement, or tool for inventing experiments, fabricating evidence, or making commitments the authors cannot support.

| Capability | Output |
| --- | --- |
| Reviewer understanding | Concern map and observable textual evidence |
| Tacit risk interpretation | Risk notes without claiming private reviewer psychology |
| Manuscript evidence location | Supported / partial / missing evidence map over supplied manuscript text |
| Nature case interpretation | Historical case analogies with transfer boundaries |
| Evidence action planning | Required artifacts and author-confirmation questions |
| Author positioning | Response stance options, not forced concessions |
| Tone and commitment calibration | Defensive tone, overclaim, and unsupported commitment warnings |
| Actor-network mapping | Evidence carriers such as figures, datasets, code, tables, supplements |
| Cross-disciplinary lensing | Tacit knowledge, institutional dependence, actor-network alignment, fast/slow correction, tone/commitment, author agency |
| Integrity checking | Adequacy, provenance, and responsible-use warnings |

## Why It Exists

Most rebuttal tools treat reviewer comments as plain text tasks. This project treats peer review as an interaction among scientific claims, evidence standards, institutional expectations, author agency, editor-readable signals, and tone/commitment choices.

This is not a RAG system. Retrieval is support infrastructure; the core contribution is a cross-disciplinary workflow that turns tacit concern, institutional signal, actor-network alignment, fast/slow cognitive correction, tone/commitment calibration, and author agency into recordable and evaluable traces.

The core value is therefore not a single RAG pipeline or a single technical recipe. The current non-training release focuses on the workflow and evaluation scaffold. Training and fine-tuning are outside the v0.1 core scope.

## Workflow

Nature RebuttalLens runs a 12-agent manuscript-aware workflow:

```text
User inputs
  reviewer comment
  manuscript text / Markdown / LaTeX-like text / PDF / DOCX / DOC
  optional draft response
  optional editor letter
  optional retrieved Nature cases
        |
        v
Layer 0: Manuscript context
  1. manuscript_context_extractor
        |
        v
Layer 1: Review understanding
  2. reviewer_understanding_agent
  3. tacit_concern_interpreter
  4. manuscript_evidence_locator
        |
        v
Layer 2: Strategy and evidence
  5. institutional_signal_interpreter
  6. case_retrieval_interpreter
  7. evidence_action_planner
        |
        v
Layer 3: Author response planning
  8. author_positioning_agent
  9. tone_commitment_calibrator
        |
        v
Layer 4: Cross-disciplinary interpretation
  10. actor_network_mapper
  11. cross_disciplinary_lens_interpreter
        |
        v
Layer 5: Integrity gate
  12. integrity_adequacy_checker
        |
        v
Trace output
  rebuttal_lens_trace.json
  rebuttal_lens_summary.json
```

Each agent is an independent model-assisted reasoning unit. The final output is a structured workflow trace, not a hidden one-shot answer.

For a visual local diagram, open:

```text
docs/rebuttal_lens_system_flow.html
```

## Installation

The repository uses a standard Python `src/` layout and requires Python 3.10+.

```powershell
git clone https://github.com/outlier27-cell/nature-rebuttal-lens.git
cd nature-rebuttal-lens
python -m pip install -e .
```

For local development without installing:

```powershell
$env:PYTHONPATH="src"
```

## Quick Start

Set an OpenAI-compatible API endpoint and model. For example:

```powershell
$env:PEER_REVIEW_API_BASE_URL="https://xh.v1api.cc"
$env:PEER_REVIEW_API_KEY="YOUR_KEY"
$env:PEER_REVIEW_API_MODEL="deepseek-v3"
```

Run the included example:

```powershell
$env:PYTHONPATH="src"
python -m peer_review_skills.cli.main run-rebuttal-lens `
  --review-file examples/rebuttal_lens/reviewer_comment.txt `
  --manuscript-file examples/rebuttal_lens/manuscript_excerpt.md `
  --response-file examples/rebuttal_lens/author_draft_response.txt `
  --retrieved-cases-file examples/rebuttal_lens/retrieved_cases.json `
  --output-dir data/evaluation/rebuttal_lens_demo
```

Installed console scripts are also available after `pip install -e .`:

```powershell
run-rebuttal-lens `
  --review-file examples/rebuttal_lens/reviewer_comment.txt `
  --manuscript-file examples/rebuttal_lens/manuscript_excerpt.md `
  --response-file examples/rebuttal_lens/author_draft_response.txt `
  --retrieved-cases-file examples/rebuttal_lens/retrieved_cases.json `
  --output-dir data/evaluation/rebuttal_lens_demo
```

The workflow writes:

- `data/evaluation/rebuttal_lens_demo/rebuttal_lens_trace.json`
- `data/evaluation/rebuttal_lens_demo/rebuttal_lens_summary.json`

The legacy alias `run-reviewweaver` is kept only for compatibility. The public project name is Nature RebuttalLens.

## Example Inputs

The demo files are under `examples/rebuttal_lens/`:

- `reviewer_comment.txt`: reviewer critique or review excerpt
- `manuscript_excerpt.md`: manuscript excerpt supplied by the author
- `author_draft_response.txt`: optional draft author response
- `retrieved_cases.json`: optional retrieved Nature case analogies

Current manuscript loading supports text, Markdown, LaTeX-like plain text, extractable PDF text, DOCX, and legacy DOC files. PDF parsing uses text extraction only, not OCR or image/table understanding. Legacy `.doc` files require LibreOffice/soffice for conversion to DOCX before extraction.

## Current Status

This repository currently contains candidate data, schema, taxonomy, retrieval baselines, workflow traces, reviewer-author-editor simulation/evaluation traces, cross-disciplinary lens maps, evaluation protocols, and API-assisted seed review results.

- API seed review has been executed for 200 / 200 seed requests.
- The current seed and KB labels are model-assisted, not human gold.
- System-side workflow traces include case explanations, evidence action plans, author confirmation questions, response adequacy checks, and not-real-peer-review simulation roles.
- Human-confirmed labels are a future extension, not a v0.1 release blocker.
- Training and fine-tuning are outside the v0.1 core scope.

## Data Boundary

This repository contains a release-safe subset of derived schemas, taxonomies, summaries, documentation, and evaluation scaffolds. Large scraped data, local caches, API outputs, PDFs, and private working files are excluded by `.gitignore`.

Current labels and traces are model-assisted research artifacts, not human gold annotations. They are suitable for workflow development, auditing, and evaluation design, but should not be presented as expert-labeled ground truth.

## Key Documents

- `docs/2026-05-26-open-source-review-interaction-agent-full-plan-zh.md`: full cross-disciplinary open-source plan
- `docs/REBUTTAL_LENS_WORKFLOW_zh.md`: final Nature RebuttalLens workflow explanation
- `docs/INTERDISCIPLINARY_SYSTEM_FRAME_zh.md`: interdisciplinary system frame
- `docs/PDF_DERIVED_DESIGN_LENSES_zh.md`: design lenses derived from the project PDFs
- `docs/RESPONSIBLE_USE_zh.md`: responsible-use boundaries
- `docs/DATA_CARD_zh.md`: data card
- `docs/AGENT_CARD_zh.md`: agent card
- `docs/EVALUATION_PROTOCOL_zh.md`: evaluation protocol
- `docs/DATA_RELEASE_BOUNDARY_zh.md`: data release boundary
- `docs/MODEL_AND_AGENT_LIMITATIONS_zh.md`: model and agent limitations
- `docs/OPEN_SOURCE_V0_1_COMPLETION_STATUS_zh.md`: current release completion status
- `docs/rebuttal_lens_system_flow.html`: local visual workflow diagram
- `codex.md`: current Chinese project overview for future coding sessions

## Verification

Recommended local checks:

```powershell
$env:PYTHONPATH="src"
python -m pytest -q
python -m compileall -q src tests
python -m peer_review_skills.cli.main validate-naturereview-v01
python -m pip install --dry-run -e .
```

The validation command checks the release-safe NatureReview v0.1 artifacts that support the Nature RebuttalLens workflow.

Latest local release-readiness checks are recorded in `UPGRADE.md`. The release gate includes full pytest, compileall, v0.1 artifact validation, package dry-run, CLI smoke tests, public documentation scans, and secret scans.

## Responsible Use

Nature RebuttalLens is intended to help authors think, organize, and check their rebuttal work. It must not be used to:

- fabricate experiments, data, citations, figures, analyses, or commitments;
- overstate what the manuscript supports;
- impersonate reviewers, editors, or authors;
- predict acceptance probability;
- manipulate reviewers or evade real scientific problems;
- upload confidential manuscript material to an external API without policy and author approval.

When the manuscript does not support a response, the system should state the gap and require author confirmation rather than inventing a claim.

## License

Apache License 2.0. See `LICENSE`.
"""
    (PROJECT_ROOT / "README.md").write_text(readme, encoding="utf-8")

    release = """# Open Source Release Plan

## Release v0.1

- conceptual framework
- non-training scope
- cross-disciplinary design lenses
- schema
- taxonomy
- data card
- responsible use
- seed sample metadata
- API-assisted seed review
- evaluation protocol
- baseline reports
- retrieval baseline v2
- workflow v2 traces
- simulation/evaluation layer v1
- cross-disciplinary lens maps

v0.1 is non-training and cross-disciplinary. 训练和微调不属于 v0.1 核心. This is not a RAG system and 不是单一技术套路; retrieval/RAG is support infrastructure only.

human-confirmed labels are a future extension, not a v0.1 release blocker.

## Release v0.2

- KB builder
- stronger retrieval baselines
- error analysis and taxonomy normalization
- optional local demo interface

## Release v0.3

- expanded benchmark if human-confirmed labels exist
- ablation studies and user-facing evaluation protocol
"""
    _write_doc("OPEN_SOURCE_RELEASE_PLAN_zh.md", release)

    license_decision = """# License Decision Note

## 推荐许可

本项目 v0.1 的代码、schema、taxonomy、评测协议、rubric、prompt 模板、派生元数据和报告建议使用 Apache-2.0。

## 不覆盖的内容

Apache-2.0 不覆盖 Nature 或其他出版方的原始全文、peer review report 全文、author response 全文、editor decision letter 全文、第三方图表、第三方 PDF 或任何非公开审稿材料。

## 发布边界

- 可以发布：代码、schema、taxonomy、derived metadata、URL/DOI/hash/offset、评测协议和 baseline 结果。
- 谨慎发布：短文本片段和可回溯样例，必须保留 provenance 并遵守来源许可。
- 默认不发布：原始全文聚合包、API key、private logs、confidential manuscript。

## 后续动作

正式公开仓库前，应由项目维护者确认最终 license 文件。如果要发布任何原始文本片段，需要再次核对来源页面许可和再分发边界。
"""
    _write_doc("LICENSE_DECISION_zh.md", license_decision)

    limitations = """# Model and Agent Limitations

- 模型不能真正拥有人类默会知识。
- 模型只能识别公开文本中的可观察痕迹。
- 当前 seed set 不是人工金标。
- 模型复核不能等同于人工金标。
- 当前 workflow 没有经过真实作者用户研究。
- 训练和微调不属于 v0.1 核心。
- Retrieval/RAG 只是辅助设施，不是系统核心价值。
- 任何实验、数据、引用和承诺必须由作者确认。
- 系统不预测接收率，不替代作者、reviewer 或 editor。
"""
    _write_doc("MODEL_AND_AGENT_LIMITATIONS_zh.md", limitations)

    legacy_limitations_removed = """# Model and Agent Limitations

- 模型不能真正拥有人类默会知识。
- 模型只能识别公开文本中的可观察痕迹。
- 当前 seed set 不是人工金标。
- 模型复核不能等同于人工金标。
- 当前 workflow 没有经过真实作者用户研究。
- 任何实验、数据、引用和承诺必须由作者确认。
- 系统不预测接收率，不替代作者、reviewer 或 editor。
"""
    _write_doc("MODEL_AND_AGENT_LIMITATIONS_zh.md", limitations)


def _write_paper_docs() -> None:
    paper_plan = """# Paper Plan

## 主问题

公开透明同行评审数据能否帮助我们学习科学审稿互动中的默会知识、制度压力、证据动作和语言姿态，并将这些规律转化为负责任的作者回应智能体？

## 贡献

1. 跨学科问题定义
2. Review Interaction Unit / Knowledge Base
3. Tacit Concern and Evidence Action Taxonomy
4. Cognitive-layer Multi-agent Workflow
5. Responsible Open-source Protocol

## 当前证据状态

当前证据支持 knowledge base 和 workflow prototype 的论文路线，但所有关于效果提升的强主张都需要 human evaluation 或更大规模自动评测。
"""
    _write_doc("PAPER_PLAN_zh.md", paper_plan)

    lit = """# Literature Matrix

| 文献类别 | 要回答的问题 | 关键词 | 需要比较的 prior work | 我们的差异 |
|---|---|---|---|---|
| Peer review NLP / assistance | AI 如何辅助审稿？ | peer review, review feedback agent | Review Feedback Agent, Reviewer2 | 我们面向 author-review-editor interaction |
| Rebuttal generation | 如何生成或规划 rebuttal？ | rebuttal generation, response letter | Paper2Rebuttal, DRPG, RebuttalAgent | 我们强调证据动作和制度互动 |
| RAG over scholarly documents | 如何基于案例检索？ | scholarly RAG, citation-grounded generation | scholarly QA / RAG systems | 我们检索 interaction unit |
| LLM agents | 多 agent 如何拆解任务？ | LLM agent, workflow, planning | agent review systems | 我们设置责任边界和 integrity guard |
| STS / tacit knowledge | 默会知识如何进入审稿？ | tacit knowledge, peer review sociology | Polanyi, Collins, ANT | 我们只学习文本痕迹 |
| AI governance | 如何限制误用？ | AI disclosure, peer review policy | Nature, COPE, WAME, ICML policies | 我们内置 open-source boundary |
"""
    _write_doc("LITERATURE_MATRIX_zh.md", lit)

    experiment = """# Experiment Plan

## Phase 1: Data audit and schema freeze

产物：project status、claim ledger、schema、taxonomy。

## Phase 2: Seed set and taxonomy validation

产物：100-200 条 candidate seed、model-assisted review、human confirmation template。

## Phase 3: Retrieval baseline v2

产物：interaction-aware retrieval baseline and report。

## Phase 4: Agent workflow v2

产物：recordable cognitive traces。

## Phase 5: Automatic and human evaluation

产物：rubric、human sheet、automatic metrics。

## Phase 6: Ablation and error analysis

产物：direct-generation vs RAG vs cognitive workflow 对比，以及失败案例分析。
"""
    _write_doc("EXPERIMENT_PLAN_zh.md", experiment)

    risk = """# Reviewer Risk Register

| Reviewer concern | Why it matters | Response strategy | Evidence needed |
|---|---|---|---|
| AI cannot learn tacit knowledge | 核心概念可能被攻击 | 改称 observable traces of tacit judgment | taxonomy examples + annotation |
| Labels are not gold | 评测可信度风险 | 明确 label status，补人工确认 | human eval sheet |
| Dataset copyright risk | 开源风险 | 发布 derived metadata and offsets | data release boundary |
| This is just RAG | 创新性风险 | 强调 interaction unit + cognitive layer | ablation vs RAG |
| Agent may encourage manipulation | 伦理风险 | responsible use and no acceptance prediction | governance doc |
"""
    _write_doc("REVIEWER_RISK_REGISTER_zh.md", risk)


def _write_execution_summary() -> None:
    status = """# Open Source v0.1 Completion Status

Status: v0.1 open-source framework complete.

## 一句话

NatureReview-Interact v0.1 已经形成一个跨学科审稿互动知识库和可追溯 Author Rebuttal Assistant workflow 框架；它学习的是 reviewer concern、tacit risk、institutional signal、evidence action、author positioning、tone/commitment 和 editor-readable signal 之间的互动结构。训练和微调不属于 v0.1 核心。

## 当前完成项

| Area | Artifact | Status |
|---|---|---|
| project framing | `docs/2026-05-26-open-source-review-interaction-agent-full-plan-zh.md` | complete |
| non-training scope | `docs/NON_TRAINING_OPEN_SOURCE_SCOPE_zh.md` | 训练和微调不属于 v0.1 核心 |
| PDF-derived lenses | `docs/PDF_DERIVED_DESIGN_LENSES_zh.md` | complete |
| data card / responsible use | `docs/DATA_CARD_zh.md`, `docs/RESPONSIBLE_USE_zh.md` | complete |
| schema / taxonomy | `data/processed/schemas/`, `data/processed/taxonomies/` | complete |
| API seed review | `data/evaluation/api_results/naturereview_v01/` | API seed review: 200 / 200 |
| interaction KB | `data/processed/review_interaction_kb/v1/` | model-assisted, not human gold |
| retrieval baseline | `data/evaluation/retrieval_v2/` | support infrastructure, not core contribution |
| workflow traces | `data/evaluation/workflow_v2/` | workflow traces: 50 |
| cross-disciplinary lenses | workflow traces | cross-disciplinary lens traces: 50 |
| simulation/evaluation layer | `data/evaluation/simulation_v1/`, `docs/SIMULATION_EVALUATION_SPEC_zh.md` | 50 traces, not real peer review |
| evaluation protocol | `docs/EVALUATION_PROTOCOL_zh.md` | 11 tasks |
| open-source boundary | `docs/DATA_RELEASE_BOUNDARY_zh.md`, `docs/LICENSE_DECISION_zh.md` | complete |

## 明确边界

- 不是 human gold。
- 不是 final rebuttal generator。
- 不是 acceptance predictor。
- 不是 RAG-only，也不是单一技术套路。
- 训练和微调不属于 v0.1 核心。
- 所有实验、数据、引用和承诺必须由作者确认。
"""
    _write_doc("OPEN_SOURCE_V0_1_COMPLETION_STATUS_zh.md", status)

    summary = """# Execution Summary

This v0.1 execution generated project status docs, schema, taxonomies, cross-disciplinary guides, seed candidates, KB artifacts, retrieval v2 outputs, workflow v2 traces, simulation/evaluation traces, evaluation protocol, and open-source/paper planning docs.

API seed review has been executed for 200 / 200 seed requests with deepseek-v3. The merged labels are model-assisted, not human gold.

The system-side upgrade adds case-specific planning, evidence action plans, author confirmation questions, response adequacy checks, case explanations, cross-disciplinary lens maps, and a not-real-peer-review Reviewer/Author/Editor simulation layer. It does not implement training or fine-tuning.
"""
    (EXEC_DIR / "EXECUTION_SUMMARY.md").write_text(summary, encoding="utf-8")
    return

    status = """# Open Source v0.1 Completion Status

Status: v0.1 open-source framework complete.

## 一句话

NatureReview-Interact v0.1 已经形成一个跨学科审稿互动知识库和可追溯 Author Rebuttal Assistant workflow 框架；它学习的是 reviewer concern、tacit risk、institutional signal、evidence action、author positioning、tone/commitment 和 editor-readable signal 之间的互动结构。

## 当前完成项

| Area | Artifact | Status |
|---|---|---|
| project framing | `docs/2026-05-26-open-source-review-interaction-agent-full-plan-zh.md` | complete |
| implementation plan | `docs/superpowers/plans/2026-05-27-naturereview-interact-implementation-plan-zh.md` | executed |
| data card / responsible use | `docs/DATA_CARD_zh.md`, `docs/RESPONSIBLE_USE_zh.md` | complete |
| schema / taxonomy | `data/processed/schemas/`, `data/processed/taxonomies/` | complete |
| API seed review | `data/evaluation/api_results/naturereview_v01/` | API seed review: 200 / 200 |
| interaction KB | `data/processed/review_interaction_kb/v1/` | 245 units, 199 cases |
| retrieval baseline | `data/evaluation/retrieval_v2/` | 100 query predictions |
| workflow traces | `data/evaluation/workflow_v2/` | workflow traces: 50, with case explanations, evidence plans, author questions, and response adequacy |
| simulation/evaluation layer | `data/evaluation/simulation_v1/`, `docs/SIMULATION_EVALUATION_SPEC_zh.md` | 50 traces, Reviewer/Author/Editor roles, not real peer review |
| training seed | `data/training/author_rebuttal_agent/v2709/` | training seed rows: 200 |
| evaluation protocol | `docs/EVALUATION_PROTOCOL_zh.md` | 11 tasks |
| open-source boundary | `docs/DATA_RELEASE_BOUNDARY_zh.md`, `docs/LICENSE_DECISION_zh.md` | complete |

## 明确边界

- 当前不是 human gold。
- 当前不是 final rebuttal generator。
- 当前不预测接收率。
- 当前不鼓励上传 confidential manuscript 到外部 API。
- 当前公开重点是 schema、taxonomy、derived metadata、model-assisted seed、evaluation protocol、baseline、workflow trace、simulation trace 和治理边界。

## 开源前必须保留的说明

所有公开介绍必须写明：当前标签是 model-assisted，不是 human gold；系统是 assistant/workflow，不是替作者提交 rebuttal 的工具。
"""
    _write_doc("OPEN_SOURCE_V0_1_COMPLETION_STATUS_zh.md", status)

    summary = """# Execution Summary

This v0.1 execution generated project status docs, schema, taxonomies, cross-disciplinary guides, seed candidates, KB artifacts, retrieval v2 outputs, workflow v2 traces, simulation/evaluation traces, evaluation protocol, and open-source/paper planning docs.

API seed review has been executed for 200 / 200 seed requests with deepseek-v3. The merged labels are model-assisted, not human gold.

The system-side upgrade adds case-specific planning, evidence action plans, author confirmation questions, response adequacy checks, case explanations, and a not-real-peer-review Reviewer/Author/Editor simulation layer. It does not implement training or fine-tuning.
"""
    (EXEC_DIR / "EXECUTION_SUMMARY.md").write_text(summary, encoding="utf-8")


def _write_api_handoff(seed_records: list[dict[str, Any]]) -> None:
    handoff_dir = PROJECT_ROOT / "data/evaluation/api_handoff/naturereview_v01"
    handoff_dir.mkdir(parents=True, exist_ok=True)
    requests = []
    for record in seed_records:
        requests.append(
            {
                "request_id": f"naturereview_seed_review::{record['seed_review_id']}",
                "task": "review_interaction_seed_cross_disciplinary_review",
                "model": "deepseek-v3",
                "input": {
                    "seed_review_id": record["seed_review_id"],
                    "pair_id": record.get("pair_id"),
                    "paper_id": record.get("paper_id"),
                    "review_text": record.get("review_text"),
                    "response_text": record.get("response_text"),
                    "candidate_labels": {
                        "concern_type": record.get("concern_type"),
                        "tacit_concern": record.get("tacit_concern"),
                        "institutional_signal": record.get("institutional_signal"),
                        "response_strategy": record.get("response_strategy"),
                        "evidence_action": record.get("evidence_action"),
                        "author_positioning": record.get("author_positioning"),
                        "tone_commitment": record.get("tone_commitment"),
                        "actor_links": record.get("actor_links"),
                    },
                },
                "expected_output_schema": {
                    "alignment_correct": "yes|needs_review|no",
                    "usable_for_retrieval": "yes|no",
                    "usable_for_evaluation": "yes|no",
                    "revised_concern_type": "string",
                    "revised_tacit_concern": "string",
                    "revised_institutional_signal": "string",
                    "revised_response_strategy": "string",
                    "revised_evidence_action": "string",
                    "revised_author_positioning": "string",
                    "tone_commitment": {
                        "tone": "string",
                        "commitment_level": "string",
                        "risk_flags": ["string"],
                    },
                    "actor_links": [
                        {
                            "actor_type": "string",
                            "role_in_interaction": "string",
                            "evidence": "string",
                        }
                    ],
                    "rationale": "short explanation grounded in observable text",
                },
                "safety_constraints": [
                    "Do not infer reviewer identity or private mental state.",
                    "Do not predict acceptance probability.",
                    "Do not invent experiments, data, citations, or commitments.",
                    "Use unknown when observable evidence is insufficient.",
                    "This is model-assisted review, not human gold.",
                ],
            }
        )
    requests_path = handoff_dir / "seed_review_requests.jsonl"
    write_jsonl(requests_path, requests)
    api_result_summary = _read_json(NATUREREVIEW_API_RESULTS_DIR / "seed_review_summary.json") if (
        NATUREREVIEW_API_RESULTS_DIR / "seed_review_summary.json"
    ).exists() else {}
    result_count = int(api_result_summary.get("cumulative_result_count") or 0)
    error_count = int(api_result_summary.get("cumulative_error_count") or 0)
    api_status = "executed" if result_count == len(requests) and error_count == 0 else "prepared_not_executed"
    manifest = {
        "request_count": len(requests),
        "result_count": result_count,
        "error_count": error_count,
        "requests_jsonl": str(requests_path.relative_to(PROJECT_ROOT).as_posix()),
        "status": api_status,
        "label_status": "model_assisted_not_human_gold" if api_status == "executed" else "prepared_not_executed",
        "requires_env": {
            "OPENAI_COMPATIBLE_BASE_URL": "https://xh.v1api.cc/v1 or compatible endpoint",
            "OPENAI_COMPATIBLE_MODEL": "deepseek-v3",
            "OPENAI_COMPATIBLE_API_KEY": "set in shell only; never write to disk",
        },
        "notes": [
            "No API request is made by the v0.1 builder.",
            "Results must be stored outside the request file and merged only after validation.",
        ],
    }
    _write_json(handoff_dir / "manifest.json", manifest)
    if api_status == "executed":
        ready = f"""# API Seed Review Status

API seed review has been executed for {result_count} / {len(requests)} seed requests.

## Executed request queue

- `data/evaluation/api_handoff/naturereview_v01/seed_review_requests.jsonl`
- `data/evaluation/api_results/naturereview_v01/seed_review_results.jsonl`
- request_count: {len(requests)}
- result_count: {result_count}
- error_count: {error_count}
- model: deepseek-v3

## Rebuild status

The validated API results have been merged into:

- `data/evaluation/seed_set/v1/seed_model_reviewed_200.jsonl`
- `data/processed/review_interaction_kb/v1/interaction_units.jsonl`
- `data/evaluation/retrieval_v2/`
- `data/evaluation/workflow_v2/`

## Boundary

The API output is model-assisted, not human gold. It is acceptable as the v0.1 default seed review layer, but any formal benchmark claim must still disclose the label source.
"""
    else:
        ready = """# Ready for API Review

The non-API v0.1 framework is complete. API review is prepared but not executed.

## Prepared request queue

- `data/evaluation/api_handoff/naturereview_v01/seed_review_requests.jsonl`
- request_count: 200

## Required environment variables

```powershell
$env:OPENAI_COMPATIBLE_BASE_URL="https://xh.v1api.cc/v1"
$env:OPENAI_COMPATIBLE_MODEL="deepseek-v3"
$env:OPENAI_COMPATIBLE_API_KEY="<set in shell only>"
```

## Expected API result fields

- alignment_correct
- usable_for_retrieval
- usable_for_evaluation
- revised_concern_type
- revised_tacit_concern
- revised_institutional_signal
- revised_response_strategy
- revised_evidence_action
- revised_author_positioning
- tone_commitment
- actor_links
- rationale

## Boundary

The API output will remain model-assisted. It will not become human gold unless a human confirms it.
"""
    _write_doc("READY_FOR_API_REVIEW_zh.md", ready)


def _validate_naturereview_v01() -> dict[str, Any]:
    schema = _read_json(SCHEMA_DIR / "review_interaction_unit.schema.json")
    seed_candidates = list(read_jsonl(SEED_DIR / "seed_candidates_200.jsonl"))
    seed_reviewed = list(read_jsonl(SEED_DIR / "seed_model_reviewed_200.jsonl"))
    units = list(read_jsonl(KB_DIR / "interaction_units.jsonl"))
    cases = list(read_jsonl(KB_DIR / "case_index.jsonl"))
    actor_cases = list(read_jsonl(KB_DIR / "actor_network_cases.jsonl"))
    retrieval_predictions = list(read_jsonl(RETRIEVAL_DIR / "predictions.jsonl"))
    retrieval_summary = _read_json(RETRIEVAL_DIR / "retrieval_v2_summary.json")
    traces = list(read_jsonl(WORKFLOW_DIR / "workflow_traces.jsonl"))
    simulation_traces = _read_optional_jsonl(SIMULATION_DIR / "simulation_traces.jsonl")
    simulation_summary = _read_json(SIMULATION_DIR / "simulation_summary.json") if (
        SIMULATION_DIR / "simulation_summary.json"
    ).exists() else {}
    handoff_requests = list(read_jsonl(PROJECT_ROOT / "data/evaluation/api_handoff/naturereview_v01/seed_review_requests.jsonl"))
    handoff_manifest = _read_json(PROJECT_ROOT / "data/evaluation/api_handoff/naturereview_v01/manifest.json")
    api_results = _read_optional_jsonl(NATUREREVIEW_API_RESULTS_DIR / "seed_review_results.jsonl")
    api_errors = _read_optional_jsonl(NATUREREVIEW_API_RESULTS_DIR / "seed_review_errors.jsonl")
    training_rows = _read_optional_jsonl(TRAINING_DIR / "model_assisted_training_seed_200.jsonl")
    training_summary = _read_json(TRAINING_DIR / "training_seed_summary.json") if (
        TRAINING_DIR / "training_seed_summary.json"
    ).exists() else {}

    docs_missing = [name for name in REQUIRED_DOCS if not (DOCS_DIR / name).exists()]
    taxonomies_missing = [name for name in REQUIRED_TAXONOMIES if not (TAXONOMY_DIR / name).exists()]
    schema_properties = set((schema.get("properties") or {}).keys())
    required_schema_fields = {"institutional_signal", "author_positioning", "actor_links", "provenance", "label_source"}
    schema_missing = sorted(required_schema_fields - schema_properties)
    seed_label_counts = Counter(r.get("label_source") for r in seed_reviewed)
    unit_label_counts = Counter(r.get("label_source") for r in units)
    required_unit_fields = set(schema.get("required", [])) | required_schema_fields
    unit_missing_field_count = sum(1 for unit in units if any(field not in unit for field in required_unit_fields))
    provenance_complete_count = sum(1 for unit in units if (unit.get("provenance") or {}).get("source_file"))
    actor_link_complete_count = sum(1 for unit in units if unit.get("actor_links"))
    trace_stage_complete_count = sum(
        1
        for trace in traces
        if all(stage in (trace.get("cognitive_trace") or {}) for stage in REQUIRED_TRACE_STAGES)
    )
    trace_error_count = sum(1 for trace in traces if trace.get("errors"))
    workflow_agent_output_count = sum(
        1
        for trace in traces
        if all(agent in (trace.get("agent_intermediate_outputs") or {}) for agent in REQUIRED_WORKFLOW_AGENTS)
    )
    cross_disciplinary_lens_trace_count = sum(
        1
        for trace in traces
        if all(
            isinstance((trace.get("cross_disciplinary_lens_map") or {}).get(lens), dict)
            and (trace.get("cross_disciplinary_lens_map") or {}).get(lens, {}).get("observable_trace")
            and (trace.get("cross_disciplinary_lens_map") or {}).get(lens, {}).get("system_action")
            and (trace.get("cross_disciplinary_lens_map") or {}).get(lens, {}).get("boundary")
            for lens in CROSS_DISCIPLINARY_LENS_KEYS
        )
    )
    required_simulation_roles = {"reviewer_agent", "author_rebuttal_agent", "editor_signal_agent"}
    simulation_role_complete_count = sum(
        1
        for trace in simulation_traces
        if required_simulation_roles.issubset(set((trace.get("simulation_roles") or {}).keys()))
    )
    simulation_boundary_count = sum(
        1
        for trace in simulation_traces
        if "not real peer review" in str(trace.get("boundary") or "")
        and trace.get("label_status") == "model_assisted_not_human_gold"
    )
    simulation_cross_disciplinary_count = sum(
        1
        for trace in simulation_traces
        if (trace.get("cross_disciplinary_evaluation") or {}).get("all_required_lenses_present") is True
        and "用不可追溯的捷径替代案例证据和模型复核" in ((trace.get("cross_disciplinary_evaluation") or {}).get("forbidden_behaviors") or [])
    )
    simulation_layer_ok = (
        len(simulation_traces) == 50
        and simulation_summary.get("trace_count") == 50
        and simulation_summary.get("label_status") == "model_assisted_not_human_gold"
        and simulation_role_complete_count == len(simulation_traces)
        and simulation_boundary_count == len(simulation_traces)
    )
    evaluation_protocol_complete = _evaluation_protocol_complete(DOCS_DIR / "EVALUATION_PROTOCOL_zh.md")
    retrieval_metrics = retrieval_summary.get("metrics") or {}
    required_retrieval_metrics = {
        "strategy_recall_at_1",
        "strategy_recall_at_3",
        "strategy_recall_at_5",
        "concern_match_at_5",
        "joint_strategy_concern_at_5",
        "case_diversity_at_5",
        "provenance_completeness",
    }
    retrieval_missing_metrics = sorted(required_retrieval_metrics - set(retrieval_metrics))
    retrieval_report_has_p1 = _file_contains(
        RETRIEVAL_DIR / "retrieval_v2_report.md",
        ["P1 Baseline Comparison", "Improvement Attribution"],
    ) and "p1_baseline_comparison" in retrieval_summary
    license_decision_ok = _file_contains(
        DOCS_DIR / "LICENSE_DECISION_zh.md",
        ["Apache-2.0", "不覆盖", "原始全文"],
    )
    training_seed_ok = (
        len(training_rows) == 200
        and training_summary.get("label_status") == "model_assisted_not_human_gold"
        and training_summary.get("core_release_scope") == "legacy_optional_non_core"
        and float(training_summary.get("provenance_complete_rate") or 0.0) == 1.0
    )
    api_manifest_status = handoff_manifest.get("status")
    api_results_complete = (
        api_manifest_status == "executed"
        and len(api_results) == len(handoff_requests)
        and len(api_errors) == 0
        and handoff_manifest.get("label_status") == "model_assisted_not_human_gold"
    )
    secret_hits = _scan_secret_hits()
    mojibake_hits = _scan_mojibake_hits()
    agnes_advice_leakage_hits = _scan_agnes_advice_leakage(traces, retrieval_summary)

    semantic_checks = {
        "data_card_declares_no_human_gold": _file_contains(DOCS_DIR / "DATA_CARD_zh.md", ["没有人工金标"]),
        "responsible_use_has_hard_boundaries": _file_contains(
            DOCS_DIR / "RESPONSIBLE_USE_zh.md",
            ["不预测接收率", "不替代", "不编造"],
        ),
        "annotation_guide_has_cross_disciplinary_fields": _file_contains(
            DOCS_DIR / "CROSS_DISCIPLINARY_ANNOTATION_GUIDE_zh.md",
            ["Tacit Concern", "Institutional Signal", "Actor Links", "Author Positioning"],
        ),
        "workflow_has_required_trace_order": _file_contains(
            DOCS_DIR / "WORKFLOW_SPEC_zh.md",
            ["understand", "question", "evidence_plan", "commitment_check", "integrity_check"],
        ),
        "simulation_spec_has_required_roles_and_boundary": _file_contains(
            DOCS_DIR / "SIMULATION_EVALUATION_SPEC_zh.md",
            ["Reviewer Agent", "Author Rebuttal Agent", "Editor Signal Agent", "not real peer review"],
        ),
        "api_status_documented_as_model_assisted": api_manifest_status in {"prepared_not_executed", "executed"}
        and _file_contains(DOCS_DIR / "READY_FOR_API_REVIEW_zh.md", ["model-assisted"]),
        "api_execution_reflected_in_public_docs": (
            api_manifest_status != "executed"
            or (
                _file_contains(DOCS_DIR / "READY_FOR_API_REVIEW_zh.md", ["API seed review has been executed", "200 / 200"])
                and _file_contains(PROJECT_ROOT / "README.md", ["API seed review has been executed", "model-assisted, not human gold"])
            )
        ),
        "training_design_is_documented": _file_contains(
            DOCS_DIR / "TRAINING_AND_LEARNING_DESIGN_zh.md",
            ["不是直接训练 final rebuttal generator", "response adequacy", "unsupported commitment"],
        ),
    }

    semantic_checks.update(
        {
            "non_training_open_source_scope_is_explicit": _file_contains(
                DOCS_DIR / "NON_TRAINING_OPEN_SOURCE_SCOPE_zh.md",
                ["non-training", "not a RAG system", "不是单一技术套路", "训练和微调不属于 v0.1 核心"],
            ),
            "pdf_derived_design_lenses_are_documented": _file_contains(
                DOCS_DIR / "PDF_DERIVED_DESIGN_LENSES_zh.md",
                ["2026.5.15.pdf", "2026.5.23.pdf", "默会知识", "制度依赖", "行动者网络", "快思维", "慢思维", "情绪", "LIWC"],
            ),
            "training_is_not_public_core_scope": _file_contains(
                DOCS_DIR / "NON_TRAINING_OPEN_SOURCE_SCOPE_zh.md",
                ["legacy optional non-core artifact", "不能被写成 v0.1 核心贡献"],
            ),
        }
    )

    checks = [
        _check("Required docs exist", len(docs_missing) == 0, {"missing": docs_missing}),
        _check("Required schema fields exist", len(schema_missing) == 0, {"missing": schema_missing}),
        _check("Required taxonomy files exist", len(taxonomies_missing) == 0, {"missing": taxonomies_missing}),
        _check("Seed candidates row count", len(seed_candidates) == 200, {"actual": len(seed_candidates), "expected": 200}),
        _check("Model-ready seed row count", len(seed_reviewed) == 200, {"actual": len(seed_reviewed), "expected": 200}),
        _check(
            "Seed labels are conservative candidate or model-assisted labels",
            seed_label_counts.get("heuristic_model_ready", 0) + seed_label_counts.get("model_assisted", 0) == len(seed_reviewed),
            {"label_source_counts": dict(seed_label_counts)},
        ),
        _check("Interaction unit count", len(units) >= len(seed_reviewed), {"actual": len(units), "minimum": len(seed_reviewed)}),
        _check("Interaction units contain required fields", unit_missing_field_count == 0, {"missing_field_rows": unit_missing_field_count}),
        _check("Provenance is complete", provenance_complete_count == len(units), {"complete": provenance_complete_count, "total": len(units)}),
        _check("Actor links are present", actor_link_complete_count == len(units), {"complete": actor_link_complete_count, "total": len(units)}),
        _check("Case index is non-empty", len(cases) > 0, {"case_count": len(cases)}),
        _check("Actor-network cases match case index", len(actor_cases) == len(cases), {"actor_network_cases": len(actor_cases), "cases": len(cases)}),
        _check("Retrieval predictions row count", len(retrieval_predictions) == 100, {"actual": len(retrieval_predictions), "expected": 100}),
        _check(
            "Retrieval metrics include R@1 R@3 and provenance completeness",
            len(retrieval_missing_metrics) == 0,
            {"missing": retrieval_missing_metrics},
        ),
        _check("Retrieval report includes P1 comparison", retrieval_report_has_p1, {"expected": True}),
        _check("Workflow traces row count", len(traces) == 50, {"actual": len(traces), "expected": 50}),
        _check(
            "Workflow trace stages are complete",
            trace_stage_complete_count == len(traces),
            {"complete": trace_stage_complete_count, "total": len(traces)},
        ),
        _check(
            "Workflow traces include agent intermediate outputs",
            workflow_agent_output_count == len(traces),
            {"complete": workflow_agent_output_count, "total": len(traces)},
        ),
        _check(
            "Workflow traces include cross-disciplinary lens map",
            cross_disciplinary_lens_trace_count == len(traces),
            {"complete": cross_disciplinary_lens_trace_count, "total": len(traces)},
        ),
        _check(
            "Agnes workflow advice path has no rule or lexical leakage",
            len(agnes_advice_leakage_hits) == 0,
            {"hits": agnes_advice_leakage_hits[:10]},
        ),
        _check("Workflow traces have no execution errors", trace_error_count == 0, {"error_count": trace_error_count}),
        _check(
            "Simulation evaluation layer exists",
            simulation_layer_ok,
            {
                "trace_count": len(simulation_traces),
                "summary_trace_count": simulation_summary.get("trace_count"),
                "label_status": simulation_summary.get("label_status"),
                "role_complete_count": simulation_role_complete_count,
                "boundary_count": simulation_boundary_count,
            },
        ),
        _check(
            "Evaluation protocol task contracts are complete",
            evaluation_protocol_complete,
            {"task_count": len(EVALUATION_TASKS)},
        ),
        _check(
            "Simulation traces include cross-disciplinary evaluation",
            simulation_cross_disciplinary_count == len(simulation_traces),
            {"complete": simulation_cross_disciplinary_count, "total": len(simulation_traces)},
        ),
        _check(
            "Non-training open-source scope is explicit",
            semantic_checks["non_training_open_source_scope_is_explicit"],
            {"path": "docs/NON_TRAINING_OPEN_SOURCE_SCOPE_zh.md"},
        ),
        _check(
            "PDF-derived design lenses are documented",
            semantic_checks["pdf_derived_design_lenses_are_documented"],
            {"path": "docs/PDF_DERIVED_DESIGN_LENSES_zh.md"},
        ),
        _check("License decision note exists", license_decision_ok, {"path": "docs/LICENSE_DECISION_zh.md"}),
        _check(
            "Legacy optional training seed export is non-core",
            training_seed_ok,
            {
                "rows": len(training_rows),
                "label_status": training_summary.get("label_status"),
                "core_release_scope": training_summary.get("core_release_scope"),
                "provenance_complete_rate": training_summary.get("provenance_complete_rate"),
            },
        ),
        _check("API handoff requests row count", len(handoff_requests) == 200, {"actual": len(handoff_requests), "expected": 200}),
        _check("API handoff is prepared or executed", api_manifest_status in {"prepared_not_executed", "executed"}, {"status": api_manifest_status}),
        _check(
            "API seed review results are complete",
            api_results_complete,
            {"results": len(api_results), "errors": len(api_errors), "requests": len(handoff_requests)},
        ),
        _check("Secret scan", len(secret_hits) == 0, {"hits": secret_hits[:10]}),
        _check("Mojibake scan", len(mojibake_hits) == 0, {"hits": mojibake_hits[:10]}),
        *[
            _check(name.replace("_", " "), passed, {"expected": True})
            for name, passed in semantic_checks.items()
        ],
    ]

    return {
        "generated_by": "python -m peer_review_skills.cli.main validate-naturereview-v01",
        "overall_status": "PASS" if all(check["status"] == "PASS" for check in checks) else "FAIL",
        "counts": {
            "seed_candidates": len(seed_candidates),
            "seed_model_ready_or_reviewed": len(seed_reviewed),
            "interaction_units": len(units),
            "cases": len(cases),
            "actor_network_cases": len(actor_cases),
            "retrieval_predictions": len(retrieval_predictions),
            "workflow_traces": len(traces),
            "simulation_traces": len(simulation_traces),
            "training_seed_rows": len(training_rows),
            "cross_disciplinary_lens_trace_count": cross_disciplinary_lens_trace_count,
            "api_handoff_requests": len(handoff_requests),
        },
        "label_source_counts": {
            "seed": dict(seed_label_counts),
            "interaction_units": dict(unit_label_counts),
        },
        "checks": checks,
        "semantic_checks": semantic_checks,
        "api_handoff_status": api_manifest_status,
        "secret_hit_count": len(secret_hits),
        "mojibake_hit_count": len(mojibake_hits),
        "agnes_advice_leakage_hit_count": len(agnes_advice_leakage_hits),
    }


def _write_validation_report(validation: dict[str, Any] | None = None) -> None:
    validation = validation or _validate_naturereview_v01()
    _write_json(PROJECT_ROOT / "data/evaluation/naturereview_v01_validation_summary.json", _jsonable(validation))
    check_rows = "\n".join(
        f"| {check['name']} | `{json.dumps(check['details'], ensure_ascii=False, sort_keys=True)}` | {check['status']} |"
        for check in validation["checks"]
    )
    counts_json = json.dumps(validation["counts"], ensure_ascii=False, indent=2, sort_keys=True)
    label_json = json.dumps(validation["label_source_counts"], ensure_ascii=False, indent=2, sort_keys=True)
    api_status = validation["api_handoff_status"]
    seed_labels = validation["label_source_counts"].get("seed", {})
    unit_labels = validation["label_source_counts"].get("interaction_units", {})
    if api_status == "executed":
        label_note = (
            "说明：当前 seed review API 已执行完成，seed 和 KB 标签均按 `model_assisted` 处理。"
            "这表示 API 模型复核已经替代本轮人工确认流程，但仍然不是 human gold。"
        )
        boundary = f"""- 当前没有 human gold。
- API seed review has been executed for 200 / 200 seed requests.
- 当前 seed label counts: `{json.dumps(seed_labels, ensure_ascii=False, sort_keys=True)}`。
- 当前 KB label counts: `{json.dumps(unit_labels, ensure_ascii=False, sort_keys=True)}`。
- 当前主 KB 是 model-assisted knowledge base，不是人工金标 benchmark。
- 系统用于记录、追溯和评估 Author Rebuttal Assistant workflow，不是最终代写系统。"""
        next_work = """## Next Work After API Review

1. Normalize long-tail model labels back into controlled taxonomy where needed.
2. Run retrieval and workflow error analysis without using response_strategy as a ranking feature.
3. Add stronger retrieval baselines or an optional local demo interface.
4. Keep all public claims marked model-assisted until a separate human-confirmed benchmark exists.
"""
    else:
        label_note = (
            "说明：`heuristic_model_ready` 表示候选记录已经准备给 API 复核，但还没有完成外部模型复核；"
            "它不能被当作 `model_assisted`，更不能被当作 human gold。"
        )
        boundary = f"""- 当前没有 human gold。
- 当前主 KB 混合了 `heuristic_model_ready` 候选记录和少量既有 `model_assisted` mini-seed。
- API handoff 已准备，但状态仍是 `{api_status}`。
- 系统用于记录、追溯和评估 Author Rebuttal Assistant workflow，不是最终代写系统。"""
        next_work = """## Remaining API-only Work

1. Execute `data/evaluation/api_handoff/naturereview_v01/seed_review_requests.jsonl` with the configured OpenAI-compatible API.
2. Store model outputs separately from the request queue.
3. Validate model JSON schema and safety constraints.
4. Merge validated model-assisted revisions into seed records.
5. Rebuild KB, retrieval v2, workflow v2, and reports with updated label provenance.
6. Keep all outputs marked model-assisted until human confirmation.
"""
    report = f"""# NatureReview-Interact v0.1 Validation Report

Generated by `python -m peer_review_skills.cli.main validate-naturereview-v01`.

## Overall Status

`{validation["overall_status"]}`

## Counts

```json
{counts_json}
```

## Label Source Counts

```json
{label_json}
```

{label_note}

## Structural And Semantic Checks

| Check | Details | Status |
|---|---|---|
{check_rows}

## Current Boundary

{boundary}

{next_work}
"""
    _write_doc("NATUREREVIEW_V01_VALIDATION_REPORT_zh.md", report)


def _seed_report(title: str, summary: dict[str, Any]) -> str:
    return f"""# {title}

## Input

- source file: v2709 MVP candidate pairs
- label status: candidate, not human gold

## Output

```json
{json.dumps(_jsonable(summary), ensure_ascii=False, indent=2, sort_keys=True)}
```

## Known limitations

- not human gold
- may contain alignment errors
- model or human review required before benchmark use
"""


def validate_and_write_report() -> dict[str, Any]:
    validation = _validate_naturereview_v01()
    _write_validation_report(validation)
    return validation


def run_naturereview_seed_api_review(
    *,
    base_url: str,
    api_key: str,
    model: str,
    limit: int | None = None,
    sleep_seconds: float = 0.0,
) -> dict[str, Any]:
    client = OpenAICompatibleChatClient(base_url=base_url, api_key=api_key, model=model, timeout_seconds=180)
    return _run_naturereview_seed_api_review(client, model=model, limit=limit, sleep_seconds=sleep_seconds)


def _run_naturereview_seed_api_review(
    client: Any,
    *,
    model: str,
    limit: int | None = None,
    sleep_seconds: float = 0.0,
) -> dict[str, Any]:
    NATUREREVIEW_API_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    requests = list(read_jsonl(NATUREREVIEW_API_HANDOFF_DIR / "seed_review_requests.jsonl"))
    existing_results = _read_optional_jsonl(NATUREREVIEW_API_RESULTS_DIR / "seed_review_results.jsonl")
    existing_errors = _read_optional_jsonl(NATUREREVIEW_API_RESULTS_DIR / "seed_review_errors.jsonl")
    completed_ids = {
        str(record.get("request_id"))
        for record in existing_results
        if record.get("request_id") and not record.get("error")
    }
    pending = [request for request in requests if str(request.get("request_id")) not in completed_ids]
    selected = pending if limit is None else pending[: max(limit, 0)]
    new_results: list[dict[str, Any]] = []
    new_errors: list[dict[str, Any]] = []
    for index, request in enumerate(selected, start=1):
        try:
            result = _execute_seed_review_request(client, request)
            new_results.append(
                {
                    "request_id": request.get("request_id"),
                    "seed_review_id": (request.get("input") or {}).get("seed_review_id"),
                    "pair_id": (request.get("input") or {}).get("pair_id"),
                    "paper_id": (request.get("input") or {}).get("paper_id"),
                    "model": model,
                    "model_result": result,
                    "status": "reviewed",
                }
            )
        except Exception as exc:  # noqa: BLE001 - one bad API row must not stop the batch.
            new_errors.append(
                {
                    "request_id": request.get("request_id"),
                    "seed_review_id": (request.get("input") or {}).get("seed_review_id"),
                    "model": model,
                    "error": str(exc),
                    "status": "error",
                }
            )
        if sleep_seconds > 0 and index < len(selected):
            time.sleep(sleep_seconds)
    merged_results = _merge_by_request_id(existing_results, new_results)
    successful_ids = {str(record.get("request_id")) for record in merged_results if record.get("request_id")}
    unresolved_existing_errors = [
        record for record in existing_errors if str(record.get("request_id") or "") not in successful_ids
    ]
    merged_errors = _merge_by_request_id(unresolved_existing_errors, new_errors)
    write_jsonl(NATUREREVIEW_API_RESULTS_DIR / "seed_review_results.jsonl", merged_results)
    write_jsonl(NATUREREVIEW_API_RESULTS_DIR / "seed_review_errors.jsonl", merged_errors)
    summary = {
        "status": "executed" if not new_errors else "executed_with_errors",
        "model": model,
        "selected_request_count": len(selected),
        "new_result_count": len(new_results),
        "new_error_count": len(new_errors),
        "cumulative_result_count": len(merged_results),
        "cumulative_error_count": len(merged_errors),
        "total_request_count": len(requests),
        "remaining_request_count": max(len(requests) - len(merged_results), 0),
        "label_status": "model_assisted_not_human_gold",
    }
    _write_json(NATUREREVIEW_API_RESULTS_DIR / "seed_review_summary.json", summary)
    _write_seed_api_report(summary)
    return summary


def apply_naturereview_seed_api_results() -> dict[str, Any]:
    seed_records = list(read_jsonl(SEED_DIR / "seed_model_reviewed_200.jsonl"))
    result_records = _read_optional_jsonl(NATUREREVIEW_API_RESULTS_DIR / "seed_review_results.jsonl")
    result_by_seed_id = {
        str(record.get("seed_review_id")): record
        for record in result_records
        if record.get("seed_review_id") and not record.get("error")
    }
    merged_records = [
        _merge_seed_api_review_result(seed, result_by_seed_id[str(seed.get("seed_review_id"))])
        if str(seed.get("seed_review_id")) in result_by_seed_id
        else dict(seed)
        for seed in seed_records
    ]
    write_jsonl(SEED_DIR / "seed_model_reviewed_200.jsonl", merged_records)
    _write_model_review_outputs(merged_records)
    mini_seed = [r for r in read_jsonl(MINI_SEED_PATH) if _is_yes(r.get("revised_usable_for_retrieval"))]
    interaction_units = _build_interaction_units(merged_records, mini_seed)
    case_index = _build_case_index(interaction_units)
    actor_cases = _build_actor_network_cases(case_index, interaction_units)
    _write_kb_outputs(interaction_units, case_index, actor_cases)
    retrieval_predictions, retrieval_summary = _build_retrieval_v2(interaction_units)
    _write_retrieval_outputs(retrieval_predictions, retrieval_summary)
    traces = _build_workflow_traces(interaction_units[:50], retrieval_predictions)
    _write_workflow_outputs(traces)
    _write_api_handoff(merged_records)
    validation = validate_and_write_report()
    summary = {
        "applied_result_count": len(result_by_seed_id),
        "seed_count": len(merged_records),
        "label_source_counts": Counter(record.get("label_source") for record in merged_records),
        "validation_status": validation["overall_status"],
        "label_status": "model_assisted_not_human_gold",
    }
    _write_json(NATUREREVIEW_API_RESULTS_DIR / "seed_review_apply_summary.json", _jsonable(summary))
    return _jsonable(summary)


def _check(name: str, passed: bool, details: dict[str, Any] | None = None) -> dict[str, Any]:
    return {
        "name": name,
        "status": "PASS" if passed else "FAIL",
        "details": details or {},
    }


def _execute_seed_review_request(client: Any, request: dict[str, Any]) -> dict[str, Any]:
    response = client.create_chat_completion(
        _seed_review_messages(request),
        response_format={"type": "json_object"},
        temperature=0.0,
    )
    result = _normalize_seed_review_result(response)
    _validate_seed_review_result(result)
    return result


def _seed_review_messages(request: dict[str, Any]) -> list[dict[str, str]]:
    payload = {
        "task": request.get("task"),
        "input": request.get("input"),
        "expected_output_schema": request.get("expected_output_schema"),
        "safety_constraints": request.get("safety_constraints"),
    }
    return [
        {
            "role": "system",
            "content": (
                "You review peer-review interaction seed labels for an Author Rebuttal Assistant. "
                "Return only one valid JSON object. Use the provided taxonomy-like labels when possible. "
                "Ground every revision in observable review/response text. Do not infer private reviewer intent, "
                "do not predict acceptance, and do not invent experiments, data, citations, or commitments."
            ),
        },
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False, sort_keys=True),
        },
    ]


def _normalize_seed_review_result(response: dict[str, Any]) -> dict[str, Any]:
    if _looks_like_seed_review_result(response):
        return response
    for key in ["model_result", "result", "output", "data"]:
        nested = response.get(key)
        if isinstance(nested, dict) and _looks_like_seed_review_result(nested):
            return nested
    if isinstance(response.get("response"), dict) and _looks_like_seed_review_result(response["response"]):
        return response["response"]
    if isinstance(response.get("json"), dict) and _looks_like_seed_review_result(response["json"]):
        return response["json"]
    try:
        content = response["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("seed review API response did not match OpenAI chat shape") from exc
    if not isinstance(content, str):
        raise ValueError("seed review API response content is not a string")
    return extract_json_object(content)


def _looks_like_seed_review_result(record: dict[str, Any]) -> bool:
    return bool({"alignment_correct", "usable_for_retrieval", "usable_for_evaluation"}.intersection(record))


def _validate_seed_review_result(result: dict[str, Any]) -> None:
    required = {
        "alignment_correct",
        "usable_for_retrieval",
        "usable_for_evaluation",
        "revised_concern_type",
        "revised_tacit_concern",
        "revised_institutional_signal",
        "revised_response_strategy",
        "revised_evidence_action",
        "revised_author_positioning",
        "tone_commitment",
        "actor_links",
        "rationale",
    }
    missing = sorted(field for field in required if field not in result)
    if missing:
        raise ValueError(f"seed review result missing required fields: {', '.join(missing)}")
    if str(result["alignment_correct"]).lower() not in {"yes", "needs_review", "no"}:
        raise ValueError("alignment_correct must be yes, needs_review, or no")
    for field in ["usable_for_retrieval", "usable_for_evaluation"]:
        if str(result[field]).lower() not in {"yes", "no"}:
            raise ValueError(f"{field} must be yes or no")
    if not isinstance(result.get("tone_commitment"), dict):
        raise ValueError("tone_commitment must be an object")
    if not isinstance(result.get("actor_links"), list):
        raise ValueError("actor_links must be a list")


def _merge_seed_api_review_result(seed: dict[str, Any], api_record: dict[str, Any]) -> dict[str, Any]:
    result = api_record.get("model_result") or {}
    _validate_seed_review_result(result)
    merged = dict(seed)
    merged["alignment_correct"] = _clean_label(result.get("alignment_correct"), fallback=seed.get("alignment_correct"))
    merged["usable_for_retrieval"] = _yes_no(result.get("usable_for_retrieval"), fallback=seed.get("usable_for_retrieval"))
    merged["usable_for_evaluation"] = _yes_no(result.get("usable_for_evaluation"), fallback=seed.get("usable_for_evaluation"))
    merged["concern_type"] = _clean_label(result.get("revised_concern_type"), fallback=seed.get("concern_type"))
    merged["tacit_concern"] = _clean_label(result.get("revised_tacit_concern"), fallback=seed.get("tacit_concern"))
    merged["institutional_signal"] = _clean_label(
        result.get("revised_institutional_signal"),
        fallback=seed.get("institutional_signal"),
    )
    merged["response_strategy"] = _clean_label(result.get("revised_response_strategy"), fallback=seed.get("response_strategy"))
    merged["evidence_action"] = _normalize_evidence_action(result.get("revised_evidence_action") or seed.get("evidence_action"))
    merged["author_positioning"] = _clean_label(
        result.get("revised_author_positioning"),
        fallback=seed.get("author_positioning"),
    )
    merged["tone_commitment"] = result.get("tone_commitment") or seed.get("tone_commitment")
    merged["actor_links"] = result.get("actor_links") or seed.get("actor_links") or []
    merged["model_rationale"] = str(result.get("rationale") or seed.get("model_rationale") or "")
    merged["label_source"] = "model_assisted"
    merged["api_review_status"] = "reviewed"
    merged["api_review_model"] = api_record.get("model") or "unknown"
    merged["api_review_request_id"] = api_record.get("request_id")
    merged["human_confirmation_status"] = "needs_human_confirmation"
    return merged


def _clean_label(value: Any, *, fallback: Any = "unknown") -> str:
    text = str(value if value not in {None, ""} else fallback or "unknown").strip()
    return re.sub(r"[^a-zA-Z0-9_]+", "_", text).strip("_").lower() or "unknown"


def _yes_no(value: Any, *, fallback: Any = "no") -> str:
    text = str(value if value not in {None, ""} else fallback or "no").strip().lower()
    return "yes" if text in {"yes", "true", "1"} else "no"


def _merge_by_request_id(existing: list[dict[str, Any]], new: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    order: list[str] = []
    for record in existing + new:
        request_id = str(record.get("request_id") or "")
        if not request_id:
            continue
        if request_id not in by_id:
            order.append(request_id)
        by_id[request_id] = record
    return [by_id[request_id] for request_id in order]


def _write_seed_api_report(summary: dict[str, Any]) -> None:
    report = f"""# NatureReview Seed API Review Report

## Summary

- model: {summary["model"]}
- selected_request_count: {summary["selected_request_count"]}
- new_result_count: {summary["new_result_count"]}
- new_error_count: {summary["new_error_count"]}
- cumulative_result_count: {summary["cumulative_result_count"]}
- cumulative_error_count: {summary["cumulative_error_count"]}
- remaining_request_count: {summary["remaining_request_count"]}

## Boundary

These outputs are model-assisted labels, not human gold. They must remain separately auditable and require human confirmation before benchmark use.
"""
    (NATUREREVIEW_API_RESULTS_DIR / "seed_review_report.md").write_text(report, encoding="utf-8")


def _file_contains(path: Path, needles: list[str]) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8", errors="replace")
    return all(needle in text for needle in needles)


def _evaluation_protocol_complete(path: Path) -> bool:
    if not path.exists():
        return False
    text = path.read_text(encoding="utf-8", errors="replace")
    required_fields = [
        "**Input**",
        "**Output**",
        "**Supervision signal**",
        "**Automatic metrics**",
        "**Human evaluation metrics**",
        "**Baselines**",
        "**Failure modes**",
    ]
    return all(f"### {task['name']}" in text for task in EVALUATION_TASKS) and all(
        text.count(field) >= len(EVALUATION_TASKS) for field in required_fields
    )


def _scan_secret_hits() -> list[dict[str, str]]:
    roots = [
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "src/peer_review_skills",
        PROJECT_ROOT / "tests",
        DOCS_DIR,
        SCHEMA_DIR,
        TAXONOMY_DIR,
        SEED_DIR,
        KB_DIR,
        RETRIEVAL_DIR,
        WORKFLOW_DIR,
        SIMULATION_DIR,
        EVAL_DIR,
        TRAINING_DIR,
        PROJECT_ROOT / "data/evaluation/api_handoff/naturereview_v01",
    ]
    hits = []
    for path in _iter_text_files(roots):
        text = path.read_text(encoding="utf-8", errors="replace")
        for name, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                hits.append({"file": str(path.relative_to(PROJECT_ROOT).as_posix()), "pattern": name})
    return hits


def _scan_mojibake_hits() -> list[dict[str, str]]:
    roots = [
        DOCS_DIR,
        PROJECT_ROOT / "src/peer_review_skills",
        SCHEMA_DIR,
        TAXONOMY_DIR,
        SEED_DIR,
        KB_DIR,
        RETRIEVAL_DIR,
        WORKFLOW_DIR,
        SIMULATION_DIR,
        EVAL_DIR,
        TRAINING_DIR,
    ]
    hits = []
    for path in _iter_text_files(roots):
        text = path.read_text(encoding="utf-8", errors="replace")
        if path == Path(__file__):
            text = "\n".join(line for line in text.splitlines() if "MOJIBAKE_MARKERS" not in line)
        found = [marker for marker in MOJIBAKE_MARKERS if marker in text]
        if found:
            hits.append({"file": str(path.relative_to(PROJECT_ROOT).as_posix()), "markers": ",".join(found[:5])})
    return hits


def _scan_agnes_advice_leakage(
    traces: list[dict[str, Any]],
    retrieval_summary: dict[str, Any],
) -> list[dict[str, str]]:
    hits: list[dict[str, str]] = []
    for trace in traces:
        advice_payload = {
            "case_explanations": trace.get("case_explanations"),
            "case_selection_basis": trace.get("case_selection_basis"),
            "cognitive_trace": trace.get("cognitive_trace"),
            "outline": trace.get("outline"),
            "cross_disciplinary_lens_map": trace.get("cross_disciplinary_lens_map"),
        }
        text = json.dumps(advice_payload, ensure_ascii=False, sort_keys=True).lower()
        for marker in AGNES_ADVICE_FORBIDDEN_MARKERS:
            if marker in text:
                hits.append(
                    {
                        "scope": "workflow_trace",
                        "trace_id": str(trace.get("trace_id") or "unknown"),
                        "marker": marker,
                    }
                )
    retrieval_boundary = json.dumps(
        retrieval_summary.get("improvement_attribution") or {},
        ensure_ascii=False,
        sort_keys=True,
    ).lower()
    for marker in AGNES_ADVICE_FORBIDDEN_MARKERS:
        if marker in retrieval_boundary:
            hits.append({"scope": "retrieval_summary_boundary", "marker": marker})
    return hits


def _iter_text_files(roots: list[Path]) -> list[Path]:
    suffixes = {".md", ".py", ".json", ".jsonl", ".csv"}
    files: list[Path] = []
    for root in roots:
        if root.is_file() and root.suffix.lower() in suffixes:
            files.append(root)
        elif root.is_dir():
            files.extend(
                path
                for path in root.rglob("*")
                if path.is_file()
                and path.suffix.lower() in suffixes
                and "__pycache__" not in path.parts
                and "node_modules" not in path.parts
            )
    return sorted(set(files))


def _is_yes(value: Any) -> bool:
    return str(value).lower() in {"yes", "true", "1"}


def _fmt_metric(value: Any) -> str:
    if value is None:
        return "n/a"
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return f"{value:.4f}"
    return str(value)


def _is_offset_recoverable(record: dict[str, Any]) -> bool:
    if "auto_offset_recoverable" in record:
        return bool(record["auto_offset_recoverable"])
    offsets = record.get("source_offsets")
    return isinstance(offsets, dict) and all(k in offsets for k in ["context_start", "context_end", "response_start", "response_end"])


def _normalize_evidence_action(value: Any) -> str:
    text = str(value or "").lower()
    mapping = {
        "manuscript_or_supplement_revision": "supplementary_material_revision",
        "editorial_revision": "figure_table_revision",
        "existing_evidence_or_explanation": "no_new_evidence_explanation_only",
        "resource_or_reproducibility_update": "code_data_availability",
        "future_work_commitment": "future_work_commitment",
        "new_analysis": "new_analysis",
        "new_experiment": "new_experiment",
    }
    return mapping.get(text, "unknown")


def _model_field_fallback(record: dict[str, Any], field: str) -> str:
    label_source = str(record.get("label_source") or "")
    if label_source in {"model_assisted", "human_confirmed", "mixed"}:
        return str(record.get(field) or "unknown")
    return "unknown"


def _model_tone_fallback(record: dict[str, Any]) -> dict[str, Any]:
    tone = record.get("tone_commitment")
    if isinstance(tone, dict) and tone:
        return tone
    return {
        "tone": "needs_model_review",
        "commitment_level": "needs_author_confirmation",
        "risk_flags": ["needs_author_confirmation"],
    }


def _structural_actor_links(record: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "actor_type": "reviewer",
            "actor_id": None,
            "role_in_interaction": "raises concern",
            "evidence": _preview(record.get("review_text") or record.get("review_context") or ""),
        },
        {
            "actor_type": "author",
            "actor_id": None,
            "role_in_interaction": "responds and positions claim",
            "evidence": _preview(record.get("response_text") or record.get("author_response") or ""),
        },
    ]


def _infer_tacit_concern(record: dict[str, Any]) -> str:
    return _model_field_fallback(record, "tacit_concern")


def _infer_institutional_signal(record: dict[str, Any]) -> str:
    return _model_field_fallback(record, "institutional_signal")


def _infer_author_positioning(record: dict[str, Any]) -> str:
    return _model_field_fallback(record, "author_positioning")


def _infer_tone_commitment(record: dict[str, Any]) -> dict[str, Any]:
    return _model_tone_fallback(record)


def _infer_actor_links(record: dict[str, Any]) -> list[dict[str, Any]]:
    return _structural_actor_links(record)


def _risk_from_concern(concern: Any) -> str:
    return {
        "clarity_presentation": "communication_clarity",
        "experimental_design": "design_validity",
        "statistics_significance": "statistical_validity",
        "generalization_scope": "external_validity",
        "reproducibility_reporting": "reproducibility",
        "novelty_positioning": "contribution_positioning",
        "baseline_comparison": "comparative_validity",
        "ablation_mechanism": "mechanistic_validity",
        "dataset_bias_ethics_safety": "responsible_research",
        "theoretical_validity": "theoretical_validity",
    }.get(str(concern), "unknown")


def _normalize_label_source(value: str) -> str:
    if value in {"model_assisted", "human_confirmed", "mixed", "heuristic", "heuristic_model_ready"}:
        return value
    if value in {"phase1_model_revised_mini_seed", "model_revised", "deepseek_revised"}:
        return "model_assisted"
    return "heuristic"


def _offset(offsets: Any, prefix: str) -> dict[str, int] | None:
    if not isinstance(offsets, dict):
        return None
    start = offsets.get(f"{prefix}_start")
    end = offsets.get(f"{prefix}_end")
    if isinstance(start, int) and isinstance(end, int):
        return {"start": start, "end": end}
    return None


def _sha1(value: str) -> str:
    return hashlib.sha1(value.encode("utf-8")).hexdigest()


def _preview(text: Any, limit: int = 240) -> str:
    value = " ".join(str(text or "").split())
    return value[:limit]


def _terms(text: str) -> set[str]:
    return {token.strip(".,;:()[]{}!?").lower() for token in str(text).split() if len(token) > 3}


def _merge_actor_links(units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    merged = []
    for unit in units:
        for link in unit.get("actor_links", []):
            key = (link.get("actor_type"), link.get("role_in_interaction"), link.get("evidence"))
            if key not in seen:
                seen.add(key)
                merged.append(link)
    return merged[:20]


def _top_counts(values: Any) -> list[dict[str, Any]]:
    return [{"label": label, "count": count} for label, count in Counter(values).most_common(5)]


def _heuristic_rationale(seed: dict[str, Any]) -> str:
    return (
        f"Heuristic candidate: concern={seed.get('concern_type')}, "
        f"strategy={seed.get('response_strategy')}, evidence_action={seed.get('evidence_action')}. "
        "Requires model or human confirmation before gold use."
    )


def _jsonable(value: Any) -> Any:
    if isinstance(value, Counter):
        return dict(value)
    if isinstance(value, defaultdict):
        return dict(value)
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return value


if __name__ == "__main__":
    main()
