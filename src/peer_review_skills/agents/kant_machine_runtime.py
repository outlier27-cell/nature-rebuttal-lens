"""Runtime adapter for Kant Machine Organic RebuttalLens."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from peer_review_skills.agents.computational_self_legislation import build_self_legislation
from peer_review_skills.agents.kantian_categories import CategoryRegistry
from peer_review_skills.agents.reflective_judgment import build_reflective_judgment
from peer_review_skills.agents.unknowability_ledger import build_unknowability_ledger


def build_kant_machine_runtime(trace: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Build deterministic Kant-machine metadata for a RebuttalLens trace."""
    ethics_audit_chain_enabled = bool(config.get("enable_ethics_audit_chain", True))
    phase2_enabled = bool(config.get("enable_kant_phase2"))
    enabled = (
        bool(config.get("enable_kantian_categories"))
        or bool(config.get("enable_universalization_gate"))
        or bool(config.get("enable_reflective_judgment"))
        or bool(config.get("enable_self_legislation"))
        or bool(config.get("enable_unknowability_ledger"))
        or bool(config.get("enable_blackbox_transparency"))
        or bool(config.get("enable_organic_quality"))
        or phase2_enabled
        or ethics_audit_chain_enabled
    )
    registry_path = _category_registry_path(config)
    threshold = int(config.get("category_confirmation_threshold", 3))
    registry = CategoryRegistry.load(
        path=registry_path,
        confirmation_threshold=threshold,
    )
    reflective_judgment = {}
    if bool(config.get("enable_reflective_judgment")):
        reflective_judgment = build_reflective_judgment(
            concern_text=_concern_text(trace),
            registry=registry,
            min_similarity=float(config.get("reflective_similarity_threshold", 0.25)),
        )
    if enabled and (
        bool(config.get("enable_kantian_categories"))
        or bool(config.get("enable_reflective_judgment"))
        or registry.all()
    ):
        registry.save()
    self_legislation = build_self_legislation(trace=trace, config=config)
    unknowability_ledger = build_unknowability_ledger(trace=trace, config=config)
    blackbox_transparency = {
        "enabled": bool(config.get("enable_blackbox_transparency") or phase2_enabled)
    }
    organic_quality = {
        "enabled": bool(config.get("enable_organic_quality") or phase2_enabled)
    }
    cognition_loop = _build_cognition_loop(
        trace=trace,
        reflective_judgment=reflective_judgment,
        self_legislation=self_legislation,
        unknowability_ledger=unknowability_ledger,
        blackbox_transparency=blackbox_transparency,
        organic_quality=organic_quality,
    )
    return {
        "enabled": enabled,
        "phase": "kant_machine_phase2" if phase2_enabled else "kant_machine_phase1",
        "category_registry_path": str(registry_path),
        "category_confirmation_threshold": threshold,
        "category_count": len(registry.all()),
        "ethics_audit_chain_enabled": ethics_audit_chain_enabled,
        "reflective_judgment": reflective_judgment,
        "self_legislation": self_legislation,
        "unknowability_ledger": unknowability_ledger,
        "blackbox_transparency": blackbox_transparency,
        "organic_quality": organic_quality,
        "cognition_loop": cognition_loop,
        "heteronomy_boundary": {
            "system_may_commit_for_author": False,
            "category_generation_requires_author_confirmation": True,
            "derived_categories_are_forgetting_eligible": True,
        },
    }


def attach_kant_machine_runtime(trace: dict[str, Any], config: dict[str, Any]) -> dict[str, Any]:
    """Attach Kant-machine metadata without mutating caller-owned config."""
    trace["kant_machine_runtime"] = build_kant_machine_runtime(trace, config)
    return trace


def _category_registry_path(config: dict[str, Any]) -> Path:
    raw_path = config.get("category_registry_path")
    if raw_path:
        path = Path(raw_path)
    else:
        output_dir = Path(
            config.get("output_dir")
            or _output_dir_from_checkpoint(config.get("checkpoint_dir"))
            or "."
        )
        path = output_dir / "kantian_category_registry.json"
    if path.suffix.lower() != ".json":
        path = path / "kantian_category_registry.json"
    return path


def _output_dir_from_checkpoint(checkpoint_dir: Any) -> Path | None:
    if not checkpoint_dir:
        return None
    checkpoint_path = Path(checkpoint_dir)
    if checkpoint_path.name == "checkpoints":
        return checkpoint_path.parent
    return checkpoint_path


def _concern_text(trace: dict[str, Any]) -> str:
    outputs = trace.get("agent_intermediate_outputs", {})
    reviewer = outputs.get("reviewer_understanding_agent") or outputs.get("reviewer_understanding") or {}
    if not isinstance(reviewer, dict):
        return ""
    parts: list[str] = []
    for concern in reviewer.get("concern_map", []):
        if not isinstance(concern, dict):
            continue
        for key in ("surface_request", "text_evidence", "latent_concern", "concern_type"):
            value = concern.get(key)
            if value:
                parts.append(str(value))
    return " ".join(parts)


def _build_cognition_loop(
    *,
    trace: dict[str, Any],
    reflective_judgment: dict[str, Any],
    self_legislation: dict[str, Any],
    unknowability_ledger: dict[str, Any],
    blackbox_transparency: dict[str, Any],
    organic_quality: dict[str, Any],
) -> dict[str, list[str]]:
    """Expose the mechanical/empirical/category layers behind the run."""
    outputs = trace.get("agent_intermediate_outputs", {})
    mechanical = [
        "dag_or_layered_workflow",
        "response_package_schema",
        "universalization_gate",
    ]
    empirical = [
        name
        for name in [
            "reviewer_understanding_agent",
            "manuscript_evidence_locator",
            "evidence_action_planner",
            "case_retrieval_agent",
            "committee_meta_reviewer",
            "strategy_meta_planner",
        ]
        if isinstance(outputs, dict) and name in outputs
    ]
    if not empirical:
        empirical = ["provided_trace_outputs"]
    category = []
    if reflective_judgment:
        category.append(str(reflective_judgment.get("mode", "reflective_judgment")))
    if self_legislation.get("enabled"):
        category.append("computational_self_legislation")
    if unknowability_ledger.get("enabled"):
        category.append("unknowability_boundary")
    if blackbox_transparency.get("enabled"):
        category.append("blackbox_transparency")
    if organic_quality.get("enabled"):
        category.append("organic_quality")
    return {
        "mechanical_layer": mechanical,
        "empirical_layer": empirical,
        "category_layer": category,
    }
