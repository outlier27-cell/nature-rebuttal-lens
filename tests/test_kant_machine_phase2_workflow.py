import json
from pathlib import Path

from peer_review_skills.agents.final_report import (
    compose_final_user_report,
    render_final_user_report_markdown,
)
from peer_review_skills.agents.kant_machine_runtime import build_kant_machine_runtime
from peer_review_skills.agents.rebuttal_lens_workflow import run_rebuttal_lens_workflow
from peer_review_skills.cli.main import build_parser

try:
    from tests.test_rebuttal_lens_workflow import RebuttalLensMockLLMClient
except ModuleNotFoundError:
    from test_rebuttal_lens_workflow import RebuttalLensMockLLMClient


def test_kant_phase2_runtime_contains_self_legislation_and_unknowability(tmp_path):
    trace = {
        "workflow_engine": "dag",
        "agent_intermediate_outputs": {
            "reviewer_understanding_agent": {
                "concern_map": [
                    {
                        "surface_request": (
                            "The reviewer probably wants stronger temporal evidence."
                        )
                    }
                ]
            },
            "evidence_action_planner": {
                "evidence_action_plan": [
                    {
                        "required_artifact": "temporal holdout validation",
                        "requires_author_confirmation": True,
                    }
                ]
            },
        },
    }

    runtime = build_kant_machine_runtime(
        trace=trace,
        config={
            "output_dir": tmp_path,
            "enable_kant_phase2": True,
            "enable_reflective_judgment": True,
        },
    )

    assert runtime["enabled"] is True
    assert runtime["phase"] == "kant_machine_phase2"
    assert runtime["self_legislation"]["enabled"] is True
    assert runtime["unknowability_ledger"]["enabled"] is True
    assert runtime["blackbox_transparency"]["enabled"] is True
    assert runtime["organic_quality"]["enabled"] is True
    assert runtime["cognition_loop"]["mechanical_layer"]
    assert runtime["cognition_loop"]["empirical_layer"]
    assert runtime["cognition_loop"]["category_layer"]


def test_kant_phase2_runtime_can_enable_individual_modules(tmp_path):
    runtime = build_kant_machine_runtime(
        trace={"agent_intermediate_outputs": {}},
        config={
            "output_dir": tmp_path,
            "enable_blackbox_transparency": True,
            "enable_organic_quality": True,
            "enable_ethics_audit_chain": False,
        },
    )

    assert runtime["enabled"] is True
    assert runtime["phase"] == "kant_machine_phase1"
    assert runtime["blackbox_transparency"]["enabled"] is True
    assert runtime["organic_quality"]["enabled"] is True


def test_final_report_surfaces_kant_phase2_sections():
    trace = {
        "query_unit_id": "case_phase2",
        "workflow_version": "rebuttal_lens_v1",
        "kant_machine_runtime": {
            "enabled": True,
            "phase": "kant_machine_phase2",
            "ethics_audit_chain_enabled": True,
            "self_legislation": {
                "enabled": True,
                "maxims": [
                    {
                        "maxim_id": "author_decision_boundary",
                        "maxim_zh": "系统不能替作者承诺实验。",
                    }
                ],
                "system_may_commit_for_author": False,
                "author_confirmation_required_for": ["temporal validation"],
            },
            "unknowability_ledger": {
                "enabled": True,
                "boundaries": [
                    {
                        "boundary_type": "future_editorial_outcome",
                        "status": "standing_boundary",
                    }
                ],
                "blocked_inferences": [],
                "author_questions": ["系统不能预测接收结果。"],
            },
            "cognition_loop": {
                "mechanical_layer": ["dag_or_layered_workflow"],
                "empirical_layer": ["manuscript_evidence_locator"],
                "category_layer": ["computational_self_legislation"],
            },
            "reflective_judgment": {},
        },
        "agent_intermediate_outputs": {
            "reviewer_understanding_agent": {
                "concern_map": [
                    {
                        "concern_id": "concern_001",
                        "concern_type": "experimental_design",
                        "surface_request": "Add temporal validation.",
                        "text_evidence": "temporal leakage risk",
                        "confidence": "high",
                    }
                ]
            },
            "manuscript_evidence_locator": {
                "manuscript_evidence_map": [
                    {
                        "concern_id": "concern_001",
                        "status": "partially_supported",
                        "section_id": "section_004",
                        "gap": "temporal validation missing",
                    }
                ]
            },
            "evidence_action_planner": {
                "evidence_action_plan": [
                    {
                        "concern_id": "concern_001",
                        "action_type": "new_analysis",
                        "required_artifact": "temporal validation",
                        "requires_author_confirmation": True,
                    }
                ]
            },
        },
    }

    report = compose_final_user_report(trace)
    markdown = render_final_user_report_markdown(report)

    assert report["self_legislation"]["enabled"] is True
    assert report["unknowability_ledger"]["enabled"] is True
    assert report["blackbox_transparency"]["enabled"] is True
    assert report["organic_quality"]["enabled"] is True
    assert "计算域自我立法" in markdown
    assert "不可知边界" in markdown
    assert "黑箱透明化摘要" in markdown
    assert "有机性评估" in markdown
    assert "机械-经验-范畴三层认知循环" in markdown
    assert "\\u" not in json.dumps(report, ensure_ascii=False)


def test_cli_accepts_kant_phase2_flags():
    parser = build_parser()
    args = parser.parse_args([
        "run-rebuttal-lens",
        "--review-file",
        "examples/rebuttal_lens/reviewer_comment.txt",
        "--enable-kant-phase2",
        "--enable-self-legislation",
        "--enable-unknowability-ledger",
        "--enable-blackbox-transparency",
        "--enable-organic-quality",
    ])

    assert args.enable_kant_phase2 is True
    assert args.enable_self_legislation is True
    assert args.enable_unknowability_ledger is True
    assert args.enable_blackbox_transparency is True
    assert args.enable_organic_quality is True


def test_kant_phase2_mock_workflow_outputs_json_and_markdown(tmp_path):
    manuscript = tmp_path / "manuscript.md"
    manuscript.write_text(
        (
            "## Methods\n\nWe used a random paper-level split.\n\n"
            "## Limitations\n\nTemporal validation is planned."
        ),
        encoding="utf-8",
    )
    output_dir = tmp_path / "phase2_output"

    run_rebuttal_lens_workflow(
        project_root=Path.cwd(),
        review_text=(
            "Please add temporal validation. Without it, the generalization claim may be overstated."
        ),
        manuscript_path=manuscript,
        retrieved_cases=[{"unit_id": "case_001", "score": 0.8}],
        taxonomies={},
        model_client=RebuttalLensMockLLMClient(),
        config={
            "output_dir": output_dir,
            "workflow_engine": "dag",
            "enable_committee": True,
            "enable_strategy_tournament": True,
            "enable_kant_phase2": True,
            "enable_reflective_judgment": True,
            "enable_universalization_gate": True,
        },
    )

    trace = json.loads((output_dir / "rebuttal_lens_trace.json").read_text(encoding="utf-8"))
    report = json.loads((output_dir / "final_user_report.json").read_text(encoding="utf-8"))
    markdown = (output_dir / "final_user_report.md").read_text(encoding="utf-8")

    assert trace["kant_machine_runtime"]["phase"] == "kant_machine_phase2"
    assert report["self_legislation"]["enabled"] is True
    assert report["unknowability_ledger"]["enabled"] is True
    assert report["blackbox_transparency"]["enabled"] is True
    assert report["organic_quality"]["enabled"] is True
    assert report["not_final_submission_text"] is True
    assert "计算域自我立法" in markdown
    assert "不可知边界" in markdown
