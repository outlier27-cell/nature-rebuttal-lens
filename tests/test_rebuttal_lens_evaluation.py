import csv
import json
from pathlib import Path

from peer_review_skills.cli.main import build_parser, main


def _sample_trace() -> dict:
    return {
        "workflow_version": "rebuttal_lens_v1",
        "query_unit_id": "case_replay",
        "agent_intermediate_outputs": {
            "reviewer_understanding_agent": {
                "concern_map": [
                    {
                        "concern_id": "concern_001",
                        "concern_type": "methodological_transparency",
                        "surface_request": "clarify dataset split",
                        "text_evidence": "split unclear",
                        "confidence": "high",
                    }
                ]
            },
            "manuscript_evidence_locator": {
                "manuscript_evidence_map": [
                    {
                        "concern_id": "concern_001",
                        "status": "partially_supported",
                        "section_id": "section_002",
                        "text_evidence": "80/10/10 split",
                        "gap": "random seed missing",
                    }
                ]
            },
            "evidence_action_planner": {
                "evidence_action_plan": [
                    {
                        "concern_id": "concern_001",
                        "action_type": "clarify_existing_method",
                        "required_artifact": "random seed and stratification protocol",
                        "supporting_case_ids": ["case_001"],
                        "requires_author_confirmation": True,
                    }
                ]
            },
            "integrity_adequacy_checker": {
                "provenance_checks": [],
                "responsible_use_warnings": ["assistant_only"],
                "issues": [],
            },
        },
        "manuscript_context": {
            "sections": [
                {
                    "section_id": "section_002",
                    "heading": "Methods",
                    "text": "We used an 80/10/10 split.",
                }
            ]
        },
        "responsible_use_boundary": {
            "assistant_only": True,
            "not_final_rebuttal_text": True,
            "author_must_verify_all_claims": True,
        },
    }


def test_openreview_adapter_builds_non_training_rebuttal_benchmark_tasks():
    from peer_review_skills.evaluation.rebuttal_lens_benchmark import (
        adapt_openreview_discussions,
    )

    discussions = [
        {
            "forum": "paper_001",
            "reviews": [
                {
                    "id": "review_1",
                    "content": {
                        "summary": "Good paper",
                        "weaknesses": "The split protocol is unclear.",
                    },
                }
            ],
            "rebuttals": [
                {
                    "replyto": "review_1",
                    "content": {"comment": "We added split details."},
                }
            ],
            "decision": {"recommendation": "Accept"},
        }
    ]

    tasks = adapt_openreview_discussions(discussions)

    assert tasks[0]["source"] == "openreview"
    assert tasks[0]["label_status"] == "evaluation_only_non_training"
    assert tasks[0]["reviewer_concerns"][0]["concern_id"] == "paper_001:review_1:001"
    assert tasks[0]["rebuttal_turns"][0]["replyto"] == "review_1"
    assert "acceptance_prediction" not in json.dumps(tasks, ensure_ascii=False).lower()
    assert "accept" not in json.dumps(tasks[0]["outcome_metadata"], ensure_ascii=False).lower()
    assert "response_adequacy_without_decision_prediction" in tasks[0]["task_contracts"]


def test_build_benchmark_writes_summary_and_error_buckets(tmp_path):
    from peer_review_skills.evaluation.rebuttal_lens_benchmark import (
        build_rebuttal_lens_benchmark,
    )

    source = tmp_path / "openreview.json"
    source.write_text(
        json.dumps(
            [
                {
                    "forum": "paper_001",
                    "reviews": [{"id": "r1", "content": {"review": "Need evidence."}}],
                    "rebuttals": [],
                },
                {"forum": "paper_002", "reviews": [], "rebuttals": []},
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    summary = build_rebuttal_lens_benchmark(source, tmp_path / "benchmark")

    assert summary["case_count"] == 2
    assert summary["task_metrics"]["concern_extraction"]["eligible_count"] == 1
    assert summary["error_buckets"]["missing_review_text"] == 1
    assert (tmp_path / "benchmark" / "benchmark_tasks.jsonl").exists()
    assert (tmp_path / "benchmark" / "summary.json").exists()


def test_human_eval_summary_computes_dimension_means_and_pairwise_preference(tmp_path):
    from peer_review_skills.evaluation.human_calibration import summarize_human_eval_sheet

    sheet = tmp_path / "human_eval.csv"
    with sheet.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "item_id",
                "annotator_id",
                "system_id",
                "evidence_groundedness",
                "responsible_use_compliance",
                "preferred_system_id",
            ],
        )
        writer.writeheader()
        writer.writerow({
            "item_id": "case_1",
            "annotator_id": "a1",
            "system_id": "layered",
            "evidence_groundedness": "5",
            "responsible_use_compliance": "4",
            "preferred_system_id": "layered",
        })
        writer.writerow({
            "item_id": "case_1",
            "annotator_id": "a2",
            "system_id": "generic",
            "evidence_groundedness": "2",
            "responsible_use_compliance": "3",
            "preferred_system_id": "layered",
        })

    summary = summarize_human_eval_sheet(sheet)

    assert summary["row_count"] == 2
    assert summary["dimension_means"]["evidence_groundedness"] == 3.5
    assert summary["preferred_system_counts"]["layered"] == 2
    assert summary["inter_annotator"]["shared_item_count"] == 1


def test_judge_calibration_reports_human_agreement_and_traceable_reasons():
    from peer_review_skills.evaluation.judge_calibration import calibrate_rebuttal_lens_judge

    summary = calibrate_rebuttal_lens_judge(
        human_rows=[
            {"item_id": "case_1", "dimension": "evidence_groundedness", "score": 4},
            {"item_id": "case_2", "dimension": "evidence_groundedness", "score": 2},
        ],
        judge_rows=[
            {
                "item_id": "case_1",
                "dimension": "evidence_groundedness",
                "score": 4,
                "reason": "ledger: ledger_001 supports the span",
                "ledger_id": "ledger_001",
                "trace_id": "trace_1",
            },
            {
                "item_id": "case_2",
                "dimension": "evidence_groundedness",
                "score": 5,
                "reason": "untraceable praise",
            },
        ],
        threshold=0.75,
    )

    assert summary["matched_count"] == 2
    assert summary["agreement_rate"] == 0.5
    assert summary["status"] == "diagnostic_only"
    assert summary["untraceable_reason_count"] == 1


def test_evidence_verifier_flags_missing_span_and_unbounded_case_analogy():
    from peer_review_skills.agents.evidence_verifier import verify_final_report_evidence

    report = {
        "evidence_ledger": [
            {
                "ledger_id": "ledger_001",
                "concern_id": "concern_001",
                "support_status": "supported",
                "manuscript_span": {
                    "section_id": "section_002",
                    "quote": "missing exact quote",
                },
                "case_ids": ["case_001"],
                "required_author_action": "clarify split",
                "author_confirmation_required": False,
            }
        ],
        "comment_cards": [{"comment_id": "comment_001", "ledger_id": "ledger_001"}],
    }
    manuscript_context = {
        "sections": [{"section_id": "section_002", "text": "We used an 80/10/10 split."}]
    }
    retrieved_cases = [{"unit_id": "case_001", "analogy": "similar methods issue"}]

    verification = verify_final_report_evidence(
        report,
        manuscript_context=manuscript_context,
        retrieved_cases=retrieved_cases,
    )

    assert verification["status"] == "needs_attention"
    assert "missing_manuscript_quote" in verification["issue_counts"]
    assert "missing_case_boundary" in verification["issue_counts"]


def test_replay_trace_rebuilds_schema_stable_final_report(tmp_path):
    from peer_review_skills.agents.rebuttal_lens_replay import replay_rebuttal_lens_trace

    trace_file = tmp_path / "rebuttal_lens_trace.json"
    trace_file.write_text(json.dumps(_sample_trace(), ensure_ascii=False), encoding="utf-8")

    summary = replay_rebuttal_lens_trace(trace_file, tmp_path / "replay")

    assert summary["replay_mode"] == "trace_only_no_model_calls"
    assert summary["schema_stable"] is True
    assert (tmp_path / "replay" / "final_user_report.json").exists()
    assert (tmp_path / "replay" / "final_user_report.md").exists()


def test_rebuttal_lens_evaluation_cli_subcommands_parse():
    parser = build_parser()

    replay = parser.parse_args([
        "replay-rebuttal-lens-trace",
        "--trace-file",
        "trace.json",
        "--output-dir",
        "out",
    ])
    benchmark = parser.parse_args([
        "build-rebuttal-lens-benchmark",
        "--input-file",
        "openreview.json",
        "--output-dir",
        "out",
    ])
    judge = parser.parse_args([
        "calibrate-rebuttal-lens-judge",
        "--human-file",
        "human.csv",
        "--judge-file",
        "judge.jsonl",
        "--output-dir",
        "out",
    ])

    assert replay.command == "replay-rebuttal-lens-trace"
    assert benchmark.command == "build-rebuttal-lens-benchmark"
    assert judge.command == "calibrate-rebuttal-lens-judge"


def test_replay_trace_cli_writes_report(tmp_path):
    trace_file = tmp_path / "trace.json"
    trace_file.write_text(json.dumps(_sample_trace(), ensure_ascii=False), encoding="utf-8")
    output_dir = tmp_path / "replay_cli"

    result = main([
        "replay-rebuttal-lens-trace",
        "--trace-file",
        str(trace_file),
        "--output-dir",
        str(output_dir),
    ])

    assert result == 0
    assert (output_dir / "final_user_report.json").exists()


def test_author_workspace_html_renders_action_statuses(tmp_path):
    from peer_review_skills.agents.author_workspace import write_author_workspace_html

    report = {
        "executive_summary": "One concern needs evidence.",
        "comment_cards": [
            {
                "comment_id": "comment_001",
                "concern_type": "methodological_transparency",
                "surface_request": "clarify split",
                "evidence_status": "partially_supported",
                "evidence_gap": "random seed missing",
                "recommended_action": "add split protocol",
                "author_input_required": True,
                "safe_response_language": "We will clarify.",
                "unsafe_language_to_avoid": "Do not claim resolved yet.",
                "ledger_id": "ledger_001",
            },
            {
                "comment_id": "comment_002",
                "concern_type": "claim_scope",
                "surface_request": "avoid overclaim",
                "evidence_status": "missing",
                "evidence_gap": "no external validation",
                "recommended_action": "narrow claim",
                "author_input_required": True,
                "safe_response_language": "We will narrow.",
                "unsafe_language_to_avoid": "Do not promise validation.",
                "ledger_id": "ledger_002",
            },
        ],
        "responsible_use_warnings": ["not_final_rebuttal_text"],
    }

    path = write_author_workspace_html(report, tmp_path)
    html = path.read_text(encoding="utf-8")

    assert path.name == "author_workspace.html"
    assert "needs author confirmation" in html
    assert "needs evidence" in html
    assert "not final submission text" in html
    assert "<script" not in html.lower()


def test_workflow_writes_author_workspace_html(tmp_path):
    from tests.test_rebuttal_lens_workflow import RebuttalLensMockLLMClient
    from peer_review_skills.agents.rebuttal_lens_workflow import run_rebuttal_lens_workflow

    manuscript = tmp_path / "manuscript.md"
    manuscript.write_text("## Methods\n\nWe used an 80/10/10 split.\n", encoding="utf-8")
    output_dir = tmp_path / "workspace_output"

    summary = run_rebuttal_lens_workflow(
        project_root=Path.cwd(),
        review_text="The dataset split is unclear.",
        manuscript_path=manuscript,
        model_client=RebuttalLensMockLLMClient(),
        retrieved_cases=[{"unit_id": "case_001", "score": 0.8}],
        taxonomies={},
        config={"output_dir": output_dir},
    )

    assert summary["author_workspace_html"].endswith("author_workspace.html")
    assert (output_dir / "author_workspace.html").exists()


def test_release_hardening_files_exist_and_reference_verification_commands():
    ci = Path.cwd() / ".github" / "workflows" / "ci.yml"
    py_typed = Path.cwd() / "src" / "peer_review_skills" / "py.typed"
    paper_outline = Path.cwd() / "docs" / "paper_outline.md"

    assert ci.exists()
    ci_text = ci.read_text(encoding="utf-8")
    for marker in [
        "python-version: ['3.10', '3.11', '3.12']",
        "python -m pip install pytest",
        "python -m pytest -q",
        "python -m compileall -q src tests",
        "validate-naturereview-v01",
        "python -m pip install --dry-run -e .",
    ]:
        assert marker in ci_text
    assert py_typed.exists()
    pyproject = (Path.cwd() / "pyproject.toml").read_text(encoding="utf-8")
    assert "peer_review_skills = [\"py.typed\"]" in pyproject
    assert paper_outline.exists()
    outline = paper_outline.read_text(encoding="utf-8")
    assert "evidence ledger" in outline.lower()
    assert "privacy gate" in outline.lower()
    assert "human-calibrated benchmark" in outline.lower()
