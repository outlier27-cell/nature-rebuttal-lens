"""Nature RebuttalLens manuscript-aware workflow entry point."""

import json
from pathlib import Path
from typing import Any

from peer_review_skills.agents.manuscript_context import build_rebuttal_lens_unit
from peer_review_skills.agents.multi_agent_orchestrator import MultiAgentOrchestrator
from peer_review_skills.agents.rebuttal_lens_agents import create_rebuttal_lens_frontend_agents
from peer_review_skills.agents.specialized_agents_part2 import create_all_specialized_agents
from peer_review_skills.agents.workflow_integration import (
    _create_model_client,
    _json_safe_config,
    _load_taxonomies,
)


DEFAULT_REBUTTAL_LENS_OUTPUT_DIR = Path("data/evaluation/rebuttal_lens_demo")


def run_rebuttal_lens_workflow(
    *,
    project_root: Path,
    review_text: str,
    response_text: str = "",
    manuscript_path: str | Path | None = None,
    manuscript_text: str | None = None,
    editor_text: str = "",
    retrieved_cases: list[dict[str, Any]] | None = None,
    taxonomies: dict[str, Any] | None = None,
    config: dict[str, Any] | None = None,
    model_client: Any | None = None,
) -> dict[str, Any]:
    """Run one manuscript-aware Nature RebuttalLens workflow trace."""
    config = config or {}
    if config.get("enable_refinement", False):
        raise ValueError(
            "Nature RebuttalLens refinement is not yet supported; run without enable_refinement "
            "or use the legacy v3 KB workflow refinement path."
        )
    root = Path(project_root)
    unit = build_rebuttal_lens_unit(
        review_text=review_text,
        response_text=response_text,
        manuscript_path=manuscript_path,
        manuscript_text=manuscript_text,
        editor_text=editor_text,
        unit_id=str(config.get("unit_id") or "rebuttal_lens_user_case"),
    )
    taxonomies = taxonomies if taxonomies is not None else _load_taxonomies(root)
    model_client = model_client or _create_model_client(config)
    retrieval = {
        "query_unit_id": unit["unit_id"],
        "top_k": retrieved_cases or [],
    }

    trace = execute_rebuttal_lens_trace(
        unit=unit,
        retrieval=retrieval,
        taxonomies=taxonomies,
        model_client=model_client,
        config=config,
    )

    output_dir = Path(config.get("output_dir") or root / DEFAULT_REBUTTAL_LENS_OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    trace_path = output_dir / "rebuttal_lens_trace.json"
    trace_path.write_text(
        json.dumps(trace, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    summary = {
        "system_name": "Nature RebuttalLens",
        "workflow_version": "rebuttal_lens_v1",
        "total_traces": 1,
        "total_llm_calls": trace.get("execution_metadata", {}).get("total_llm_calls", 0),
        "manuscript_mode": unit.get("manuscript_context", {}).get("mode"),
        "output_trace_path": str(trace_path),
        "config": _json_safe_config(config),
    }
    (output_dir / "rebuttal_lens_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return summary


def execute_rebuttal_lens_trace(
    *,
    unit: dict[str, Any],
    retrieval: dict[str, Any],
    taxonomies: dict[str, Any],
    model_client: Any,
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Execute the 12-agent Nature RebuttalLens workflow for a prepared unit."""
    config = config or {}
    if config.get("enable_refinement", False):
        raise ValueError(
            "Nature RebuttalLens refinement is not yet supported; run without enable_refinement."
        )
    agents = {
        **create_rebuttal_lens_frontend_agents(model_client),
        **create_all_specialized_agents(model_client),
    }
    orchestrator = MultiAgentOrchestrator(
        agents=agents,
        enable_refinement=config.get("enable_refinement", False),
        max_refinement_iterations=int(config.get("max_refinement_iterations", 2)),
    )

    trace = orchestrator.execute_rebuttal_lens_workflow(unit, retrieval, taxonomies)
    trace["system_name"] = "Nature RebuttalLens"
    trace["workflow_version"] = "rebuttal_lens_v1"
    trace["manuscript_context"] = unit.get("manuscript_context", {})
    trace["responsible_use_boundary"] = {
        "assistant_only": True,
        "not_final_rebuttal_text": True,
        "author_must_verify_all_claims": True,
        "no_acceptance_prediction": True,
        "no_confidential_upload_recommendation": True,
    }
    return trace
