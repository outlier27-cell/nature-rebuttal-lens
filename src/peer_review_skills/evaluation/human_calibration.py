"""Human-evaluation summary helpers for RebuttalLens."""

from __future__ import annotations

import csv
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


NON_SCORE_FIELDS = {
    "item_id",
    "unit_id",
    "case_id",
    "annotator_id",
    "system_id",
    "preferred_system_id",
    "human_notes",
}


def summarize_human_eval_sheet(path: str | Path) -> dict[str, Any]:
    """Summarize a CSV human-evaluation sheet without external dependencies."""
    rows = _read_rows(path)
    score_values: dict[str, list[float]] = defaultdict(list)
    by_system: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    preferred = Counter()
    item_annotators: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        system_id = str(row.get("system_id") or "unknown")
        preferred_id = str(row.get("preferred_system_id") or "").strip()
        if preferred_id:
            preferred[preferred_id] += 1
        item_id = str(row.get("item_id") or row.get("unit_id") or row.get("case_id") or "")
        annotator_id = str(row.get("annotator_id") or "")
        if item_id and annotator_id:
            item_annotators[item_id].add(annotator_id)
        for key, value in row.items():
            if key in NON_SCORE_FIELDS:
                continue
            score = _float_or_none(value)
            if score is None:
                continue
            score_values[key].append(score)
            by_system[system_id][key].append(score)
    return {
        "row_count": len(rows),
        "dimension_means": {
            key: round(sum(values) / len(values), 4)
            for key, values in sorted(score_values.items())
            if values
        },
        "system_dimension_means": {
            system: {
                key: round(sum(values) / len(values), 4)
                for key, values in sorted(dimensions.items())
                if values
            }
            for system, dimensions in sorted(by_system.items())
        },
        "preferred_system_counts": dict(sorted(preferred.items())),
        "inter_annotator": {
            "shared_item_count": sum(1 for annotators in item_annotators.values() if len(annotators) > 1),
            "method": "shared-item-count-lite",
            "note": "Use as a lightweight audit signal; formal agreement requires completed gold labels.",
        },
        "label_status": "human_calibration_summary_not_gold_by_itself",
    }


def _read_rows(path: str | Path) -> list[dict[str, str]]:
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def _float_or_none(value: Any) -> float | None:
    try:
        text = str(value).strip()
        if not text:
            return None
        return float(text)
    except (TypeError, ValueError):
        return None
