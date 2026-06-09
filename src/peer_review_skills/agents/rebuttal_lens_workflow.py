"""Nature RebuttalLens manuscript-aware workflow entry point."""

import json
from pathlib import Path
from typing import Any

from peer_review_skills.agents.base import (
    agent_model_client,
    agent_runtime_options,
)
from peer_review_skills.agents.final_report import (
    compose_final_user_report,
    write_final_user_report,
)
from peer_review_skills.agents.kant_machine_runtime import attach_kant_machine_runtime
from peer_review_skills.agents.manuscript_context import build_rebuttal_lens_unit
from peer_review_skills.agents.memory_ethics import (
    build_memory_ethics_runtime,
    filter_runtime_memory,
)
from peer_review_skills.agents.multi_agent_orchestrator import MultiAgentOrchestrator
from peer_review_skills.agents.rebuttal_lens_agents import create_rebuttal_lens_frontend_agents
from peer_review_skills.agents.committee_agents import (
    CommitteeMetaReviewerAgent,
    CommitteeReviewerAgent,
)
from peer_review_skills.agents.specialized_agents_part2 import create_all_specialized_agents
from peer_review_skills.agents.strategy_tournament import (
    StrategyMetaPlannerAgent,
    StrategyTournamentAgent,
)
from peer_review_skills.agents.workflow_integration import (
    _create_model_client,
    _json_safe_config,
    _load_taxonomies,
)


DEFAULT_REBUTTAL_LENS_OUTPUT_DIR = Path("data/evaluation/rebuttal_lens_demo")
DEFAULT_REBUTTAL_LENS_CONFIG_PATH = Path("config/multi_agent_config.yaml")


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
    root = Path(project_root)
    config = _merged_rebuttal_lens_config(root, config)
    if config.get("enable_refinement", False):
        raise ValueError(
            "Nature RebuttalLens refinement is not yet supported; run without enable_refinement "
            "or use the legacy v3 KB workflow refinement path."
        )
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
    output_dir = Path(config.get("output_dir") or root / DEFAULT_REBUTTAL_LENS_OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)

    trace_path = output_dir / "rebuttal_lens_trace.json"
    try:
        trace = execute_rebuttal_lens_trace(
            unit=unit,
            retrieval=retrieval,
            taxonomies=taxonomies,
            model_client=model_client,
            config={
                **config,
                "checkpoint_dir": output_dir / "checkpoints",
            },
        )
        trace_path.write_text(
            json.dumps(trace, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        final_report = compose_final_user_report(trace)
        final_report_paths = write_final_user_report(final_report, output_dir)
    except Exception as exc:
        _write_failure_trace(output_dir, exc)
        raise
    summary = {
        "system_name": "Nature RebuttalLens",
        "workflow_version": "rebuttal_lens_v1",
        "total_traces": 1,
        "total_llm_calls": trace.get("execution_metadata", {}).get("total_llm_calls", 0),
        "manuscript_mode": unit.get("manuscript_context", {}).get("mode"),
        "output_trace_path": str(trace_path),
        "final_user_report_json": final_report_paths["final_user_report_json"],
        "final_user_report_markdown": final_report_paths["final_user_report_markdown"],
        "workflow_engine": config.get("workflow_engine", "layered"),
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
    if config.get("workflow_engine") == "dag":
        return execute_rebuttal_lens_dag_trace(
            unit=unit,
            retrieval=retrieval,
            taxonomies=taxonomies,
            model_client=model_client,
            config=config,
        )
    agents = {
        **create_rebuttal_lens_frontend_agents(model_client, config),
        **create_all_specialized_agents(model_client, config),
    }
    checkpoint_dir = config.get("checkpoint_dir")
    checkpoint_callback = (
        _checkpoint_writer(Path(checkpoint_dir))
        if checkpoint_dir is not None
        else None
    )
    orchestrator = MultiAgentOrchestrator(
        agents=agents,
        enable_refinement=config.get("enable_refinement", False),
        max_refinement_iterations=int(config.get("max_refinement_iterations", 2)),
        checkpoint_callback=checkpoint_callback,
    )

    trace = orchestrator.execute_rebuttal_lens_workflow(unit, retrieval, taxonomies)
    return _with_rebuttal_lens_trace_metadata(trace, unit, config)


def execute_rebuttal_lens_dag_trace(
    *,
    unit: dict[str, Any],
    retrieval: dict[str, Any],
    taxonomies: dict[str, Any],
    model_client: Any,
    config: dict[str, Any],
) -> dict[str, Any]:
    """Execute the optional DAG/committee/tournament RebuttalLens workflow."""
    from peer_review_skills.agents.dag_runtime import (
        WorkflowExecutionError,
        run_workflow_graph,
    )
    from peer_review_skills.agents.rebuttal_lens_graph import build_rebuttal_lens_graph

    agents = {
        **create_rebuttal_lens_frontend_agents(model_client, config),
        **create_all_specialized_agents(model_client, config),
        **_create_optional_rebuttal_lens_agents(model_client, config),
    }
    graph = build_rebuttal_lens_graph(
        enable_committee=bool(config.get("enable_committee", False)),
        enable_strategy_tournament=bool(config.get("enable_strategy_tournament", False)),
    )
    base_inputs = {
        "review_text": unit.get("review_text", ""),
        "response_text": unit.get("response_text", ""),
        "editor_text": unit.get("editor_text", ""),
        "taxonomies": taxonomies,
        "unit_id": unit.get("unit_id", "unknown"),
        "unit": unit,
        "retrieval": retrieval,
        "manuscript_context": unit.get("manuscript_context", {}),
    }
    message_bus = []

    def run_node(node, context):
        if node.agent_id == "final_user_report_composer":
            return {}
        outputs = context["outputs"]
        agent = agents[node.agent_id]
        inputs = _build_rebuttal_lens_node_inputs(node.node_id, base_inputs, outputs, retrieval)
        message = agent.execute(inputs)
        message_bus.append(message)
        return message.content

    try:
        graph_trace = run_workflow_graph(
            graph,
            run_node,
            initial_context=base_inputs,
            parallel=bool(config.get("dag_parallel", True)),
            max_workers=int(config.get("dag_max_workers", 4)),
        )
    except WorkflowExecutionError as exc:
        partial_graph_trace = exc.partial_trace
        exc.partial_trace = _rebuttal_lens_dag_trace_from_graph_trace(
            graph=graph,
            graph_trace=partial_graph_trace,
            message_bus=message_bus,
            unit=unit,
            config=config,
        )
        raise
    return _rebuttal_lens_dag_trace_from_graph_trace(
        graph=graph,
        graph_trace=graph_trace,
        message_bus=message_bus,
        unit=unit,
        config=config,
    )


def _rebuttal_lens_dag_trace_from_graph_trace(
    *,
    graph: Any,
    graph_trace: dict[str, Any],
    message_bus: list[Any],
    unit: dict[str, Any],
    config: dict[str, Any],
) -> dict[str, Any]:
    node_outputs = graph_trace["outputs"]
    agent_outputs = {
        graph.node_by_id[node_id].agent_id: output
        for node_id, output in node_outputs.items()
        if graph.node_by_id[node_id].agent_id != "final_user_report_composer"
    }
    return _with_rebuttal_lens_trace_metadata({
        "trace_id": f"rebuttal_lens_dag_{unit.get('unit_id', 'unknown')}",
        "query_unit_id": unit.get("unit_id", "unknown"),
        "agent_intermediate_outputs": agent_outputs,
        "message_bus": [msg.to_dict() for msg in message_bus],
        "execution_trace": graph_trace["execution_trace"],
        "execution_metadata": {
            **graph_trace["execution_metadata"],
            "total_llm_calls": len(message_bus),
            "workflow_engine": "dag",
            "manuscript_mode": unit.get("manuscript_context", {}).get("mode"),
        },
    }, unit, config=config)


def _with_rebuttal_lens_trace_metadata(
    trace: dict[str, Any],
    unit: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = config or {}
    forget_scope = _as_forget_scope(config.get("forget_scope"))
    memory_policy = str(config.get("memory_policy", "default"))
    memory_runtime = build_memory_ethics_runtime(
        reset_memory=bool(config.get("reset_memory", False)),
        memory_policy=memory_policy,
        forget_scope=forget_scope,
    )
    trace["system_name"] = "Nature RebuttalLens"
    trace["workflow_version"] = "rebuttal_lens_v1"
    trace["manuscript_context"] = unit.get("manuscript_context", {})
    trace["responsible_use_boundary"] = _rebuttal_lens_responsible_use_boundary()
    trace["memory_passport"] = memory_runtime["memory_passport"]
    trace["forgetting_ledger"] = memory_runtime["forgetting_ledger"]
    trace["irreversible_forgetting_statement"] = memory_runtime[
        "irreversible_forgetting_statement"
    ]
    trace["runtime_memory_after_forgetting"] = filter_runtime_memory(
        dict(config.get("runtime_memory") or {}),
        memory_policy=memory_policy,
        forget_scope=forget_scope,
    )
    trace["memory_ethics_boundary"] = _rebuttal_lens_memory_ethics_boundary(
        reset_memory=bool(config.get("reset_memory", False)),
        forgetting_ledger_attached=True,
    )
    trace = attach_kant_machine_runtime(trace, config)
    return trace


def _rebuttal_lens_responsible_use_boundary() -> dict[str, bool]:
    return {
        "assistant_only": True,
        "not_final_rebuttal_text": True,
        "author_must_verify_all_claims": True,
        "no_acceptance_prediction": True,
        "no_confidential_upload_recommendation": True,
    }


def _as_forget_scope(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]


def _rebuttal_lens_memory_ethics_boundary(
    *,
    reset_memory: bool = False,
    forgetting_ledger_attached: bool = False,
) -> dict[str, bool | str]:
    return {
        "justification_memory_not_conclusion_memory": True,
        "cross_run_strategy_memory_used": False,
        "author_decisions_reset_each_run": True,
        "per_item_author_confirmation_required": True,
        "trace_bound_to_output": True,
        "forgetting_ledger_attached": bool(forgetting_ledger_attached),
        "reset_memory_requested": bool(reset_memory),
        "reset_memory_effect": (
            "No cross-run strategy or author-preference memory is loaded; this run is treated independently."
            if reset_memory
            else "No cross-run strategy or author-preference memory is loaded by default."
        ),
    }


def load_rebuttal_lens_config(path: str | Path) -> dict[str, Any]:
    """Load the small public RebuttalLens YAML config without adding a runtime YAML dependency."""
    config_path = Path(path)
    if not config_path.exists():
        return {}
    return _parse_simple_yaml(config_path.read_text(encoding="utf-8"))


def _create_optional_rebuttal_lens_agents(
    model_client: Any,
    config: dict[str, Any],
) -> dict[str, Any]:
    def runtime_options(agent_id: str) -> dict[str, Any]:
        return agent_runtime_options(config, agent_id)

    def client(agent_id: str) -> Any:
        return agent_model_client(model_client, config, agent_id)

    optional_agents = {}
    if config.get("enable_committee", False):
        optional_agents.update({
            "methodology_committee_reviewer": CommitteeReviewerAgent(
                "methodology_committee_reviewer",
                client("methodology_committee_reviewer"),
                reviewer_role="methodology",
                **runtime_options("methodology_committee_reviewer"),
            ),
            "claim_committee_reviewer": CommitteeReviewerAgent(
                "claim_committee_reviewer",
                client("claim_committee_reviewer"),
                reviewer_role="claim_calibration",
                **runtime_options("claim_committee_reviewer"),
            ),
            "tone_committee_reviewer": CommitteeReviewerAgent(
                "tone_committee_reviewer",
                client("tone_committee_reviewer"),
                reviewer_role="tone_and_interaction",
                **runtime_options("tone_committee_reviewer"),
            ),
            "committee_meta_reviewer": CommitteeMetaReviewerAgent(
                "committee_meta_reviewer",
                client("committee_meta_reviewer"),
                **runtime_options("committee_meta_reviewer"),
            ),
        })
    if config.get("enable_strategy_tournament", False):
        optional_agents.update({
            "strategy_tournament_agent": StrategyTournamentAgent(
                "strategy_tournament_agent",
                client("strategy_tournament_agent"),
                **runtime_options("strategy_tournament_agent"),
            ),
            "strategy_meta_planner": StrategyMetaPlannerAgent(
                "strategy_meta_planner",
                client("strategy_meta_planner"),
                **runtime_options("strategy_meta_planner"),
            ),
        })
    return optional_agents


def _build_rebuttal_lens_node_inputs(
    node_id: str,
    base_inputs: dict[str, Any],
    outputs: dict[str, Any],
    retrieval: dict[str, Any],
) -> dict[str, Any]:
    all_outputs = _agent_outputs_from_node_outputs(outputs)
    common = {**base_inputs, "all_agent_outputs": all_outputs}
    if node_id == "manuscript_context":
        return common
    if node_id == "reviewer_understanding":
        return {**common, "manuscript_context_note": outputs.get("manuscript_context", {})}
    if node_id == "tacit_concern":
        return {**common, "concern_map": outputs.get("reviewer_understanding", {})}
    if node_id == "manuscript_evidence":
        return {
            **common,
            "manuscript_context_note": outputs.get("manuscript_context", {}),
            "concern_map": outputs.get("reviewer_understanding", {}),
        }
    if node_id == "institutional_signal":
        return {
            **common,
            "concern_map": outputs.get("reviewer_understanding", {}),
            "manuscript_evidence": outputs.get("manuscript_evidence", {}),
        }
    if node_id == "case_interpretation":
        return {
            **common,
            "concern_map": outputs.get("reviewer_understanding", {}),
            "risk_interpretation": outputs.get("tacit_concern", {}),
            "retrieved_cases": retrieval.get("top_k", []),
            "manuscript_evidence": outputs.get("manuscript_evidence", {}),
        }
    if node_id == "evidence_action":
        return {
            **common,
            "concern_map": outputs.get("reviewer_understanding", {}),
            "risk_interpretation": outputs.get("tacit_concern", {}),
            "retrieved_cases": retrieval.get("top_k", []),
            "manuscript_evidence": outputs.get("manuscript_evidence", {}),
            "case_interpretation": outputs.get("case_interpretation", {}),
        }
    if node_id == "author_positioning":
        return {
            **common,
            "institutional_signal": outputs.get("institutional_signal", {}),
            "evidence_plan": outputs.get("evidence_action", {}),
            "manuscript_evidence": outputs.get("manuscript_evidence", {}),
        }
    if node_id == "tone_commitment":
        return {
            **common,
            "evidence_plan": outputs.get("evidence_action", {}),
            "author_positioning": outputs.get("author_positioning", {}),
            "manuscript_evidence": outputs.get("manuscript_evidence", {}),
        }
    if node_id == "actor_network":
        return {
            **common,
            "evidence_plan": outputs.get("evidence_action", {}),
            "retrieved_cases": retrieval.get("top_k", []),
            "author_positioning": outputs.get("author_positioning", {}),
            "tone_calibration": outputs.get("tone_commitment", {}),
            "manuscript_evidence": outputs.get("manuscript_evidence", {}),
        }
    if node_id == "cross_disciplinary_lens":
        return common
    if node_id in {
        "committee_methodology_review",
        "committee_claim_review",
        "committee_tone_review",
        "strategy_tournament",
        "integrity",
    }:
        return common
    if node_id == "committee_meta_review":
        return {
            **common,
            "committee_outputs": {
                "methodology_committee_reviewer": outputs.get("committee_methodology_review", {}),
                "claim_committee_reviewer": outputs.get("committee_claim_review", {}),
                "tone_committee_reviewer": outputs.get("committee_tone_review", {}),
            },
        }
    if node_id == "meta_synthesis":
        return {
            **common,
            "strategy_candidates": outputs.get("strategy_tournament", {}).get(
                "strategy_candidates",
                [],
            ),
        }
    if node_id == "final_user_report":
        return common
    raise ValueError(f"Unknown RebuttalLens graph node: {node_id}")


def _agent_outputs_from_node_outputs(outputs: dict[str, Any]) -> dict[str, Any]:
    mapping = {
        "manuscript_context": "manuscript_context_extractor",
        "reviewer_understanding": "reviewer_understanding_agent",
        "tacit_concern": "tacit_concern_interpreter",
        "manuscript_evidence": "manuscript_evidence_locator",
        "institutional_signal": "institutional_signal_interpreter",
        "case_interpretation": "case_retrieval_interpreter",
        "evidence_action": "evidence_action_planner",
        "author_positioning": "author_positioning_agent",
        "tone_commitment": "tone_commitment_calibrator",
        "actor_network": "actor_network_mapper",
        "cross_disciplinary_lens": "cross_disciplinary_lens_interpreter",
        "committee_methodology_review": "methodology_committee_reviewer",
        "committee_claim_review": "claim_committee_reviewer",
        "committee_tone_review": "tone_committee_reviewer",
        "committee_meta_review": "committee_meta_reviewer",
        "strategy_tournament": "strategy_tournament_agent",
        "meta_synthesis": "strategy_meta_planner",
        "integrity": "integrity_adequacy_checker",
    }
    return {
        mapping.get(node_id, node_id): output
        for node_id, output in outputs.items()
        if node_id in mapping
    }


def _merged_rebuttal_lens_config(
    project_root: Path,
    override_config: dict[str, Any] | None,
) -> dict[str, Any]:
    file_config = load_rebuttal_lens_config(project_root / DEFAULT_REBUTTAL_LENS_CONFIG_PATH)
    merged = dict(file_config)
    override_config = override_config or {}
    for key, value in override_config.items():
        if isinstance(value, dict) and isinstance(merged.get(key), dict):
            merged[key] = _deep_merge_dicts(merged[key], value)
        else:
            merged[key] = value
    multi_agent = merged.get("multi_agent")
    if isinstance(multi_agent, dict):
        for key in ["enable_refinement", "max_refinement_iterations"]:
            if key in multi_agent and key not in merged:
                merged[key] = multi_agent[key]
    workflow = merged.get("workflow")
    if isinstance(workflow, dict) and "workflow_engine" not in merged:
        engine = workflow.get("engine")
        if engine:
            merged["workflow_engine"] = engine
    rebuttal_lens = merged.get("rebuttal_lens")
    if isinstance(rebuttal_lens, dict):
        for key in [
            "enable_committee",
            "enable_strategy_tournament",
            "final_user_report",
        ]:
            if key in rebuttal_lens and key not in merged:
                merged[key] = rebuttal_lens[key]
    return merged


def _deep_merge_dicts(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    result = dict(base)
    for key, value in override.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = _deep_merge_dicts(result[key], value)
        else:
            result[key] = value
    return result


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    root: dict[str, Any] = {}
    stack: list[tuple[int, dict[str, Any]]] = [(-1, root)]
    for raw_line in text.splitlines():
        line = raw_line.split("#", 1)[0].rstrip()
        if not line.strip():
            continue
        indent = len(line) - len(line.lstrip(" "))
        stripped = line.strip()
        if ":" not in stripped:
            continue
        key, raw_value = stripped.split(":", 1)
        key = key.strip()
        raw_value = raw_value.strip()
        while stack and indent <= stack[-1][0]:
            stack.pop()
        parent = stack[-1][1]
        if raw_value == "":
            child: dict[str, Any] = {}
            parent[key] = child
            stack.append((indent, child))
        else:
            parent[key] = _parse_simple_yaml_scalar(raw_value)
    return root


def _parse_simple_yaml_scalar(value: str) -> Any:
    if value in {"true", "false"}:
        return value == "true"
    if (value.startswith('"') and value.endswith('"')) or (value.startswith("'") and value.endswith("'")):
        return value[1:-1]
    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        return value


def _checkpoint_writer(checkpoint_dir: Path):
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    counter = {"value": 0}

    def write_checkpoint(layer_name: str, partial_trace: dict[str, Any]) -> None:
        counter["value"] += 1
        filename = f"{counter['value']:02d}_{_safe_filename(layer_name)}.json"
        payload = {
            "status": "checkpoint",
            "layer": layer_name,
            "partial_trace": partial_trace,
        }
        (checkpoint_dir / filename).write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return write_checkpoint


def _write_failure_trace(output_dir: Path, exc: Exception) -> None:
    trace_path = output_dir / "rebuttal_lens_trace.json"
    checkpoint_dir = output_dir / "checkpoints"
    checkpoint_files = sorted(checkpoint_dir.glob("*.json")) if checkpoint_dir.exists() else []
    partial_trace: dict[str, Any] = {
        "message_bus": [],
        "execution_trace": [],
        "summary": {},
    }
    if trace_path.exists():
        try:
            partial_trace = json.loads(trace_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            partial_trace["summary"] = {"trace_read_error": str(trace_path)}
    elif checkpoint_files:
        try:
            checkpoint = json.loads(checkpoint_files[-1].read_text(encoding="utf-8"))
            partial_trace = checkpoint.get("partial_trace", partial_trace)
        except (OSError, json.JSONDecodeError):
            partial_trace = {
                "message_bus": [],
                "execution_trace": [],
                "summary": {"checkpoint_read_error": str(checkpoint_files[-1])},
            }
    exception_partial_trace = getattr(exc, "partial_trace", None)
    if isinstance(exception_partial_trace, dict):
        partial_trace = exception_partial_trace
    payload = {
        "status": "failed",
        "error": str(exc),
        "partial_trace": partial_trace,
    }
    (output_dir / "rebuttal_lens_failure_trace.json").write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def _safe_filename(value: str) -> str:
    safe = []
    for char in value.lower():
        if char.isalnum():
            safe.append(char)
        elif safe and safe[-1] != "_":
            safe.append("_")
    return "".join(safe).strip("_") or "layer"
