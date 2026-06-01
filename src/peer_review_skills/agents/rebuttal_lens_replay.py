"""Trace-only replay for Nature RebuttalLens final reports."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from peer_review_skills.agents.evidence_ledger import canonical_report_json
from peer_review_skills.agents.final_report import (
    compose_final_user_report,
    validate_final_user_report,
    write_final_user_report,
)


def replay_rebuttal_lens_trace(
    trace_file: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    """Rebuild final reports from a stored trace without model calls."""
    trace_path = Path(trace_file)
    target = Path(output_dir)
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    if not isinstance(trace, dict):
        raise ValueError("trace file must contain a JSON object")
    report = compose_final_user_report(trace)
    is_valid, errors = validate_final_user_report(report)
    if not is_valid:
        raise ValueError("replayed final report contract failed: " + "; ".join(errors))
    before = canonical_report_json(report)
    paths = write_final_user_report(report, target)
    written = json.loads(Path(paths["final_user_report_json"]).read_text(encoding="utf-8"))
    after = canonical_report_json(written)
    summary = {
        "replay_mode": "trace_only_no_model_calls",
        "trace_file": str(trace_path),
        "schema_stable": before == after,
        "final_user_report_json": paths["final_user_report_json"],
        "final_user_report_markdown": paths["final_user_report_markdown"],
        "workflow_version": trace.get("workflow_version", "rebuttal_lens_v1"),
    }
    (target / "replay_summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return summary
