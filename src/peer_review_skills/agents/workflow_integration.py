"""
Multi-Agent Workflow Integration

Integrates the true multi-agent system with the NatureReview-Interact v0.1
knowledge base, retrieval artifacts, provenance, and cross-disciplinary lenses.
"""

import json
import re
from pathlib import Path
from typing import Any

from peer_review_skills.agents.multi_agent_orchestrator import MultiAgentOrchestrator
from peer_review_skills.agents.specialized_agents_part2 import create_all_specialized_agents
from peer_review_skills.api.openai_compatible import OpenAICompatibleChatClient
from peer_review_skills.io.jsonl import read_jsonl, write_jsonl


DEFAULT_OUTPUT_DIR = Path("data/evaluation/workflow_v3")
OFFICIAL_UNIT_PATHS = (
    Path("data/processed/review_interaction_kb/v1/interaction_units.jsonl"),
)
OFFICIAL_RETRIEVAL_PATHS = (
    Path("data/evaluation/retrieval_v2/predictions.jsonl"),
)


def build_multi_agent_workflow_traces(
    interaction_units: list[dict[str, Any]],
    retrieval_predictions: list[dict[str, Any]],
    model_client: Any,
    taxonomies: dict[str, Any],
    config: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    """
    Build workflow traces using true multi-agent system.

    Args:
        interaction_units: List of interaction units
        retrieval_predictions: List of retrieval results
        model_client: OpenAI-compatible client
        taxonomies: Taxonomy definitions
        config: Optional configuration

    Returns:
        List of workflow traces with agent outputs
    """
    config = config or {}
    if not interaction_units:
        raise ValueError("No interaction units supplied to multi-agent workflow")
    if not retrieval_predictions:
        raise ValueError("No retrieval predictions supplied to multi-agent workflow")

    # Create agents
    agents = create_all_specialized_agents(model_client)

    # Create orchestrator
    orchestrator = MultiAgentOrchestrator(
        agents=agents,
        enable_refinement=config.get("enable_refinement", False),
        max_refinement_iterations=config.get("max_refinement_iterations", 2)
    )

    # Build traces
    traces = []
    retrieval_by_unit = {
        str(pred.get("query_unit_id")): pred
        for pred in retrieval_predictions
        if pred.get("query_unit_id")
    }
    if not retrieval_by_unit:
        raise ValueError("Retrieval predictions do not contain query_unit_id values")

    for unit in interaction_units:
        unit_id = str(unit.get("unit_id") or "")
        pred = retrieval_by_unit.get(unit_id)
        if pred is None:
            continue
        trace = orchestrator.execute_workflow(unit, pred, taxonomies)
        traces.append(trace)

    if not traces:
        raise ValueError(
            "Multi-agent workflow produced zero traces; check KB/retrieval alignment by unit_id"
        )

    return traces


def run_multi_agent_workflow(
    project_root: Path,
    scope: str = "mvp",
    config: dict[str, Any] | None = None,
    model_client: Any | None = None,
) -> dict[str, Any]:
    """
    Run the complete NatureReview true multi-agent workflow.

    Args:
        project_root: Project root directory
        scope: Scope (mvp or all)
        config: Optional configuration

    Returns:
        Workflow execution summary
    """
    config = config or {}

    interaction_units = _load_interaction_units(project_root)
    retrieval_predictions = _load_retrieval_predictions(project_root)

    # Load taxonomies
    taxonomies = _load_taxonomies(project_root)

    model_client = model_client or _create_model_client(config)
    limit = int(config.get("limit", 50))
    if limit <= 0:
        raise ValueError("config limit must be > 0")

    traces = build_multi_agent_workflow_traces(
        interaction_units[:limit],
        retrieval_predictions,
        model_client,
        taxonomies,
        config,
    )

    # Save traces
    output_dir = Path(config.get("output_dir") or project_root / DEFAULT_OUTPUT_DIR)
    output_dir.mkdir(parents=True, exist_ok=True)
    write_jsonl(output_dir / "workflow_traces.jsonl", traces)

    # Generate summary
    summary = {
        "mode": "multi_agent",
        "scope": scope,
        "total_traces": len(traces),
        "total_llm_calls": sum(
            trace.get("execution_metadata", {}).get("total_llm_calls", 0)
            for trace in traces
        ),
        "input_interaction_units": len(interaction_units),
        "input_retrieval_predictions": len(retrieval_predictions),
        "config": _json_safe_config(config),
    }

    # Save summary
    (output_dir / "workflow_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2),
        encoding="utf-8"
    )

    return summary


def _json_safe_config(config: dict[str, Any]) -> dict[str, Any]:
    return {
        str(key): _json_safe_config_value(str(key), value)
        for key, value in config.items()
    }


def _json_safe_config_value(key: str, value: Any) -> Any:
    if _is_secret_config_key(key):
        return "<redacted>"
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {
            str(child_key): _json_safe_config_value(str(child_key), child_value)
            for child_key, child_value in value.items()
        }
    if isinstance(value, list):
        return [_json_safe_config_value(key, item) for item in value]
    if isinstance(value, tuple):
        return [_json_safe_config_value(key, item) for item in value]
    if isinstance(value, str) and _looks_like_secret_config_value(value):
        return "<redacted>"
    return value


def _is_secret_config_key(key: str) -> bool:
    normalized = key.lower().replace("-", "_")
    secret_markers = ("api_key", "authorization", "bearer", "token", "secret", "password")
    return any(marker in normalized for marker in secret_markers)


def _looks_like_secret_config_value(value: str) -> bool:
    stripped = value.strip()
    lowered = stripped.lower()
    if lowered.startswith("bearer "):
        return True
    if re.fullmatch(r"sk-[A-Za-z0-9_\-]{16,}", stripped):
        return True
    if "must-not-be-written" in lowered:
        return True
    return False


def _load_interaction_units(project_root: Path) -> list[dict[str, Any]]:
    """Load the official NatureReview-Interact v0.1 interaction units."""
    return _read_first_existing_jsonl(
        project_root,
        OFFICIAL_UNIT_PATHS,
        artifact_name="interaction units",
    )


def _load_retrieval_predictions(project_root: Path) -> list[dict[str, Any]]:
    """Load the official NatureReview-Interact v0.1 retrieval predictions."""
    return _read_first_existing_jsonl(
        project_root,
        OFFICIAL_RETRIEVAL_PATHS,
        artifact_name="retrieval predictions",
    )


def _read_first_existing_jsonl(
    project_root: Path,
    relative_paths: tuple[Path, ...],
    *,
    artifact_name: str,
) -> list[dict[str, Any]]:
    checked = []
    for relative_path in relative_paths:
        path = project_root / relative_path
        checked.append(str(path))
        if path.exists():
            records = list(read_jsonl(path))
            if not records:
                raise ValueError(f"{artifact_name} file is empty: {path}")
            return records
    raise FileNotFoundError(f"Missing {artifact_name}; checked: {checked}")


def _load_taxonomies(project_root: Path) -> dict[str, Any]:
    """Load all taxonomies"""
    taxonomy_dir = project_root / "data/processed/taxonomies"
    taxonomies = {}

    for taxonomy_file in taxonomy_dir.glob("*.json"):
        taxonomy_name = taxonomy_file.stem
        taxonomy = json.loads(taxonomy_file.read_text(encoding="utf-8"))
        taxonomies[taxonomy_name] = taxonomy
        alias = _taxonomy_alias(taxonomy_name, taxonomy)
        if alias:
            taxonomies[alias] = taxonomy

    return taxonomies


def _taxonomy_alias(taxonomy_name: str, taxonomy: dict[str, Any]) -> str | None:
    canonical = str(taxonomy.get("taxonomy_name") or taxonomy_name)
    canonical = canonical.removesuffix("_taxonomy")
    canonical = canonical.split(".", 1)[0]
    aliases = {
        "concern": "concern_taxonomy",
        "tacit_concern": "tacit_concern",
        "institutional_signal": "institutional_signal",
        "evidence_action": "evidence_action",
        "author_positioning": "author_positioning",
        "tone_commitment": "tone_commitment",
        "editor_signal": "editor_signal",
        "response_strategy": "response_strategy",
        "skill": "skill",
    }
    return aliases.get(canonical)


def _create_model_client(config: dict[str, Any]) -> Any:
    """Create model client from config"""
    import os

    api_base = config.get("api_base") or os.getenv("PEER_REVIEW_API_BASE_URL")
    api_key = config.get("api_key") or os.getenv("PEER_REVIEW_API_KEY")
    model = config.get("model") or os.getenv("PEER_REVIEW_API_MODEL", "deepseek-v3")

    if not api_base or not api_key:
        raise ValueError(
            "API configuration required. Set PEER_REVIEW_API_BASE_URL and PEER_REVIEW_API_KEY, "
            "or pass via config dict."
        )

    return OpenAICompatibleChatClient(
        base_url=api_base,
        api_key=api_key,
        model=model
    )


# CLI integration
def main():
    """CLI entry point for multi-agent workflow"""
    import argparse

    parser = argparse.ArgumentParser(description="Run multi-agent workflow")
    parser.add_argument("--project-root", type=Path, default=Path.cwd())
    parser.add_argument("--scope", choices=["mvp", "all"], default="mvp")
    parser.add_argument("--enable-refinement", action="store_true")
    parser.add_argument("--max-refinement-iterations", type=int, default=2)
    parser.add_argument("--limit", type=int, default=5)

    args = parser.parse_args()

    config = {
        "enable_refinement": args.enable_refinement,
        "max_refinement_iterations": args.max_refinement_iterations,
        "limit": args.limit,
    }

    result = run_multi_agent_workflow(
        args.project_root,
        args.scope,
        config,
    )
    print("\n=== Workflow Summary ===")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
