import json
from pathlib import Path
from typing import Any

import pytest

from peer_review_skills.agents.manuscript_context import (
    build_rebuttal_lens_unit,
    load_manuscript_context,
)
from peer_review_skills.agents.rebuttal_lens_agents import (
    CaseRetrievalInterpreterAgent,
    ManuscriptContextExtractorAgent,
    ManuscriptEvidenceLocatorAgent,
    create_rebuttal_lens_frontend_agents,
)
from peer_review_skills.agents.rebuttal_lens_workflow import (
    run_rebuttal_lens_workflow,
)
from peer_review_skills.agents.specialized_agents import EvidenceActionPlannerAgent
from peer_review_skills.agents.specialized_agents_part2 import (
    CrossDisciplinaryLensInterpreterAgent,
    IntegrityAdequacyCheckerAgent,
)
from peer_review_skills.cli.main import build_parser, build_rebuttal_lens_argv, main


class RebuttalLensMockLLMClient:
    def __init__(self):
        self.model_name = "mock-deepseek-v3"
        self.call_count = 0

    def create_chat_completion(
        self,
        messages: list[dict[str, str]],
        response_format: dict[str, str] | None = None,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        self.call_count += 1
        system_prompt = messages[0]["content"].lower()
        if "cross-disciplinary" in system_prompt:
            content = {
                "lens_interpretations": {
                    "tacit_knowledge_boundary": {"observable_trace": "review text"},
                    "institutional_dependence": {"observable_trace": "transparency norm"},
                    "actor_network_alignment": {"observable_trace": "dataset split"},
                    "fast_slow_cognitive_correction": {"observable_trace": "plan-first workflow"},
                    "emotion_tone_commitment_calibration": {"observable_trace": "calibrated commitment"},
                    "author_agency_gate": {"observable_trace": "author confirmation required"},
                },
                "reasoning": "Cross-disciplinary lenses are grounded in observable traces.",
            }
        elif "manuscript context extractor" in system_prompt:
            content = {
                "manuscript_context_note": {
                    "mode": "manuscript_aware",
                    "usable_sections": ["section_002"],
                    "limits": ["text-only extraction"],
                },
                "section_inventory": [
                    {
                        "section_id": "section_002",
                        "heading": "Methods",
                        "evidence_role": "method transparency",
                    }
                ],
                "author_confirmation_questions": [
                    "Does the methods section describe the exact dataset split?"
                ],
                "reasoning": "The supplied manuscript context includes a Methods section.",
            }
        elif "manuscript evidence locator" in system_prompt:
            content = {
                "manuscript_evidence_map": [
                    {
                        "concern_id": "concern_001",
                        "status": "partially_supported",
                        "section_id": "section_002",
                        "text_evidence": "80/10/10 dataset split",
                        "gap": "random seed and stratification need confirmation",
                    }
                ],
                "evidence_gaps": [
                    "random seed and stratification need author confirmation"
                ],
                "author_confirmation_questions": [
                    "Can you confirm the random seed and stratification protocol?"
                ],
                "reasoning": "The manuscript text supports the split but not every protocol detail.",
            }
        elif "case retrieval interpreter" in system_prompt:
            content = {
                "case_interpretation": [
                    {
                        "case_id": "case_001",
                        "analogy": "method transparency concern",
                        "transferable_strategy": "clarify existing method and add missing protocol detail",
                        "boundary": "case analogy only; not outcome prediction",
                    }
                ],
                "case_use_boundary": "Retrieved Nature cases support analogy, not automatic recommendations.",
                "reasoning": "The retrieved case has a similar methods-transparency issue.",
            }
        elif "reviewer understanding" in system_prompt:
            content = {
                "concern_map": [{
                    "concern_type": "methodological_transparency",
                    "surface_request": "clarify dataset split",
                    "text_evidence": "dataset split is unclear",
                    "confidence": "high",
                }],
                "reasoning": "Reviewer explicitly asks for clarification.",
            }
        elif "tacit concern" in system_prompt:
            content = {
                "risk_interpretation": [{
                    "risk_type": "reproducibility_risk",
                    "tacit_concern": "insufficient_method_transparency",
                    "observable_trace": "dataset split is unclear",
                    "boundary": "Observable textual trace only; not reviewer psychology.",
                }],
                "reasoning": "The concern is tied to reproducibility.",
            }
        elif "institutional signal" in system_prompt:
            content = {
                "institutional_signal_note": [{
                    "institutional_signal": "transparency_norm",
                    "action_link": "make dataset split auditable",
                    "boundary": "Not an acceptance prediction; author judgment required.",
                }],
                "reasoning": "Transparency is institutionally relevant.",
            }
        elif "evidence action" in system_prompt:
            content = {
                "evidence_action_plan": [{
                    "action_type": "clarify_existing_method",
                    "required_artifact": "dataset split protocol and random seed",
                    "supporting_case_ids": ["case_001"],
                    "requires_author_confirmation": True,
                }],
                "author_confirmation_questions": [
                    "Can you confirm the random seed and stratification protocol?"
                ],
                "reasoning": "The manuscript evidence is partial and case analogy supports clarification.",
            }
        elif "author positioning" in system_prompt:
            content = {
                "author_positioning": [{
                    "position": "acknowledge_and_clarify",
                    "stance_boundary": "Offer options for author judgment; do not force concession.",
                    "alternative_positions": ["clarify_existing_evidence"],
                }],
                "reasoning": "Acknowledge the ambiguity and clarify the method.",
            }
        elif "tone and commitment" in system_prompt:
            content = {
                "tone_commitment_warnings": [{
                    "tone": "professional_specific",
                    "commitment_level": "requires_author_confirmation",
                    "risk_flags": ["avoid promising unavailable robustness checks"],
                    "boundary": "Not a psychological diagnosis; observable text only.",
                }],
                "reasoning": "Commitment must match available evidence.",
            }
        elif "actor network" in system_prompt:
            content = {
                "actor_network_note": [{
                    "actor_type": "dataset",
                    "actor_id": "dataset split",
                    "role": "carries reproducibility evidence",
                    "evidence_link": "Methods section and author confirmation",
                }],
                "retrieved_case_ids": ["case_001"],
                "boundary": "Observable alignment only; not causal claims.",
                "reasoning": "Dataset split is a non-human evidence carrier.",
            }
        elif "integrity and adequacy" in system_prompt:
            content = {
                "adequacy_report": ["The plan is adequate if author confirms missing protocol details."],
                "response_adequacy": {
                    "is_adequate": True,
                    "missing_elements": [],
                    "strengths": ["manuscript evidence and case analogy are separated"],
                },
                "provenance_checks": [{
                    "claim": "dataset split appears in Methods",
                    "source": "section_002",
                    "traceable": True,
                }],
                "responsible_use_warnings": [
                    "assistant_only",
                    "author_must_verify_all_claims",
                    "not_final_rebuttal_text",
                    "no_acceptance_prediction",
                ],
                "issues": [],
                "reasoning": "No unsupported final rebuttal claim is made.",
            }
        else:
            content = {"unexpected": system_prompt}
        return {
            "choices": [{"message": {"content": json.dumps(content)}}],
            "usage": {"prompt_tokens": 10, "completion_tokens": 10},
        }


def test_load_manuscript_context_splits_markdown_sections(tmp_path):
    manuscript = tmp_path / "manuscript.md"
    manuscript.write_text(
        "# Title\n\n"
        "Nature RebuttalLens example.\n\n"
        "## Methods\n\n"
        "We used an 80/10/10 dataset split with a fixed random seed.\n\n"
        "## Results\n\n"
        "Table 1 reports the robustness check.\n",
        encoding="utf-8",
    )

    context = load_manuscript_context(manuscript)

    assert context["mode"] == "manuscript_aware"
    assert context["source_path"].endswith("manuscript.md")
    assert [section["heading"] for section in context["sections"]] == [
        "Title",
        "Methods",
        "Results",
    ]
    assert context["sections"][1]["section_id"] == "section_002"
    assert "80/10/10 dataset split" in context["sections"][1]["text"]
    assert context["evidence_boundary"]["can_locate_textual_evidence"] is True
    assert context["evidence_boundary"]["requires_author_confirmation"] is True


def test_load_manuscript_context_without_file_returns_review_only_boundary():
    context = load_manuscript_context(None)

    assert context["mode"] == "review_only"
    assert context["sections"] == []
    assert context["evidence_boundary"]["can_locate_textual_evidence"] is False
    assert context["evidence_boundary"]["missing_manuscript_warning"]


def test_build_rebuttal_lens_unit_preserves_inputs_and_manuscript_context(tmp_path):
    manuscript = tmp_path / "manuscript.txt"
    manuscript.write_text("Methods\nWe describe the control experiment.", encoding="utf-8")

    unit = build_rebuttal_lens_unit(
        review_text="The control experiment is unclear.",
        response_text="We will clarify this point.",
        manuscript_path=manuscript,
        editor_text="Major revision requested.",
        unit_id="user_case_001",
    )

    assert unit["unit_id"] == "user_case_001"
    assert unit["review_text"] == "The control experiment is unclear."
    assert unit["response_text"] == "We will clarify this point."
    assert unit["editor_text"] == "Major revision requested."
    assert unit["manuscript_context"]["mode"] == "manuscript_aware"
    assert unit["provenance"]["input_source"] == "user_supplied"


@pytest.mark.parametrize(
    ("agent_cls", "expected_field", "inputs"),
    [
        (
            ManuscriptContextExtractorAgent,
            "manuscript_context_note",
            {
                "manuscript_context": {
                    "mode": "manuscript_aware",
                    "sections": [{"section_id": "section_002", "heading": "Methods"}],
                }
            },
        ),
        (
            ManuscriptEvidenceLocatorAgent,
            "manuscript_evidence_map",
            {
                "review_text": "The dataset split is unclear.",
                "concern_map": {"concern_map": []},
                "manuscript_context_note": {"mode": "manuscript_aware"},
                "manuscript_context": {
                    "mode": "manuscript_aware",
                    "sections": [{"section_id": "section_002", "text": "80/10/10 dataset split"}],
                },
            },
        ),
        (
            CaseRetrievalInterpreterAgent,
            "case_interpretation",
            {
                "review_text": "The dataset split is unclear.",
                "concern_map": {"concern_map": []},
                "risk_interpretation": {"risk_interpretation": []},
                "retrieved_cases": [{"unit_id": "case_001", "score": 0.8}],
            },
        ),
    ],
)
def test_rebuttal_lens_frontend_agents_are_independent_llm_units(agent_cls, expected_field, inputs):
    client = RebuttalLensMockLLMClient()
    agent = agent_cls(agent_cls.__name__, client)

    message = agent.execute(inputs)

    assert message.message_type == "output"
    assert expected_field in message.content
    assert client.call_count == 1


def test_create_rebuttal_lens_frontend_agents_returns_three_agents():
    agents = create_rebuttal_lens_frontend_agents(RebuttalLensMockLLMClient())

    assert set(agents) == {
        "manuscript_context_extractor",
        "manuscript_evidence_locator",
        "case_retrieval_interpreter",
    }


def test_run_rebuttal_lens_workflow_returns_manuscript_aware_trace(tmp_path):
    manuscript = tmp_path / "manuscript.md"
    manuscript.write_text(
        "## Methods\n\nWe used an 80/10/10 dataset split.\n",
        encoding="utf-8",
    )
    output_dir = tmp_path / "rebuttal_lens_output"

    summary = run_rebuttal_lens_workflow(
        project_root=Path.cwd(),
        review_text="The dataset split is unclear.",
        response_text="We will clarify the dataset split.",
        manuscript_path=manuscript,
        model_client=RebuttalLensMockLLMClient(),
        retrieved_cases=[{"unit_id": "case_001", "score": 0.8}],
        taxonomies={},
        config={"output_dir": output_dir},
    )

    assert summary["system_name"] == "Nature RebuttalLens"
    assert summary["total_traces"] == 1
    assert summary["total_llm_calls"] == 12
    trace_path = output_dir / "rebuttal_lens_trace.json"
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    assert trace["workflow_version"] == "rebuttal_lens_v1"
    assert trace["manuscript_context"]["mode"] == "manuscript_aware"
    outputs = trace["agent_intermediate_outputs"]
    assert "manuscript_context_extractor" in outputs
    assert "manuscript_evidence_locator" in outputs
    assert "case_retrieval_interpreter" in outputs
    assert "integrity_adequacy_checker" in outputs
    assert outputs["manuscript_evidence_locator"]["manuscript_evidence_map"][0]["section_id"] == "section_002"
    assert "author_must_verify_all_claims" in outputs["integrity_adequacy_checker"]["responsible_use_warnings"]


def test_rebuttal_lens_refinement_flag_fails_fast_until_supported(tmp_path):
    manuscript = tmp_path / "manuscript.md"
    manuscript.write_text("## Methods\n\nWe used an 80/10/10 split.\n", encoding="utf-8")

    with pytest.raises(ValueError, match="Nature RebuttalLens refinement is not yet supported"):
        run_rebuttal_lens_workflow(
            project_root=Path.cwd(),
            review_text="The dataset split is unclear.",
            manuscript_path=manuscript,
            model_client=RebuttalLensMockLLMClient(),
            taxonomies={},
            config={"enable_refinement": True},
        )


def test_evidence_action_planner_prompt_uses_manuscript_evidence_and_case_interpretation():
    agent = EvidenceActionPlannerAgent("evidence_action_planner", RebuttalLensMockLLMClient())

    prompt = agent.build_prompt({
        "concern_map": {"concern_map": []},
        "risk_interpretation": {"risk_interpretation": []},
        "retrieved_cases": [{"unit_id": "case_001"}],
        "manuscript_evidence": {"evidence_gaps": ["random seed missing"]},
        "case_interpretation": {"case_use_boundary": "case analogy only"},
    })
    user_payload = json.loads(prompt[1]["content"])

    assert user_payload["manuscript_evidence"]["evidence_gaps"] == ["random seed missing"]
    assert user_payload["case_interpretation"]["case_use_boundary"] == "case analogy only"


def test_integrity_prompt_receives_manuscript_context_boundary():
    agent = IntegrityAdequacyCheckerAgent("integrity_adequacy_checker", RebuttalLensMockLLMClient())

    prompt = agent.build_prompt({
        "all_agent_outputs": {},
        "unit": {
            "unit_id": "rebuttal_lens_user_case",
            "review_text": "Dataset split is unclear",
            "response_text": "We will clarify.",
            "provenance": {"input_source": "user_supplied"},
            "manuscript_context": {
                "mode": "review_only",
                "evidence_boundary": {"can_locate_textual_evidence": False},
            },
        },
    })
    user_payload = json.loads(prompt[1]["content"])

    assert user_payload["unit"]["manuscript_context"]["mode"] == "review_only"
    assert user_payload["unit"]["manuscript_context"]["evidence_boundary"]["can_locate_textual_evidence"] is False


def test_cli_parser_accepts_run_rebuttal_lens_file_inputs():
    parser = build_parser()

    args = parser.parse_args([
        "run-rebuttal-lens",
        "--review-file",
        "examples/rebuttal_lens/reviewer_comment.txt",
        "--manuscript-file",
        "examples/rebuttal_lens/manuscript_excerpt.md",
        "--response-file",
        "examples/rebuttal_lens/author_draft_response.txt",
        "--retrieved-cases-file",
        "examples/rebuttal_lens/retrieved_cases.json",
        "--output-dir",
        "data/evaluation/rebuttal_lens_demo",
        "--limit-cases",
        "3",
    ])

    assert args.command == "run-rebuttal-lens"
    assert str(args.review_file).endswith("reviewer_comment.txt")
    assert str(args.manuscript_file).endswith("manuscript_excerpt.md")
    assert str(args.response_file).endswith("author_draft_response.txt")
    assert str(args.retrieved_cases_file).endswith("retrieved_cases.json")
    assert args.limit_cases == 3


def test_cross_disciplinary_prompt_uses_readable_chinese_lens_names():
    agent = CrossDisciplinaryLensInterpreterAgent(
        "cross_disciplinary_lens_interpreter",
        RebuttalLensMockLLMClient(),
    )

    prompt = agent.build_prompt(
        {
            "all_agent_outputs": {},
            "unit": {"unit_id": "u1"},
            "retrieval": {"top_k": [{"unit_id": "case_001"}]},
        }
    )
    system_prompt = prompt[0]["content"]

    for phrase in [
        "默会知识边界",
        "制度依赖",
        "行动者网络对齐",
        "快慢思维校正",
        "情绪-语气-承诺校准",
        "作者主体性门控",
    ]:
        assert phrase in system_prompt
    for mojibake_marker in ["榛樹細", "鍒跺害", "琛屬", "鎯呯华", "浣滆€"]:
        assert mojibake_marker not in system_prompt


def test_public_config_lists_complete_rebuttal_lens_agent_set():
    config_text = (Path.cwd() / "config/multi_agent_config.yaml").read_text(encoding="utf-8")

    for agent_id in [
        "manuscript_context_extractor",
        "manuscript_evidence_locator",
        "case_retrieval_interpreter",
        "reviewer_understanding_agent",
        "tacit_concern_interpreter",
        "institutional_signal_interpreter",
        "evidence_action_planner",
        "author_positioning_agent",
        "tone_commitment_calibrator",
        "actor_network_mapper",
        "cross_disciplinary_lens_interpreter",
        "integrity_adequacy_checker",
    ]:
        assert f"{agent_id}:" in config_text
    assert 'mode: "rebuttal_lens"' in config_text


def test_public_audit_docs_are_not_stale_rule_based_findings():
    audit_paths = [
        Path.cwd() / "docs/audit/FINAL-AUDIT-SUMMARY.md",
        Path.cwd() / "docs/audit/agent-implementation-audit.md",
    ]
    combined = "\n".join(path.read_text(encoding="utf-8") for path in audit_paths)

    assert "Nature RebuttalLens" in combined
    assert "12 independent LLM calls" in combined
    assert "rule-based workflow assembly" not in combined.lower()
    assert "NOT independent LLM-based agents" not in combined


def test_python_project_has_installable_package_metadata():
    pyproject_path = Path.cwd() / "pyproject.toml"
    text = pyproject_path.read_text(encoding="utf-8")

    assert 'name = "nature-rebuttal-lens"' in text
    assert 'where = ["src"]' in text
    assert 'include = ["peer_review_skills*"]' in text
    assert 'run-rebuttal-lens = "peer_review_skills.cli.main:run_rebuttal_lens_cli"' in text
    assert 'pythonpath = ["src"]' in text


def test_console_script_wrapper_adds_run_rebuttal_lens_subcommand():
    argv = build_rebuttal_lens_argv([
        "--review-file",
        "examples/rebuttal_lens/reviewer_comment.txt",
        "--output-dir",
        "data/evaluation/rebuttal_lens_demo",
    ])

    assert argv == [
        "run-rebuttal-lens",
        "--review-file",
        "examples/rebuttal_lens/reviewer_comment.txt",
        "--output-dir",
        "data/evaluation/rebuttal_lens_demo",
    ]


def test_run_rebuttal_lens_cli_reports_missing_api_without_traceback(monkeypatch, capsys):
    monkeypatch.delenv("PEER_REVIEW_API_BASE_URL", raising=False)
    monkeypatch.delenv("PEER_REVIEW_API_KEY", raising=False)
    monkeypatch.delenv("PEER_REVIEW_API_MODEL", raising=False)

    with pytest.raises(SystemExit) as exc_info:
        main([
            "run-rebuttal-lens",
            "--review-file",
            "examples/rebuttal_lens/reviewer_comment.txt",
            "--output-dir",
            "data/evaluation/rebuttal_lens_demo",
        ])

    captured = capsys.readouterr()
    assert exc_info.value.code == 2
    assert "missing PEER_REVIEW_API_KEY" in captured.err
    assert "Traceback" not in captured.err


def test_readme_keeps_release_critical_open_source_sections():
    readme = (Path.cwd() / "README.md").read_text(encoding="utf-8")

    for required in [
        "## Installation",
        "python -m pip install -e .",
        "run-rebuttal-lens",
        "docs/rebuttal_lens_system_flow.html",
        "docs/assets/rebuttal-lens-workflow.svg",
        "docs/DATA_CARD_zh.md",
        "docs/AGENT_CARD_zh.md",
        "docs/DATA_RELEASE_BOUNDARY_zh.md",
        "python -m compileall -q src tests",
        "python -m pip install --dry-run -e .",
        "upload confidential manuscript material to an external API",
        "Apache License 2.0",
        "| Capability | Output |",
        "Layer 0: Manuscript context",
        "Layer 5: Integrity gate",
    ]:
        assert required in readme


def test_core_public_chinese_docs_are_readable_not_mojibake():
    public_docs = [
        Path.cwd() / "docs/REBUTTAL_LENS_WORKFLOW_zh.md",
        Path.cwd() / "docs/RESPONSIBLE_USE_zh.md",
        Path.cwd() / "docs/DATA_CARD_zh.md",
        Path.cwd() / "docs/AGENT_CARD_zh.md",
        Path.cwd() / "docs/DATA_RELEASE_BOUNDARY_zh.md",
        Path.cwd() / "docs/MODEL_AND_AGENT_LIMITATIONS_zh.md",
        Path.cwd() / "docs/OPEN_SOURCE_V0_1_COMPLETION_STATUS_zh.md",
    ]
    mojibake_markers = [
        "绯荤粺",
        "瀹＄",
        "浣滆",
        "杈撳",
        "鍙戝",
        "鎺ユ",
        "鐨",
        "榛樹細",
    ]

    for path in public_docs:
        text = path.read_text(encoding="utf-8")
        assert len(text.strip()) > 100, f"{path} unexpectedly short"
        for marker in mojibake_markers:
            assert marker not in text, f"{path} contains mojibake marker {marker!r}"
