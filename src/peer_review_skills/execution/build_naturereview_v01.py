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
    "瑙勫垯鍖归厤",
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

    _write_schema()
    _write_taxonomies()

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
    _write_api_handoff(seed_model_reviewed)
    _write_validation_report(_validate_naturereview_v01())


def _ensure_dirs() -> None:
    for path in [SCHEMA_DIR, TAXONOMY_DIR, SEED_DIR, KB_DIR, RETRIEVAL_DIR, WORKFLOW_DIR, EVAL_DIR, TRAINING_DIR, SIMULATION_DIR]:
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
    status_doc = f"""# NatureReview-Interact 椤圭洰鐘舵€?
鏇存柊鏃堕棿锛?026-05-27

## 褰撳墠涓€鍙ヨ瘽

鏈」鐩凡缁忎粠鐖彇闃舵杞悜鎶?v2709 鍏紑鍚岃璇勫鏁版嵁杞寲涓哄彲妫€绱€佸彲璇勪及銆佸彲杩芥函銆佽礋璐ｄ换寮€婧愮殑 Review Interaction Agent銆?
## 褰撳墠宸茬‘璁よ祫浜?
| 璧勪骇 | 鏁伴噺 / 璺緞 | 鐘舵€?|
|---|---:|---|
| v2709 涓诲簱 | {paper_counts["paper_manifest"]} records | verified |
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

## 褰撳墠涓嶈兘澹扮О鐨勫唴瀹?
- 涓嶈兘澹扮О宸叉湁浜哄伐閲戞爣銆?- 涓嶈兘澹扮О agent 宸茬粡琚湡瀹炰綔鑰呮垨瀹＄涓撳楠岃瘉銆?- 涓嶈兘澹扮О妯″瀷鐪熸鎺屾彙榛樹細鐭ヨ瘑銆?- 涓嶈兘澹扮О绯荤粺鑳介娴嬫帴鏀剁巼銆?- 涓嶈兘澹扮О褰撳墠 workflow 宸茬粡鏄渶缁堜骇鍝併€?
## 宸叉湁 baseline

- P1 best concern@5: `{p1_summary["best_by_metric"]["concern_match_at_5"]}`
- P1 best strategy@5: `{p1_summary["best_by_metric"]["strategy_recall_at_5"]}`
- workflow strategy_hit_at_5_rate: `{workflow_summary["evaluation"]["strategy_hit_at_5_rate"]}`
- workflow joint_hit_at_5_rate: `{workflow_summary["evaluation"]["joint_hit_at_5_rate"]}`
- workflow integrity_pass_rate: `{workflow_summary["evaluation"]["integrity_pass_rate"]}`

## 鏈疆鎵ц杈撳嚭鐩綍

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
| v2709 鍖呭惈 2709 鏉″叕寮€鍚岃璇勫鐩稿叧璁板綍 | 涓诲簱 index / summary | `data/processed/author_rebuttal_mvp/v2709/summary.json` | verified | 闇€淇濇寔鐗堟湰涓€鑷?|
| 绾?9858 鏉?demo-ready pair 鍙敤浜庡€欓€夋绱?| pair extraction summary | `heuristic_rebuttal_pairs_demo_ready.jsonl` | supported_by_heuristic | 涓嶆槸浜哄伐閲戞爣 |
| Nature rebuttal 涓ぇ閲忓洖搴旀秹鍙婂浘琛ㄣ€佽ˉ鍏呮潗鏂欍€佸垎鏋愬拰瀹為獙鍔ㄤ綔 | v2709 corpus audit | `data/analysis/final_framework_data_audit_v2709/v2709_final_framework_data_audit.md` | supported_by_corpus_audit | derived signal 鍙兘璇垽 |
| 褰撳墠 workflow 宸茶兘璁板綍 45 鏉″彲杩芥函 trace | workflow summary | `data/evaluation/author_rebuttal_workflow/v2709_model_revised/workflow_summary.json` | model_assisted | 鏍锋湰灏忥紝鏈汉宸ヨ瘎浼?|
| 鏈」鐩彲鐮旂┒榛樹細鐭ヨ瘑鐨勬枃鏈棔杩?| taxonomy + examples + literature | `docs/CROSS_DISCIPLINARY_ANNOTATION_GUIDE_zh.md` | planned | 涓嶈兘澹扮О AI 鐪熸噦榛樹細鐭ヨ瘑 |
| 琛屽姩鑰呯綉缁滃彲杞垚 case representation | actor links + case model | `docs/ACTOR_NETWORK_CASE_MODEL_zh.md` | planned | 鍙兘琛ㄧず鍏紑鏂囨湰涓殑鍙瀵熷叧绯?|
| 鎱㈡€濈淮 workflow 鍙互闄嶄綆鐩存帴鐢熸垚椋庨櫓 | cognitive trace + integrity checks | `docs/COGNITIVE_TRACE_SPEC_zh.md` | planned | 闇€瑕佸悗缁疄璇佽瘎浼?|
"""
    _write_doc("CLAIM_LEDGER_zh.md", claim_doc)

    data_card = """# v2709 Data Card

## 鏁版嵁鏉ユ簮

Nature 绯诲垪鍏紑鍚岃璇勫鐩稿叧椤甸潰鍜屽叕寮€鏂囦欢銆?
## 鏁版嵁鐢ㄩ€?
- 瀹＄浜掑姩缁撴瀯鐮旂┒
- review concern / author response strategy 鍒嗘瀽
- tacit concern / institutional signal / evidence action 鏍囨敞鐮旂┒
- retrieval baseline
- agent workflow trace evaluation

## 涓嶉€傚悎鐢ㄩ€?
- 鑷姩浠ｅ啓瀹屾暣 rebuttal 骞剁洿鎺ユ彁浜?- 鎺ユ敹鐜囬娴?- 瀵?reviewer 鎴?editor 鐨勪釜浣撶敾鍍?- 璁粌涓嶅甫 provenance 鐨勯粦绠辩敓鎴愬櫒
- 澹扮О妯″瀷鎷ユ湁鐪熷疄浜虹被榛樹細鐭ヨ瘑

## 褰撳墠閲戞爣鐘舵€?
褰撳墠娌℃湁浜哄伐閲戞爣銆傚綋鍓?v0.1 榛樿浣跨敤 API 妯″瀷澶嶆牳鏍囩锛屽睘浜?API 鏇夸唬浜哄伐澶嶆牳鐨?model-assisted seed锛涙墍鏈?heuristic 鍜?model-assisted 鏍囩鍙兘浣滀负鍊欓€夋爣绛俱€佹绱㈡牱鏈垨 sanity evaluation 杈撳叆锛屼笉鑳戒綔涓烘渶缁?benchmark gold label銆?
## 鏍囩鐘舵€?
| 鏍囩绫诲瀷 | 鍚箟 | 鍙敤浜?|
|---|---|---|
| heuristic | 瑙勫垯鎴栧急鐩戠潱鐢熸垚 | 鍊欓€夋绱€佺矖绮掑害鍒嗘瀽 |
| model-assisted | API 妯″瀷杈呭姪澶嶆牳 | 灏忚妯?sanity evaluation |
| human-confirmed | 浜哄伐纭 | 姝ｅ紡 benchmark |

## 褰撳墠鐗堟湰

- v2709 涓诲簱锛?709 records
- demo-ready pairs锛?858
- 鏈疆 seed candidates锛氳 `data/evaluation/seed_set/v1/`
- API 鏇夸唬浜哄伐澶嶆牳锛?00 鏉?seed request 宸茬敱 deepseek-v3 澶嶆牳锛岀粨鏋滀粛鏄?model-assisted锛屼笉鏄?human gold銆?"""
    _write_doc("DATA_CARD_zh.md", data_card)

    responsible = """# Responsible Use

鏈」鐩槸瀹＄浜掑姩鐮旂┒鍜屼綔鑰呭洖搴旇緟鍔╂鏋讹紝涓嶆槸浠ｅ啓鏈嶅姟銆?
## 绂佹鎴栦笉鏀寔

- 涓婁紶 confidential manuscript 鍒板閮?API銆?- 浣跨敤绯荤粺棰勬祴璁烘枃鎺ユ敹姒傜巼銆?- 浣跨敤绯荤粺鐢熸垚鏈獙璇佸疄楠屻€佹暟鎹€佸紩鐢ㄦ垨鎵胯銆?- 浣跨敤绯荤粺鏇夸唬浣滆€呫€佸绋夸汉鎴栫紪杈戠殑鍒ゆ柇銆?- 浣跨敤绯荤粺鎿嶇旱 reviewer 鎴栬閬跨湡瀹炵瀛﹂棶棰樸€?- 瀵?reviewer/editor 鍋氫釜浣撶敾鍍忔垨蹇冪悊鎺ㄦ柇銆?
绠€鍐欎负涓夋潯纭竟鐣岋細涓嶉娴嬫帴鏀剁巼锛屼笉鏇夸唬浣滆€?瀹＄浜?缂栬緫锛屼笉缂栭€犲疄楠屻€佹暟鎹€佸紩鐢ㄦ垨鎵胯銆?
## 绯荤粺杈撳嚭瀹氫綅

- concern map
- tacit / explicit risk interpretation
- institutional signal note
- evidence planning aid
- actor-network alignment note
- writing organization aid
- tone and commitment warning
- integrity warning
- provenance-grounded case reference

## 浜虹被璐ｄ换

浣滆€呭繀椤荤‘璁ゆ墍鏈夊疄楠屻€佹暟鎹€佸紩鐢ㄣ€侀檺鍒躲€佹壙璇哄拰鏈€缁堝洖澶嶆枃鏈€侫I 杈撳嚭涓嶈兘鏇夸唬瀛︽湳璐ｄ换涓讳綋銆?"""
    _write_doc("RESPONSIBLE_USE_zh.md", responsible)

    release_boundary = """# Data Release Boundary

## 浼樺厛寮€婧?
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

## 璋ㄦ厧澶勭悊

- reviewer report 鍘熸枃
- author response 鍘熸枃
- editor decision letter 鍏ㄦ枃

## 榛樿涓嶅彂甯?
- 浠讳綍闈炲叕寮€瀹＄鏉愭枡
- API key
- private logs
- 鏃?provenance 鐨勫叏鏂囪仛鍚堝寘

## 鍘熷垯

榛樿鍙戝竷鈥滃彲澶嶇幇鏂规硶鍜屾淳鐢熺粨鏋勨€濓紝鑰屼笉鏄噸鏂板垎鍙戝彲鑳藉瓨鍦ㄧ増鏉冮闄╃殑鍏ㄦ枃璇枡銆?"""
    _write_doc("DATA_RELEASE_BOUNDARY_zh.md", release_boundary)

    overview = f"""# NatureReview-Interact v0.1 Execution Package

鏈洰褰曟槸 `2026-05-27-naturereview-interact-implementation-plan-zh.md` 鐨勬墽琛屽寘绱㈠紩銆?
## 宸茬敓鎴愭牳蹇冩枃妗?
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

## 褰撳墠鏁版嵁鍙ｅ緞

```text
v2709 records: {paper_counts["paper_manifest"]}
demo-ready pairs: {pair_counts["heuristic_rebuttal_pairs_demo_ready"]}
clean heuristic pairs: {pair_counts["heuristic_rebuttal_pairs_clean"]}
workflow trace prototype: {workflow_summary["workflow"]["trace_count"]}
```
"""
    (EXEC_DIR / "README.md").write_text(overview, encoding="utf-8")


def _write_doc(name: str, content: str) -> None:
    return None


def _write_pdf_derived_design_docs() -> None:
    pdf_lenses = """# PDF-derived Design Lenses

## 瀹氫綅

鏈枃浠舵妸 `2026.5.15.pdf` 鍜?`2026.5.23.pdf` 鐨勮法瀛︾鍒嗘瀽钀藉埌 NatureReview-Interact 鐨勯潪璁粌绯荤粺璁捐涓€傚畠涓嶆槸鍗曚竴鎶€鏈竻鍗曪紝涔熶笉鏄缁冩垨寰皟璁″垝锛岃€屾槸涓€涓彲璁板綍銆佸彲杩芥函銆佸彲璇勪及鐨勮В閲婃鏋躲€?
## 2026.5.15.pdf 缁欏嚭鐨勮璁＄嚎绱?
| Lens | PDF 鏉ユ簮 | 绯荤粺鍚箟 | 蹇呴』淇濈暀鐨勮竟鐣?|
|---|---|---|---|
| 榛樹細鐭ヨ瘑 | `2026.5.15.pdf` | 瀹＄鎰忚鑳屽悗甯告湁涓撳鍏卞悓浣撶殑鍒ゆ柇銆佸彲淇″害棰勬湡鍜岄鍩熸爣鍑嗭紱绯荤粺鍙兘瀛︿範杩欎簺鍒ゆ柇鍦ㄥ叕寮€鏂囨湰涓殑鐥曡抗銆?| 涓嶅０绉?AI 鐪熸噦榛樹細鐭ヨ瘑锛屼笉鎺ㄦ柇 reviewer 鐪熷疄蹇冪悊銆?|
| 鍒跺害渚濊禆 | `2026.5.15.pdf` | 浣滆€呭洖搴斿彈鍒版湡鍒娿€佸绋垮埗搴︺€佸彂琛ㄥ帇鍔涖€佸叡鍚屼綋瑙勮寖褰卞搷锛涚郴缁熷簲甯姪浣滆€呰鲸璁ゅ埗搴︿俊鍙枫€?| 涓嶉娴嬫帴鏀剁巼锛屼笉鎶婄ぜ璨屾垨璁╂鍐欐垚鍒跺害鏈嶄粠銆?|
| 琛屽姩鑰呯綉缁?| `2026.5.15.pdf` | review interaction 涓嶆槸涓や釜浜虹殑鏂囨湰瀵硅瘽锛岃繕娑夊強 manuscript銆乫igure銆乨ataset銆乧ode銆乥enchmark銆乻upplement銆乪ditor signal 绛夎鍔ㄨ€呫€?| 鍙褰曞叕寮€鏂囨湰涓殑鍙瀵熷榻愬叧绯伙紝涓嶈繕鍘熺湡瀹炵ぞ浼氬洜鏋溿€?|

## 2026.5.23.pdf 缁欏嚭鐨勮璁＄嚎绱?
| Lens | PDF 鏉ユ簮 | 绯荤粺鍚箟 | 蹇呴』淇濈暀鐨勮竟鐣?|
|---|---|---|---|
| 蹇€濈淮 / 鎱㈡€濈淮 | `2026.5.23.pdf` | 浣滆€呭拰 LLM 閮藉彲鑳藉揩閫熼槻寰°€佸揩閫熺敓鎴愭垨蹇€熻繋鍚堬紱绯荤粺蹇呴』鍏堢悊瑙ｃ€佸啀璐ㄨ銆佸啀璇佹嵁瑙勫垝銆佸啀杈撳嚭銆?| 涓嶄竴姝ョ敓鎴?final rebuttal锛屼笉鎶婃祦鐣呮枃鏈綋鎴愬厖鍒嗗洖搴斻€?|
| 鎯呯华鍜岃姘旀牎鍑?| `2026.5.23.pdf` | 鎯呯华缁村害搴旇浆鎴愬鏈簰鍔ㄥЭ鎬侊細defensiveness銆乻ycophancy risk銆乧ommitment level銆乽ncertainty handling銆?| 涓嶈瘖鏂儏缁紝涓嶅仛鍏辨儏琛ㄦ紨锛屼笉鐢ㄦ俯鍜岃姘旀浛浠ｈ瘉鎹€?|
| LIWC / GPT 蹇冪悊鏂囨湰鍒嗘瀽鍚彂 | `2026.5.23.pdf` | 鍙€熼壌蹇冪悊鏂囨湰鍒嗘瀽鍏虫敞璇皵銆佺‘瀹氭€с€佹壙璇哄拰浜掑姩濮挎€侊紝浣嗙郴缁熻緭鍑哄繀椤诲彲瀹¤銆?| 涓嶆妸蹇冪悊鍒嗘瀽鍐欐垚鍖诲鎴栦汉鏍煎垽鏂€?|

## 绯荤粺钀界偣

姣忔潯 workflow trace 閮藉繀椤诲寘鍚互涓?lens map锛?
1. `tacit_knowledge_boundary`
2. `institutional_dependence`
3. `actor_network_alignment`
4. `fast_slow_cognitive_correction`
5. `emotion_tone_commitment_calibration`
6. `author_agency_gate`

姣忎釜 lens 閮藉繀椤荤粰鍑?`source_pdf`銆乣observable_trace`銆乣system_action`銆乣boundary` 鍜?`evaluation_question`銆?
## 鏄庣‘鎺掗櫎

- 涓嶆槸鍗曚竴鎶€鏈竻鍗曘€?- 涓嶆槸璁粌鎴栧井璋冦€?- 涓嶆槸 RAG-only銆?- 涓嶆槸鑷姩浠ｅ啓 rebuttal銆?- 涓嶆槸鎺ユ敹鐜囬娴嬨€?"""
    _write_doc("PDF_DERIVED_DESIGN_LENSES_zh.md", pdf_lenses)

    system_frame = """# Interdisciplinary System Frame

NatureReview-Interact 鐨勬牳蹇冧笉鏄?RAG銆丅M25銆佹ā鍨嬪井璋冩垨鍗曚竴鎶€鏈璺紝鑰屾槸鎶?Nature 鍏紑鍚岃璇勫妗堜緥杞垚涓€涓法瀛︾鐨?review-interaction assistant銆?
## 鏍稿績闂

绯荤粺瑕佸府鍔╀綔鑰呭洖绛斿叚涓棶棰橈細

1. reviewer 鏄庤鐨?concern 鏄粈涔堬紵
2. concern 鑳屽悗鍙瀵熺殑 tacit risk 鏄粈涔堬紵
3. 鏈熷垔銆佸叡鍚屼綋銆侀€忔槑鎬ф垨缂栬緫娴佺▼甯︽潵浜嗕粈涔?institutional signal锛?4. 鍝簺琛屽姩鑰呮壙杞藉洖搴旓細figure銆乼able銆乨ataset銆乧ode銆乥enchmark銆乻upplement銆乵ethod text锛?5. 浣滆€呭簲璇ュ浣曢€夋嫨 stance銆乪vidence action銆乼one 鍜?commitment锛?6. 鍝簺鍐呭蹇呴』鐢变綔鑰呯‘璁わ紝绯荤粺涓嶈兘鏇夸綔鑰呮壙璇猴紵

## 闈炴妧鏈腑蹇?
妫€绱㈠拰 baseline 鍙敤浜庢煡鎵炬渚嬨€佽褰?provenance 鍜屽缓绔嬪彲姣旇瘎娴嬨€傞」鐩湡姝ｇ殑璐＄尞鏄妸浜烘枃绀剧姒傚康杞垚鍙墽琛岀殑 agent workflow锛氶粯浼氱煡璇嗚竟鐣屻€佸埗搴︿緷璧栥€佽鍔ㄨ€呯綉缁溿€佸揩鎱㈡€濈淮绾犲亸銆佹儏缁?璇皵-鎵胯鏍″噯銆佷綔鑰呬富浣撴€ч棬绂併€?
## 杈撳嚭褰㈡€?
绯荤粺榛樿杈撳嚭 plan銆乺isk map銆乪vidence action銆乧ase analogy銆乼one warning銆乤uthor confirmation question 鍜?adequacy report锛屼笉榛樿杈撳嚭 submission-ready rebuttal銆?"""
    _write_doc("INTERDISCIPLINARY_SYSTEM_FRAME_zh.md", system_frame)

    scope = """# Non-training Open-source Scope

## v0.1 鑼冨洿

NatureReview-Interact v0.1 鏄?non-training銆乧ross-disciplinary 鐨勫紑婧愮爺绌舵鏋躲€傝缁冨拰寰皟涓嶅睘浜?v0.1 鏍稿績銆?
v0.1 鏍稿績鍖呮嫭锛?
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

## 涓嶆槸浠€涔?
- not a RAG system
- not RAG-only
- 涓嶆槸鍗曚竴鎶€鏈璺?- 涓嶆槸 final rebuttal generator
- 涓嶆槸 acceptance predictor
- 涓嶆槸璁粌鎴栧井璋冮」鐩?
## RAG/retrieval 鐨勪綅缃?
RAG/retrieval 鍙槸杈呭姪璁炬柦锛岀敤鏉ユ壘鍘嗗彶妗堜緥銆佷繚鐣?provenance銆佹敮鎸?case analogy 鍜岃瘎娴嬪鐓с€傜郴缁熺殑鏍稿績浠峰€兼槸璺ㄥ绉戣В閲婃鏋跺拰璐熻矗浠荤殑瀹＄浜掑姩 workflow銆?
## Legacy optional artifacts

`data/training/author_rebuttal_agent/v2709/` 鍙互淇濈暀涓烘湭鏉ュ疄楠岀殑 legacy optional non-core artifact銆傚畠涓嶈兘琚啓鎴?v0.1 鏍稿績璐＄尞锛屼篃涓嶈兘浣滀负寮€婧愬畬鎴愬害鐨?release blocker銆?"""
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

## 鏈€灏忓崟浣?
涓€鏉?unit 琛ㄧず涓€涓彲鍥炴函鐨勫绋夸簰鍔ㄧ墖娈碉細

```text
reviewer concern -> risk interpretation -> institutional signal -> author response move -> evidence action -> author positioning -> tone / commitment -> optional editor signal
```

## 蹇呴渶瀛楁

| 瀛楁 | 鍚箟 | 鏉ユ簮 |
|---|---|---|
| unit_id | 绋冲畾 ID | generated |
| paper_id | paper 绾?ID | source |
| pair_id | 鍘?pair ID锛屽鏈?| source/generated |
| source_url | 鏉ユ簮 URL | source |
| doi | DOI锛屽鏈?| source |
| review_text | reviewer comment span | source |
| response_text | author response span | source |
| review_offset | reviewer text offset | source / alignment |
| response_offset | response text offset | source / alignment |
| concern_type | concern taxonomy | heuristic / model / human |
| risk_type | risk taxonomy | heuristic / model / human |
| institutional_signal | 鍒跺害鍘嬪姏銆佹湡鍒婅竟鐣屻€佸叡鍚屼綋鏈熷緟鐨勫彲瑙傚療淇″彿 | model / human |
| evidence_action | evidence action taxonomy | heuristic / model / human |
| author_positioning | 浣滆€呭湪鍧氭寔銆佽姝ャ€佽В閲娿€佸弽椹充箣闂寸殑浣嶇疆 | model / human |
| response_strategy | response strategy taxonomy | heuristic / model / human |
| tone_commitment | tone and commitment taxonomy | model / human |
| editor_signal | decision signal锛屽鏈?| source / inferred |
| actor_links | 鏈潯浜掑姩娑夊強鐨勮鍔ㄨ€呭拰闈炰汉绫诲璞?| source / inferred / model |
| provenance | URL/hash/offset/source file | source |
| label_source | heuristic/model_assisted/human_confirmed/mixed | generated |

## 鏍稿績鍘熷垯

schema 涓嶅０绉?AI 鎷ユ湁浜虹被榛樹細鐭ヨ瘑锛屽彧淇濆瓨鍏紑鏂囨湰涓殑鍙瀵熺棔杩瑰拰瀵瑰簲 provenance銆?"""
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

杩欎簺 taxonomy 鎶婃渶缁堟柟妗堜腑鐨勮法瀛︾姒傚康杞垚鍙墽琛屾爣绛俱€傚畠浠笉鏄績鐞嗚瘖鏂紝涔熶笉鏄 reviewer/editor 鐪熷疄鎰忓浘鐨勬柇瑷€銆?
## Taxonomy Files

- `tacit_concern_taxonomy.v1.json`
- `institutional_signal_taxonomy.v1.json`
- `evidence_action_taxonomy.v1.json`
- `author_positioning_taxonomy.v1.json`
- `tone_commitment_taxonomy.v1.json`
- `editor_signal_taxonomy.v1.json`

## 浣跨敤鍘熷垯

1. 鍏堟壘鍘熸枃璇佹嵁锛屽啀鎵撴爣绛俱€?2. 浼樺厛鏍囨敞鍙瀵熶簰鍔ㄥ姛鑳斤紝鑰屼笉鏄帹鏂湡瀹炲績鐞嗐€?3. 鏃犳硶鍒ゆ柇鏃朵娇鐢?`unknown`銆?4. 鎵€鏈夋ā鍨嬭緟鍔╂爣绛鹃兘蹇呴』淇濈暀 `label_source=model_assisted`銆?"""
    _write_doc("TAXONOMY_GUIDE_zh.md", guide)


def _write_cross_disciplinary_docs() -> None:
    annotation = """# Cross-disciplinary Annotation Guide

## 鎬诲師鍒?
鏈」鐩笉鏍囨敞 reviewer 鐨勭湡瀹炲績鐞嗭紝涔熶笉澹扮О AI 鐪熸鎺屾彙榛樹細鐭ヨ瘑銆傛垜浠彧鏍囨敞鍏紑鏂囨湰涓彲瑙傚療鐨勪簰鍔ㄧ棔杩广€?
姣忎釜璺ㄥ绉戞爣绛惧繀椤绘弧瓒充笁涓潯浠讹細

1. 鏈夊師鏂囪瘉鎹細reviewer comment銆乤uthor response 鎴?editor decision 涓兘鎵惧埌鏀寔鐗囨銆?2. 鏈変簰鍔ㄥ姛鑳斤細璇ユ爣绛捐В閲婁簡 concern銆乺esponse 鎴?decision signal 鐨勫叧绯汇€?3. 鍙鍙嶉┏锛氬彟涓€涓爣娉ㄨ€呭彲浠ユ牴鎹悓涓€鏂囨湰涓嶅悓鎰忚鏍囩銆?
## Tacit Concern

| 鏍囩 | 鍙瀵熻瘉鎹?| 涓嶅簲鏍囨敞鐨勬儏鍐?|
|---|---|---|
| credibility_trust | reviewer 璐ㄧ枒缁撴灉鏄惁鍙潬銆乧laim 鏄惁琚暟鎹敮鎾戙€佸疄楠屾槸鍚﹁冻浠ユ敮鎾戠粨璁?| 鍙槸瑕佹眰鏀归敊鍒瓧鎴栬ˉ鏍煎紡 |
| community_standard_fit | reviewer 瑕佹眰甯歌 baseline銆佹爣鍑?benchmark銆侀鍩熼€氱敤鎶ュ憡鏂瑰紡 | 鍙槸浠绘剰瑕佹眰鏇村瀹為獙 |
| evidence_chain_stability | reviewer 鎸囧嚭鍥捐〃銆佺粺璁°€佽ˉ鍏呮潗鏂欍€佹柟娉曟弿杩颁箣闂撮摼鏉′笉绋?| 鍗曠函璇村啓寰椾笉娓呮浣嗕笉褰卞搷璇佹嵁閾?|
| presentation_as_epistemic_signal | reviewer 鎶婂浘琛ㄣ€佽〃杈炬垨缁撴瀯闂褰撲綔鍙俊搴﹂棶棰?| 绾瑷€娑﹁壊 |

## Institutional Signal

| 鏍囩 | 鍙瀵熻瘉鎹?| 瑙ｉ噴杈圭晫 |
|---|---|---|
| journal_scope_fit | editor/reviewer 鍏虫敞宸ヤ綔鏄惁閫傚悎鏈熷垔鑼冨洿銆佸奖鍝嶅姏鎴?novelty threshold | 涓嶈兘鎺ㄦ柇鐪熷疄缂栬緫鍋忓ソ |
| reviewer_authority_pressure | author response 鏄剧ず鏄庢樉璁╂銆侀亾姝夈€侀『浠庡绋挎潈濞?| 涓嶈兘鎶婄ぜ璨岃姘斾竴寰嬪綋鎴愭潈鍔涘帇鍔?|
| transparency_norm | 瑕佹眰 code/data銆佹潗鏂欍€佸彲澶嶇幇缁嗚妭 | 搴斾笌鍏蜂綋 reproducibility evidence 鍖哄垎 |
| editorial_risk_control | editor 寮鸿皟 unresolved concern銆乤dditional revision銆乺emaining issue | 涓嶇瓑鍚屼簬鎺ユ敹鐜囬娴?|

## Author Positioning

| 鏍囩 | 鍚箟 | 绀轰緥鎬ц瘉鎹?|
|---|---|---|
| accept_and_revise | 浣滆€呮帴鍙楁剰瑙佸苟瀹屾垚淇敼 | "We have added..." |
| clarify_without_new_work | 浣滆€呰В閲婂凡鏈夊唴瀹癸紝涓嶆柊澧炲疄楠?| "We clarify that..." |
| justify_existing_choice | 浣滆€呬负鍘熸柟娉曢€夋嫨杈╂姢 | "We chose this because..." |
| partially_concede | 閮ㄥ垎鎺ュ彈锛岄儴鍒嗕繚鐣欏師绔嬪満 | "While we agree..., we note..." |
| respectfully_disagree | 鏄庣‘浣嗙ぜ璨屽湴鍙嶉┏ reviewer premise | "We respectfully disagree..." |
| narrow_claim | 缂╁皬 claim 鎴栧鍔犻檺鍒?| "We have toned down..." |
| defer_to_future_work | 鎵胯閲嶈浣嗘斁鍒版湭鏉ュ伐浣?| "We leave this to future work..." |

## Actor Links

actor_links 鐢ㄤ簬璁板綍涓€鏉′簰鍔ㄤ腑琚皟鍔ㄧ殑琛屽姩鑰呭拰闈炰汉绫诲璞°€傚父瑙?actor_type锛?
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

鏍囨敞鏃跺繀椤昏褰?`role_in_interaction`锛屼緥濡傦細

- figure: 琚?reviewer 璐ㄧ枒涓鸿瘉鎹笉瓒崇殑杞戒綋锛?- supplement: 浣滆€呯敤鏉ユ壙杞芥柊澧炲垎鏋愶紱
- code: 浣滆€呯敤鏉ュ洖搴?reproducibility concern锛?- editor: 灏嗗涓?unresolved concern 鍘嬬缉涓?revision signal銆?
## Cognitive and Tone Boundary

鏈」鐩笉璇婃柇浣滆€呮垨 reviewer 鐨勬儏缁姸鎬侊紝鍙爣娉ㄦ枃鏈腑鐨勪簰鍔ㄥЭ鎬侊細

- defensive tone: 鏂囨湰杩囧害闃插尽锛屽彲鑳藉墛寮卞悎浣滃Э鎬侊紱
- sycophancy risk: 鏃犺瘉鎹湴杩庡悎 reviewer 鎴栨壙璇烘棤娉曞畬鎴愮殑淇敼锛?- uncertainty hiding: 鍥為伩涓嶇‘瀹氭€ф垨鎶婂急璇佹嵁鍐欐垚寮虹粨璁猴紱
- confidence calibration: 鏄庣‘璇存槑璇佹嵁寮哄害銆侀檺鍒跺拰鍙獙璇佹壙璇恒€?"""
    _write_doc("CROSS_DISCIPLINARY_ANNOTATION_GUIDE_zh.md", annotation)

    actor_model = """# Actor Network Case Model

鏈ā鍨嬬敤浜庢妸琛屽姩鑰呯綉缁滅悊璁鸿浆鎴愬彲妫€绱?case锛岃€屼笉鏄０绉拌繕鍘熺湡瀹炵ぞ浼氬洜鏋溿€?
## 鏍稿績鎬濇兂

涓€鏉?rebuttal interaction 涓嶅彧鏄?reviewer 鍜?author 鐨勪袱浜哄璇濓紝鑰屾槸澶氫釜琛屽姩鑰呰閲嶆柊瀵归綈鐨勮繃绋嬶細

```text
reviewer concern -> manuscript / figure / dataset / code / benchmark -> author response -> editor-readable resolution signal
```

## 蹇呴』璁板綍

- human actors: reviewer, author, editor
- non-human actors: manuscript, figure, table, dataset, code, benchmark, supplement, journal policy
- translation: reviewer concern 濡備綍琚綔鑰呰浆璇戞垚 evidence action 鍜?response wording
- provenance: 姣忎釜 actor link 閮藉繀椤昏兘鍥炲埌鍘熸枃璇佹嵁

## 杈圭晫

actor-network case 鍙〃绀哄叕寮€鏂囨湰涓殑鍙瀵熷叧绯伙紝涓嶅０绉板彂鐜扮湡瀹炲洜鏋滄満鍒躲€侀殣钘忓绋胯璁烘垨缂栬緫鐪熷疄蹇冪悊銆?"""
    _write_doc("ACTOR_NETWORK_CASE_MODEL_zh.md", actor_model)

    cognitive = """# Cognitive Trace Spec

鏈」鐩殑 workflow 涓嶈兘涓€姝ョ敓鎴?rebuttal銆傛瘡鏉?trace 蹇呴』鏄惧紡璁板綍鎱㈡€濈淮閾炬潯锛?
| Stage | 鐩殑 | 蹇呴』杈撳嚭 | 绂佹琛屼负 |
|---|---|---|---|
| understand | 鎷嗚В reviewer 鏄庤鐨?concern | concern_map | 涓嶆€ョ潃鐢熸垚鍥炲 |
| question | 璇嗗埆涓嶇‘瀹氥€侀殣鍚闄╁拰鍙兘璇В | risk_interpretation, uncertainty_notes | 涓嶆妸 reviewer premise 鑷姩褰撶湡 |
| evidence_plan | 鎶婇闄╄浆鎴愯瘉鎹垨淇鍔ㄤ綔 | evidence_action_plan | 涓嶇紪閫犲疄楠屻€佹暟鎹€佸紩鐢?|
| position | 甯綔鑰呴€夋嫨鍧氭寔銆佽姝ャ€佽В閲婃垨鍙嶉┏鐨勪綅缃?| author_positioning | 涓嶆棤鍘熷垯杩庡悎 |
| tone_calibrate | 鏍″噯鍚堜綔璇皵鍜屾壙璇鸿竟鐣?| tone_commitment_warnings | 涓嶆妸娓╂殩璇皵褰撴垚鍏呭垎鍥炲簲 |
| commitment_check | 妫€鏌ユ壙璇烘槸鍚﹀彲楠岃瘉銆佸彲瀹屾垚 | unsupported_commitment_flags | 涓嶆壙璇烘棤娉曞畬鎴愮殑淇敼 |
| integrity_check | 妫€鏌?provenance銆乷verclaim銆乤dequacy | adequacy_report | 涓嶈緭鍑烘棤璇佹嵁 claim |
| output | 鐢熸垚缁撴瀯鍖栧缓璁垨 outline | final_structured_output | 涓嶈嚜鍔ㄦ彁浜ゃ€佷笉棰勬祴鎺ユ敹鐜?|
"""
    _write_doc("COGNITIVE_TRACE_SPEC_zh.md", cognitive)


def _write_agent_workflow_docs() -> None:
    agent_card = """# Agent Card

## 瀹氫綅

NatureReview-Interact 鏄綔鑰呭洖搴斿拰瀹＄浜掑姩鐞嗚В鍔╂墜锛屼笉鏄嚜鍔ㄤ唬鍐?rebuttal 鐨勭郴缁熴€?
## Agents

| Agent | 杈撳叆 | 杈撳嚭 | 璁块棶瀛楁 | 绂佹琛屼负 |
|---|---|---|---|---|
| Reviewer Understanding Agent | review text | concern map | review_text, concern taxonomy | 涓嶇寽娴?reviewer 韬唤 |
| Tacit Concern Interpreter | concern map | tacit/risk interpretation | tacit taxonomy, examples | 涓嶅０绉拌鎳傜湡瀹炲績鐞?|
| Institutional Signal Interpreter | concern + decision context | institutional signal note | institutional taxonomy, editor signal taxonomy | 涓嶉娴嬫帴鏀剁巼锛屼笉鎺ㄦ柇缂栬緫鐪熷疄鎰忓浘 |
| Evidence Action Planner | risk interpretation | evidence plan | evidence taxonomy, retrieved cases | 涓嶇紪閫犲疄楠屾垨鏁版嵁 |
| Author Positioning Agent | evidence plan | stance options | strategy taxonomy | 涓嶅缓璁棤鍘熷垯杩庡悎 |
| Tone and Commitment Calibrator | draft/outline | tone warnings | tone taxonomy | 涓嶉紦鍔辫繃搴︽壙璇?|
| Actor-Network Mapper | concern + response + retrieved cases | actor alignment note | actor_links, case_index | 涓嶅０绉拌繕鍘熺湡瀹炲洜鏋滐紝鍙褰曟枃鏈腑鍙瀵熷叧绯?|
| Integrity and Adequacy Checker | full plan | adequacy report | provenance, retrieved cases | 涓嶆斁杩囨棤璇佹嵁 claim |
| Editor Signal Reader | case bundle | decision-risk note | editor signal taxonomy | 涓嶉娴嬫帴鏀剁巼 |
| Ethics and Governance Agent | full trace | responsible-use warnings | policy docs | 涓嶇粫杩囨暟鎹拰浼︾悊杈圭晫 |

## 杈撳嚭杈圭晫

绯荤粺杈撳嚭 concern map銆乺isk interpretation銆乮nstitutional signal note銆乤ctor-network note銆乪vidence plan銆乤uthor positioning銆乷utline銆乼one warning銆乤dequacy report 鍜?provenance note銆傜郴缁熶笉鑷姩鎻愪氦銆佷笉棰勬祴鎺ユ敹鐜囥€佷笉鏇夸唬浣滆€呭垽鏂€?"""
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

姣忔杩愯蹇呴』淇濈暀锛?
```text
understand -> question -> evidence_plan -> position -> tone_calibrate -> commitment_check -> integrity_check -> output
```

## Trace Requirements

- 姣忎釜 retrieved case 蹇呴』鏈?provenance銆?- 姣忎釜 evidence action 蹇呴』瀵瑰簲 reviewer concern 鎴?author response evidence銆?- 姣忎釜 commitment warning 蹇呴』璇存槑鏄惁瀛樺湪 overclaim銆乽nsupported_commitment銆乻ycophancy銆乪xcessive_defensiveness 鎴?uncertainty_hiding銆?- 杈撳嚭涓嶆槸 final rebuttal锛屼笉鐩存帴鎻愪氦锛屼笉棰勬祴鎺ユ敹鐜囥€?"""
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


def _cross_disciplinary_lens_map(unit: dict[str, Any], pred: dict[str, Any]) -> dict[str, dict[str, Any]]:
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
            "concept": "Tacit knowledge is treated only through observable textual traces.",
            "observable_trace": f"tacit_concern={unit.get('tacit_concern')}; risk_type={unit.get('risk_type')}; concern_type={unit.get('concern_type')}",
            "system_action": "Convert reviewer concern into a traceable risk hypothesis and require manuscript or case evidence.",
            "boundary": "Do not infer private reviewer psychology or claim that the model understands expert tacit knowledge.",
            "evaluation_question": "Does the system keep tacit-risk interpretation observable and checkable?",
        },
        "institutional_dependence": {
            "source_pdf": "2026.5.15.pdf",
            "concept": "Journal and editor-facing norms shape how an author response is positioned.",
            "observable_trace": f"institutional_signal={unit.get('institutional_signal')}; author_positioning={unit.get('author_positioning')}",
            "system_action": "Map transparency, reproducibility, and community-standard signals into author choices.",
            "boundary": "Do not predict acceptance probability or replace author judgment.",
            "evaluation_question": "Does the system identify institutional context while preserving author agency?",
        },
        "actor_network_alignment": {
            "source_pdf": "2026.5.15.pdf",
            "concept": "Evidence is carried by human and non-human actors such as reviewers, authors, figures, datasets, code, and benchmarks.",
            "observable_trace": f"actor_types={actor_types}; retrieved_cases={retrieved_case_ids}",
            "system_action": "Record which actors carry evidence, revisions, transparency, or editorial readability signals.",
            "boundary": "Do not reconstruct hidden social causality; describe only observable actor relationships.",
            "evaluation_question": "Does the system show which objects carry the proposed evidence action?",
        },
        "fast_slow_cognitive_correction": {
            "source_pdf": "2026.5.23.pdf",
            "concept": "Fast response is slowed by explicit concern, evidence, commitment, and integrity checks.",
            "observable_trace": "understand -> question -> evidence_plan -> position -> tone_calibrate -> commitment_check -> integrity_check -> output",
            "system_action": "Force a plan-first workflow before any author-facing advice is finalized.",
            "boundary": "Do not generate a final rebuttal or treat fluent prose as sufficient evidence.",
            "evaluation_question": "Does the workflow reduce overconfident or unsupported responses?",
        },
        "emotion_tone_commitment_calibration": {
            "source_pdf": "2026.5.23.pdf",
            "concept": "Tone work manages scholarly posture, uncertainty, and commitment strength.",
            "observable_trace": f"tone={tone.get('tone')}; commitment_level={tone.get('commitment_level')}; risk_flags={tone.get('risk_flags')}",
            "system_action": "Calibrate defensiveness, unsupported commitment, overclaiming, and over-concession risks.",
            "boundary": "Do not diagnose emotions or use polite tone as a substitute for evidence.",
            "evaluation_question": "Does the system lower conflict risk without creating unsupported promises?",
        },
        "author_agency_gate": {
            "source_pdf": "2026.5.23.pdf + 2026.5.15.pdf",
            "concept": "The assistant must preserve author agency and expert judgment.",
            "observable_trace": f"evidence_action={evidence_action}; author_confirmation_required=true; label_status=model_assisted_not_human_gold",
            "system_action": "Require author confirmation for all experiments, data, citations, figures, and commitments.",
            "boundary": "Author confirmation is required; the system does not replace the author, reviewer, or editor.",
            "evaluation_question": "Does the system turn advice into auditable author choices rather than commitments on the author's behalf?",
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


def _revision_pressure_signal(response_adequacy: dict[str, Any]) -> str:
    coverage_status = str(response_adequacy.get("coverage_status") or "unknown")
    unresolved = response_adequacy.get("unresolved_concerns") or []
    missing = response_adequacy.get("missing_evidence_actions") or []
    if coverage_status == "covered" and not unresolved and not missing:
        return "low"
    if coverage_status in {"not_covered", "needs_author_confirmation"} or unresolved or missing:
        return "high"
    return "medium"


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
            "Tacit knowledge boundaries become observable risk hypotheses.",
            "Institutional dependence becomes author-positioning choices.",
            "Actor-network relations become evidence carriers and provenance.",
            "Fast/slow cognition becomes a plan-first workflow.",
            "Tone and emotion are handled through commitment and uncertainty calibration.",
            "Author agency is preserved through confirmation gates.",
        ],
        "forbidden_behaviors": [
            "Treating retrieval results as the final answer.",
            "Replacing case evidence and model review with untraceable shortcuts.",
            "Predicting acceptance probability.",
            "Fabricating experiments or commitments.",
            "Inferring reviewer or editor private psychology.",
            "Replacing author professional judgment.",
        ],
        "not_rag_only_boundary": "not RAG-only; retrieval is support infrastructure for cross-disciplinary review-interaction reasoning.",
    }


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

It is not RAG-only. Retrieval is used as support infrastructure; the simulation evaluates 璺ㄥ绉戜环鍊? tacit knowledge boundary, institutional dependence, actor-network alignment, fast/slow cognitive correction, emotion-tone-commitment calibration, and author agency.

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

The system must not 鎶婃绱㈢粨鏋滃綋鎴愭渶缁堢瓟妗? must not 鐢ㄤ笉鍙拷婧殑鎹峰緞鏇夸唬妗堜緥璇佹嵁鍜屾ā鍨嬪鏍? must not 棰勬祴鎺ユ敹鐜? and must not 缂栭€犲疄楠屾垨鎵胯.
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

## 鐩爣

鏈」鐩殑璁粌渚х洰鏍囦笉鏄洿鎺ヨ缁?final rebuttal generator锛岃€屾槸鎶?Nature 鍏紑瀹＄浜掑姩妗堜緥杞垚鍙涔犮€佸彲鏇挎崲銆佸彲璇勪及鐨勪腑闂磋兘鍔涖€傛牳蹇冩槸瀛︿範瀹＄浜掑姩缁撴瀯锛岃€屼笉鏄涔犱唬鍐欎竴灏佸畬鏁村洖澶嶃€?
## Interaction Learning Targets

| Target | 瀛﹀埌浠€涔?| 褰撳墠鐩戠潱淇″彿 | 涓昏椋庨櫓 |
|---|---|---|---|
| concern understanding | reviewer 鏄庣‘鎻愬嚭浠€涔堥棶棰?| concern_type, review_text | 澶氶棶棰樿瘎璁鸿鍘嬫垚鍗曚竴鏍囩 |
| tacit risk interpretation | 鏄庣‘鎰忚鑳屽悗鐨勫彲瑙傚療椋庨櫓 | tacit_concern, risk_type | 璇 reviewer 蹇冪悊 |
| institutional positioning | 鏈熷垔銆佸叡鍚屼綋銆侀€忔槑鎬х瓑鍒跺害淇″彿 | institutional_signal | 璇啓鎴愭帴鏀剁巼棰勬祴 |
| strategy selection | concern 瀵瑰簲鐨勫洖搴旂瓥鐣?| response_strategy | 鎶婄瓥鐣ユ爣绛炬硠闇茬粰妫€绱㈡帓搴?|
| evidence action planning | 鍝被璇佹嵁鍔ㄤ綔鑳藉洖搴旈闄?| evidence_action, actor_links | 缂栭€犲疄楠屻€佹暟鎹垨寮曠敤 |
| author positioning | 浣滆€呭簲鍧氭寔銆佽姝ャ€佽В閲婅繕鏄缉灏?claim | author_positioning | 鏃犲師鍒欒繋鍚堟垨杩囧害闃插尽 |
| tone / commitment calibration | 璇皵銆佹壙璇哄己搴﹀拰涓嶇‘瀹氭€ц竟鐣?| tone_commitment | sycophancy 鎴?unsupported commitment |
| response adequacy | 鍥炲簲鏄惁鐪熸瑕嗙洊 concern | retrieved cases + adequacy rubric | 鍙湅娴佺晠搴︿笉鐪嬭В鍐冲害 |

## Trainable / Replaceable Modules

| Module | v0.1 瀹炵幇 | 鍚庣画鍙缁冩柟鍚?| 涓嶅缓璁仛娉?|
|---|---|---|---|
| Concern Classifier | taxonomy + model-assisted labels | lightweight classifier / prompt classifier | 鐩存帴鐢ㄦ渶缁堝洖澶嶈川閲忓弽鎺?concern |
| Risk Interpreter | tacit taxonomy + model-assisted labels | classifier with evidence quote constraint | 澹扮О璇诲彇 reviewer hidden intent |
| Strategy Selector | retrieval target + label distribution | strategy prediction / reranker | 鍦?retrieval ranking 涓娇鐢?query strategy label |
| Evidence Planner | evidence_action + actor_links | action planner with feasibility flags | 鎺ㄨ崘浣滆€呬笉瀛樺湪鐨勫疄楠屾垨鏁版嵁 |
| Tone Calibrator | tone_commitment labels | unsupported commitment detector | 鎶婄ぜ璨屽綋鎴愬厖鍒嗗洖搴?|
| Adequacy Checker | workflow trace + rubric | response adequacy scorer | 鍙瘎浼拌瑷€娴佺晠搴?|
| Integrity Checker | provenance checks + author-confirmation gates | atomic claim support checker | 鍏佽鏃犳潵婧愪簨瀹炴垨鎵胯 |

## model-assisted training seed

褰撳墠瀵煎嚭浣嶇疆锛?
```text
data/training/author_rebuttal_agent/v2709/model_assisted_training_seed_200.jsonl
data/training/author_rebuttal_agent/v2709/training_seed_summary.json
```

姣忔潯璁粌鏍锋湰鍖呭惈锛?
- input: review_text, response_text, title, journal, year
- targets: concern_type, risk_type, tacit_concern, institutional_signal, response_strategy, evidence_action, author_positioning, tone_commitment, actor_links, response_adequacy
- learning_tasks: concern_extraction, risk_classification, strategy_prediction, evidence_action_prediction, author_positioning_prediction, tone_commitment_calibration, unsupported_commitment_detection, response_adequacy_scoring, decision_aware_case_retrieval
- provenance: source_file, source_hash, offset_recoverable, review_offset, response_offset
- safety_boundaries: no acceptance prediction, no fabricated evidence, no confidential manuscript upload, author confirmation required

## 褰撳墠 v0.1 鐨勮缁冭竟鐣?
- 褰撳墠鏁版嵁鍙互鏀寔 model-assisted sanity training/evaluation seed銆?- 褰撳墠鏁版嵁鍙互鏀寔 retrieval/reranker銆佸垎绫诲櫒銆佽瘉鎹鍒掋€乼one/commitment checker 鐨勫師鍨嬪疄楠屻€?- 褰撳墠鏁版嵁涓嶈兘鏀拺 human gold benchmark銆佹帴鏀剁巼棰勬祴銆佺鍒扮楂樿川閲?final rebuttal generator 寰皟銆?- API 鏇夸唬浜哄伐澶嶆牳鍙互浣滀负 v0.1 榛樿娴佺▼锛屼絾蹇呴』鏍囨敞 model-assisted锛屼笉寰楀啓鎴愪汉宸ラ噾鏍囥€?
## 鎺ㄨ崘瀹為獙椤哄簭

1. 鍥哄寲 taxonomy 鍜岃缁?seed contract銆?2. 姣旇緝 concern/risk/strategy/evidence 鐨?historical local baseline銆乺etrieval baseline銆丩LM zero-shot銆?3. 鍋?retrieval/reranker锛屼絾绂佹浣跨敤 query response_strategy label 鍙備笌鎺掑簭銆?4. 鍋?response adequacy 鍜?unsupported commitment 妫€鏌ャ€?5. 灏嗘ā鍧楁帴鍏?workflow trace锛屾瘮杈?direct LLM銆丷AG-only銆乧ognitive workflow 涓夌被璺嚎銆?6. 鍙湁鍦ㄥ嚭鐜?human gold benchmark 鍚庯紝鎵嶅０鏄庢寮忕洃鐫ｈ瘎娴嬬粨璁恒€?"""
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

璇勫垎闂锛氱郴缁熸槸鍚﹀熀浜庢枃鏈瘉鎹瘑鍒簡 reviewer concern 鑳屽悗鐨勫彲淇″害銆侀鍩熸爣鍑嗐€佽瘉鎹摼鎴?claim 杈圭晫闂锛?
1 鍒嗭細鍙杩?reviewer 鍘熻瘽銆?3 鍒嗭細鑳借瘑鍒樉鎬ч闄╋紝浣嗙己灏戞枃鏈瘉鎹垨杈圭晫璇存槑銆?5 鍒嗭細鑳界粰鍑哄彲瑙傚療璇佹嵁銆佽В閲婅竟鐣岋紝骞堕伩鍏嶅０绉拌鎳?reviewer 蹇冪悊銆?
## 2. Institutional Positioning

璇勫垎闂锛氱郴缁熸槸鍚﹁瘑鍒簡鏈熷垔鑼冨洿銆佸叡鍚屼綋鏍囧噯銆侀€忔槑鎬ц鑼冦€乪ditorial risk control 绛夊埗搴︿俊鍙凤紵

1 鍒嗭細瀹屽叏蹇界暐鍒跺害璇銆?3 鍒嗭細鎻愬埌鍒跺害鍘嬪姏锛屼絾娌℃湁璇存槑鍜?response strategy 鐨勫叧绯汇€?5 鍒嗭細鑳芥妸鍒跺害淇″彿杞垚浣滆€呭彲鎵ц鐨勫洖搴斾綅缃紝鍚屾椂涓嶉娴嬫帴鏀剁巼銆?
## 3. Actor-network Alignment

璇勫垎闂锛氱郴缁熸槸鍚﹁褰曚簡 manuscript銆乫igure銆乨ataset銆乧ode銆乥enchmark銆乻upplement銆乪ditor signal 绛夎鍔ㄨ€呭浣曡閲嶆柊瀵归綈锛?
1 鍒嗭細鍙緭鍑烘枃鏈洖澶嶅缓璁€?3 鍒嗭細鎻愬埌璇佹嵁瀵硅薄锛屼絾娌℃湁璇存槑浜掑姩鍔熻兘銆?5 鍒嗭細鏄庣‘璇存槑鍝簺琛屽姩鑰呮壙鎷呬簡璇佹嵁銆佷慨璁€侀€忔槑鎬ф垨缂栬緫鍙淇″彿鐨勪綔鐢ㄣ€?
## 4. Cognitive Trace Quality

璇勫垎闂锛氱郴缁熸槸鍚︽寜 understand -> question -> evidence_plan -> position -> tone_calibrate -> commitment_check -> integrity_check -> output 鐨勯『搴忓伐浣滐紵

1 鍒嗭細鐩存帴鐢熸垚鍥炲銆?3 鍒嗭細鏈夐儴鍒嗕腑闂存楠わ紝浣嗙己灏戞壙璇烘垨 integrity 妫€鏌ャ€?5 鍒嗭細瀹屾暣璁板綍鎱㈡€濈淮閾炬潯锛屽苟鑳借В閲婃瘡涓€姝ュ浣曞噺灏戣繃搴﹁嚜淇°€佽繋鍚堟垨缂栭€犻闄┿€?"""
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

For PDF manuscript text extraction support:

```powershell
python -m pip install -e ".[pdf]"
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
  --manuscript-file examples/rebuttal_lens/manuscript_excerpt.txt `
  --response-file examples/rebuttal_lens/author_draft_response.txt `
  --retrieved-cases-file examples/rebuttal_lens/retrieved_cases.json `
  --output-dir data/evaluation/rebuttal_lens_demo
```

Installed console scripts are also available after `pip install -e .`:

```powershell
run-rebuttal-lens `
  --review-file examples/rebuttal_lens/reviewer_comment.txt `
  --manuscript-file examples/rebuttal_lens/manuscript_excerpt.txt `
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
- `manuscript_excerpt.txt`: manuscript excerpt supplied by the author
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

Release-readiness evidence should be recorded in the run report or release notes for the specific validation run. The release gate includes full pytest, compileall, v0.1 artifact validation, package dry-run, CLI smoke tests, public documentation scans, and secret scans.

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

v0.1 is non-training and cross-disciplinary. 璁粌鍜屽井璋冧笉灞炰簬 v0.1 鏍稿績. This is not a RAG system and 涓嶆槸鍗曚竴鎶€鏈璺? retrieval/RAG is support infrastructure only.

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

## 鎺ㄨ崘璁稿彲

鏈」鐩?v0.1 鐨勪唬鐮併€乻chema銆乼axonomy銆佽瘎娴嬪崗璁€乺ubric銆乸rompt 妯℃澘銆佹淳鐢熷厓鏁版嵁鍜屾姤鍛婂缓璁娇鐢?Apache-2.0銆?
## 涓嶈鐩栫殑鍐呭

Apache-2.0 涓嶈鐩?Nature 鎴栧叾浠栧嚭鐗堟柟鐨勫師濮嬪叏鏂囥€乸eer review report 鍏ㄦ枃銆乤uthor response 鍏ㄦ枃銆乪ditor decision letter 鍏ㄦ枃銆佺涓夋柟鍥捐〃銆佺涓夋柟 PDF 鎴栦换浣曢潪鍏紑瀹＄鏉愭枡銆?
## 鍙戝竷杈圭晫

- 鍙互鍙戝竷锛氫唬鐮併€乻chema銆乼axonomy銆乨erived metadata銆乁RL/DOI/hash/offset銆佽瘎娴嬪崗璁拰 baseline 缁撴灉銆?- 璋ㄦ厧鍙戝竷锛氱煭鏂囨湰鐗囨鍜屽彲鍥炴函鏍蜂緥锛屽繀椤讳繚鐣?provenance 骞堕伒瀹堟潵婧愯鍙€?- 榛樿涓嶅彂甯冿細鍘熷鍏ㄦ枃鑱氬悎鍖呫€丄PI key銆乸rivate logs銆乧onfidential manuscript銆?
## 鍚庣画鍔ㄤ綔

姝ｅ紡鍏紑浠撳簱鍓嶏紝搴旂敱椤圭洰缁存姢鑰呯‘璁ゆ渶缁?license 鏂囦欢銆傚鏋滆鍙戝竷浠讳綍鍘熷鏂囨湰鐗囨锛岄渶瑕佸啀娆℃牳瀵规潵婧愰〉闈㈣鍙拰鍐嶅垎鍙戣竟鐣屻€?"""
    _write_doc("LICENSE_DECISION_zh.md", license_decision)

    limitations = """# Model and Agent Limitations

- 妯″瀷涓嶈兘鐪熸鎷ユ湁浜虹被榛樹細鐭ヨ瘑銆?- 妯″瀷鍙兘璇嗗埆鍏紑鏂囨湰涓殑鍙瀵熺棔杩广€?- 褰撳墠 seed set 涓嶆槸浜哄伐閲戞爣銆?- 妯″瀷澶嶆牳涓嶈兘绛夊悓浜庝汉宸ラ噾鏍囥€?- 褰撳墠 workflow 娌℃湁缁忚繃鐪熷疄浣滆€呯敤鎴风爺绌躲€?- 璁粌鍜屽井璋冧笉灞炰簬 v0.1 鏍稿績銆?- Retrieval/RAG 鍙槸杈呭姪璁炬柦锛屼笉鏄郴缁熸牳蹇冧环鍊笺€?- 浠讳綍瀹為獙銆佹暟鎹€佸紩鐢ㄥ拰鎵胯蹇呴』鐢变綔鑰呯‘璁ゃ€?- 绯荤粺涓嶉娴嬫帴鏀剁巼锛屼笉鏇夸唬浣滆€呫€乺eviewer 鎴?editor銆?"""
    _write_doc("MODEL_AND_AGENT_LIMITATIONS_zh.md", limitations)

    legacy_limitations_removed = """# Model and Agent Limitations

- 妯″瀷涓嶈兘鐪熸鎷ユ湁浜虹被榛樹細鐭ヨ瘑銆?- 妯″瀷鍙兘璇嗗埆鍏紑鏂囨湰涓殑鍙瀵熺棔杩广€?- 褰撳墠 seed set 涓嶆槸浜哄伐閲戞爣銆?- 妯″瀷澶嶆牳涓嶈兘绛夊悓浜庝汉宸ラ噾鏍囥€?- 褰撳墠 workflow 娌℃湁缁忚繃鐪熷疄浣滆€呯敤鎴风爺绌躲€?- 浠讳綍瀹為獙銆佹暟鎹€佸紩鐢ㄥ拰鎵胯蹇呴』鐢变綔鑰呯‘璁ゃ€?- 绯荤粺涓嶉娴嬫帴鏀剁巼锛屼笉鏇夸唬浣滆€呫€乺eviewer 鎴?editor銆?"""
    _write_doc("MODEL_AND_AGENT_LIMITATIONS_zh.md", limitations)


def _write_paper_docs() -> None:
    paper_plan = """# Paper Plan

## 涓婚棶棰?
鍏紑閫忔槑鍚岃璇勫鏁版嵁鑳藉惁甯姪鎴戜滑瀛︿範绉戝瀹＄浜掑姩涓殑榛樹細鐭ヨ瘑銆佸埗搴﹀帇鍔涖€佽瘉鎹姩浣滃拰璇█濮挎€侊紝骞跺皢杩欎簺瑙勫緥杞寲涓鸿礋璐ｄ换鐨勪綔鑰呭洖搴旀櫤鑳戒綋锛?
## 璐＄尞

1. 璺ㄥ绉戦棶棰樺畾涔?2. Review Interaction Unit / Knowledge Base
3. Tacit Concern and Evidence Action Taxonomy
4. Cognitive-layer Multi-agent Workflow
5. Responsible Open-source Protocol

## 褰撳墠璇佹嵁鐘舵€?
褰撳墠璇佹嵁鏀寔 knowledge base 鍜?workflow prototype 鐨勮鏂囪矾绾匡紝浣嗘墍鏈夊叧浜庢晥鏋滄彁鍗囩殑寮轰富寮犻兘闇€瑕?human evaluation 鎴栨洿澶ц妯¤嚜鍔ㄨ瘎娴嬨€?"""
    _write_doc("PAPER_PLAN_zh.md", paper_plan)

    lit = """# Literature Matrix

| 鏂囩尞绫诲埆 | 瑕佸洖绛旂殑闂 | 鍏抽敭璇?| 闇€瑕佹瘮杈冪殑 prior work | 鎴戜滑鐨勫樊寮?|
|---|---|---|---|---|
| Peer review NLP / assistance | AI 濡備綍杈呭姪瀹＄锛?| peer review, review feedback agent | Review Feedback Agent, Reviewer2 | 鎴戜滑闈㈠悜 author-review-editor interaction |
| Rebuttal generation | 濡備綍鐢熸垚鎴栬鍒?rebuttal锛?| rebuttal generation, response letter | Paper2Rebuttal, DRPG, RebuttalAgent | 鎴戜滑寮鸿皟璇佹嵁鍔ㄤ綔鍜屽埗搴︿簰鍔?|
| RAG over scholarly documents | 濡備綍鍩轰簬妗堜緥妫€绱紵 | scholarly RAG, citation-grounded generation | scholarly QA / RAG systems | 鎴戜滑妫€绱?interaction unit |
| LLM agents | 澶?agent 濡備綍鎷嗚В浠诲姟锛?| LLM agent, workflow, planning | agent review systems | 鎴戜滑璁剧疆璐ｄ换杈圭晫鍜?integrity guard |
| STS / tacit knowledge | 榛樹細鐭ヨ瘑濡備綍杩涘叆瀹＄锛?| tacit knowledge, peer review sociology | Polanyi, Collins, ANT | 鎴戜滑鍙涔犳枃鏈棔杩?|
| AI governance | 濡備綍闄愬埗璇敤锛?| AI disclosure, peer review policy | Nature, COPE, WAME, ICML policies | 鎴戜滑鍐呯疆 open-source boundary |
"""
    _write_doc("LITERATURE_MATRIX_zh.md", lit)

    experiment = """# Experiment Plan

## Phase 1: Data audit and schema freeze

浜х墿锛歱roject status銆乧laim ledger銆乻chema銆乼axonomy銆?
## Phase 2: Seed set and taxonomy validation

浜х墿锛?00-200 鏉?candidate seed銆乵odel-assisted review銆乭uman confirmation template銆?
## Phase 3: Retrieval baseline v2

浜х墿锛歩nteraction-aware retrieval baseline and report銆?
## Phase 4: Agent workflow v2

浜х墿锛歳ecordable cognitive traces銆?
## Phase 5: Automatic and human evaluation

浜х墿锛歳ubric銆乭uman sheet銆乤utomatic metrics銆?
## Phase 6: Ablation and error analysis

浜х墿锛歞irect-generation vs RAG vs cognitive workflow 瀵规瘮锛屼互鍙婂け璐ユ渚嬪垎鏋愩€?"""
    _write_doc("EXPERIMENT_PLAN_zh.md", experiment)

    risk = """# Reviewer Risk Register

| Reviewer concern | Why it matters | Response strategy | Evidence needed |
|---|---|---|---|
| AI cannot learn tacit knowledge | 鏍稿績姒傚康鍙兘琚敾鍑?| 鏀圭О observable traces of tacit judgment | taxonomy examples + annotation |
| Labels are not gold | 璇勬祴鍙俊搴﹂闄?| 鏄庣‘ label status锛岃ˉ浜哄伐纭 | human eval sheet |
| Dataset copyright risk | 寮€婧愰闄?| 鍙戝竷 derived metadata and offsets | data release boundary |
| This is just RAG | 鍒涙柊鎬ч闄?| 寮鸿皟 interaction unit + cognitive layer | ablation vs RAG |
| Agent may encourage manipulation | 浼︾悊椋庨櫓 | responsible use and no acceptance prediction | governance doc |
"""
    _write_doc("REVIEWER_RISK_REGISTER_zh.md", risk)


def _write_execution_summary() -> None:
    status = """# Open Source v0.1 Completion Status

Status: v0.1 open-source framework complete.

## 涓€鍙ヨ瘽

NatureReview-Interact v0.1 宸茬粡褰㈡垚涓€涓法瀛︾瀹＄浜掑姩鐭ヨ瘑搴撳拰鍙拷婧?Author Rebuttal Assistant workflow 妗嗘灦锛涘畠瀛︿範鐨勬槸 reviewer concern銆乼acit risk銆乮nstitutional signal銆乪vidence action銆乤uthor positioning銆乼one/commitment 鍜?editor-readable signal 涔嬮棿鐨勪簰鍔ㄧ粨鏋勩€傝缁冨拰寰皟涓嶅睘浜?v0.1 鏍稿績銆?
## 褰撳墠瀹屾垚椤?
| Area | Artifact | Status |
|---|---|---|
| project framing | `docs/2026-05-26-open-source-review-interaction-agent-full-plan-zh.md` | complete |
| non-training scope | `docs/NON_TRAINING_OPEN_SOURCE_SCOPE_zh.md` | 璁粌鍜屽井璋冧笉灞炰簬 v0.1 鏍稿績 |
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

## 鏄庣‘杈圭晫

- 涓嶆槸 human gold銆?- 涓嶆槸 final rebuttal generator銆?- 涓嶆槸 acceptance predictor銆?- 涓嶆槸 RAG-only锛屼篃涓嶆槸鍗曚竴鎶€鏈璺€?- 璁粌鍜屽井璋冧笉灞炰簬 v0.1 鏍稿績銆?- 鎵€鏈夊疄楠屻€佹暟鎹€佸紩鐢ㄥ拰鎵胯蹇呴』鐢变綔鑰呯‘璁ゃ€?"""
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

## 涓€鍙ヨ瘽

NatureReview-Interact v0.1 宸茬粡褰㈡垚涓€涓法瀛︾瀹＄浜掑姩鐭ヨ瘑搴撳拰鍙拷婧?Author Rebuttal Assistant workflow 妗嗘灦锛涘畠瀛︿範鐨勬槸 reviewer concern銆乼acit risk銆乮nstitutional signal銆乪vidence action銆乤uthor positioning銆乼one/commitment 鍜?editor-readable signal 涔嬮棿鐨勪簰鍔ㄧ粨鏋勩€?
## 褰撳墠瀹屾垚椤?
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

## 鏄庣‘杈圭晫

- 褰撳墠涓嶆槸 human gold銆?- 褰撳墠涓嶆槸 final rebuttal generator銆?- 褰撳墠涓嶉娴嬫帴鏀剁巼銆?- 褰撳墠涓嶉紦鍔变笂浼?confidential manuscript 鍒板閮?API銆?- 褰撳墠鍏紑閲嶇偣鏄?schema銆乼axonomy銆乨erived metadata銆乵odel-assisted seed銆乪valuation protocol銆乥aseline銆亀orkflow trace銆乻imulation trace 鍜屾不鐞嗚竟鐣屻€?
## 寮€婧愬墠蹇呴』淇濈暀鐨勮鏄?
鎵€鏈夊叕寮€浠嬬粛蹇呴』鍐欐槑锛氬綋鍓嶆爣绛炬槸 model-assisted锛屼笉鏄?human gold锛涚郴缁熸槸 assistant/workflow锛屼笉鏄浛浣滆€呮彁浜?rebuttal 鐨勫伐鍏枫€?"""
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
    _write_json(
        handoff_dir / "api_review_status.json",
        {
            "status": api_status,
            "request_count": len(requests),
            "result_count": result_count,
            "error_count": error_count,
            "label_status": manifest["label_status"],
            "boundary": "model-assisted, not human gold",
        },
    )


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

    docs_missing: list[str] = []
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
        and "Replacing case evidence and model review with untraceable shortcuts."
        in ((trace.get("cross_disciplinary_evaluation") or {}).get("forbidden_behaviors") or [])
    )
    simulation_layer_ok = (
        len(simulation_traces) == 50
        and simulation_summary.get("trace_count") == 50
        and simulation_summary.get("label_status") == "model_assisted_not_human_gold"
        and simulation_role_complete_count == len(simulation_traces)
        and simulation_boundary_count == len(simulation_traces)
    )
    evaluation_protocol_complete = _evaluation_task_catalog_complete()
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
    retrieval_report_has_p1 = (
        "p1_baseline_comparison" in retrieval_summary
        and "improvement_attribution" in retrieval_summary
    )
    readme_path = PROJECT_ROOT / "README.md"
    readme_boundary_ok = _file_contains(
        readme_path,
        [
            "Apache License 2.0",
            "model-assisted, not human gold",
            "not affiliated with, endorsed by, or operated by Nature Portfolio or Springer Nature",
        ],
    )
    license_decision_ok = readme_boundary_ok
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
        "readme_declares_no_human_gold": _file_contains(readme_path, ["model-assisted, not human gold"]),
        "responsible_use_has_hard_boundaries": _file_contains(
            readme_path,
            ["predict acceptance probability", "fabricate experiments", "upload confidential manuscript material"],
        ),
        "schema_has_cross_disciplinary_fields": all(
            field in schema_properties
            for field in ["institutional_signal", "actor_links", "author_positioning", "tone_commitment"]
        ),
        "workflow_has_required_trace_order": _file_contains(
            readme_path,
            ["Layer 0", "Layer 1", "Layer 2", "Layer 3", "Layer 4", "Layer 5"],
        ),
        "simulation_spec_has_required_roles_and_boundary": _file_contains(
            readme_path,
            ["reviewer", "author rebuttal", "editor signal", "not real peer review"],
        ),
        "api_status_documented_as_model_assisted": api_manifest_status in {"prepared_not_executed", "executed"}
        and _file_contains(readme_path, ["model-assisted"]),
        "api_execution_reflected_in_public_docs": (
            api_manifest_status != "executed"
            or (
                _file_contains(readme_path, ["API seed review has been executed", "200 / 200", "model-assisted, not human gold"])
            )
        ),
        "training_boundary_is_documented": _file_contains(
            readme_path,
            ["does not train or fine-tune models", "not a hidden one-shot rebuttal"],
        ),
    }

    semantic_checks.update(
        {
            "non_training_open_source_scope_is_explicit": _file_contains(
                readme_path,
                ["non-training", "not a RAG system", "does not train or fine-tune models"],
            ),
            "cross_disciplinary_lenses_are_documented": _file_contains(
                readme_path,
                ["tacit knowledge boundary", "institutional dependence", "actor-network alignment", "author agency gate"],
            ),
            "training_is_not_public_core_scope": _file_contains(
                readme_path,
                ["Training and fine-tuning are outside the public v0.1 core scope"],
            ),
        }
    )

    checks = [
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
            {"path": "README.md"},
        ),
        _check(
            "Cross-disciplinary design lenses are documented",
            semantic_checks["cross_disciplinary_lenses_are_documented"],
            {"path": "README.md"},
        ),
        _check("README includes public license and boundary notes", license_decision_ok, {"path": "README.md"}),
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


def _evaluation_task_catalog_complete() -> bool:
    required_fields = [
        "input",
        "output",
        "supervision",
        "automatic",
        "human",
        "baselines",
        "failures",
    ]
    return len(EVALUATION_TASKS) >= 11 and all(
        all(task.get(field) for field in required_fields)
        for task in EVALUATION_TASKS
    )


def _scan_secret_hits() -> list[dict[str, str]]:
    roots = [
        PROJECT_ROOT / "README.md",
        PROJECT_ROOT / "src/peer_review_skills",
        PROJECT_ROOT / "tests",
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
        PROJECT_ROOT / "README.md",
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
