from dataclasses import asdict, dataclass, fields
from typing import Any


EVIDENCE_STATUSES = {"validated", "candidate", "rejected"}


@dataclass(frozen=True)
class SkillCard:
    skill_id: str
    name: str
    definition: str
    trigger_pattern: str
    reviewer_intent: str
    recommended_response_strategies: list[str]
    required_evidence_types: list[str]
    successful_example_ids: list[str]
    failure_example_ids: list[str]
    anti_patterns: list[str]
    notes: str
    taxonomy_version: str
    evidence_status: str
    quality_score: float
    quality_metrics: dict[str, float | int | str]
    review_recommendation: str

    def __post_init__(self) -> None:
        for name in ("skill_id", "name", "definition", "trigger_pattern", "reviewer_intent", "taxonomy_version"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
        for name in (
            "recommended_response_strategies",
            "required_evidence_types",
            "successful_example_ids",
            "failure_example_ids",
            "anti_patterns",
        ):
            value = getattr(self, name)
            if not isinstance(value, list):
                raise ValueError(f"{name} must be a list")
        if not self.recommended_response_strategies:
            raise ValueError("recommended_response_strategies must not be empty")
        if not self.successful_example_ids and not self.failure_example_ids:
            raise ValueError("skill cards must reference at least one grounded interaction")
        if self.evidence_status not in EVIDENCE_STATUSES:
            raise ValueError(f"invalid evidence_status: {self.evidence_status}")
        if not 0.0 <= float(self.quality_score) <= 1.0:
            raise ValueError("quality_score must be between 0.0 and 1.0")
        if not isinstance(self.quality_metrics, dict):
            raise ValueError("quality_metrics must be a dictionary")
        if not isinstance(self.review_recommendation, str) or not self.review_recommendation.strip():
            raise ValueError("review_recommendation is required")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SkillCard":
        required = {field.name for field in fields(cls)}
        missing = sorted(required - set(data))
        if missing:
            raise ValueError(f"missing required SkillCard fields: {', '.join(missing)}")
        return cls(**{name: data[name] for name in required})
