from dataclasses import asdict, dataclass, fields
from typing import Any

from peer_review_skills.schemas.annotation import (
    AUTHOR_STRATEGIES,
    CONCERN_TYPES,
    EVIDENCE_REQUESTS,
    RESPONSE_STANCES,
    REVIEWER_SENTIMENTS,
    REVIEWER_SEVERITIES,
)


ALIGNMENT_STATUSES = {"matched", "missing_response", "ambiguous", "unsupported"}
RESPONSE_OUTCOMES = {"addressed", "partially_addressed", "contested", "deferred", "unanswered", "ambiguous", "unknown"}


@dataclass(frozen=True)
class InteractionUnit:
    interaction_id: str
    paper_id: str
    round_id: str
    reviewer_id: str
    review_unit_ids: list[str]
    review_span_text: str
    author_unit_ids: list[str]
    author_response_text: str
    alignment_method: str
    alignment_confidence: float
    alignment_status: str
    source_trace: dict[str, Any]
    concern_type: str
    concern_claim: str
    evidence_request: str
    reviewer_sentiment: str
    reviewer_severity: str
    author_strategy: str
    author_action: str
    response_stance: str
    response_outcome: str

    def __post_init__(self) -> None:
        for name in ("interaction_id", "paper_id", "round_id", "reviewer_id", "alignment_method"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
        if not isinstance(self.review_unit_ids, list) or not self.review_unit_ids:
            raise ValueError("review_unit_ids must be a non-empty list")
        if not all(isinstance(unit_id, str) and unit_id.strip() for unit_id in self.review_unit_ids):
            raise ValueError("review_unit_ids must contain non-empty strings")
        if not isinstance(self.author_unit_ids, list):
            raise ValueError("author_unit_ids must be a list")
        if not all(isinstance(unit_id, str) and unit_id.strip() for unit_id in self.author_unit_ids):
            raise ValueError("author_unit_ids must contain non-empty strings")
        if not 0.0 <= float(self.alignment_confidence) <= 1.0:
            raise ValueError("alignment_confidence must be between 0.0 and 1.0")
        if self.alignment_status not in ALIGNMENT_STATUSES:
            raise ValueError(f"invalid alignment_status: {self.alignment_status}")
        if self.alignment_status == "matched" and not self.author_unit_ids:
            raise ValueError("matched interactions require author_unit_ids")
        if self.concern_type not in CONCERN_TYPES:
            raise ValueError(f"invalid concern_type: {self.concern_type}")
        if self.evidence_request not in EVIDENCE_REQUESTS:
            raise ValueError(f"invalid evidence_request: {self.evidence_request}")
        if self.reviewer_sentiment not in REVIEWER_SENTIMENTS:
            raise ValueError(f"invalid reviewer_sentiment: {self.reviewer_sentiment}")
        if self.reviewer_severity not in REVIEWER_SEVERITIES:
            raise ValueError(f"invalid reviewer_severity: {self.reviewer_severity}")
        if self.author_strategy not in AUTHOR_STRATEGIES:
            raise ValueError(f"invalid author_strategy: {self.author_strategy}")
        if self.response_stance not in RESPONSE_STANCES:
            raise ValueError(f"invalid response_stance: {self.response_stance}")
        if self.response_outcome not in RESPONSE_OUTCOMES:
            raise ValueError(f"invalid response_outcome: {self.response_outcome}")
        if not isinstance(self.source_trace, dict):
            raise ValueError("source_trace must be a dictionary")
        for key in ("review_unit_ids", "author_unit_ids"):
            if key not in self.source_trace:
                raise ValueError(f"source_trace missing {key}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "InteractionUnit":
        required = {field.name for field in fields(cls)}
        missing = sorted(required - set(data))
        if missing:
            raise ValueError(f"missing required InteractionUnit fields: {', '.join(missing)}")
        return cls(**{name: data[name] for name in required})
