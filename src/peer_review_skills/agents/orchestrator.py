import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from peer_review_skills.align.pipeline import align_annotations
from peer_review_skills.annotate.pipeline import annotate_units
from peer_review_skills.api.handoff import build_api_handoff, render_api_handoff_report
from peer_review_skills.api.openai_compatible import apply_api_results, execute_api_handoff
from peer_review_skills.evaluation.diagnostics import doi_to_paper_id
from peer_review_skills.evaluation.reports import (
    build_segmentation_diagnostics,
    render_alignment_report,
    render_annotation_report,
    render_judge_report,
    render_segmentation_report,
    render_skill_quality_report,
)
from peer_review_skills.indexing.review_unit_index import build_review_unit_index, load_review_unit_index
from peer_review_skills.io.jsonl import read_jsonl, write_jsonl
from peer_review_skills.judge.pipeline import judge_artifacts
from peer_review_skills.normalize.loader import RawPaper
from peer_review_skills.normalize.paper_normalizer import normalize_papers
from peer_review_skills.readiness.pipeline import build_readiness_summary, render_readiness_report
from peer_review_skills.segment.unit_builder import build_review_units_for_paper
from peer_review_skills.skills.pipeline import induce_skill_cards, write_skill_card_files
from peer_review_skills.judge.pipeline import _load_skill_card_records
from peer_review_skills.taxonomy.pipeline import build_taxonomy_artifacts

from peer_review_skills.agents.providers import ExternalAPIProvider, ModelProvider, RuleBasedProvider


RAW_DATA_RELATIVE_PATH = Path("scraped_data/20_curated/final_nature_ai_comments")
RAW_INDEX_RELATIVE_PATH = Path("scraped_data/20_curated/final_nature_ai_comments_index.json")


@dataclass
class AgentResult:
    agent_name: str
    outputs: dict[str, Any]


class PipelineAgent:
    agent_name = "PipelineAgent"

    def __init__(self, provider: ModelProvider):
        self.provider = provider

    def run(self, project_root: Path, scope: str) -> AgentResult:
        raise NotImplementedError


class NormalizerAgent(PipelineAgent):
    agent_name = "NormalizerAgent"

    def run(self, project_root: Path, scope: str) -> AgentResult:
        records = list(
            normalize_papers(
                _iter_project_raw_papers(project_root, scope),
                _load_project_index_records(project_root),
            )
        )
        output_path = project_root / "data/processed/normalized/normalized_papers.jsonl"
        write_jsonl(output_path, (record.to_dict() for record in records))
        return AgentResult(self.agent_name, {"normalized_paper_count": len(records)})


class SegmenterAgent(PipelineAgent):
    agent_name = "SegmenterAgent"

    def run(self, project_root: Path, scope: str) -> AgentResult:
        units = []
        for raw_paper in _iter_project_raw_papers(project_root, scope):
            units.extend(
                build_review_units_for_paper(
                    None,
                    raw_paper.raw_json_path.as_posix(),
                    raw_paper.data,
                )
            )
        unit_dicts = [unit.to_dict() for unit in units]
        review_units_path = project_root / "data/processed/review_units/review_units.jsonl"
        review_unit_index_path = project_root / "data/processed/review_units/review_unit_index.jsonl"
        write_jsonl(review_units_path, unit_dicts)
        write_jsonl(review_unit_index_path, build_review_unit_index(unit_dicts))

        diagnostics = build_segmentation_diagnostics(unit_dicts)
        write_jsonl(
            project_root / "data/evaluation/review_queue/mixed_or_low_confidence_units.jsonl",
            diagnostics["review_queue_units"],
        )
        report_path = project_root / "data/evaluation/reports/segmentation_report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(render_segmentation_report(diagnostics), encoding="utf-8", newline="\n")
        return AgentResult(
            self.agent_name,
            {
                "review_unit_count": len(unit_dicts),
                "segmentation_review_queue_count": len(diagnostics["review_queue_units"]),
            },
        )


class AnnotationAgent(PipelineAgent):
    agent_name = "AnnotationAgent"

    def run(self, project_root: Path, scope: str) -> AgentResult:
        if self.provider.provider_name != "rule_based":
            raise ValueError(
                "legacy annotation agent uses local baseline annotations and is not part of the "
                "public Agnes/NatureReview model-assisted workflow"
            )
        review_units_path = project_root / "data/processed/review_units/review_units.jsonl"
        units = _scope_records(list(read_jsonl(review_units_path)), project_root, scope)
        result = annotate_units(units)
        annotations_dir = project_root / "data/processed/annotations"
        write_jsonl(
            annotations_dir / "reviewer_annotations.jsonl",
            (annotation.to_dict() for annotation in result["reviewer_annotations"]),
        )
        write_jsonl(
            annotations_dir / "author_annotations.jsonl",
            (annotation.to_dict() for annotation in result["author_annotations"]),
        )
        write_jsonl(
            project_root / "data/evaluation/review_queue/annotation_low_confidence_units.jsonl",
            result["low_confidence_annotations"],
        )
        report_path = project_root / "data/evaluation/reports/annotation_report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(render_annotation_report(result["summary"]), encoding="utf-8", newline="\n")
        return AgentResult(
            self.agent_name,
            {
                "reviewer_annotation_count": result["summary"]["reviewer_annotation_count"],
                "author_annotation_count": result["summary"]["author_annotation_count"],
                "low_confidence_annotation_count": result["summary"]["low_confidence_count"],
                "skipped_annotation_unit_count": result["summary"]["skipped_units"],
            },
        )


class ReviewerAnalystAgent(PipelineAgent):
    agent_name = "ReviewerAnalystAgent"

    def run(self, project_root: Path, scope: str) -> AgentResult:
        path = project_root / "data/processed/annotations/reviewer_annotations.jsonl"
        annotations = _scope_records(list(read_jsonl(path)), project_root, scope)
        return AgentResult(self.agent_name, {"reviewer_annotation_count": len(annotations)})


class AuthorAnalystAgent(PipelineAgent):
    agent_name = "AuthorAnalystAgent"

    def run(self, project_root: Path, scope: str) -> AgentResult:
        path = project_root / "data/processed/annotations/author_annotations.jsonl"
        annotations = _scope_records(list(read_jsonl(path)), project_root, scope)
        return AgentResult(self.agent_name, {"author_annotation_count": len(annotations)})


class AlignmentAgent(PipelineAgent):
    agent_name = "AlignmentAgent"

    def run(self, project_root: Path, scope: str) -> AgentResult:
        reviewer_annotations = _scope_records(
            list(read_jsonl(project_root / "data/processed/annotations/reviewer_annotations.jsonl")),
            project_root,
            scope,
        )
        author_annotations = _scope_records(
            list(read_jsonl(project_root / "data/processed/annotations/author_annotations.jsonl")),
            project_root,
            scope,
        )
        unit_index_path = project_root / "data/processed/review_units/review_unit_index.jsonl"
        unit_index = load_review_unit_index(unit_index_path) if unit_index_path.exists() else None
        result = align_annotations(reviewer_annotations, author_annotations, unit_index=unit_index)
        interaction_path = project_root / "data/processed/interaction_units/interaction_units.jsonl"
        unresolved_path = project_root / "data/evaluation/review_queue/unresolved_alignment_units.jsonl"
        write_jsonl(
            interaction_path,
            (interaction.to_dict() for interaction in result["interaction_units"]),
        )
        write_jsonl(unresolved_path, result["unresolved_alignment_units"])
        report_path = project_root / "data/evaluation/reports/alignment_report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(render_alignment_report(result["summary"]), encoding="utf-8", newline="\n")
        return AgentResult(
            self.agent_name,
            {
                "interaction_count": len(result["interaction_units"]),
                "unresolved_alignment_count": len(result["unresolved_alignment_units"]),
            },
        )


class SkillInductionAgent(PipelineAgent):
    agent_name = "SkillInductionAgent"

    def run(self, project_root: Path, scope: str) -> AgentResult:
        interactions = _scope_records(
            list(read_jsonl(project_root / "data/processed/interaction_units/interaction_units.jsonl")),
            project_root,
            scope,
        )
        result = induce_skill_cards(interactions)
        skill_dir = write_skill_card_files(project_root, scope, result["skill_cards"])
        report_path = project_root / "data/evaluation/reports/skill_quality_report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(render_skill_quality_report(result["summary"]), encoding="utf-8", newline="\n")
        return AgentResult(
            self.agent_name,
            {
                "skill_card_count": len(result["skill_cards"]),
                "validated_skill_count": result["summary"]["validated_count"],
                "candidate_skill_count": result["summary"]["candidate_count"],
                "ready_for_api_enrichment_count": result["summary"]["ready_for_api_enrichment_count"],
                "semantic_enrichment_review_count": result["summary"]["semantic_enrichment_review_count"],
                "skill_card_output_dir": skill_dir.as_posix(),
            },
        )


class TaxonomyAgent(PipelineAgent):
    agent_name = "TaxonomyAgent"

    def run(self, project_root: Path, scope: str) -> AgentResult:
        taxonomy_dir = project_root / "data/processed/taxonomies"
        taxonomy_dir.mkdir(parents=True, exist_ok=True)
        artifacts = build_taxonomy_artifacts()
        for filename, payload in artifacts.items():
            (taxonomy_dir / filename).write_text(
                json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
                encoding="utf-8",
                newline="\n",
            )
        return AgentResult(self.agent_name, {"taxonomy_count": len(artifacts)})


class QualityGateAgent(PipelineAgent):
    agent_name = "QualityGateAgent"

    def run(self, project_root: Path, scope: str) -> AgentResult:
        review_queue_path = project_root / "data/evaluation/review_queue/mixed_or_low_confidence_units.jsonl"
        review_queue_count = len(list(read_jsonl(review_queue_path))) if review_queue_path.exists() else 0
        output = {
            "quality_gate_blocked": review_queue_count > 0,
            "segmentation_review_queue_count": review_queue_count,
            "quality_gate_reason": "segmentation_review_queue_not_empty" if review_queue_count > 0 else "passed",
        }
        return AgentResult(self.agent_name, output)


class JudgeAgent(PipelineAgent):
    agent_name = "JudgeAgent"

    def run(self, project_root: Path, scope: str) -> AgentResult:
        result = judge_artifacts(project_root, scope=scope)
        qa_dir = project_root / "data/evaluation/qa"
        write_jsonl(qa_dir / "accepted_interactions.jsonl", result["accepted_interactions"])
        write_jsonl(qa_dir / "rejected_interactions.jsonl", result["rejected_interactions"])
        write_jsonl(qa_dir / "accepted_skill_cards.jsonl", result["accepted_skill_cards"])
        write_jsonl(qa_dir / "rejected_skill_cards.jsonl", result["rejected_skill_cards"])
        write_jsonl(qa_dir / "skill_cards_for_review.jsonl", result["skill_cards_for_review"])
        write_jsonl(qa_dir / "judge_issues.jsonl", result["errors"] + result["warnings"])
        report_path = project_root / "data/evaluation/reports/judge_report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(render_judge_report(result), encoding="utf-8", newline="\n")
        return AgentResult(
            self.agent_name,
            {
                "judge_error_count": result["summary"]["error_count"],
                "judge_warning_count": result["summary"]["warning_count"],
                "accepted_interaction_count": result["summary"]["accepted_interaction_count"],
                "accepted_skill_card_count": result["summary"]["accepted_skill_card_count"],
                "skill_card_review_count": result["summary"]["skill_card_review_count"],
            },
        )


class ApiHandoffAgent(PipelineAgent):
    agent_name = "ApiHandoffAgent"

    def run(self, project_root: Path, scope: str) -> AgentResult:
        interactions = list(read_jsonl(project_root / "data/processed/interaction_units/interaction_units.jsonl"))
        review_units_path = project_root / "data/processed/review_units/review_units.jsonl"
        review_units = list(read_jsonl(review_units_path)) if review_units_path.exists() else []
        skill_cards = _load_skill_card_records(_skill_cards_dir(project_root, scope))
        result = build_api_handoff(interactions, skill_cards, review_units=review_units)
        handoff_dir = project_root / "data/evaluation/api_handoff"
        scoped_handoff_dir = handoff_dir / scope
        write_jsonl(handoff_dir / "alignment_requests.jsonl", result["alignment_requests"])
        write_jsonl(handoff_dir / "skill_enrichment_requests.jsonl", result["skill_enrichment_requests"])
        write_jsonl(scoped_handoff_dir / "alignment_requests.jsonl", result["alignment_requests"])
        write_jsonl(scoped_handoff_dir / "skill_enrichment_requests.jsonl", result["skill_enrichment_requests"])
        report_path = project_root / "data/evaluation/reports/api_handoff_report.md"
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(render_api_handoff_report(result["summary"]), encoding="utf-8", newline="\n")
        return AgentResult(
            self.agent_name,
            {
                "api_alignment_request_count": result["summary"]["alignment_request_count"],
                "api_skill_enrichment_request_count": result["summary"]["skill_enrichment_request_count"],
                "api_handoff_request_count": result["summary"]["total_request_count"],
            },
        )


class ApiExecutionAgent(PipelineAgent):
    agent_name = "ApiExecutionAgent"

    def __init__(self, provider: ExternalAPIProvider, limit: int | None = None):
        super().__init__(provider)
        self.provider = provider
        self.limit = limit

    def run(self, project_root: Path, scope: str) -> AgentResult:
        client = self.provider.create_client()
        summary = execute_api_handoff(project_root, client, limit=self.limit, scope=scope)
        return AgentResult(
            self.agent_name,
            {
                "api_processed_request_count": summary["processed_count"],
                "api_alignment_result_count": summary["cumulative_alignment_result_count"],
                "api_skill_enrichment_result_count": summary["cumulative_skill_enrichment_result_count"],
                "api_new_alignment_result_count": summary["alignment_result_count"],
                "api_new_skill_enrichment_result_count": summary["skill_enrichment_result_count"],
                "api_error_count": summary["error_count"],
            },
        )


def run_api_handoff_workflow(
    project_root: str | Path,
    provider: ExternalAPIProvider | None = None,
    limit: int | None = 5,
    apply_results: bool = False,
    scope: str = "mvp",
) -> dict[str, Any]:
    resolved_root = Path(project_root)
    active_provider = provider or ExternalAPIProvider.from_environment()
    if provider is None and not active_provider.is_configured():
        raise ValueError(
            "external API provider is not configured; set PEER_REVIEW_API_BASE_URL, "
            "PEER_REVIEW_API_KEY, and PEER_REVIEW_API_MODEL"
        )
    result = ApiExecutionAgent(active_provider, limit=limit).run(resolved_root, scope)
    outputs = dict(result.outputs)
    if apply_results:
        apply_summary = apply_api_results(resolved_root, scope=scope)
        outputs.update(
            {
                "api_apply_resolved_alignment_count": apply_summary["resolved_alignment_count"],
                "api_apply_enriched_skill_count": apply_summary["enriched_skill_count"],
                "api_apply_merge_error_count": apply_summary["merge_error_count"],
            }
        )
    summary = {
        "provider": active_provider.provider_name,
        "provider_description": active_provider.describe(),
        "provider_capabilities": active_provider.model_capabilities(),
        "outputs": outputs,
    }
    return summary


def run_agent_workflow(
    project_root: str | Path,
    scope: str = "mvp",
    provider: ModelProvider | None = None,
    skip_normalize: bool = False,
    skip_segment: bool = False,
    skip_annotate: bool = False,
    enforce_quality_gate: bool = False,
    execute_api: bool = False,
    api_limit: int | None = 5,
    allow_legacy_baseline: bool = False,
) -> dict[str, Any]:
    resolved_root = Path(project_root)
    active_provider = provider or ExternalAPIProvider.from_environment()
    if active_provider.provider_name == "rule_based" and not allow_legacy_baseline:
        raise ValueError(
            "RuleBasedProvider is a legacy local baseline and is not part of the public "
            "Agnes/NatureReview workflow; pass allow_legacy_baseline=True only for "
            "explicit baseline experiments"
        )
    if provider is None and not active_provider.is_configured():
        raise ValueError(
            "external API provider is required for public agent workflow runs; set "
            "PEER_REVIEW_API_BASE_URL, PEER_REVIEW_API_KEY, and PEER_REVIEW_API_MODEL, "
            "or explicitly pass RuleBasedProvider with allow_legacy_baseline=True only for legacy baseline experiments"
        )
    if active_provider.provider_name != "rule_based" and not skip_annotate:
        raise ValueError(
            "run-agents with an external model provider cannot execute the legacy local annotation stage; "
            "use build-naturereview-v01 for the Agnes/NatureReview workflow or pass --skip-annotate for "
            "data-preparation-only runs"
        )
    agent_results: list[AgentResult] = []
    agents: list[PipelineAgent] = []
    if not skip_normalize:
        agents.append(NormalizerAgent(active_provider))
    if not skip_segment:
        agents.append(SegmenterAgent(active_provider))
    if not skip_annotate:
        agents.append(AnnotationAgent(active_provider))
    if enforce_quality_gate:
        for pre_gate_agent in agents:
            agent_results.append(pre_gate_agent.run(resolved_root, scope))
        agents = []
        gate_agent = QualityGateAgent(active_provider)
        gate_result = gate_agent.run(resolved_root, scope)
        agent_results.append(gate_result)
        if gate_result.outputs.get("quality_gate_blocked"):
            outputs: dict[str, Any] = {}
            for result in agent_results:
                outputs.update(result.outputs)
            summary = {
                "provider": active_provider.provider_name,
                "provider_description": active_provider.describe(),
                "provider_capabilities": active_provider.model_capabilities(),
                "scope": scope,
                "agents": [result.agent_name for result in agent_results],
                "outputs": {
                    **outputs,
                    "interaction_count": 0,
                    "skill_card_count": 0,
                    "judge_error_count": 0,
                },
                "readiness": build_readiness_summary(
                    {
                        "interaction_count": 0,
                        "skill_card_count": 0,
                        "judge_error_count": 0,
                        "judge_warning_count": 0,
                    },
                    api_configured=active_provider.provider_name != "rule_based" and active_provider.is_configured(),
                    api_execution_wired=active_provider.api_execution_wired(),
                    quality_gate_blocked=True,
                ),
                "skipped_stages": {
                    "normalize": skip_normalize,
                    "segment": skip_segment,
                    "annotate": skip_annotate,
                },
            }
            report_path = resolved_root / "data/evaluation/reports/agent_workflow_report.md"
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(render_agent_workflow_report(summary), encoding="utf-8", newline="\n")
            readiness_path = resolved_root / "data/evaluation/reports/system_readiness_report.md"
            readiness_path.write_text(render_readiness_report(summary["readiness"]), encoding="utf-8", newline="\n")
            return summary
    agents.extend(
        [
            ReviewerAnalystAgent(active_provider),
            AuthorAnalystAgent(active_provider),
            AlignmentAgent(active_provider),
            TaxonomyAgent(active_provider),
            SkillInductionAgent(active_provider),
            JudgeAgent(active_provider),
            ApiHandoffAgent(active_provider),
        ]
    )
    if execute_api:
        if not isinstance(active_provider, ExternalAPIProvider):
            raise ValueError("API execution requires an ExternalAPIProvider")
        agents.append(ApiExecutionAgent(active_provider, limit=api_limit))
    for agent in agents:
        agent_results.append(agent.run(resolved_root, scope))

    outputs: dict[str, Any] = {}
    for result in agent_results:
        outputs.update(result.outputs)
    status_counts = _interaction_status_counts(resolved_root / "data/processed/interaction_units/interaction_units.jsonl")
    readiness = build_readiness_summary(
        {
            "interaction_count": outputs.get("interaction_count", 0),
            "quality_gate_blocked": outputs.get("quality_gate_blocked", False),
            "matched_count": status_counts.get("matched", 0),
            "ambiguous_count": status_counts.get("ambiguous", 0),
            "missing_response_count": status_counts.get("missing_response", 0),
            "skill_card_count": outputs.get("skill_card_count", 0),
            "validated_skill_count": outputs.get("validated_skill_count", 0),
            "candidate_skill_count": outputs.get("candidate_skill_count", 0),
            "ready_for_api_enrichment_count": outputs.get("ready_for_api_enrichment_count", 0),
            "semantic_enrichment_review_count": outputs.get("semantic_enrichment_review_count", 0),
            "api_alignment_request_count": outputs.get("api_alignment_request_count", 0),
            "api_skill_enrichment_request_count": outputs.get("api_skill_enrichment_request_count", 0),
            "api_handoff_request_count": outputs.get("api_handoff_request_count", 0),
            "api_alignment_result_count": outputs.get("api_alignment_result_count", 0),
            "api_skill_enrichment_result_count": outputs.get("api_skill_enrichment_result_count", 0),
            "api_error_count": outputs.get("api_error_count", 0),
            "judge_error_count": outputs.get("judge_error_count", 0),
            "judge_warning_count": outputs.get("judge_warning_count", 0),
            "skill_card_review_count": outputs.get("skill_card_review_count", 0),
        },
        api_configured=active_provider.provider_name != "rule_based" and active_provider.is_configured(),
        api_execution_wired=active_provider.api_execution_wired(),
    )
    summary = {
        "provider": active_provider.provider_name,
        "provider_description": active_provider.describe(),
        "provider_capabilities": active_provider.model_capabilities(),
        "scope": scope,
        "agents": [result.agent_name for result in agent_results],
        "outputs": outputs,
        "readiness": readiness,
        "skipped_stages": {
            "normalize": skip_normalize,
            "segment": skip_segment,
            "annotate": skip_annotate,
        },
    }
    report_path = resolved_root / "data/evaluation/reports/agent_workflow_report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_agent_workflow_report(summary), encoding="utf-8", newline="\n")
    readiness_path = resolved_root / "data/evaluation/reports/system_readiness_report.md"
    readiness_path.write_text(render_readiness_report(readiness), encoding="utf-8", newline="\n")
    return summary


def render_agent_workflow_report(summary: dict[str, Any]) -> str:
    output_lines = [f"- {key}: {value}" for key, value in sorted(summary["outputs"].items())]
    agent_lines = [f"- {agent}" for agent in summary["agents"]]
    capability_lines = [
        f"- {key}: {value}" for key, value in sorted(summary["provider_capabilities"].items())
    ]
    return (
        "# Agent Workflow Report\n\n"
        "## Summary\n\n"
        f"- Provider: `{summary['provider']}`\n"
        f"- Provider description: {summary['provider_description']}\n"
        f"- Scope: `{summary['scope']}`\n\n"
        "## Provider Capabilities\n\n"
        + "\n".join(capability_lines)
        + "\n\n"
        "## Agents\n\n"
        + "\n".join(agent_lines)
        + "\n\n"
        "## Outputs\n\n"
        + "\n".join(output_lines)
        + "\n\n"
        "## Readiness\n\n"
        f"- Overall status: `{summary['readiness']['overall_status']}`\n"
        f"- Remaining blockers: {', '.join(summary['readiness']['remaining_blockers']) or 'none'}\n"
        + "\n"
    )


def _scope_records(records: list[dict[str, Any]], project_root: Path, scope: str) -> list[dict[str, Any]]:
    if scope != "mvp":
        return records
    mvp_path = project_root / "data/evaluation/samples/mvp_paper_ids.txt"
    if not mvp_path.exists():
        return records
    mvp_ids = {line.strip() for line in mvp_path.read_text(encoding="utf-8").splitlines() if line.strip()}
    return [record for record in records if record.get("paper_id") in mvp_ids]


def _interaction_status_counts(path: Path) -> dict[str, int]:
    if not path.exists():
        return {}
    counts: dict[str, int] = {}
    for record in read_jsonl(path):
        status = str(record.get("alignment_status") or "unknown")
        counts[status] = counts.get(status, 0) + 1
    return counts


def _iter_project_raw_papers(project_root: Path, scope: str) -> list[RawPaper]:
    if scope not in {"mvp", "all"}:
        raise ValueError("scope must be 'mvp' or 'all'")
    data_dir = project_root / RAW_DATA_RELATIVE_PATH
    mvp_ids = _load_project_mvp_ids(project_root) if scope == "mvp" else None
    papers: list[RawPaper] = []
    for path in sorted(data_dir.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        doi = str(data.get("doi") or path.stem.replace("_", "/"))
        paper_id = doi_to_paper_id(doi)
        if mvp_ids is not None and mvp_ids and paper_id not in mvp_ids:
            continue
        papers.append(RawPaper(raw_json_path=path, data=data))
    return papers


def _load_project_mvp_ids(project_root: Path) -> set[str]:
    mvp_path = project_root / "data/evaluation/samples/mvp_paper_ids.txt"
    if not mvp_path.exists():
        return set()
    return {line.strip() for line in mvp_path.read_text(encoding="utf-8").splitlines() if line.strip()}


def _load_project_index_records(project_root: Path) -> dict[str, dict[str, Any]]:
    index_path = project_root / RAW_INDEX_RELATIVE_PATH
    if not index_path.exists():
        return {}
    records = json.loads(index_path.read_text(encoding="utf-8"))
    return {
        record.get("doi"): record
        for record in records
        if isinstance(record, dict) and record.get("doi")
    }


def _skill_cards_dir(project_root: Path, scope: str) -> Path:
    scoped = project_root / "data/processed/skill_cards" / scope
    if scoped.exists():
        return scoped
    return project_root / "data/processed/skill_cards"
