"""Kantian category lifecycle support for reviewer-concern judgments."""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Iterable


class CategoryStatus(str, Enum):
    DRAFT = "draft"
    CANDIDATE = "candidate"
    APPROVED = "approved"
    DERIVED_FORGETTABLE = "derived_forgettable"
    RETIRED = "retired"


@dataclass
class Category:
    name: str
    description: str = ""
    status: CategoryStatus = CategoryStatus.CANDIDATE
    confirmed_run_ids: list[str] = field(default_factory=list)
    metadata: dict[str, str] = field(default_factory=dict)
    category_id: str = ""
    triggers: list[str] = field(default_factory=list)
    strategy_family: str = ""
    source: str = "manual_seed"
    forgetting_eligible: bool = True

    def to_dict(self) -> dict[str, object]:
        payload = asdict(self)
        payload["status"] = self.status.value
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, object]) -> "Category":
        return cls(
            name=str(payload["name"]),
            description=str(payload.get("description", "")),
            status=CategoryStatus(str(payload.get("status", CategoryStatus.CANDIDATE.value))),
            confirmed_run_ids=[
                str(run_id)
                for run_id in payload.get("confirmed_run_ids", [])
                if str(run_id).strip()
            ],
            metadata={
                str(key): str(value)
                for key, value in dict(payload.get("metadata", {})).items()
            },
            category_id=str(payload.get("category_id", "")),
            triggers=[
                str(trigger)
                for trigger in payload.get("triggers", [])
                if str(trigger).strip()
            ],
            strategy_family=str(payload.get("strategy_family", "")),
            source=str(payload.get("source", "manual_seed")),
            forgetting_eligible=bool(payload.get("forgetting_eligible", True)),
        )


@dataclass
class KantianCategory:
    category_id: str
    name: str
    description: str = ""
    triggers: list[str] = field(default_factory=list)
    strategy_family: str = ""
    status: CategoryStatus = CategoryStatus.CANDIDATE
    source: str = "manual_seed"
    forgetting_eligible: bool = True


@dataclass(frozen=True)
class CategoryMatch:
    category: Category
    similarity: float


class CategoryRegistry:
    """Persistent registry of Kantian categories discovered across runs."""

    def __init__(
        self,
        path: str | Path,
        *,
        approval_threshold: int | None = None,
        confirmation_threshold: int | None = None,
    ):
        self.path = Path(path)
        threshold = approval_threshold if approval_threshold is not None else confirmation_threshold
        self.approval_threshold = max(1, int(threshold or 3))
        self._categories: dict[str, Category] = {}
        if self.path.exists():
            self._categories = self._read_categories(self.path)

    @classmethod
    def load(
        cls,
        path: str | Path,
        *,
        approval_threshold: int | None = None,
        confirmation_threshold: int | None = None,
    ) -> "CategoryRegistry":
        return cls(
            path,
            approval_threshold=approval_threshold,
            confirmation_threshold=confirmation_threshold,
        )

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "categories": [
                category.to_dict()
                for category in sorted(self._categories.values(), key=lambda item: item.name)
            ]
        }
        self.path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True),
            encoding="utf-8",
        )

    def upsert(
        self,
        name: str | KantianCategory,
        *,
        description: str = "",
        status: CategoryStatus | str | None = None,
        run_id: str | None = None,
        metadata: dict[str, str] | None = None,
    ) -> Category:
        category_spec: KantianCategory | None = None
        if isinstance(name, KantianCategory):
            category_spec = name
            canonical_name = name.category_id or name.name
            metadata = {
                **(metadata or {}),
                "category_id": name.category_id,
                "display_name": name.name,
                "strategy_family": name.strategy_family,
                "source": name.source,
                "triggers": json.dumps(name.triggers, ensure_ascii=False),
            }
            description = description or name.description
            status = status or name.status
            name = canonical_name
        key = _normalize_name(name)
        next_status = _status_or_default(status, CategoryStatus.CANDIDATE)
        category = self._categories.get(key)
        if category is None:
            category = Category(name=key, status=next_status)
            self._categories[key] = category
        if category_spec is not None:
            category.category_id = _normalize_name(
                category_spec.category_id or category_spec.name
            )
            category.triggers = list(category_spec.triggers)
            category.strategy_family = category_spec.strategy_family
            category.source = category_spec.source
            category.forgetting_eligible = bool(category_spec.forgetting_eligible)
        elif not category.category_id:
            category.category_id = key
        if description:
            category.description = description
        if status is not None:
            category.status = next_status
        if metadata:
            category.metadata.update({str(k): str(v) for k, v in metadata.items()})
        if run_id:
            self._add_confirmation(category, run_id)
        return category

    def get(self, name: str) -> Category:
        key = self._resolve_key(name)
        if key not in self._categories:
            raise KeyError(f"Unknown category: {name}")
        return self._categories[key]

    def all(self) -> list[Category]:
        return [
            self._categories[name]
            for name in sorted(self._categories)
        ]

    def record_confirmation(
        self,
        name: str,
        run_id: str,
        confirmation_type: str | None = None,
    ) -> Category:
        category = self.get(name)
        self._add_confirmation(category, run_id)
        if (
            category.status in {CategoryStatus.DRAFT, CategoryStatus.CANDIDATE}
            and len(category.confirmed_run_ids) >= self.approval_threshold
        ):
            category.status = CategoryStatus.APPROVED
        return category

    def match(
        self,
        text: str,
        *,
        threshold: float = 0.2,
        statuses: Iterable[CategoryStatus | str] | None = None,
    ) -> CategoryMatch | None:
        allowed = {
            _status_or_default(status, CategoryStatus.APPROVED)
            for status in (statuses or [CategoryStatus.APPROVED])
        }
        best: CategoryMatch | None = None
        for category in self._categories.values():
            if category.status not in allowed:
                continue
            similarity = _jaccard_similarity(text, _category_match_text(category))
            if best is None or similarity > best.similarity:
                best = CategoryMatch(category=category, similarity=similarity)
        if best is None or best.similarity < threshold:
            return None
        return best

    def match_candidates(
        self,
        text: str,
        *,
        min_similarity: float = 0.0,
        statuses: Iterable[CategoryStatus | str] | None = None,
    ) -> list[dict[str, Any]]:
        allowed_statuses = statuses or [
            CategoryStatus.APPROVED,
            CategoryStatus.CANDIDATE,
            CategoryStatus.DERIVED_FORGETTABLE,
        ]
        allowed = {
            _status_or_default(status, CategoryStatus.APPROVED)
            for status in allowed_statuses
        }
        candidates = []
        for category in self._categories.values():
            if category.status not in allowed:
                continue
            similarity = _jaccard_similarity(text, _category_match_text(category))
            if similarity >= min_similarity:
                candidates.append({
                    "category_id": category.category_id
                    or category.metadata.get("category_id", category.name),
                    "name": category.name,
                    "status": category.status.value,
                    "strategy_family": category.strategy_family
                    or category.metadata.get("strategy_family", ""),
                    "similarity": similarity,
                })
        return sorted(candidates, key=lambda item: item["similarity"], reverse=True)

    def _add_confirmation(self, category: Category, run_id: str) -> None:
        run_key = str(run_id).strip()
        if run_key and run_key not in category.confirmed_run_ids:
            category.confirmed_run_ids.append(run_key)

    def _resolve_key(self, name: str) -> str:
        key = _normalize_name(name)
        if key in self._categories:
            return key
        for category_key, category in self._categories.items():
            aliases = {
                category.category_id,
                category.metadata.get("category_id", ""),
                category.metadata.get("display_name", ""),
            }
            if any(alias and _normalize_name(alias) == key for alias in aliases):
                return category_key
        return key

    @staticmethod
    def _read_categories(path: Path) -> dict[str, Category]:
        raw = json.loads(path.read_text(encoding="utf-8"))
        categories = raw.get("categories", raw)
        if isinstance(categories, dict):
            categories = categories.values()
        return {
            _normalize_name(category.name): category
            for category in (Category.from_dict(item) for item in categories)
        }


def _status_or_default(status: CategoryStatus | str | None, default: CategoryStatus) -> CategoryStatus:
    if status is None:
        return default
    if isinstance(status, CategoryStatus):
        return status
    return CategoryStatus(str(status))


def _normalize_name(name: str) -> str:
    text = str(name or "").strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text).strip("_")
    if not text:
        raise ValueError("Category name cannot be empty")
    return text


def _tokens(text: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9]+", str(text).lower())
        if len(token) > 2
    }


def _jaccard_similarity(left: str, right: str) -> float:
    left_tokens = _tokens(left)
    right_tokens = _tokens(right)
    if not left_tokens or not right_tokens:
        return 0.0
    return len(left_tokens & right_tokens) / len(left_tokens | right_tokens)


def category_similarity(text: str, triggers: list[str]) -> float:
    return _jaccard_similarity(text, " ".join(str(trigger) for trigger in triggers))


def _category_match_text(category: Category) -> str:
    triggers = " ".join(category.triggers) or category.metadata.get("triggers", "")
    display_name = category.metadata.get("display_name", "")
    return f"{category.name} {display_name} {category.description} {triggers}"
