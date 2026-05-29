from dataclasses import asdict, dataclass, fields
from typing import Any


@dataclass(frozen=True)
class PaperRecord:
    paper_id: str
    doi: str
    title: str
    journal: str
    year: int | None
    abstract: str
    quality: str
    ai_relevance_score: int | float | None
    peer_review_source: str
    source_files: list[str]
    raw_json_path: str
    reviewer_report_count: int
    has_author_response_field: bool
    has_response_markers_in_reports: bool
    has_reviewer_markers_in_reports: bool
    has_peer_review_file_block: bool
    publisher_family: str
    journal_family: str
    article_type: str
    interaction_level: str
    response_presence: bool
    decision_presence: bool

    def __post_init__(self) -> None:
        required_strings = {
            "paper_id": self.paper_id,
            "doi": self.doi,
            "raw_json_path": self.raw_json_path,
        }
        for name, value in required_strings.items():
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
        if not isinstance(self.source_files, list):
            raise ValueError("source_files must be a list")
        if self.reviewer_report_count < 0:
            raise ValueError("reviewer_report_count must be non-negative")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "PaperRecord":
        required = {field.name for field in fields(cls)}
        missing = sorted(required - set(data))
        if missing:
            raise ValueError(f"missing required PaperRecord fields: {', '.join(missing)}")
        return cls(**{name: data[name] for name in required})
