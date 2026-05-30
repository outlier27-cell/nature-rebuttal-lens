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
    except Exception as exc:
        _write_failure_trace(output_dir, exc)
        raise

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


def load_rebuttal_lens_config(path: str | Path) -> dict[str, Any]:
    """Load the small public RebuttalLens YAML config without adding a runtime YAML dependency."""
    config_path = Path(path)
    if not config_path.exists():
        return {}
    return _parse_simple_yaml(config_path.read_text(encoding="utf-8"))


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
    checkpoint_dir = output_dir / "checkpoints"
    checkpoint_files = sorted(checkpoint_dir.glob("*.json")) if checkpoint_dir.exists() else []
    partial_trace: dict[str, Any] = {
        "message_bus": [],
        "execution_trace": [],
        "summary": {},
    }
    if checkpoint_files:
        try:
            checkpoint = json.loads(checkpoint_files[-1].read_text(encoding="utf-8"))
            partial_trace = checkpoint.get("partial_trace", partial_trace)
        except (OSError, json.JSONDecodeError):
            partial_trace = {
                "message_bus": [],
                "execution_trace": [],
                "summary": {"checkpoint_read_error": str(checkpoint_files[-1])},
            }
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
