"""Runtime memory ethics helpers for Nature RebuttalLens."""

from __future__ import annotations

from typing import Any


MEMORY_OBJECT_TAXONOMY: dict[str, dict[str, str]] = {
    "evidence_trace": {
        "description": "Evidence anchors, manuscript sections, retrieved-case references.",
        "default_action": "retain",
        "ethical_reason": "Keeps justification auditable without deciding for the author.",
    },
    "reasoning_trace": {
        "description": "Agent reasoning summaries and risk explanations.",
        "default_action": "retain",
        "ethical_reason": "Preserves why a suggestion exists, not whether it must be accepted.",
    },
    "audit_trace": {
        "description": "Execution metadata, agent outputs, final-report provenance.",
        "default_action": "retain",
        "ethical_reason": "Allows accountability and reproducibility.",
    },
    "author_decision": {
        "description": "Past author choices about experiments, claim narrowing, limitations, or commitments.",
        "default_action": "forget",
        "ethical_reason": "Author agency must be renewed for every run.",
    },
    "strategy_preference": {
        "description": "Historical preference for accept, defend, clarify, or experiment strategies.",
        "default_action": "forget",
        "ethical_reason": "A past strategy must not become an automatic future answer.",
    },
    "final_wording": {
        "description": "Prior final rebuttal phrasing or submission-ready response text.",
        "default_action": "forget",
        "ethical_reason": "The system plans responses; it must not preserve final author expression.",
    },
}


POLICY_SCOPES: dict[str, set[str]] = {
    "default": {"author_decision", "strategy_preference", "final_wording"},
    "strict": {
        "author_decision",
        "strategy_preference",
        "final_wording",
        "latent_commitment",
        "unsafe_claim",
    },
}


IRREVERSIBLE_FORGETTING_STATEMENT = {
    "author_decision": (
        "Forgotten author decisions must not be reconstructed from checkpoints, "
        "cache, retrieved cases, prior final reports, or historical run summaries."
    ),
    "strategy_preference": (
        "Forgotten strategy preferences must not become defaults for later runs."
    ),
    "final_wording": (
        "Forgotten final wording must not be reused as submission-ready author expression."
    ),
}


def build_memory_ethics_runtime(
    *,
    reset_memory: bool = False,
    memory_policy: str = "default",
    forget_scope: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    policy = _normalize_policy(memory_policy)
    forgotten = _forgotten_classes(policy, forget_scope)
    retained = [
        name
        for name, meta in MEMORY_OBJECT_TAXONOMY.items()
        if meta["default_action"] == "retain" and name not in forgotten
    ]
    ledger = [
        _forget_event(memory_class=name, policy=policy, reset_memory=reset_memory)
        for name in sorted(forgotten)
    ]
    return {
        "memory_passport": {
            "policy": policy,
            "reset_memory_requested": bool(reset_memory),
            "retained_memory_classes": retained,
            "forgotten_memory_classes": sorted(forgotten),
            "justification_memory_not_conclusion_memory": True,
            "forgetting_is_active_boundary": True,
            "irreversible_forgetting": True,
        },
        "forgetting_ledger": ledger,
        "irreversible_forgetting_statement": dict(IRREVERSIBLE_FORGETTING_STATEMENT),
    }


def filter_runtime_memory(
    memory: dict[str, Any],
    *,
    memory_policy: str = "default",
    forget_scope: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    policy = _normalize_policy(memory_policy)
    forgotten = _forgotten_classes(policy, forget_scope)
    return _drop_forgotten_memory_classes(dict(memory or {}), forgotten, top_level=True)


def _normalize_policy(memory_policy: str) -> str:
    policy = str(memory_policy or "default").strip().lower()
    if policy not in POLICY_SCOPES:
        return "default"
    return policy


def _forgotten_classes(
    policy: str,
    forget_scope: list[str] | tuple[str, ...] | None,
) -> set[str]:
    forgotten = set(POLICY_SCOPES[policy])
    for item in forget_scope or []:
        text = str(item).strip()
        if text:
            forgotten.add(text)
    return forgotten


def _forget_event(
    *,
    memory_class: str,
    policy: str,
    reset_memory: bool,
) -> dict[str, Any]:
    taxonomy = MEMORY_OBJECT_TAXONOMY.get(memory_class, {})
    return {
        "memory_class": memory_class,
        "action": "forgotten",
        "policy": policy,
        "reset_memory_requested": bool(reset_memory),
        "reason": taxonomy.get(
            "ethical_reason",
            "The configured memory policy marks this class as non-authoritative for future runs.",
        ),
        "system_may_reconstruct_from_evidence": memory_class not in {
            "author_decision",
            "strategy_preference",
            "final_wording",
        },
    }


def _drop_forgotten_memory_classes(
    value: Any,
    forgotten: set[str],
    *,
    top_level: bool = False,
) -> Any:
    if isinstance(value, list):
        filtered_items = [
            _drop_forgotten_memory_classes(item, forgotten)
            for item in value
        ]
        return [
            item for item in filtered_items
            if item not in ({}, [], None)
        ]
    if isinstance(value, dict):
        if not top_level and _contains_forgotten_memory_class(value, forgotten):
            return {}
        result = {}
        for key, item in value.items():
            if key in forgotten:
                continue
            filtered_item = _drop_forgotten_memory_classes(item, forgotten)
            if filtered_item not in ({}, [], None):
                result[key] = filtered_item
        return result
    return value


def _contains_forgotten_memory_class(value: dict[str, Any], forgotten: set[str]) -> bool:
    return any(key in forgotten for key in value)
