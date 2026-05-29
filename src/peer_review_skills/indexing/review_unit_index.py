from pathlib import Path
from typing import Any

from peer_review_skills.io.jsonl import read_jsonl


STOPWORDS = {
    "about",
    "after",
    "again",
    "also",
    "and",
    "are",
    "author",
    "authors",
    "because",
    "been",
    "can",
    "could",
    "does",
    "for",
    "from",
    "have",
    "into",
    "manuscript",
    "more",
    "paper",
    "please",
    "response",
    "reviewer",
    "should",
    "study",
    "that",
    "the",
    "their",
    "there",
    "this",
    "was",
    "were",
    "with",
    "would",
}


def build_review_unit_index(units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [_index_row(unit) for unit in units]


def load_review_unit_index(path: str | Path) -> dict[str, dict[str, Any]]:
    return {str(record["unit_id"]): record for record in read_jsonl(path)}


def unit_index_from_id(unit_id: str) -> int:
    marker = ":u"
    if marker not in unit_id:
        return 0
    suffix = unit_id.rsplit(marker, 1)[1]
    digits = []
    for char in suffix:
        if char.isdigit():
            digits.append(char)
        else:
            break
    return int("".join(digits) or "0")


def reviewer_index_from_id(unit_id: str) -> int:
    marker = ":r"
    if marker not in unit_id:
        return -1
    suffix = unit_id.split(marker, 1)[1]
    digits = []
    for char in suffix:
        if char.isdigit():
            digits.append(char)
        else:
            break
    return int("".join(digits) or "-1")


def keywords_for_text(text: str, limit: int = 40) -> list[str]:
    tokens = []
    current = []
    for char in text.lower():
        if char.isalnum() or char == "-":
            current.append(char)
        elif current:
            tokens.append("".join(current))
            current = []
    if current:
        tokens.append("".join(current))
    keywords = []
    seen = set()
    for token in tokens:
        if len(token) < 5 or token in STOPWORDS or token in seen:
            continue
        seen.add(token)
        keywords.append(token)
        if len(keywords) >= limit:
            break
    return keywords


def _index_row(unit: dict[str, Any]) -> dict[str, Any]:
    text = str(unit.get("text") or "")
    unit_id = str(unit.get("unit_id") or "")
    compact_preview = " ".join(text.split())[:320]
    return {
        "unit_id": unit_id,
        "paper_id": str(unit.get("paper_id") or ""),
        "speaker_type": str(unit.get("speaker_type") or "unknown"),
        "speaker_id": str(unit.get("speaker_id") or "unknown"),
        "round_id": str(unit.get("round_id") or "round_unknown"),
        "source_report_index": int(unit.get("source_report_index", -1)),
        "source_report_reviewer": str(unit.get("source_report_reviewer") or ""),
        "unit_index": unit_index_from_id(unit_id),
        "reviewer_report_index": reviewer_index_from_id(unit_id),
        "char_start": int(unit.get("char_start", 0)),
        "char_end": int(unit.get("char_end", 0)),
        "marker_text": str(unit.get("marker_text") or ""),
        "segmentation_confidence": float(unit.get("segmentation_confidence", 0.0)),
        "text_preview": compact_preview,
        "text_keywords": keywords_for_text(text),
        "source_trace": dict(unit.get("source_trace") or {}),
    }
