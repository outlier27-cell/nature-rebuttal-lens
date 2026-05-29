from dataclasses import dataclass

from peer_review_skills.segment.marker_patterns import Marker, find_markers


@dataclass(frozen=True)
class Segment:
    speaker_type: str
    speaker_id: str
    section_label: str
    text: str
    char_start: int
    char_end: int
    marker_text: str
    segmentation_method: str
    segmentation_confidence: float
    round_id: str


def _speaker_id(marker: Marker | None, fallback_label: str) -> str:
    text = (marker.text if marker else fallback_label).lower()
    digits = "".join(ch for ch in text if ch.isdigit())
    if digits:
        if marker and marker.marker_type == "reviewer":
            return f"reviewer_{digits}"
        return f"speaker_{digits}"
    if marker:
        return marker.marker_type
    return "unknown"


def _marker_to_speaker(marker: Marker) -> str:
    if marker.marker_type in {"reviewer", "author", "editor"}:
        return marker.marker_type
    return "unknown"


def segment_report_text(
    text: str,
    source_report_reviewer: str = "",
    prefix_speaker_hint: str | None = None,
) -> list[Segment]:
    markers = [marker for marker in find_markers(text) if marker.marker_type != "page"]
    raw_speaker_markers = [
        marker for marker in markers if marker.marker_type in {"reviewer", "author", "editor"}
    ]
    speaker_markers: list[Marker] = []
    for marker in raw_speaker_markers:
        if (
            speaker_markers
            and speaker_markers[-1].marker_type == marker.marker_type
            and marker.start - speaker_markers[-1].end <= 40
        ):
            continue
        speaker_markers.append(marker)

    if not speaker_markers:
        label = source_report_reviewer or ""
        lower_label = label.lower()
        if "reviewer" in lower_label or "referee" in lower_label:
            speaker_type = "reviewer"
            confidence = 0.72
            speaker_id = _speaker_id(None, label)
        else:
            speaker_type = "unknown"
            confidence = 0.45
            speaker_id = "unknown"
        return [
            Segment(
                speaker_type=speaker_type,
                speaker_id=speaker_id,
                section_label=label,
                text=text,
                char_start=0,
                char_end=len(text),
                marker_text=label,
                segmentation_method="report_label_fallback" if speaker_type != "unknown" else "unmarked_fallback",
                segmentation_confidence=confidence,
                round_id="round_unknown",
            )
        ]

    segments: list[Segment] = []
    first_marker = speaker_markers[0]
    if first_marker.start > 0:
        prefix_text = text[: first_marker.start]
        if prefix_text.strip():
            label = source_report_reviewer or ""
            lower_label = label.lower()
            if prefix_speaker_hint in {"author", "reviewer", "editor"}:
                prefix_speaker_type = prefix_speaker_hint
                prefix_speaker_id = prefix_speaker_hint
                prefix_confidence = 0.72
                prefix_method = f"{prefix_speaker_hint}_prefix"
            elif first_marker.marker_type != "reviewer" and (
                "reviewer" in lower_label or "referee" in lower_label
            ):
                prefix_speaker_type = "reviewer"
                prefix_speaker_id = _speaker_id(None, label)
                prefix_confidence = 0.72
                prefix_method = "report_label_prefix"
            else:
                prefix_speaker_type = "unknown"
                prefix_speaker_id = "unknown"
                prefix_confidence = 0.45
                prefix_method = "unmarked_prefix"
            segments.append(
                Segment(
                    speaker_type=prefix_speaker_type,
                    speaker_id=prefix_speaker_id,
                    section_label=label,
                    text=prefix_text,
                    char_start=0,
                    char_end=first_marker.start,
                    marker_text=label,
                    segmentation_method=prefix_method,
                    segmentation_confidence=prefix_confidence,
                    round_id="round_unknown",
                )
            )
    for index, marker in enumerate(speaker_markers):
        next_start = speaker_markers[index + 1].start if index + 1 < len(speaker_markers) else len(text)
        if next_start <= marker.start:
            continue
        segment_text = text[marker.start:next_start]
        round_id = "round_unknown"
        prior_rounds = [item for item in markers if item.marker_type == "round" and item.start <= marker.start]
        if prior_rounds:
            round_marker = prior_rounds[-1].text.lower()
            digits = "".join(ch for ch in round_marker if ch.isdigit())
            if digits:
                round_id = f"round_{digits}"
            elif "first" in round_marker:
                round_id = "round_1"
            elif "second" in round_marker:
                round_id = "round_2"
        segments.append(
            Segment(
                speaker_type=_marker_to_speaker(marker),
                speaker_id=_speaker_id(marker, source_report_reviewer),
                section_label=marker.text,
                text=segment_text,
                char_start=marker.start,
                char_end=next_start,
                marker_text=marker.text,
                segmentation_method="marker_based",
                segmentation_confidence=0.9,
                round_id=round_id,
            )
        )
    return segments
