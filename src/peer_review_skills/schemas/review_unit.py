from dataclasses import asdict, dataclass, fields
from typing import Any


SPEAKER_TYPES = {"reviewer", "author", "editor", "unknown"}


@dataclass(frozen=True)
class ReviewUnit:
    unit_id: str
    paper_id: str
    source_report_index: int
    source_report_reviewer: str
    round_id: str
    speaker_type: str
    speaker_id: str
    section_label: str
    text: str
    char_start: int
    char_end: int
    marker_text: str
    segmentation_method: str
    segmentation_confidence: float
    source_trace: dict[str, Any]

    def __post_init__(self) -> None:
        for name in ("unit_id", "paper_id", "round_id", "speaker_type", "speaker_id"):
            value = getattr(self, name)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"{name} is required")
        if self.speaker_type not in SPEAKER_TYPES:
            raise ValueError(f"invalid speaker_type: {self.speaker_type}")
        if self.source_report_index < -1:
            raise ValueError("source_report_index must be -1 or greater")
        if self.char_start < 0 or self.char_end < self.char_start:
            raise ValueError("invalid character offsets")
        if not 0.0 <= float(self.segmentation_confidence) <= 1.0:
            raise ValueError("segmentation_confidence must be between 0.0 and 1.0")
        if not isinstance(self.source_trace, dict):
            raise ValueError("source_trace must be a dictionary")
        for key in ("raw_json_path", "json_pointer", "source_report_index"):
            if key not in self.source_trace:
                raise ValueError(f"source_trace missing {key}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ReviewUnit":
        required = {field.name for field in fields(cls)}
        missing = sorted(required - set(data))
        if missing:
            raise ValueError(f"missing required ReviewUnit fields: {', '.join(missing)}")
        return cls(**{name: data[name] for name in required})
