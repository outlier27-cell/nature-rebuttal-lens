"""Deterministic evidence-boundary checks for final RebuttalLens reports."""

from __future__ import annotations

from collections import Counter
from typing import Any


def verify_final_report_evidence(
    report: dict[str, Any],
    *,
    manuscript_context: dict[str, Any],
    retrieved_cases: list[dict[str, Any]],
) -> dict[str, Any]:
    """Check ledger spans and case analogies for obvious unsupported claims."""
    sections = _sections_by_id(manuscript_context)
    cases = _cases_by_id(retrieved_cases)
    issues = []
    for entry in _dicts(report.get("evidence_ledger")):
        ledger_id = str(entry.get("ledger_id") or "unknown")
        span = entry.get("manuscript_span") if isinstance(entry.get("manuscript_span"), dict) else {}
        section_id = str(span.get("section_id") or "")
        quote = str(span.get("quote") or "").strip()
        section_text = sections.get(section_id, "")
        support_status = str(entry.get("support_status") or "uncertain")
        if support_status == "supported" and (not quote or quote not in section_text):
            issues.append({
                "ledger_id": ledger_id,
                "issue": "missing_manuscript_quote",
                "severity": "high",
                "detail": f"quote is not found in manuscript section {section_id}",
            })
        for case_id in _strings(entry.get("case_ids")):
            case = cases.get(case_id, {})
            boundary_text = " ".join(
                str(case.get(key) or "")
                for key in ("boundary", "case_use_boundary", "limits", "limitation")
            ).strip()
            if not boundary_text:
                issues.append({
                    "ledger_id": ledger_id,
                    "case_id": case_id,
                    "issue": "missing_case_boundary",
                    "severity": "medium",
                    "detail": "case analogy lacks a boundary statement",
                })
    counts = Counter(issue["issue"] for issue in issues)
    return {
        "status": "passed" if not issues else "needs_attention",
        "issue_counts": dict(sorted(counts.items())),
        "issues": issues,
        "checked_ledger_count": len(_dicts(report.get("evidence_ledger"))),
    }


def _sections_by_id(manuscript_context: dict[str, Any]) -> dict[str, str]:
    sections = manuscript_context.get("sections", [])
    return {
        str(section.get("section_id")): str(section.get("text") or "")
        for section in sections
        if isinstance(section, dict) and section.get("section_id")
    } if isinstance(sections, list) else {}


def _cases_by_id(retrieved_cases: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
    cases = {}
    for case in retrieved_cases:
        if not isinstance(case, dict):
            continue
        for key in ("unit_id", "case_id", "id", "pair_id"):
            value = case.get(key)
            if value:
                cases[str(value)] = case
    return cases


def _dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        value = [value]
    return [str(item).strip() for item in value if str(item).strip()]
