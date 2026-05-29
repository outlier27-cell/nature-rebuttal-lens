from typing import Any


MIN_ALIGNMENT_COVERAGE = 0.7
MAX_UNRESOLVED_ALIGNMENT_RATIO = 0.3
MAX_SKILL_CARD_REVIEW_COUNT = 0
MAX_JUDGE_WARNING_RATIO = 0.1


def build_readiness_summary(
    metrics: dict[str, Any],
    api_configured: bool,
    api_execution_wired: bool = False,
    quality_gate_blocked: bool = False,
) -> dict[str, Any]:
    interaction_count = int(metrics.get("interaction_count", 0))
    skill_card_count = int(metrics.get("skill_card_count", 0))
    validated_skill_count = int(metrics.get("validated_skill_count", 0))
    candidate_skill_count = int(metrics.get("candidate_skill_count", 0))
    ready_for_api_enrichment_count = int(metrics.get("ready_for_api_enrichment_count", 0))
    semantic_enrichment_review_count = int(metrics.get("semantic_enrichment_review_count", 0))
    api_alignment_request_count = int(metrics.get("api_alignment_request_count", 0))
    api_skill_enrichment_request_count = int(metrics.get("api_skill_enrichment_request_count", 0))
    api_handoff_request_count = int(metrics.get("api_handoff_request_count", 0))
    api_alignment_result_count = int(metrics.get("api_alignment_result_count", 0))
    api_skill_enrichment_result_count = int(metrics.get("api_skill_enrichment_result_count", 0))
    api_error_count = int(metrics.get("api_error_count", 0))
    judge_error_count = int(metrics.get("judge_error_count", 0))
    judge_warning_count = int(metrics.get("judge_warning_count", 0))
    skill_card_review_count = int(metrics.get("skill_card_review_count", 0))
    ambiguous_count = int(metrics.get("ambiguous_count", 0))
    missing_response_count = int(metrics.get("missing_response_count", 0))
    matched_count = int(metrics.get("matched_count", 0))
    alignment_coverage = matched_count / interaction_count if interaction_count else 0.0
    unresolved_alignment_ratio = (
        (ambiguous_count + missing_response_count) / interaction_count if interaction_count else 0.0
    )
    unresolved_alignment_count = ambiguous_count + missing_response_count
    unresolved_alignment_queued = (
        unresolved_alignment_count > 0 and api_alignment_request_count >= unresolved_alignment_count
    )
    alignment_api_executed = (
        api_alignment_request_count == 0
        or api_alignment_result_count >= api_alignment_request_count
    )
    skill_api_executed = (
        api_skill_enrichment_request_count == 0
        or api_skill_enrichment_result_count >= api_skill_enrichment_request_count
    )
    warning_ratio = judge_warning_count / max(interaction_count + skill_card_count, 1)

    pipeline_artifacts_status = "ready" if interaction_count > 0 and skill_card_count > 0 else "blocked"
    if quality_gate_blocked:
        pipeline_artifacts_status = "blocked"
    schema_status = "ready" if judge_error_count == 0 else "blocked"
    if not interaction_count:
        alignment_status = "blocked"
    elif unresolved_alignment_queued:
        alignment_status = "queued_for_api_resolution"
    elif (
        alignment_coverage < MIN_ALIGNMENT_COVERAGE
        or unresolved_alignment_ratio > MAX_UNRESOLVED_ALIGNMENT_RATIO
    ):
        alignment_status = "needs_quality_review"
    elif ambiguous_count or missing_response_count:
        alignment_status = "ready_with_warnings"
    else:
        alignment_status = "ready"

    if skill_card_count < 10:
        skill_status = "needs_more_evidence"
    elif candidate_skill_count > 0:
        skill_status = "needs_quality_review"
    elif (
        validated_skill_count >= 10
        and ready_for_api_enrichment_count >= 10
        and skill_card_review_count <= semantic_enrichment_review_count
    ):
        skill_status = "ready"
    elif skill_card_review_count > MAX_SKILL_CARD_REVIEW_COUNT:
        skill_status = "needs_quality_review"
    else:
        skill_status = "ready"

    if quality_gate_blocked:
        alignment_status = "not_run_due_to_segmentation_gate"
        skill_status = "not_run_due_to_segmentation_gate"

    if api_configured and api_execution_wired:
        if api_error_count > 0:
            semantic_status = "api_execution_errors"
            expert_status = "api_execution_errors"
        elif not alignment_api_executed or not skill_api_executed:
            semantic_status = "api_configured_pending_execution"
            expert_status = "api_configured_pending_execution"
        else:
            semantic_status = "ready"
            expert_status = "ready"
    elif api_configured:
        semantic_status = "api_configured_provider_not_wired"
        expert_status = "api_configured_provider_not_wired"
    else:
        semantic_status = "pending_api"
        expert_status = "pending_api"

    checks = {
        "pipeline_artifacts": pipeline_artifacts_status,
        "schema_and_grounding": schema_status,
        "local_alignment": alignment_status,
        "skill_induction": skill_status,
        "semantic_annotation": semantic_status,
        "expert_judging": expert_status,
    }
    remaining_blockers = []
    if not api_configured:
        remaining_blockers.append("external_model_api")
    elif not api_execution_wired:
        remaining_blockers.append("api_provider_execution_hooks")
    if api_configured and api_execution_wired and api_error_count > 0:
        remaining_blockers.append("api_execution_errors")
    if semantic_enrichment_review_count > 0 and not api_execution_wired and not quality_gate_blocked:
        remaining_blockers.append("semantic_skill_enrichment_api")
    elif api_configured and api_execution_wired and not skill_api_executed and not quality_gate_blocked:
        remaining_blockers.append("semantic_skill_enrichment_api_execution")
    if unresolved_alignment_queued and not api_execution_wired and not quality_gate_blocked:
        remaining_blockers.append("semantic_alignment_api")
    elif api_configured and api_execution_wired and not alignment_api_executed and not quality_gate_blocked:
        remaining_blockers.append("semantic_alignment_api_execution")
    if checks["pipeline_artifacts"] == "blocked":
        remaining_blockers.append("pipeline_artifacts")
    if quality_gate_blocked:
        remaining_blockers.append("segmentation_quality_gate")
    if checks["schema_and_grounding"] == "blocked":
        remaining_blockers.append("schema_or_grounding_errors")
    if checks["local_alignment"] in {"blocked", "needs_quality_review"}:
        remaining_blockers.append("alignment_quality_review")
    if checks["skill_induction"] in {"needs_more_evidence", "needs_quality_review"}:
        remaining_blockers.append("skill_card_quality_review")
    if (
        judge_warning_count
        and warning_ratio > MAX_JUDGE_WARNING_RATIO
        and not unresolved_alignment_queued
        and not quality_gate_blocked
    ):
        remaining_blockers.append("judge_warning_review")

    api_only_blockers = {
        "external_model_api",
        "semantic_skill_enrichment_api",
        "semantic_alignment_api",
    }
    api_execution_only_blockers = {
        "semantic_skill_enrichment_api_execution",
        "semantic_alignment_api_execution",
    }

    if remaining_blockers and set(remaining_blockers).issubset(api_only_blockers):
        overall_status = "api_ready_pending_key"
    elif remaining_blockers and set(remaining_blockers).issubset(api_execution_only_blockers):
        overall_status = "api_configured_pending_execution"
    elif "external_model_api" in remaining_blockers and any(
        blocker in remaining_blockers
        for blocker in ("alignment_quality_review", "skill_card_quality_review", "judge_warning_review")
    ):
        overall_status = "pipeline_ready_needs_api_and_quality_review"
    elif "api_provider_execution_hooks" in remaining_blockers and len(remaining_blockers) == 1:
        overall_status = "api_configured_provider_not_wired"
    elif "api_execution_errors" in remaining_blockers:
        overall_status = "api_execution_failed"
    elif not remaining_blockers:
        overall_status = "ready"
    else:
        overall_status = "blocked"

    return {
        "overall_status": overall_status,
        "remaining_blockers": remaining_blockers,
        "readiness_checks": checks,
        "metrics": {
            "interaction_count": interaction_count,
            "skill_card_count": skill_card_count,
            "validated_skill_count": validated_skill_count,
            "candidate_skill_count": candidate_skill_count,
            "ready_for_api_enrichment_count": ready_for_api_enrichment_count,
            "semantic_enrichment_review_count": semantic_enrichment_review_count,
            "api_alignment_request_count": api_alignment_request_count,
            "api_skill_enrichment_request_count": api_skill_enrichment_request_count,
            "api_handoff_request_count": api_handoff_request_count,
            "api_alignment_result_count": api_alignment_result_count,
            "api_skill_enrichment_result_count": api_skill_enrichment_result_count,
            "api_error_count": api_error_count,
            "judge_error_count": judge_error_count,
            "judge_warning_count": judge_warning_count,
            "skill_card_review_count": skill_card_review_count,
            "matched_count": matched_count,
            "ambiguous_count": ambiguous_count,
            "missing_response_count": missing_response_count,
            "alignment_coverage": round(alignment_coverage, 4),
            "unresolved_alignment_ratio": round(unresolved_alignment_ratio, 4),
            "judge_warning_ratio": round(warning_ratio, 4),
        },
    }


def render_readiness_report(summary: dict[str, Any]) -> str:
    check_lines = [
        f"- {name}: {status}" for name, status in summary["readiness_checks"].items()
    ]
    metric_lines = [f"- {name}: {value}" for name, value in summary["metrics"].items()]
    blockers = summary["remaining_blockers"] or ["none"]
    blocker_lines = [f"- {blocker}" for blocker in blockers]
    return (
        "# System Readiness Report\n\n"
        "## Summary\n\n"
        f"- Overall status: `{summary['overall_status']}`\n\n"
        "## Remaining Blockers\n\n"
        + "\n".join(blocker_lines)
        + "\n\n"
        "## Readiness Checks\n\n"
        + "\n".join(check_lines)
        + "\n\n"
        "## Metrics\n\n"
        + "\n".join(metric_lines)
        + "\n"
    )
