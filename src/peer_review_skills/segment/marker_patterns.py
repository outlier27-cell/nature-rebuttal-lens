import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Marker:
    marker_type: str
    start: int
    end: int
    text: str


MARKER_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("page", re.compile(r"---PAGE\s+\d+---", re.IGNORECASE)),
    ("round", re.compile(r"\b(Round\s+\d+|First revision|Second revision|Reviewers' comments)\b", re.IGNORECASE)),
    (
        "reviewer",
        re.compile(
            r"\b(Reviewer\s*#?\s*\d+|Referee\s*#?\s*\d+|Remarks to the Author|REVIEWER REPORT|REVIEWER COMMENTS)\b",
            re.IGNORECASE,
        ),
    ),
    (
        "author",
        re.compile(
            r"(?:\bRESPONSE:|\bResponse:|\bAuthor response\b|\bAuthor Reply\b|\bResponses?\s+to\s+Reviewers?'?(?:\s+Comments)?(?:\s+#?\d+(?:\s*(?:,|and)\s*#?\d+)*)?\b)",
            re.IGNORECASE,
        ),
    ),
    (
        "editor",
        re.compile(
            r"(?:^|\n)\s*(Decision letter|Editorial decision|Senior Editor|Editor)\b",
            re.IGNORECASE,
        ),
    ),
)


def find_markers(text: str) -> list[Marker]:
    markers: list[Marker] = []
    for marker_type, pattern in MARKER_PATTERNS:
        for match in pattern.finditer(text):
            markers.append(
                Marker(
                    marker_type=marker_type,
                    start=match.start(1) if marker_type == "editor" else match.start(),
                    end=match.end(),
                    text=match.group(1) if marker_type == "editor" else match.group(0),
                )
            )
    return sorted(markers, key=lambda marker: (marker.start, marker.end, marker.marker_type))
