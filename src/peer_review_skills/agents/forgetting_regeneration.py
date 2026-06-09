"""Regenerate abstract category candidates from safe forgetting-ledger signals."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

try:
    from peer_review_skills.agents.kantian_categories import CategoryStatus
except ModuleNotFoundError:  # pragma: no cover - removed once core category module lands.
    CategoryStatus = None  # type: ignore[assignment]

from peer_review_skills.agents.memory_ethics import (
    REGENERATION_BLOCKED_MEMORY_CLASSES,
    regeneration_safe_forgetting_events,
)


def regenerate_categories_from_forgetting_ledger(
    forgetting_ledger: list[dict[str, Any]] | tuple[dict[str, Any], ...],
    *,
    run_id: str | None = None,
    registry_path: str | Path | None = None,
    min_pattern_count: int = 1,
    confirmation_threshold: int = 3,
) -> dict[str, Any]:
    blocked_memory_classes = _blocked_memory_classes(forgetting_ledger)
    safe_events = regeneration_safe_forgetting_events(forgetting_ledger)
    pattern_counts = _pattern_counts(safe_events)
    derived_forgettable = []
    for event in safe_events:
        source_text = event.get("pattern_hint") or event.get("reason") or ""
        if pattern_counts.get(source_text, 0) < max(1, int(min_pattern_count)):
            continue
        derived_forgettable.append(_candidate_from_safe_event(event, run_id=run_id))
    derived_forgettable = [candidate for candidate in derived_forgettable if candidate is not None]
    if registry_path and derived_forgettable:
        _write_registry_candidates(
            Path(registry_path),
            derived_forgettable,
            confirmation_threshold=confirmation_threshold,
        )
    return {
        "derived_forgettable": derived_forgettable,
        "regenerated_category_candidates": derived_forgettable,
        "blocked_memory_classes": blocked_memory_classes,
        "regeneration_policy": "retain_structure_discard_sensitive_details",
    }


def _blocked_memory_classes(
    forgetting_ledger: list[dict[str, Any]] | tuple[dict[str, Any], ...],
) -> list[str]:
    blocked: list[str] = []
    for event in forgetting_ledger or []:
        memory_class = str(event.get("memory_class", "")).strip()
        if memory_class in REGENERATION_BLOCKED_MEMORY_CLASSES and memory_class not in blocked:
            blocked.append(memory_class)
    return blocked


def _candidate_from_safe_event(
    event: dict[str, str],
    *,
    run_id: str | None,
) -> dict[str, Any] | None:
    source_text = event.get("pattern_hint") or event.get("reason") or ""
    name = _category_name(source_text)
    if not name:
        return None
    candidate = {
        "category_id": name,
        "name": name,
        "description": source_text,
        "status": _derived_forgettable_status(),
        "source_memory_class": event["memory_class"],
    }
    if run_id:
        candidate["source_run_id"] = run_id
    return candidate


def _derived_forgettable_status() -> str:
    if CategoryStatus is None:
        return "derived_forgettable"
    return CategoryStatus.DERIVED_FORGETTABLE.value


def _category_name(text: str) -> str:
    words = re.findall(r"[a-z0-9]+", text.lower())
    if not words:
        return ""
    stop_words = {
        "a",
        "an",
        "are",
        "as",
        "but",
        "can",
        "from",
        "is",
        "of",
        "or",
        "past",
        "the",
        "this",
        "to",
    }
    normalized = [word for word in words if word not in stop_words]
    return "_".join(normalized[:7])


def _pattern_counts(events: list[dict[str, str]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for event in events:
        source_text = event.get("pattern_hint") or event.get("reason") or ""
        if not source_text:
            continue
        counts[source_text] = counts.get(source_text, 0) + 1
    return counts


def _write_registry_candidates(
    registry_path: Path,
    candidates: list[dict[str, Any]],
    *,
    confirmation_threshold: int,
) -> None:
    from peer_review_skills.agents.kantian_categories import CategoryRegistry, CategoryStatus

    registry = CategoryRegistry.load(
        registry_path,
        confirmation_threshold=confirmation_threshold,
    )
    for candidate in candidates:
        registry.upsert(
            str(candidate["name"]),
            description=str(candidate.get("description", "")),
            status=CategoryStatus.DERIVED_FORGETTABLE,
            metadata={
                "source_memory_class": str(candidate.get("source_memory_class", "")),
                "category_id": str(candidate.get("category_id", "")),
            },
        )
    registry.save()
