"""Input safety checks for Nature RebuttalLens untrusted text."""

from __future__ import annotations

import re
from typing import Any


_HIGH_RISK_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "html_comment_instruction",
        re.compile(r"<!--.*?(ignore|disregard|override).{0,120}?(instruction|system|developer|editor|reviewer|accept)", re.IGNORECASE | re.DOTALL),
    ),
    (
        "role_override_instruction",
        re.compile(r"\b(ignore|disregard|override)\b.{0,120}\b(previous|above|system|developer)\b.{0,120}\b(instruction|prompt|message)s?\b", re.IGNORECASE | re.DOTALL),
    ),
    (
        "forced_editorial_outcome",
        re.compile(r"\b(tell|instruct|make|force)\b.{0,80}\b(editor|reviewer|model|assistant)\b.{0,80}\b(accept|approve)\b", re.IGNORECASE | re.DOTALL),
    ),
)


def build_input_safety_report(
    *,
    review_text: str,
    response_text: str,
    editor_text: str,
    manuscript_context: dict[str, Any],
    retrieved_cases: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    """Scan untrusted input surfaces for prompt-injection style instructions."""
    findings: list[dict[str, Any]] = []
    sources = [
        ("review", review_text),
        ("response", response_text),
        ("editor", editor_text),
        ("manuscript", _manuscript_text(manuscript_context)),
        ("retrieved_cases", _retrieved_case_text(retrieved_cases or [])),
    ]
    for source, text in sources:
        findings.extend(_scan_text(source, text))
    highest = _highest_severity(findings)
    return {
        "report_type": "rebuttal_lens_input_safety_report",
        "blocked": highest == "high",
        "highest_severity": highest,
        "findings": findings,
    }


def _scan_text(source: str, text: str) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []
    if not text:
        return findings
    for pattern_id, pattern in _HIGH_RISK_PATTERNS:
        match = pattern.search(text)
        if match:
            findings.append({
                "source": source,
                "severity": "high",
                "pattern_id": pattern_id,
                "snippet": _snippet(text, match.start(), match.end()),
                "recommended_action": "block_before_model_call",
            })
    return findings


def _manuscript_text(manuscript_context: dict[str, Any]) -> str:
    sections = manuscript_context.get("sections", [])
    if not isinstance(sections, list):
        return ""
    return "\n\n".join(
        str(section.get("text", ""))
        for section in sections
        if isinstance(section, dict)
    )


def _retrieved_case_text(retrieved_cases: list[dict[str, Any]]) -> str:
    return "\n\n".join(str(case) for case in retrieved_cases)


def _highest_severity(findings: list[dict[str, Any]]) -> str:
    if any(finding.get("severity") == "high" for finding in findings):
        return "high"
    if findings:
        return "low"
    return "none"


def _snippet(text: str, start: int, end: int) -> str:
    left = max(0, start - 40)
    right = min(len(text), end + 40)
    return re.sub(r"\s+", " ", text[left:right]).strip()
