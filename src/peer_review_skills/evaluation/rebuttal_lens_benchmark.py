"""Offline RebuttalLens benchmark adapters and summaries."""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

from peer_review_skills.io.jsonl import write_jsonl


TASK_CONTRACTS = [
    "concern_extraction",
    "evidence_action_planning",
    "rebuttal_turn_state_tracking",
    "response_adequacy_without_decision_prediction",
    "unsafe_claim_detection",
]


def adapt_openreview_discussions(discussions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert OpenReview/Re^2-style discussions into evaluation-only tasks."""
    tasks = []
    for index, discussion in enumerate(discussions, start=1):
        forum_id = _text(discussion.get("forum") or discussion.get("id") or f"paper_{index:03d}")
        reviews = _list_of_dicts(discussion.get("reviews"))
        rebuttals = _list_of_dicts(discussion.get("rebuttals") or discussion.get("responses"))
        concerns = []
        for review_index, review in enumerate(reviews, start=1):
            review_id = _text(review.get("id") or review.get("note_id") or f"review_{review_index}")
            review_text = _review_text(review)
            if not review_text:
                continue
            concerns.append({
                "concern_id": f"{forum_id}:{review_id}:{review_index:03d}",
                "review_id": review_id,
                "review_text": review_text,
                "source_field": "review",
                "requires_author_action": True,
            })
        tasks.append({
            "task_id": f"openreview_{index:04d}_{_safe_id(forum_id)}",
            "source": "openreview",
            "forum_id": forum_id,
            "label_status": "evaluation_only_non_training",
            "reviewer_concerns": concerns,
            "rebuttal_turns": [_rebuttal_turn(turn) for turn in rebuttals],
            "outcome_metadata": _outcome_metadata(discussion),
            "task_contracts": list(TASK_CONTRACTS),
            "notes": [
                "Imported for evaluation only.",
                "Do not train or fine-tune on this task by default.",
                "Do not predict acceptance; evaluate response adequacy and evidence boundaries.",
            ],
        })
    return tasks


def build_rebuttal_lens_benchmark(
    input_file: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Build a small benchmark artifact from a JSON list of discussions."""
    source = Path(input_file)
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    discussions = json.loads(source.read_text(encoding="utf-8"))
    if not isinstance(discussions, list):
        raise ValueError("benchmark input must be a JSON array")
    tasks = adapt_openreview_discussions([d for d in discussions if isinstance(d, dict)])
    write_jsonl(target / "benchmark_tasks.jsonl", tasks)
    error_buckets = Counter()
    eligible_concern_count = 0
    for task in tasks:
        if task["reviewer_concerns"]:
            eligible_concern_count += 1
        else:
            error_buckets["missing_review_text"] += 1
        if not task["rebuttal_turns"]:
            error_buckets["missing_rebuttal_turns"] += 1
    summary = {
        "benchmark_id": "rebuttal_lens_openreview_v1",
        "source_file": str(source),
        "case_count": len(tasks),
        "task_metrics": {
            "concern_extraction": {"eligible_count": eligible_concern_count},
            "evidence_action_planning": {"eligible_count": eligible_concern_count},
            "rebuttal_turn_state_tracking": {
                "eligible_count": sum(1 for task in tasks if task["rebuttal_turns"])
            },
            "response_adequacy_without_decision_prediction": {
                "eligible_count": len(tasks)
            },
            "unsafe_claim_detection": {"eligible_count": len(tasks)},
        },
        "error_buckets": dict(sorted(error_buckets.items())),
        "label_status": "evaluation_only_non_training",
        "files": {
            "tasks": str(target / "benchmark_tasks.jsonl"),
            "summary": str(target / "summary.json"),
        },
    }
    (target / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return summary


def _review_text(review: dict[str, Any]) -> str:
    content = review.get("content")
    if isinstance(content, dict):
        parts = []
        for key in ("weaknesses", "questions", "review", "comment", "summary"):
            value = _text(content.get(key))
            if value:
                parts.append(value)
        return "\n".join(parts).strip()
    return _text(review.get("text") or review.get("review") or review.get("comment"))


def _rebuttal_turn(turn: dict[str, Any]) -> dict[str, Any]:
    content = turn.get("content")
    if isinstance(content, dict):
        text = "\n".join(_text(value) for value in content.values() if _text(value)).strip()
    else:
        text = _text(turn.get("text") or turn.get("comment"))
    return {
        "turn_id": _text(turn.get("id") or turn.get("note_id") or "unknown"),
        "replyto": _text(turn.get("replyto") or turn.get("parent") or ""),
        "text": text,
    }


def _outcome_metadata(discussion: dict[str, Any]) -> dict[str, Any]:
    decision = discussion.get("decision")
    if isinstance(decision, dict):
        return {
            key: value
            for key, value in decision.items()
            if not _looks_like_acceptance_decision(key, value)
        }
    return {}


def _list_of_dicts(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _text(value: Any) -> str:
    return str(value or "").strip()


def _looks_like_acceptance_decision(key: Any, value: Any) -> bool:
    text = f"{key} {value}".lower()
    decision_markers = (
        "accept",
        "reject",
        "accepted",
        "rejected",
        "withdraw",
        "desk reject",
        "decision",
        "recommendation",
    )
    return any(marker in text for marker in decision_markers)


def _safe_id(value: str) -> str:
    safe = "".join(char if char.isalnum() else "-" for char in value)
    return "-".join(part for part in safe.split("-") if part)[:80] or "unknown"
