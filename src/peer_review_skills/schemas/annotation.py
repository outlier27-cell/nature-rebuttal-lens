from dataclasses import asdict, dataclass, fields
from typing import Any


CONCERN_TYPES = {
    "baseline_comparison",
    "generalization_scope",
    "reproducibility_reporting",
    "statistics_significance",
    "ablation_mechanism",
    "clarity_presentation",
    "experimental_design",
    "dataset_bias_ethics_safety",
    "theoretical_validity",
    "novelty_positioning",
    "unknown",
}
EVIDENCE_REQUESTS = {
    "baseline",
    "ablation",
    "experiment",
    "statistics",
    "data_code",
    "clarification",
    "scope",
    "none",
    "unknown",
}
REVIEWER_SENTIMENTS = {"supportive", "neutral", "skeptical", "critical", "strongly_critical"}
REVIEWER_SEVERITIES = {"minor", "moderate", "major", "blocking", "unknown"}

AUTHOR_STRATEGIES = {
    "acknowledge_and_fix",
    "clarify_existing_evidence",
    "add_new_experiment",
    "add_new_analysis",
    "narrow_claim_scope",
    "contest_reviewer_premise",
    "defer_future_work",
    "justify_method_choice",
    "reframe_contribution",
    "editorial_only_change",
    "unknown",
}
RESPONSE_STANCES = {"agree", "partial", "disagree", "neutral", "unknown"}
EVIDENCE_SUPPLIED = {"experiment", "analysis", "data_code", "text_revision", "none", "unknown"}
SCOPE_ADJUSTMENTS = {"narrowed", "expanded", "none", "unknown"}


def _require_fields(cls, data: dict[str, Any]) -> dict[str, Any]:
    required = {field.name for field in fields(cls)}
    missing = sorted(required - set(data))
    if missing:
        raise ValueError(f"missing required {cls.__name__} fields: {', '.join(missing)}")
    return {name: data[name] for name in required}


def _validate_common(annotation_id: str, unit_id: str, paper_id: str, confidence: float) -> None:
    for name, value in {
        "annotation_id": annotation_id,
        "unit_id": unit_id,
        "paper_id": paper_id,
    }.items():
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"{name} is required")
    if not 0.0 <= float(confidence) <= 1.0:
        raise ValueError("confidence must be between 0.0 and 1.0")


@dataclass(frozen=True)
class ReviewerAnnotation:
    annotation_id: str
    unit_id: str
    paper_id: str
    concern_type: str
    concern_claim: str
    evidence_request: str
    reviewer_sentiment: str
    reviewer_severity: str
    confidence: float
    annotation_method: str
    matched_keywords: list[str]
    source_trace: dict[str, Any]

    def __post_init__(self) -> None:
        _validate_common(self.annotation_id, self.unit_id, self.paper_id, self.confidence)
        if self.concern_type not in CONCERN_TYPES:
            raise ValueError(f"invalid concern_type: {self.concern_type}")
        if self.evidence_request not in EVIDENCE_REQUESTS:
            raise ValueError(f"invalid evidence_request: {self.evidence_request}")
        if self.reviewer_sentiment not in REVIEWER_SENTIMENTS:
            raise ValueError(f"invalid reviewer_sentiment: {self.reviewer_sentiment}")
        if self.reviewer_severity not in REVIEWER_SEVERITIES:
            raise ValueError(f"invalid reviewer_severity: {self.reviewer_severity}")
        if not isinstance(self.matched_keywords, list):
            raise ValueError("matched_keywords must be a list")
        if not isinstance(self.source_trace, dict):
            raise ValueError("source_trace must be a dictionary")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReviewerAnnotation":
        return cls(**_require_fields(cls, data))


@dataclass(frozen=True)
class AuthorAnnotation:
    annotation_id: str
    unit_id: str
    paper_id: str
    author_strategy: str
    author_action: str
    response_stance: str
    evidence_supplied: str
    scope_adjustment: str
    confidence: float
    annotation_method: str
    matched_keywords: list[str]
    source_trace: dict[str, Any]

    def __post_init__(self) -> None:
        _validate_common(self.annotation_id, self.unit_id, self.paper_id, self.confidence)
        if self.author_strategy not in AUTHOR_STRATEGIES:
            raise ValueError(f"invalid author_strategy: {self.author_strategy}")
        if self.response_stance not in RESPONSE_STANCES:
            raise ValueError(f"invalid response_stance: {self.response_stance}")
        if self.evidence_supplied not in EVIDENCE_SUPPLIED:
            raise ValueError(f"invalid evidence_supplied: {self.evidence_supplied}")
        if self.scope_adjustment not in SCOPE_ADJUSTMENTS:
            raise ValueError(f"invalid scope_adjustment: {self.scope_adjustment}")
        if not isinstance(self.matched_keywords, list):
            raise ValueError("matched_keywords must be a list")
        if not isinstance(self.source_trace, dict):
            raise ValueError("source_trace must be a dictionary")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "AuthorAnnotation":
        return cls(**_require_fields(cls, data))
