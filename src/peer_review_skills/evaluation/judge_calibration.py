"""Calibration utilities for RebuttalLens automatic judges."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from peer_review_skills.io.jsonl import read_jsonl


def calibrate_rebuttal_lens_judge(
    *,
    human_rows: list[dict[str, Any]],
    judge_rows: list[dict[str, Any]],
    threshold: float = 0.75,
) -> dict[str, Any]:
    """Compare judge scores to human scores and classify judge readiness."""
    human_by_key = {
        _key(row): _score(row)
        for row in human_rows
        if _key(row) and _score(row) is not None
    }
    judge_by_key = {
        _key(row): row
        for row in judge_rows
        if _key(row)
    }
    matched = []
    for key, human_score in human_by_key.items():
        judge = judge_by_key.get(key)
        judge_score = _score(judge) if judge else None
        if judge_score is None:
            continue
        matched.append((human_score, judge_score, judge))
    agreement_count = sum(1 for human_score, judge_score, _ in matched if human_score == judge_score)
    matched_count = len(matched)
    agreement_rate = agreement_count / matched_count if matched_count else 0.0
    untraceable_reason_count = sum(
        1
        for _, _, judge in matched
        if not (judge.get("ledger_id") or judge.get("trace_id") or "ledger:" in str(judge.get("reason", "")))
    )
    return {
        "matched_count": matched_count,
        "agreement_count": agreement_count,
        "agreement_rate": round(agreement_rate, 4),
        "threshold": threshold,
        "status": "calibrated_for_assistive_use" if agreement_rate >= threshold and untraceable_reason_count == 0 else "diagnostic_only",
        "untraceable_reason_count": untraceable_reason_count,
        "notes": [
            "Judge outputs must cite trace or ledger provenance.",
            "Diagnostic-only judges can triage but should not support benchmark claims.",
        ],
    }


def calibrate_rebuttal_lens_judge_files(
    human_file: str | Path,
    judge_file: str | Path,
    output_dir: str | Path,
    *,
    threshold: float = 0.75,
) -> dict[str, Any]:
    """Load human and judge files, write calibration summary."""
    human_rows = _read_records(human_file)
    judge_rows = _read_records(judge_file)
    summary = calibrate_rebuttal_lens_judge(
        human_rows=human_rows,
        judge_rows=judge_rows,
        threshold=threshold,
    )
    target = Path(output_dir)
    target.mkdir(parents=True, exist_ok=True)
    path = target / "judge_calibration_summary.json"
    path.write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    summary["summary_path"] = str(path)
    return summary


def _read_records(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    if source.suffix.lower() == ".csv":
        with source.open("r", encoding="utf-8-sig", newline="") as handle:
            return [dict(row) for row in csv.DictReader(handle)]
    if source.suffix.lower() == ".jsonl":
        return list(read_jsonl(source))
    value = json.loads(source.read_text(encoding="utf-8"))
    if isinstance(value, list):
        return [row for row in value if isinstance(row, dict)]
    raise ValueError("calibration files must be CSV, JSONL, or JSON arrays")


def _key(row: dict[str, Any] | None) -> tuple[str, str] | None:
    if not row:
        return None
    item_id = str(row.get("item_id") or row.get("case_id") or row.get("unit_id") or "").strip()
    dimension = str(row.get("dimension") or row.get("metric") or "").strip()
    if not item_id or not dimension:
        return None
    return item_id, dimension


def _score(row: dict[str, Any] | None) -> int | None:
    if not row:
        return None
    try:
        return int(float(str(row.get("score")).strip()))
    except (TypeError, ValueError):
        return None
