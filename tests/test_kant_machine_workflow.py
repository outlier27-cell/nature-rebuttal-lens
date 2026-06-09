import json
from pathlib import Path

from peer_review_skills.agents.final_report import compose_final_user_report
from peer_review_skills.agents.rebuttal_lens_workflow import run_rebuttal_lens_workflow
from peer_review_skills.cli.main import build_parser

try:
    from tests.test_rebuttal_lens_workflow import RebuttalLensMockLLMClient
except ModuleNotFoundError:
    from test_rebuttal_lens_workflow import RebuttalLensMockLLMClient


def test_cli_parser_accepts_kant_machine_flags():
    parser = build_parser()
    args = parser.parse_args([
        "run-rebuttal-lens",
        "--review-file",
        "examples/rebuttal_lens/reviewer_comment.txt",
        "--enable-kantian-categories",
        "--enable-universalization-gate",
        "--enable-reflective-judgment",
        "--category-confirmation-threshold",
        "4",
        "--category-registry-path",
        "tmp/kantian_category_registry.json",
    ])

    assert args.enable_kantian_categories is True
    assert args.enable_universalization_gate is True
    assert args.enable_reflective_judgment is True
    assert args.category_confirmation_threshold == 4
    assert str(args.category_registry_path).endswith("kantian_category_registry.json")


def test_workflow_surfaces_kant_machine_runtime(tmp_path):
    manuscript = tmp_path / "manuscript.md"
    manuscript.write_text("## Methods\n\nWe used a random paper-level split.\n", encoding="utf-8")
    output_dir = tmp_path / "kant_machine_output"

    run_rebuttal_lens_workflow(
        project_root=Path.cwd(),
        review_text="Please add temporal validation and do not overstate generalization.",
        manuscript_path=manuscript,
        retrieved_cases=[{"unit_id": "case_001", "score": 0.8}],
        taxonomies={},
        model_client=RebuttalLensMockLLMClient(),
        config={
            "output_dir": output_dir,
            "workflow_engine": "dag",
            "enable_committee": True,
            "enable_strategy_tournament": True,
            "enable_kantian_categories": True,
            "enable_universalization_gate": True,
            "enable_reflective_judgment": True,
            "category_registry_path": output_dir / "kantian_category_registry.json",
        },
    )

    trace = json.loads((output_dir / "rebuttal_lens_trace.json").read_text(encoding="utf-8"))
    report = json.loads((output_dir / "final_user_report.json").read_text(encoding="utf-8"))

    assert trace["kant_machine_runtime"]["enabled"] is True
    assert "universalization_checks" in report
    assert "ethics_audit_chain" in report
    assert report["ethics_audit_chain"]["heteronomy_transparency_statement"]
    assert report["not_final_submission_text"] is True
    assert (output_dir / "kantian_category_registry.json").exists()


def test_disable_ethics_audit_chain_keeps_other_kant_runtime_features(tmp_path):
    manuscript = tmp_path / "manuscript.md"
    manuscript.write_text("## Methods\n\nWe used a random paper-level split.\n", encoding="utf-8")
    output_dir = tmp_path / "kant_no_audit_output"

    run_rebuttal_lens_workflow(
        project_root=Path.cwd(),
        review_text="Please add temporal validation and do not overstate generalization.",
        manuscript_path=manuscript,
        retrieved_cases=[],
        taxonomies={},
        model_client=RebuttalLensMockLLMClient(),
        config={
            "output_dir": output_dir,
            "workflow_engine": "dag",
            "enable_universalization_gate": True,
            "enable_reflective_judgment": True,
            "enable_ethics_audit_chain": False,
        },
    )

    trace = json.loads((output_dir / "rebuttal_lens_trace.json").read_text(encoding="utf-8"))
    report = json.loads((output_dir / "final_user_report.json").read_text(encoding="utf-8"))

    assert trace["kant_machine_runtime"]["enabled"] is True
    assert trace["kant_machine_runtime"]["ethics_audit_chain_enabled"] is False
    assert "universalization_checks" in report
    assert report["ethics_audit_chain"] == {}


def test_default_category_registry_uses_output_dir_not_repo_root(tmp_path):
    manuscript = tmp_path / "manuscript.md"
    manuscript.write_text("## Methods\n\nWe used a random paper-level split.\n", encoding="utf-8")
    project_root = tmp_path / "project"
    project_root.mkdir()
    output_dir = project_root / "data" / "evaluation" / "rebuttal_lens_demo"

    run_rebuttal_lens_workflow(
        project_root=project_root,
        review_text="Please add temporal validation and do not overstate generalization.",
        manuscript_path=manuscript,
        retrieved_cases=[],
        taxonomies={},
        model_client=RebuttalLensMockLLMClient(),
        config={
            "workflow_engine": "dag",
            "enable_kantian_categories": True,
            "enable_reflective_judgment": True,
        },
    )

    trace = json.loads((output_dir / "rebuttal_lens_trace.json").read_text(encoding="utf-8"))

    assert (output_dir / "kantian_category_registry.json").exists()
    assert trace["kant_machine_runtime"]["category_registry_path"] == str(
        output_dir / "kantian_category_registry.json"
    )


def test_universalization_defer_updates_top_level_package_readiness():
    report = compose_final_user_report(
        {
            "query_unit_id": "case_001",
            "kant_machine_runtime": {
                "enabled": True,
                "ethics_audit_chain_enabled": True,
            },
            "agent_intermediate_outputs": {
                "reviewer_understanding_agent": {
                    "concern_map": [
                        {
                            "concern_id": "concern_001",
                            "concern_type": "experimental_design",
                            "surface_request": "Run temporal split validation.",
                            "text_evidence": "temporal split missing",
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
                            "gap": "temporal split result not supplied",
                        }
                    ]
                },
                "evidence_action_planner": {
                    "evidence_action_plan": [
                        {
                            "concern_id": "concern_001",
                            "action_type": "method_clarification",
                            "required_artifact": "author-confirmed split leakage clarification",
                            "requires_author_confirmation": True,
                        }
                    ]
                },
            },
        }
    )

    card = report["comment_cards"][0]

    assert report["universalization_checks"][0]["decision"] == "defer"
    assert card["readiness"] == "decision_deferred"
    assert report["package_readiness"] == "decision_deferred"
    assert report["ethics_audit_chain"]["deferred_author_decisions"][0]["comment_id"] == (
        card["comment_id"]
    )


def test_final_report_markdown_contains_kant_machine_sections(tmp_path):
    manuscript = tmp_path / "manuscript.md"
    manuscript.write_text("## Results\n\nThe evidence is currently from a random split.\n", encoding="utf-8")
    output_dir = tmp_path / "kant_markdown_output"

    run_rebuttal_lens_workflow(
        project_root=Path.cwd(),
        review_text="The generalization claim may be overstated without temporal validation.",
        manuscript_path=manuscript,
        retrieved_cases=[],
        taxonomies={},
        model_client=RebuttalLensMockLLMClient(),
        config={
            "output_dir": output_dir,
            "workflow_engine": "dag",
            "enable_kantian_categories": True,
            "enable_universalization_gate": True,
            "enable_reflective_judgment": True,
        },
    )

    report = json.loads((output_dir / "final_user_report.json").read_text(encoding="utf-8"))
    markdown = (output_dir / "final_user_report.md").read_text(encoding="utf-8")

    assert report["not_final_submission_text"] is True
    assert "universalization_checks" in report
    assert "ethics_audit_chain" in report
    assert "## 伦理审计链" in markdown
    assert "## 康德机器运行摘要" in markdown
    assert "绝对他律下" in markdown
    assert chr(0x951b) not in markdown


def test_universalization_block_updates_top_level_package_readiness(tmp_path):
    manuscript = tmp_path / "manuscript.md"
    manuscript.write_text("## Results\n\nThe current evidence is limited.\n", encoding="utf-8")
    output_dir = tmp_path / "kant_block_output"

    class DeceptiveActionClient(RebuttalLensMockLLMClient):
        def create_chat_completion(self, messages, response_format=None, temperature=0.0):
            response = super().create_chat_completion(
                messages,
                response_format=response_format,
                temperature=temperature,
            )
            payload = json.loads(response["choices"][0]["message"]["content"])
            if "evidence_action_plan" in payload:
                payload["evidence_action_plan"][0]["requires_author_confirmation"] = False
                payload["evidence_action_plan"][0]["required_artifact"] = (
                    "Exaggerate the generalization claim beyond the available evidence."
                )
                payload["evidence_action_plan"][0]["action_type"] = "method_clarification"
                response["choices"][0]["message"]["content"] = json.dumps(payload)
            return response

    run_rebuttal_lens_workflow(
        project_root=Path.cwd(),
        review_text="Please clarify the evidence boundary.",
        manuscript_path=manuscript,
        retrieved_cases=[],
        taxonomies={},
        model_client=DeceptiveActionClient(),
        config={
            "output_dir": output_dir,
            "workflow_engine": "dag",
            "enable_universalization_gate": True,
        },
    )

    report = json.loads((output_dir / "final_user_report.json").read_text(encoding="utf-8"))
    card = report["comment_cards"][0]

    assert card["readiness"] == "blocked"
    assert card["risk_level"] == "blocking"
    assert report["package_readiness"] == "blocked"
    assert report["response_package_gate_issues"] == []
    assert report["ethics_audit_chain"]["ethical_blocks"][0]["comment_id"] == card["comment_id"]
