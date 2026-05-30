import json
import subprocess
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile
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
    load_rebuttal_lens_config,
    run_rebuttal_lens_workflow,
)
from peer_review_skills.agents.specialized_agents import EvidenceActionPlannerAgent
from peer_review_skills.agents.specialized_agents_part2 import (
    CrossDisciplinaryLensInterpreterAgent,
    IntegrityAdequacyCheckerAgent,
    create_all_specialized_agents,
)
from peer_review_skills.cli.main import build_parser, build_rebuttal_lens_argv, main


class RebuttalLensMockLLMClient:
    def __init__(self):
        self.model = "mock-deepseek-v3"
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


class RebuttalLensFailingLLMClient(RebuttalLensMockLLMClient):
    def __init__(self, fail_on_call: int):
        super().__init__()
        self.fail_on_call = fail_on_call
        self.shared_call_count = {"value": 0}

    def __copy__(self):
        cloned = type(self)(self.fail_on_call)
        cloned.model = self.model
        cloned.model_name = self.model_name
        cloned.shared_call_count = self.shared_call_count
        return cloned

    def create_chat_completion(
        self,
        messages: list[dict[str, str]],
        response_format: dict[str, str] | None = None,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        next_call = self.shared_call_count["value"] + 1
        if next_call == self.fail_on_call:
            self.shared_call_count["value"] = next_call
            self.call_count = next_call
            raise RuntimeError("simulated provider failure")
        self.shared_call_count["value"] = next_call
        response = super().create_chat_completion(messages, response_format, temperature)
        self.call_count = self.shared_call_count["value"]
        return response


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


def test_load_manuscript_context_extracts_text_from_pdf(tmp_path):
    pytest.importorskip("matplotlib")
    pytest.importorskip("pdfplumber")
    from matplotlib.backends.backend_pdf import PdfPages
    import matplotlib.pyplot as plt

    manuscript = tmp_path / "manuscript.pdf"
    with PdfPages(manuscript) as pdf:
        figure = plt.figure(figsize=(8.5, 11))
        figure.text(
            0.1,
            0.9,
            "Methods\nWe used an 80/10/10 dataset split with a fixed seed.",
            fontsize=12,
        )
        pdf.savefig(figure)
        plt.close(figure)

    context = load_manuscript_context(manuscript)

    assert context["mode"] == "manuscript_aware"
    assert context["source_path"].endswith("manuscript.pdf")
    assert context["extraction"]["format"] == "pdf"
    assert context["evidence_boundary"]["no_binary_ocr_claim"] is True
    assert any("80/10/10 dataset split" in section["text"] for section in context["sections"])


def test_load_manuscript_context_extracts_text_from_docx(tmp_path):
    manuscript = tmp_path / "manuscript.docx"
    _write_minimal_docx(
        manuscript,
        ["Title", "Methods", "We used an 80/10/10 dataset split with a fixed seed."],
    )

    context = load_manuscript_context(manuscript)

    assert context["mode"] == "manuscript_aware"
    assert context["source_path"].endswith("manuscript.docx")
    assert context["extraction"]["format"] == "docx"
    assert any(section["heading"] == "Methods" for section in context["sections"])
    assert any("80/10/10 dataset split" in section["text"] for section in context["sections"])


def test_load_manuscript_context_doc_requires_converter_when_soffice_missing(tmp_path, monkeypatch):
    manuscript = tmp_path / "manuscript.doc"
    manuscript.write_bytes(b"legacy word binary")
    monkeypatch.setattr("peer_review_skills.agents.manuscript_context.shutil.which", lambda name: None)

    with pytest.raises(RuntimeError, match="LibreOffice/soffice is required"):
        load_manuscript_context(manuscript)


def _write_minimal_docx(path: Path, paragraphs: list[str]) -> None:
    document_xml = (
        '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        + "".join(
            f"<w:p><w:r><w:t>{_xml_escape(paragraph)}</w:t></w:r></w:p>"
            for paragraph in paragraphs
        )
        + "</w:body></w:document>"
    )
    with ZipFile(path, "w", ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
            '<Default Extension="xml" ContentType="application/xml"/>'
            '<Override PartName="/word/document.xml" '
            'ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            "</Types>",
        )
        archive.writestr(
            "_rels/.rels",
            '<?xml version="1.0" encoding="UTF-8"?>'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" '
            'Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" '
            'Target="word/document.xml"/>'
            "</Relationships>",
        )
        archive.writestr("word/document.xml", document_xml)


def _xml_escape(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


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


def test_manuscript_evidence_prompt_selects_late_review_relevant_sections():
    agent = ManuscriptEvidenceLocatorAgent("manuscript_evidence_locator", RebuttalLensMockLLMClient())
    sections = [
        {
            "section_id": f"section_{index:03d}",
            "heading": f"Background {index}",
            "text": "general background unrelated to dataset splitting",
        }
        for index in range(1, 18)
    ]
    sections.append({
        "section_id": "section_018",
        "heading": "Supplementary Methods",
        "text": "The final dataset split uses 80/10/10 train validation test partitions.",
    })

    prompt = agent.build_prompt({
        "review_text": "The dataset split is unclear and needs train validation test detail.",
        "concern_map": {"concern_map": []},
        "manuscript_context_note": {"mode": "manuscript_aware"},
        "manuscript_context": {
            "mode": "manuscript_aware",
            "section_count": len(sections),
            "sections": sections,
        },
    })
    user_payload = json.loads(prompt[1]["content"])

    selected_section_ids = [section["section_id"] for section in user_payload["sections"]]
    assert "section_018" in selected_section_ids
    assert user_payload["selection_metadata"]["total_sections"] == 18
    assert user_payload["selection_metadata"]["truncated_sections"] >= 1
    assert user_payload["selection_metadata"]["selection_strategy"] == "review_relevance_then_document_order"


def test_manuscript_context_prompt_records_section_and_character_truncation():
    agent = ManuscriptContextExtractorAgent("manuscript_context_extractor", RebuttalLensMockLLMClient())
    sections = [
        {
            "section_id": "section_001",
            "heading": "Methods",
            "text": "dataset split " + ("x" * 1200),
        }
    ]

    prompt = agent.build_prompt({
        "manuscript_context": {
            "mode": "manuscript_aware",
            "section_count": len(sections),
            "sections": sections,
        },
    })
    user_payload = json.loads(prompt[1]["content"])

    assert user_payload["selection_metadata"]["truncated_chars"] > 0
    assert user_payload["sections"][0]["char_count"] > len(user_payload["sections"][0]["text_preview"])


@pytest.mark.parametrize(
    ("agent_cls", "output", "expected_error"),
    [
        (
            ManuscriptEvidenceLocatorAgent,
            {"manuscript_evidence_map": "not-a-list", "evidence_gaps": []},
            "manuscript_evidence_map",
        ),
        (
            CaseRetrievalInterpreterAgent,
            {"case_interpretation": [], "case_use_boundary": ["not-a-string"]},
            "case_use_boundary",
        ),
        (
            EvidenceActionPlannerAgent,
            {"evidence_action_plan": [{"requires_author_confirmation": "yes"}]},
            "requires_author_confirmation",
        ),
        (
            IntegrityAdequacyCheckerAgent,
            {
                "adequacy_report": [],
                "response_adequacy": [],
                "provenance_checks": [],
                "responsible_use_warnings": ["assistant_only", "author_must_verify_all_claims"],
            },
            "response_adequacy",
        ),
    ],
)
def test_rebuttal_lens_agents_reject_malformed_field_types(agent_cls, output, expected_error):
    agent = agent_cls(agent_cls.__name__, RebuttalLensMockLLMClient())

    valid, error = agent.validate_output(output)

    assert valid is False
    assert expected_error in str(error)


def test_rebuttal_lens_workflow_writes_failure_trace_on_agent_error(tmp_path):
    manuscript = tmp_path / "manuscript.md"
    manuscript.write_text("## Methods\n\nWe used an 80/10/10 split.\n", encoding="utf-8")
    output_dir = tmp_path / "rebuttal_lens_failure_output"

    with pytest.raises(RuntimeError, match="simulated provider failure"):
        run_rebuttal_lens_workflow(
            project_root=Path.cwd(),
            review_text="The dataset split is unclear.",
            manuscript_path=manuscript,
            model_client=RebuttalLensFailingLLMClient(fail_on_call=3),
            retrieved_cases=[{"unit_id": "case_001", "score": 0.8}],
            taxonomies={},
            config={"output_dir": output_dir, "agent_max_retries": 1},
        )

    failure_trace_path = output_dir / "rebuttal_lens_failure_trace.json"
    assert failure_trace_path.exists()
    failure_trace = json.loads(failure_trace_path.read_text(encoding="utf-8"))
    assert failure_trace["status"] == "failed"
    assert "simulated provider failure" in failure_trace["error"]
    assert failure_trace["partial_trace"]["message_bus"]
    assert "api_key" not in json.dumps(failure_trace).lower()


def test_rebuttal_lens_workflow_writes_layer_checkpoints(tmp_path):
    manuscript = tmp_path / "manuscript.md"
    manuscript.write_text("## Methods\n\nWe used an 80/10/10 split.\n", encoding="utf-8")
    output_dir = tmp_path / "rebuttal_lens_checkpoint_output"

    run_rebuttal_lens_workflow(
        project_root=Path.cwd(),
        review_text="The dataset split is unclear.",
        manuscript_path=manuscript,
        model_client=RebuttalLensMockLLMClient(),
        retrieved_cases=[{"unit_id": "case_001", "score": 0.8}],
        taxonomies={},
        config={"output_dir": output_dir},
    )

    checkpoint_dir = output_dir / "checkpoints"
    checkpoint_files = sorted(checkpoint_dir.glob("*.json"))
    assert len(checkpoint_files) == 12
    first_checkpoint = json.loads(checkpoint_files[0].read_text(encoding="utf-8"))
    assert first_checkpoint["status"] == "checkpoint"
    assert first_checkpoint["partial_trace"]["execution_trace"][0]["layer"] == "Layer 0: Manuscript Context"


def test_rebuttal_lens_agent_config_controls_retry_and_temperature():
    agents = create_rebuttal_lens_frontend_agents(
        RebuttalLensMockLLMClient(),
        {
            "agents": {
                "manuscript_evidence_locator": {
                    "temperature": 0.25,
                    "max_retries": 5,
                }
            }
        },
    )

    evidence_agent = agents["manuscript_evidence_locator"]
    context_agent = agents["manuscript_context_extractor"]
    assert evidence_agent.temperature == 0.25
    assert evidence_agent.max_retries == 5
    assert context_agent.temperature == 0.0
    assert context_agent.max_retries == 3


def test_rebuttal_lens_config_loader_reads_public_agent_settings(tmp_path):
    config_path = tmp_path / "multi_agent_config.yaml"
    config_path.write_text(
        """
workflow:
  mode: "rebuttal_lens"

multi_agent:
  enable_refinement: false
  max_refinement_iterations: 2
  agents:
    manuscript_evidence_locator:
      model: "deepseek-v3"
      temperature: 0.25
      max_retries: 5
""".strip(),
        encoding="utf-8",
    )

    config = load_rebuttal_lens_config(config_path)

    assert config["workflow"]["mode"] == "rebuttal_lens"
    assert config["multi_agent"]["enable_refinement"] is False
    assert config["multi_agent"]["max_refinement_iterations"] == 2
    assert config["multi_agent"]["agents"]["manuscript_evidence_locator"]["temperature"] == 0.25
    assert config["multi_agent"]["agents"]["manuscript_evidence_locator"]["max_retries"] == 5


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
        "examples/rebuttal_lens/manuscript_excerpt.txt",
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
    assert str(args.manuscript_file).endswith("manuscript_excerpt.txt")
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
    for mojibake_marker in [
        "".join(chr(code) for code in [0x699B, 0x6A39, 0x7D30]),
        "".join(chr(code) for code in [0x934F, 0x8DFA, 0x5BB3]),
        "".join(chr(code) for code in [0x7403, 0x5C70, 0x59E9]),
        chr(0x93AF),
        chr(0x6D63),
    ]:
        assert mojibake_marker not in system_prompt


def test_backend_specialized_agents_apply_per_agent_model_config():
    agents = create_all_specialized_agents(
        RebuttalLensMockLLMClient(),
        {
            "agents": {
                "reviewer_understanding_agent": {
                    "model": "reviewer-model",
                    "temperature": 0.25,
                    "max_retries": 5,
                }
            }
        },
    )

    agent = agents["reviewer_understanding_agent"]
    assert agent.client.model == "reviewer-model"
    assert agent.client.model_name == "reviewer-model"
    assert agent.temperature == 0.25
    assert agent.max_retries == 5

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


def test_public_repository_does_not_reference_internal_docs():
    readme = (Path.cwd() / "README.md").read_text(encoding="utf-8")
    tracked_markdown = set(
        subprocess.run(
            ["git", "ls-files", "*.md"],
            cwd=Path.cwd(),
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
    )

    assert "README.md" in tracked_markdown
    assert "examples/rebuttal_lens/WORKED_EXAMPLE_zh.md" not in tracked_markdown
    assert "codex.md" not in tracked_markdown
    assert "UPGRADE.md" not in tracked_markdown
    assert "docs/" not in readme
    assert "codex.md" not in readme
    assert "UPGRADE.md" not in readme
    assert ".understand-anything" not in readme


def test_python_project_has_installable_package_metadata():
    pyproject_path = Path.cwd() / "pyproject.toml"
    text = pyproject_path.read_text(encoding="utf-8")

    assert 'name = "nature-rebuttal-lens"' in text
    assert 'where = ["src"]' in text
    assert 'include = ["peer_review_skills*"]' in text
    assert 'run-rebuttal-lens = "peer_review_skills.cli.main:run_rebuttal_lens_cli"' in text
    assert 'pythonpath = ["src"]' in text
    assert '[project.optional-dependencies]' in text
    assert 'pdf = ["pdfplumber>=0.11"]' in text


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
        'python -m pip install -e ".[pdf]"',
        "run-rebuttal-lens",
        "Layer 0",
        "Layer 5",
        "tacit knowledge boundary",
        "author agency gate",
        "python -m compileall -q src tests",
        "python -m pip install --dry-run -e .",
        "upload confidential manuscript material to an external API",
        "Apache License 2.0",
        "extractable PDF text",
        "DOCX",
        "legacy DOC",
        "model-assisted, not human gold",
        "not a hidden one-shot rebuttal",
    ]:
        assert required in readme


def test_public_readme_is_readable_not_mojibake():
    text = (Path.cwd() / "README.md").read_text(encoding="utf-8")
    mojibake_markers = [
        "".join(chr(code) for code in [0x7F01, 0xE218, 0x5D35]),
        "".join(chr(code) for code in [0x943E, 0x7678]),
        "".join(chr(code) for code in [0x6D63, 0x6C86]),
        "".join(chr(code) for code in [0x93C9, 0x5820]),
        "".join(chr(code) for code in [0x95B8, 0x6B04]),
        "".join(chr(code) for code in [0x95B9, 0x6052]),
        chr(0x95BB),
        "".join(chr(code) for code in [0x6992, 0x6DBC, 0x7D31]),
    ]

    assert len(text.strip()) > 1000
    for marker in mojibake_markers:
        assert marker not in text, f"README.md contains mojibake marker {marker!r}"
