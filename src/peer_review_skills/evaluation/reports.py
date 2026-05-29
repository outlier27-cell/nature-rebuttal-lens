from pathlib import Path
from typing import Any


def _render_counts(counts: dict[str, int] | dict[int, int], limit: int = 20) -> str:
    if not counts:
        return "- none\n"
    lines = []
    for key, value in list(counts.items())[:limit]:
        lines.append(f"- {key}: {value}")
    return "\n".join(lines) + "\n"


def render_data_audit_report(audit: dict[str, Any]) -> str:
    return (
        "# Data Audit Report\n\n"
        "## Inputs\n\n"
        f"- Raw data dir: `{audit['raw_data_dir']}`\n"
        f"- Raw index path: `{audit['raw_index_path']}`\n\n"
        "## Summary\n\n"
        f"- Paper count: {audit['paper_count']}\n"
        f"- Index record count: {audit.get('index_record_count', 'n/a')}\n"
        f"- Report block count: {audit['report_block_count']}\n"
        f"- Author response field count: {audit['author_response_field_count']}\n"
        f"- Peer review file block paper count: {audit['peer_review_file_block_paper_count']}\n"
        f"- Response presence count: {audit.get('response_presence_count', 0)}\n"
        f"- Decision presence count: {audit.get('decision_presence_count', 0)}\n"
        f"- Scientific Reports count: {audit.get('scientific_reports_count', 0)}\n\n"
        "## Marker Coverage\n\n"
        f"- Response marker paper count: {audit['response_marker_paper_count']}\n"
        f"- Reviewer marker paper count: {audit['reviewer_marker_paper_count']}\n"
        f"- Editor marker paper count: {audit['editor_marker_paper_count']}\n\n"
        "## Journal Counts\n\n"
        f"{_render_counts(audit.get('journal_counts', {}))}\n"
        "## Publisher Family Counts\n\n"
        f"{_render_counts(audit.get('publisher_family_counts', {}))}\n"
        "## Journal Family Counts\n\n"
        f"{_render_counts(audit.get('journal_family_counts', {}))}\n"
        "## Interaction Level Counts\n\n"
        f"{_render_counts(audit.get('interaction_level_counts', {}))}\n"
        "## Quality Counts\n\n"
        f"{_render_counts(audit.get('quality_counts', {}))}\n"
        "## Reviewer Report Count Distribution\n\n"
        f"{_render_counts(audit.get('reviewer_report_count_distribution', {}), limit=100)}"
    )


def write_text(path: str | Path, text: str) -> None:
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(text, encoding="utf-8", newline="\n")


def _bucket_confidence(value: float) -> str:
    if value < 0.5:
        return "0.00-0.49"
    if value < 0.7:
        return "0.50-0.69"
    if value < 0.9:
        return "0.70-0.89"
    return "0.90-1.00"


def _failure_mode(unit: dict[str, Any]) -> str:
    if unit.get("speaker_type") == "unknown":
        return "unknown_speaker"
    if float(unit.get("segmentation_confidence", 0.0)) < 0.7:
        return "low_confidence"
    text = str(unit.get("text") or "")
    if "response:" in text.lower() and unit.get("speaker_type") == "reviewer":
        return "mixed_response_in_reviewer_span"
    return "review_required"


def build_segmentation_diagnostics(units: list[dict[str, Any]]) -> dict[str, Any]:
    speaker_counts: dict[str, int] = {}
    method_counts: dict[str, int] = {}
    confidence_distribution: dict[str, int] = {}
    review_queue_units: list[dict[str, Any]] = []
    failure_modes: dict[str, int] = {}

    for unit in units:
        speaker = str(unit.get("speaker_type") or "unknown")
        method = str(unit.get("segmentation_method") or "unknown")
        confidence = float(unit.get("segmentation_confidence", 0.0))
        speaker_counts[speaker] = speaker_counts.get(speaker, 0) + 1
        method_counts[method] = method_counts.get(method, 0) + 1
        bucket = _bucket_confidence(confidence)
        confidence_distribution[bucket] = confidence_distribution.get(bucket, 0) + 1

        needs_review = (
            speaker == "unknown"
            or confidence < 0.7
            or _failure_mode(unit) == "mixed_response_in_reviewer_span"
        )
        if needs_review:
            mode = _failure_mode(unit)
            failure_modes[mode] = failure_modes.get(mode, 0) + 1
            queue_item = dict(unit)
            queue_item["review_reason"] = mode
            review_queue_units.append(queue_item)

    return {
        "unit_count": len(units),
        "speaker_counts": dict(sorted(speaker_counts.items())),
        "method_counts": dict(sorted(method_counts.items())),
        "confidence_distribution": dict(sorted(confidence_distribution.items())),
        "review_queue_units": review_queue_units,
        "failure_modes": dict(sorted(failure_modes.items())),
        "low_confidence_examples": review_queue_units[:20],
    }


def render_segmentation_report(diagnostics: dict[str, Any]) -> str:
    examples = diagnostics.get("low_confidence_examples", [])
    example_lines = []
    for item in examples[:10]:
        text = str(item.get("text") or "").replace("\n", " ")[:240]
        example_lines.append(
            f"- {item.get('unit_id')} ({item.get('review_reason')}): {text}"
        )
    if not example_lines:
        example_lines.append("- none")

    return (
        "# Segmentation Report\n\n"
        "## Summary\n\n"
        f"- Unit count: {diagnostics['unit_count']}\n"
        f"- Review queue unit count: {len(diagnostics.get('review_queue_units', []))}\n\n"
        "## Speaker Counts\n\n"
        f"{_render_counts(diagnostics.get('speaker_counts', {}))}\n"
        "## Segmentation Method Counts\n\n"
        f"{_render_counts(diagnostics.get('method_counts', {}))}\n"
        "## Confidence Distribution\n\n"
        f"{_render_counts(diagnostics.get('confidence_distribution', {}))}\n"
        "## Failure Modes\n\n"
        f"{_render_counts(diagnostics.get('failure_modes', {}))}\n"
        "## Low-Confidence Examples\n\n"
        + "\n".join(example_lines)
        + "\n"
    )


def render_annotation_report(summary: dict[str, Any]) -> str:
    return (
        "# Annotation Report\n\n"
        "## Summary\n\n"
        f"- Reviewer annotation count: {summary['reviewer_annotation_count']}\n"
        f"- Author annotation count: {summary['author_annotation_count']}\n"
        f"- Low-confidence annotation count: {summary['low_confidence_count']}\n"
        f"- Skipped units: {summary['skipped_units']}\n"
        f"- Annotation method: `rule_based_v1`\n\n"
        "## Concern Type Counts\n\n"
        f"{_render_counts(summary.get('concern_type_counts', {}), limit=50)}\n"
        "## Reviewer Sentiment Counts\n\n"
        f"{_render_counts(summary.get('reviewer_sentiment_counts', {}), limit=20)}\n"
        "## Reviewer Severity Counts\n\n"
        f"{_render_counts(summary.get('reviewer_severity_counts', {}), limit=20)}\n"
        "## Author Strategy Counts\n\n"
        f"{_render_counts(summary.get('author_strategy_counts', {}), limit=50)}\n"
        "## Response Stance Counts\n\n"
        f"{_render_counts(summary.get('response_stance_counts', {}), limit=20)}"
    )


def render_alignment_report(summary: dict[str, Any]) -> str:
    return (
        "# Alignment Report\n\n"
        "## Summary\n\n"
        f"- Interaction count: {summary['interaction_count']}\n"
        f"- Review queue count: {summary['review_queue_count']}\n"
        f"- Alignment method: `rule_based_v1`\n\n"
        "## Status Counts\n\n"
        f"{_render_counts(summary.get('status_counts', {}), limit=20)}\n"
        "## Method Counts\n\n"
        f"{_render_counts(summary.get('method_counts', {}), limit=20)}\n"
        "## Concern Type Counts\n\n"
        f"{_render_counts(summary.get('concern_type_counts', {}), limit=50)}\n"
        "## Author Strategy Counts\n\n"
        f"{_render_counts(summary.get('author_strategy_counts', {}), limit=50)}"
    )


def render_skill_quality_report(summary: dict[str, Any]) -> str:
    return (
        "# Skill Quality Report\n\n"
        "## Summary\n\n"
        f"- Skill card count: {summary['skill_card_count']}\n"
        f"- Validated count: {summary['validated_count']}\n"
        f"- Candidate count: {summary['candidate_count']}\n"
        f"- Ready for API enrichment count: {summary.get('ready_for_api_enrichment_count', 0)}\n"
        f"- Semantic enrichment review count: {summary.get('semantic_enrichment_review_count', 0)}\n"
        f"- Rejected group count: {summary['rejected_group_count']}\n"
        f"- Untrusted group count: {summary.get('untrusted_group_count', 0)}\n"
        f"- Total group count: {summary['total_group_count']}\n"
        f"- Taxonomy version: `v1`\n\n"
        "## Evidence Status Counts\n\n"
        f"{_render_counts(summary.get('evidence_status_counts', {}), limit=20)}\n"
        "## Rejected Reason Counts\n\n"
        f"{_render_counts(summary.get('rejected_reason_counts', {}), limit=20)}"
    )


def render_judge_report(result: dict[str, Any]) -> str:
    summary = result["summary"]
    error_examples = result.get("errors", [])[:10]
    warning_examples = result.get("warnings", [])[:10]
    error_lines = [
        f"- {item.get('artifact_type')} {item.get('artifact_id')}: {item.get('issue')}"
        for item in error_examples
    ] or ["- none"]
    warning_lines = [
        f"- {item.get('artifact_type')} {item.get('artifact_id')}: {item.get('issue')}"
        for item in warning_examples
    ] or ["- none"]
    return (
        "# Judge QA Report\n\n"
        "## Summary\n\n"
        f"- Review unit count: {summary['review_unit_count']}\n"
        f"- Interaction count: {summary['interaction_count']}\n"
        f"- Skill card count: {summary['skill_card_count']}\n"
        f"- Accepted interaction count: {summary['accepted_interaction_count']}\n"
        f"- Rejected interaction count: {summary['rejected_interaction_count']}\n"
        f"- Accepted skill card count: {summary['accepted_skill_card_count']}\n"
        f"- Rejected skill card count: {summary['rejected_skill_card_count']}\n"
        f"- Skill card review count: {summary.get('skill_card_review_count', 0)}\n"
        f"- Error count: {summary['error_count']}\n"
        f"- Warning count: {summary['warning_count']}\n\n"
        "## Error Examples\n\n"
        + "\n".join(error_lines)
        + "\n\n"
        "## Warning Examples\n\n"
        + "\n".join(warning_lines)
        + "\n"
    )
