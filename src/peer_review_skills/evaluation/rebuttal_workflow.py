import argparse
import csv
import json
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from peer_review_skills.api.openai_compatible import build_client_from_environment
from peer_review_skills.config import project_relative_path, resolve_project_path
from peer_review_skills.evaluation.p0_baselines import _has_label, _preview
from peer_review_skills.evaluation.p1_retrieval_baselines import (
    DEFAULT_INPUT_DIR,
    DEFAULT_TOP_K,
    retrieve_cases,
)
from peer_review_skills.io.jsonl import read_jsonl, write_jsonl


DEFAULT_OUTPUT_DIR = Path("data/evaluation/author_rebuttal_workflow/v2709_model_revised")
DEFAULT_RETRIEVAL_METHOD = "hybrid_bm25_concern_strategy"
WORKFLOW_VERSION = "author_rebuttal_assistant_workflow_v1"

RISK_TYPES = {
    "baseline_comparison": "comparative_validity",
    "generalization_scope": "external_validity",
    "reproducibility_reporting": "reproducibility",
    "statistics_significance": "statistical_validity",
    "ablation_mechanism": "mechanistic_validity",
    "clarity_presentation": "communication_clarity",
    "experimental_design": "design_validity",
    "dataset_bias_ethics_safety": "responsible_research",
    "theoretical_validity": "theoretical_validity",
    "novelty_positioning": "contribution_positioning",
}

EVIDENCE_TEMPLATES = {
    "baseline_comparison": [
        "Identify the exact baseline or prior method requested by the reviewer.",
        "State whether a comparison, re-analysis, or limitation discussion is available.",
        "Cite the manuscript table, figure, supplement, or response paragraph where the comparison is documented.",
    ],
    "generalization_scope": [
        "List the tested datasets, cohorts, domains, or populations.",
        "Separate evidence already available from validation that remains future work.",
        "Narrow claims when external validation is not available.",
    ],
    "reproducibility_reporting": [
        "Specify data, code, parameter, protocol, and availability artifacts.",
        "Include repository, accession, appendix, or supplement references when available.",
        "Flag any restricted asset and explain the access route without overstating openness.",
    ],
    "statistics_significance": [
        "Identify the exact quantitative claim being challenged.",
        "Provide uncertainty, statistical test, sample size, or sensitivity analysis details.",
        "Avoid claiming significance unless the test and threshold are explicitly available.",
    ],
    "ablation_mechanism": [
        "Map each mechanism claim to an ablation, feature analysis, or explanatory result.",
        "Distinguish new analysis from clarification of existing evidence.",
        "Soften mechanism language if causal support is incomplete.",
    ],
    "clarity_presentation": [
        "Name the figure, table, section, sentence, or legend being revised.",
        "Describe the concrete wording, formatting, or organization change.",
        "Avoid presenting editorial changes as new scientific evidence.",
    ],
    "experimental_design": [
        "Identify the missing control, validation, sample, or protocol issue.",
        "State whether a new experiment was performed, a design rationale was added, or the limitation was acknowledged.",
        "Keep claims within the design that was actually executed.",
    ],
    "dataset_bias_ethics_safety": [
        "Document dataset composition, fairness, privacy, consent, or safety handling.",
        "Add limitations or mitigation steps when direct evidence is unavailable.",
        "Avoid implying risk has been eliminated without supporting analysis.",
    ],
    "theoretical_validity": [
        "Identify the challenged assumption, formal statement, or causal interpretation.",
        "Provide proof, rationale, citation, or scope limitation for the claim.",
        "Avoid causal or universal language when only empirical support is available.",
    ],
    "novelty_positioning": [
        "Clarify the relation to the closest prior work.",
        "State the distinct contribution without exaggerating novelty.",
        "Add citations or positioning text where needed.",
    ],
}

STRATEGY_GUIDANCE = {
    "acknowledge_and_fix": "Acknowledge the point and name the concrete manuscript or analysis change.",
    "clarify_existing_evidence": "Clarify what was already in the work and point to exact evidence.",
    "add_new_experiment": "Describe the added experiment only if it was actually performed and documented.",
    "add_new_analysis": "Describe the added analysis, metric, robustness check, or re-analysis with exact location.",
    "narrow_claim_scope": "Softly reduce the claim to match demonstrated evidence.",
    "contest_reviewer_premise": "Disagree narrowly and respectfully, with rationale and citations.",
    "defer_future_work": "Acknowledge importance while making clear what is outside the present study.",
    "justify_method_choice": "Explain the methodological choice with rationale, standard practice, or constraints.",
    "reframe_contribution": "Reposition the contribution in terms the evidence can support.",
    "editorial_only_change": "Describe the presentation edit without implying substantive new evidence.",
}

FORBIDDEN_ACTIONS = [
    "Do not fabricate evidence",
    "Do not invent experiments, analyses, datasets, or manuscript changes",
    "Do not promise revisions the authors have not decided to make",
    "Do not replace author or domain-expert judgment",
    "Do not hide uncertainty, limitations, or unresolved reviewer concerns",
]


def build_evidence_plan(
    query_record: dict[str, Any],
    retrieved_cases: list[dict[str, Any]],
    *,
    workflow_id: str,
) -> dict[str, Any]:
    concern = _label(query_record.get("concern_type_gold")) or "unknown"
    strategy = _recommended_strategy(query_record, retrieved_cases)
    risk_type = RISK_TYPES.get(concern, "unknown")
    evidence_plan = list(EVIDENCE_TEMPLATES.get(concern, ["Identify the evidence needed to answer the reviewer."]))
    if strategy in {"add_new_experiment", "add_new_analysis"}:
        evidence_plan.append("Separate completed work from proposed work and require exact artifact locations.")
    if strategy == "narrow_claim_scope":
        evidence_plan.append("Mark any overbroad claim that should be softened or scoped.")

    return {
        "workflow_id": workflow_id,
        "concern_type": concern,
        "risk_type": risk_type,
        "recommended_response_strategy": strategy,
        "strategy_guidance": STRATEGY_GUIDANCE.get(strategy, "Use a specific, evidence-grounded response."),
        "concern_summary": _preview(_query_text(query_record), limit=500),
        "evidence_plan": evidence_plan,
        "case_provenance": [_case_provenance(item) for item in retrieved_cases],
        "forbidden_actions": list(FORBIDDEN_ACTIONS),
        "status": "model_assisted_plan_needs_human_confirmation",
    }


def generate_workflow_trace(
    query_record: dict[str, Any],
    retrieved_cases: list[dict[str, Any]],
    *,
    workflow_id: str,
    outline_client: Any | None,
    model_id: str,
    retrieval_method: str,
) -> dict[str, Any]:
    evidence_plan = build_evidence_plan(query_record, retrieved_cases, workflow_id=workflow_id)
    outline, outline_error = _generate_outline(query_record, evidence_plan, outline_client)
    integrity_check = _integrity_check(outline, evidence_plan)
    stage_status = "completed" if outline_error is None else "completed_with_outline_error"
    return {
        "workflow_id": workflow_id,
        "workflow_version": WORKFLOW_VERSION,
        "created_at": datetime.now(UTC).isoformat(),
        "stage_status": stage_status,
        "sample_id": query_record.get("sample_id"),
        "pair_id": query_record.get("pair_id"),
        "paper_id": query_record.get("paper_id"),
        "doi": query_record.get("doi"),
        "title": query_record.get("title"),
        "journal": query_record.get("journal"),
        "journal_family": query_record.get("journal_family"),
        "input_review_context": _preview(_query_text(query_record), limit=900),
        "input_author_response_preview": _preview(
            str(query_record.get("author_response") or query_record.get("author_response_preview") or ""),
            limit=700,
        ),
        "labels": {
            "concern_type": query_record.get("concern_type_gold"),
            "response_strategy": query_record.get("response_strategy_gold"),
            "label_status": query_record.get("mini_gold_status")
            or query_record.get("validation_source")
            or "model_revised_needs_human_confirmation",
        },
        "agents": {
            "review_understanding_agent": {
                "output": {
                    "concern_summary": evidence_plan["concern_summary"],
                    "concern_type": evidence_plan["concern_type"],
                }
            },
            "concern_risk_classifier": {
                "output": {
                    "risk_type": evidence_plan["risk_type"],
                    "recommended_response_strategy": evidence_plan["recommended_response_strategy"],
                }
            },
            "case_retrieval_agent": {
                "retrieval_method": retrieval_method,
                "top_k": len(retrieved_cases),
                "retrieved_cases": retrieved_cases,
            },
            "evidence_planner": {"output": evidence_plan},
            "rebuttal_drafting_assistant": {
                "model_id": model_id,
                "output": outline,
                "error": outline_error,
                "status": "model_assisted_outline_needs_human_confirmation",
            },
            "tone_and_structure_editor": {
                "output": {
                    "tone_guidance": outline.get("tone_guidance", []),
                    "structure_checks": [
                        "Start from the reviewer concern.",
                        "Separate response, evidence, and manuscript change.",
                        "Keep disagreement specific and evidence-grounded.",
                    ],
                }
            },
            "integrity_overclaim_checker": {"output": integrity_check},
        },
        "evidence_plan": evidence_plan,
        "outline": outline,
        "integrity_check": integrity_check,
        "evaluation_signals": _evaluation_signals(query_record, retrieved_cases, integrity_check, outline_error),
        "source_trace": {
            "source_json_path": query_record.get("source_json_path"),
            "source_field": query_record.get("source_field"),
            "source_offsets": query_record.get("source_offsets"),
            "retrieval_case_source_paths": sorted(
                {
                    str(item.get("source_json_path") or "")
                    for item in retrieved_cases
                    if item.get("source_json_path")
                }
            ),
        },
        "notes": [
            "Trace is generated from model-revised candidate mini-gold labels, not final human gold.",
            "Outline is assistant output for human review, not a final rebuttal.",
        ],
    }


def run_author_rebuttal_workflow(
    input_dir: str | Path = DEFAULT_INPUT_DIR,
    output_dir: str | Path = DEFAULT_OUTPUT_DIR,
    *,
    outline_client: Any | None = None,
    model_id: str = "deepseek-v3",
    top_k: int = DEFAULT_TOP_K,
    retrieval_method: str = DEFAULT_RETRIEVAL_METHOD,
    limit: int | None = None,
    resume: bool = True,
) -> dict[str, Any]:
    source_dir = resolve_project_path(input_dir)
    target_dir = resolve_project_path(output_dir)
    target_dir.mkdir(parents=True, exist_ok=True)
    query_records = list(read_jsonl(source_dir / "phase1_mini_gold_seed_50.jsonl"))
    index_records = list(read_jsonl(source_dir / "phase1_retrieval_candidate_pool.jsonl"))
    selected_records = query_records[:limit] if limit is not None else query_records
    active_client = outline_client
    if active_client is None:
        active_client = build_client_from_environment()

    trace_path = target_dir / "workflow_traces.jsonl"
    error_path = target_dir / "workflow_errors.jsonl"
    existing_traces = _read_existing_traces(trace_path) if resume else {}
    traces: list[dict[str, Any]] = []
    errors: list[dict[str, Any]] = []

    for index, record in enumerate(selected_records, start=1):
        pair_id = str(record.get("pair_id") or "")
        if resume and pair_id in existing_traces:
            traces.append(existing_traces[pair_id])
            continue
        workflow_id = f"ara-v2709-{index:04d}-{_safe_id(pair_id)}"
        try:
            retrieved = retrieve_cases(record, index_records, method=retrieval_method, top_k=top_k)
            traces.append(
                generate_workflow_trace(
                    record,
                    retrieved,
                    workflow_id=workflow_id,
                    outline_client=active_client,
                    model_id=model_id,
                    retrieval_method=retrieval_method,
                )
            )
        except Exception as exc:  # noqa: BLE001 - keep per-row failures inspectable.
            errors.append(
                {
                    "workflow_id": workflow_id,
                    "sample_id": record.get("sample_id"),
                    "pair_id": record.get("pair_id"),
                    "error": str(exc),
                }
            )

    write_jsonl(trace_path, traces)
    write_jsonl(error_path, errors)
    _write_csv(target_dir / "workflow_traces.csv", traces)
    summary = _workflow_summary(
        source_dir=source_dir,
        target_dir=target_dir,
        query_count=len(selected_records),
        pool_count=len(index_records),
        top_k=top_k,
        retrieval_method=retrieval_method,
        model_id=model_id,
        traces=traces,
        errors=errors,
    )
    (target_dir / "workflow_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    (target_dir / "workflow_report.md").write_text(_workflow_report(summary), encoding="utf-8")
    return summary


def _generate_outline(
    query_record: dict[str, Any],
    evidence_plan: dict[str, Any],
    outline_client: Any | None,
) -> tuple[dict[str, Any], str | None]:
    fallback = _fallback_outline(query_record, evidence_plan)
    if outline_client is None:
        return fallback, "outline_client_not_configured"
    try:
        result = outline_client.create_chat_completion(
            _outline_messages(query_record, evidence_plan),
            response_format={"type": "json_object"},
            temperature=0.0,
        )
        if not isinstance(result, dict):
            raise ValueError("outline result is not a JSON object")
        return _normalize_outline(result, fallback), None
    except Exception as exc:  # noqa: BLE001 - workflow should preserve traceability on model failure.
        return fallback, str(exc)


def _outline_messages(query_record: dict[str, Any], evidence_plan: dict[str, Any]) -> list[dict[str, str]]:
    payload = {
        "task": "generate_author_rebuttal_outline_for_human_review",
        "rules": [
            "Return only one JSON object.",
            "Do not fabricate experiments, analyses, datasets, results, citations, or manuscript changes.",
            "Do not write a final rebuttal; write an outline and planning guidance for the author.",
            "Use retrieved case provenance only as examples, not as evidence for the current paper.",
            "Flag missing evidence and overclaim risk explicitly.",
        ],
        "schema": {
            "outline_sections": [
                {
                    "heading": "string",
                    "purpose": "string",
                    "draft_points": ["string"],
                }
            ],
            "evidence_needed": ["string"],
            "tone_guidance": ["string"],
            "case_citations": ["retrieved pair_id"],
            "integrity_warnings": ["string"],
            "confidence": "float 0..1",
        },
        "review_context": _preview(_query_text(query_record), limit=1200),
        "current_author_response_preview": _preview(
            str(query_record.get("author_response") or query_record.get("author_response_preview") or ""),
            limit=900,
        ),
        "evidence_plan": evidence_plan,
    }
    return [
        {
            "role": "system",
            "content": (
                "You are an Author Rebuttal Assistant for scholarly peer review. "
                "You help authors structure evidence-grounded responses, and you must not invent facts."
            ),
        },
        {"role": "user", "content": json.dumps(payload, ensure_ascii=False, sort_keys=True)},
    ]


def _fallback_outline(query_record: dict[str, Any], evidence_plan: dict[str, Any]) -> dict[str, Any]:
    strategy = evidence_plan["recommended_response_strategy"]
    return {
        "outline_sections": [
            {
                "heading": "Restate the reviewer concern",
                "purpose": "Show that the specific concern has been understood.",
                "draft_points": [evidence_plan["concern_summary"]],
            },
            {
                "heading": "Response strategy",
                "purpose": "Choose an evidence-grounded response path.",
                "draft_points": [STRATEGY_GUIDANCE.get(strategy, "Use a specific response strategy.")],
            },
            {
                "heading": "Evidence and manuscript changes",
                "purpose": "List evidence, changes, and unresolved gaps for author confirmation.",
                "draft_points": list(evidence_plan["evidence_plan"]),
            },
        ],
        "evidence_needed": list(evidence_plan["evidence_plan"]),
        "tone_guidance": ["Be specific.", "Avoid defensiveness.", "Mark limits clearly."],
        "case_citations": [case["pair_id"] for case in evidence_plan["case_provenance"][:3]],
        "integrity_warnings": list(FORBIDDEN_ACTIONS),
        "confidence": 0.35,
        "generation_mode": "local_fallback",
    }


def _normalize_outline(result: dict[str, Any], fallback: dict[str, Any]) -> dict[str, Any]:
    outline = dict(fallback)
    for key in ("outline_sections", "evidence_needed", "tone_guidance", "case_citations", "integrity_warnings"):
        value = result.get(key)
        if isinstance(value, list):
            outline[key] = value
    confidence = result.get("confidence", fallback.get("confidence", 0.0))
    try:
        outline["confidence"] = max(0.0, min(1.0, float(confidence)))
    except (TypeError, ValueError):
        outline["confidence"] = fallback.get("confidence", 0.0)
    outline["generation_mode"] = "api_model"
    return outline


def _integrity_check(outline: dict[str, Any], evidence_plan: dict[str, Any]) -> dict[str, Any]:
    warnings = [str(item) for item in outline.get("integrity_warnings", [])]
    evidence_needed = [str(item) for item in outline.get("evidence_needed", [])]
    issues = []
    if not warnings:
        issues.append("missing_integrity_warnings")
    if not evidence_needed:
        issues.append("missing_evidence_needed")
    if not outline.get("outline_sections"):
        issues.append("missing_outline_sections")
    forbidden = list(evidence_plan.get("forbidden_actions") or FORBIDDEN_ACTIONS)
    return {
        "passed": not issues,
        "issues": issues,
        "forbidden_actions": forbidden,
        "requires_human_confirmation": True,
    }


def _evaluation_signals(
    query_record: dict[str, Any],
    retrieved_cases: list[dict[str, Any]],
    integrity_check: dict[str, Any],
    outline_error: str | None,
) -> dict[str, Any]:
    return {
        "strategy_hit_at_5": _yes_no(_has_label(retrieved_cases[:5], "response_strategy_gold", query_record.get("response_strategy_gold"))),
        "concern_hit_at_5": _yes_no(_has_label(retrieved_cases[:5], "concern_type_gold", query_record.get("concern_type_gold"))),
        "joint_hit_at_5": _yes_no(
            any(
                _label(item.get("response_strategy_gold")) == _label(query_record.get("response_strategy_gold"))
                and _label(item.get("concern_type_gold")) == _label(query_record.get("concern_type_gold"))
                for item in retrieved_cases[:5]
            )
        ),
        "same_concern_case_count": sum(
            1
            for item in retrieved_cases[:5]
            if _label(item.get("concern_type_gold")) == _label(query_record.get("concern_type_gold"))
        ),
        "distinct_strategy_count": len(
            {
                _label(item.get("response_strategy_gold"))
                for item in retrieved_cases[:5]
                if _label(item.get("response_strategy_gold"))
            }
        ),
        "integrity_passed": _yes_no(bool(integrity_check.get("passed"))),
        "outline_error": outline_error,
    }


def _workflow_summary(
    *,
    source_dir: Path,
    target_dir: Path,
    query_count: int,
    pool_count: int,
    top_k: int,
    retrieval_method: str,
    model_id: str,
    traces: list[dict[str, Any]],
    errors: list[dict[str, Any]],
) -> dict[str, Any]:
    completed = [trace for trace in traces if trace.get("stage_status") == "completed"]
    completed_with_outline_error = [
        trace for trace in traces if trace.get("stage_status") == "completed_with_outline_error"
    ]
    evaluation = _aggregate_evaluation(traces)
    return {
        "workflow_id": WORKFLOW_VERSION,
        "input": {
            "input_dir": project_relative_path(source_dir),
            "query_count": query_count,
            "retrieval_pool_count": pool_count,
            "label_status": "model_revised_candidate_needs_human_confirmation",
        },
        "configuration": {
            "retrieval_method": retrieval_method,
            "top_k": top_k,
            "outline_model_id": model_id,
        },
        "workflow": {
            "trace_count": len(traces),
            "completed_count": len(completed),
            "completed_with_outline_error_count": len(completed_with_outline_error),
            "error_count": len(errors),
            "risk_type_counts": dict(
                Counter(
                    trace.get("evidence_plan", {}).get("risk_type", "unknown")
                    for trace in traces
                )
            ),
            "recommended_strategy_counts": dict(
                Counter(
                    trace.get("evidence_plan", {}).get("recommended_response_strategy", "unknown")
                    for trace in traces
                )
            ),
        },
        "evaluation": evaluation,
        "files": {
            "trace_jsonl": project_relative_path(target_dir / "workflow_traces.jsonl"),
            "trace_csv": project_relative_path(target_dir / "workflow_traces.csv"),
            "errors_jsonl": project_relative_path(target_dir / "workflow_errors.jsonl"),
            "summary": project_relative_path(target_dir / "workflow_summary.json"),
            "report": project_relative_path(target_dir / "workflow_report.md"),
        },
        "notes": [
            "This is a recordable and traceable assistant workflow over model-revised candidate labels.",
            "It is not a final human-evaluated benchmark or a final rebuttal-writing system.",
        ],
    }


def _aggregate_evaluation(traces: list[dict[str, Any]]) -> dict[str, Any]:
    denominator = len(traces) or 1
    signals = [trace.get("evaluation_signals", {}) for trace in traces]
    return {
        "strategy_hit_at_5_rate": sum(1 for signal in signals if signal.get("strategy_hit_at_5") == "yes") / denominator,
        "concern_hit_at_5_rate": sum(1 for signal in signals if signal.get("concern_hit_at_5") == "yes") / denominator,
        "joint_hit_at_5_rate": sum(1 for signal in signals if signal.get("joint_hit_at_5") == "yes") / denominator,
        "integrity_pass_rate": sum(1 for signal in signals if signal.get("integrity_passed") == "yes") / denominator,
        "average_same_concern_case_count": (
            sum(int(signal.get("same_concern_case_count") or 0) for signal in signals) / denominator
        ),
        "average_distinct_strategy_count": (
            sum(int(signal.get("distinct_strategy_count") or 0) for signal in signals) / denominator
        ),
    }


def _workflow_report(summary: dict[str, Any]) -> str:
    evaluation = summary["evaluation"]
    workflow = summary["workflow"]
    lines = [
        "# Author Rebuttal Assistant Workflow Report",
        "",
        "## Scope",
        "",
        "This report records a traceable, evaluable workflow over the v2709 model-revised mini-gold seed.",
        "The outputs require human confirmation and should not be treated as final rebuttal text.",
        "",
        "## Inputs",
        "",
        f"- Query rows: `{summary['input']['query_count']}`",
        f"- Retrieval pool rows: `{summary['input']['retrieval_pool_count']}`",
        f"- Retrieval method: `{summary['configuration']['retrieval_method']}`",
        f"- Top-k: `{summary['configuration']['top_k']}`",
        f"- Outline model: `{summary['configuration']['outline_model_id']}`",
        "",
        "## Workflow Status",
        "",
        f"- Trace count: `{workflow['trace_count']}`",
        f"- Completed count: `{workflow['completed_count']}`",
        f"- Completed with outline error count: `{workflow['completed_with_outline_error_count']}`",
        f"- Error count: `{workflow['error_count']}`",
        "",
        "## Evaluation Signals",
        "",
        f"- Strategy hit@5: `{evaluation['strategy_hit_at_5_rate']:.4f}`",
        f"- Concern hit@5: `{evaluation['concern_hit_at_5_rate']:.4f}`",
        f"- Joint hit@5: `{evaluation['joint_hit_at_5_rate']:.4f}`",
        f"- Integrity pass rate: `{evaluation['integrity_pass_rate']:.4f}`",
        f"- Avg same-concern cases: `{evaluation['average_same_concern_case_count']:.2f}`",
        f"- Avg distinct strategies: `{evaluation['average_distinct_strategy_count']:.2f}`",
        "",
        "## Files",
        "",
    ]
    for key, value in summary["files"].items():
        lines.append(f"- `{key}`: `{value}`")
    lines.extend(["", "## Caveats", ""])
    for note in summary["notes"]:
        lines.append(f"- {note}")
    return "\n".join(lines) + "\n"


def _case_provenance(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "rank": item.get("rank"),
        "pair_id": item.get("pair_id"),
        "sample_id": item.get("sample_id"),
        "paper_id": item.get("paper_id"),
        "doi": item.get("doi"),
        "title": item.get("title"),
        "journal": item.get("journal"),
        "concern_type": item.get("concern_type_gold"),
        "response_strategy": item.get("response_strategy_gold"),
        "score": item.get("score"),
        "hybrid_score": item.get("hybrid_score"),
        "source_json_path": item.get("source_json_path"),
        "source_field": item.get("source_field"),
        "source_offsets": item.get("source_offsets"),
        "review_context_preview": item.get("review_context_preview"),
        "author_response_preview": item.get("author_response_preview"),
    }


def _recommended_strategy(query_record: dict[str, Any], retrieved_cases: list[dict[str, Any]]) -> str:
    query_strategy = _label(query_record.get("response_strategy_gold"))
    if query_strategy:
        return query_strategy
    strategies = [
        _label(case.get("response_strategy_gold"))
        for case in retrieved_cases
        if _label(case.get("response_strategy_gold"))
    ]
    if not strategies:
        return "unknown"
    return Counter(strategies).most_common(1)[0][0]


def _read_existing_traces(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    traces = {}
    for trace in read_jsonl(path):
        pair_id = str(trace.get("pair_id") or "")
        if pair_id:
            traces[pair_id] = trace
    return traces


def _write_csv(path: Path, records: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = _csv_fields(records)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="ignore")
        writer.writeheader()
        for record in records:
            row = dict(record)
            for key, value in list(row.items()):
                if isinstance(value, (dict, list)):
                    row[key] = json.dumps(value, ensure_ascii=False, sort_keys=True)
            writer.writerow(row)


def _csv_fields(records: list[dict[str, Any]]) -> list[str]:
    preferred = [
        "workflow_id",
        "workflow_version",
        "created_at",
        "stage_status",
        "sample_id",
        "pair_id",
        "paper_id",
        "doi",
        "title",
        "journal",
        "journal_family",
        "input_review_context",
        "input_author_response_preview",
        "labels",
        "evaluation_signals",
        "integrity_check",
        "evidence_plan",
        "outline",
        "agents",
        "source_trace",
        "notes",
    ]
    present = set().union(*(record.keys() for record in records)) if records else set()
    extras = sorted(present - set(preferred))
    return [field for field in preferred if field in present] + extras


def _query_text(record: dict[str, Any]) -> str:
    return str(record.get("review_context") or record.get("review_context_preview") or "")


def _label(value: Any) -> str:
    return str(value or "").strip()


def _safe_id(value: str) -> str:
    safe = "".join(char if char.isalnum() else "-" for char in str(value or "unknown"))
    return "-".join(part for part in safe.split("-") if part)[:80] or "unknown"


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def main() -> None:
    parser = argparse.ArgumentParser(description="Run traceable Author Rebuttal Assistant workflow over v2709.")
    parser.add_argument("--input-dir", default=str(DEFAULT_INPUT_DIR))
    parser.add_argument("--output-dir", default=str(DEFAULT_OUTPUT_DIR))
    parser.add_argument("--top-k", type=int, default=DEFAULT_TOP_K)
    parser.add_argument("--retrieval-method", default=DEFAULT_RETRIEVAL_METHOD)
    parser.add_argument("--model-id", default="deepseek-v3")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--no-resume", action="store_true")
    args = parser.parse_args()
    summary = run_author_rebuttal_workflow(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        top_k=args.top_k,
        retrieval_method=args.retrieval_method,
        model_id=args.model_id,
        limit=args.limit,
        resume=not args.no_resume,
    )
    print(json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
