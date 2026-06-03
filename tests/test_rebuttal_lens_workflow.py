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
        elif "committee meta-reviewer" in system_prompt:
            content = {
                "committee_synthesis": {
                    "highest_priority_risks": ["dataset split leakage"],
                    "agreement": ["methodology and claim reviewers agree"],
                    "disagreement": [],
                    "recommended_focus": "clarify split and avoid overclaim",
                },
                "author_confirmation_questions": [
                    "Can the temporal split validation be completed?"
                ],
                "reasoning": "The committee agrees the split evidence is central.",
            }
        elif "reviewer committee" in system_prompt:
            content = {
                "reviewer_role": "methodology",
                "findings": [
                    {
                        "risk": "dataset split leakage",
                        "severity": "high",
                        "evidence": "random split without temporal validation",
                        "recommendation": "add temporal validation or narrow the claim",
                    }
                ],
                "author_confirmation_questions": [
                    "Can the temporal split validation be completed?"
                ],
                "reasoning": "Committee reviewer focuses on split validity.",
            }
        elif "strategy meta-planner" in system_prompt:
            content = {
                "selected_strategy_id": "strategy_a",
                "merged_plan": {
                    "response_position": "accept_and_revise",
                    "required_actions": ["clarify split", "narrow unsupported generalization"],
                    "claim_adjustments": ["avoid claiming cross-context generalization"],
                },
                "rejection_reasons": [
                    {"strategy_id": "strategy_b", "reason": "unsupported overclaim"}
                ],
                "author_confirmation_questions": [
                    "Can the temporal split validation be completed?"
                ],
                "reasoning": "Strategy A best preserves evidence boundaries.",
            }
        elif "strategy tournament" in system_prompt:
            content = {
                "strategy_candidates": [
                    {
                        "strategy_id": "strategy_a",
                        "name": "clarify split and narrow claim",
                        "response_position": "accept_and_revise",
                        "required_actions": ["clarify split"],
                        "rubric_scores": {
                            "concern_coverage": 5,
                            "evidence_grounding": 4,
                            "feasibility": 4,
                            "overclaim_risk": 1,
                        },
                        "author_confirmation_required": True,
                    }
                ],
                "reasoning": "The safest strategy avoids unsupported claims.",
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


class RebuttalLensNullableCaseIdsLLMClient(RebuttalLensMockLLMClient):
    def create_chat_completion(
        self,
        messages: list[dict[str, str]],
        response_format: dict[str, str] | None = None,
        temperature: float = 0.0,
    ) -> dict[str, Any]:
        response = super().create_chat_completion(messages, response_format, temperature)
        system_prompt = messages[0]["content"].lower()
        if "evidence action" in system_prompt:
            content = json.loads(response["choices"][0]["message"]["content"])
            content["evidence_action_plan"][0]["supporting_case_ids"] = None
            response["choices"][0]["message"]["content"] = json.dumps(content)
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


def test_rebuttal_lens_final_report_composer_builds_user_package():
    from peer_review_skills.agents.final_report import compose_final_user_report

    trace = {
        "query_unit_id": "case_001",
        "agent_intermediate_outputs": {
            "reviewer_understanding_agent": {
                "concern_map": [
                    {
                        "concern_type": "experimental_design",
                        "surface_request": "clarify temporal split",
                        "text_evidence": "temporal leakage was not explained",
                        "confidence": "high",
                    }
                ]
            },
            "manuscript_evidence_locator": {
                "manuscript_evidence_map": [
                    {
                        "concern_id": "experimental_design",
                        "status": "partially_supported",
                        "section_id": "section_004",
                        "text_evidence": "random paper-level split",
                        "gap": "no temporal split result",
                    }
                ],
                "evidence_gaps": ["no temporal split result"],
                "author_confirmation_questions": ["Can you run a temporal split?"],
            },
            "evidence_action_planner": {
                "evidence_action_plan": [
                    {
                        "action_type": "new_analysis",
                        "required_artifact": "temporally held-out split",
                        "supporting_case_ids": ["nature_case_temporal_split_017"],
                        "requires_author_confirmation": True,
                    }
                ]
            },
            "tone_commitment_calibrator": {
                "tone_commitment_warnings": [
                    {
                        "tone": "assertive",
                        "commitment_level": "unknown",
                        "risk_flags": ["overclaim"],
                        "boundary": "observable text only",
                    }
                ]
            },
            "integrity_adequacy_checker": {
                "response_adequacy": {
                    "is_adequate": True,
                    "missing_elements": ["temporal split details"],
                    "strengths": ["concern coverage"],
                },
                "provenance_checks": [
                    {
                        "claim": "generalizes across contexts",
                        "source": "none",
                        "traceable": False,
                    }
                ],
                "responsible_use_warnings": [
                    "assistant_only",
                    "author_must_verify_all_claims",
                    "not_final_rebuttal_text",
                    "no_acceptance_prediction",
                ],
                "issues": [
                    {
                        "severity": "warning",
                        "agent_id": "tone_commitment_calibrator",
                        "description": "overclaim risk",
                    }
                ],
            },
        },
        "responsible_use_boundary": {
            "assistant_only": True,
            "not_final_rebuttal_text": True,
            "author_must_verify_all_claims": True,
            "no_acceptance_prediction": True,
        },
    }

    report = compose_final_user_report(trace)

    assert report["report_type"] == "author_rebuttal_assistant_report"
    assert report["comment_cards"][0]["comment_id"] == "comment_001"
    assert report["comment_cards"][0]["evidence_status"] == "partially_supported"
    assert report["comment_cards"][0]["author_input_required"] is True
    assert "generalizes across contexts" in report["unsafe_claims"][0]["claim"]
    assert "assistant_only" in report["responsible_use_warnings"]
    assert report["recommended_rebuttal_outline"]


def test_final_report_matches_evidence_and_actions_by_concern_id():
    from peer_review_skills.agents.final_report import compose_final_user_report

    trace = {
        "query_unit_id": "case_001",
        "agent_intermediate_outputs": {
            "reviewer_understanding_agent": {
                "concern_map": [
                    {
                        "concern_id": "concern_method",
                        "concern_type": "experimental_design",
                        "surface_request": "clarify temporal split",
                        "text_evidence": "temporal leakage was not explained",
                        "confidence": "high",
                    },
                    {
                        "concern_id": "concern_clarity",
                        "concern_type": "clarity_presentation",
                        "surface_request": "clarify wording",
                        "text_evidence": "wording is ambiguous",
                        "confidence": "medium",
                    },
                ]
            },
            "manuscript_evidence_locator": {
                "manuscript_evidence_map": [
                    {
                        "concern_id": "concern_clarity",
                        "status": "supported",
                        "section_id": "section_001",
                        "gap": "",
                    },
                    {
                        "concern_id": "concern_method",
                        "status": "partially_supported",
                        "section_id": "section_004",
                        "gap": "no temporal split result",
                    },
                ],
            },
            "evidence_action_planner": {
                "evidence_action_plan": [
                    {
                        "concern_id": "concern_clarity",
                        "action_type": "text_revision",
                        "required_artifact": "clarify wording",
                        "supporting_case_ids": ["case_clarity"],
                        "requires_author_confirmation": False,
                    },
                    {
                        "concern_id": "concern_method",
                        "action_type": "new_analysis",
                        "required_artifact": "temporally held-out split",
                        "supporting_case_ids": ["case_method"],
                        "requires_author_confirmation": True,
                    },
                ],
            },
        },
    }

    report = compose_final_user_report(trace)

    method_card = report["comment_cards"][0]
    clarity_card = report["comment_cards"][1]
    assert method_card["recommended_action"] == "temporally held-out split"
    assert method_card["manuscript_section"] == "section_004"
    assert method_card["supporting_case_ids"] == ["case_method"]
    assert clarity_card["recommended_action"] == "clarify wording"
    assert clarity_card["manuscript_section"] == "section_001"
    assert clarity_card["supporting_case_ids"] == ["case_clarity"]


def test_final_report_accepts_nullable_supporting_case_ids():
    from peer_review_skills.agents.final_report import compose_final_user_report

    trace = {
        "query_unit_id": "case_001",
        "agent_intermediate_outputs": {
            "reviewer_understanding_agent": {
                "concern_map": [
                    {
                        "concern_id": "concern_001",
                        "concern_type": "methodological_transparency",
                        "surface_request": "clarify dataset split",
                        "text_evidence": "dataset split is unclear",
                        "confidence": "high",
                    }
                ]
            },
            "evidence_action_planner": {
                "evidence_action_plan": [
                    {
                        "concern_id": "concern_001",
                        "action_type": "clarify_existing_method",
                        "required_artifact": "dataset split protocol",
                        "supporting_case_ids": None,
                        "requires_author_confirmation": True,
                    }
                ]
            },
        },
    }

    report = compose_final_user_report(trace)

    assert report["comment_cards"][0]["supporting_case_ids"] == []


def test_final_report_does_not_fuzzy_match_prefix_concern_ids():
    from peer_review_skills.agents.final_report import compose_final_user_report

    trace = {
        "query_unit_id": "case_001",
        "agent_intermediate_outputs": {
            "reviewer_understanding_agent": {
                "concern_map": [
                    {
                        "concern_id": "concern_1",
                        "concern_type": "unknown",
                        "surface_request": "first concern",
                        "text_evidence": "first",
                        "confidence": "medium",
                    },
                    {
                        "concern_id": "concern_2",
                        "concern_type": "unknown",
                        "surface_request": "second concern",
                        "text_evidence": "second",
                        "confidence": "medium",
                    }
                ]
            },
            "evidence_action_planner": {
                "evidence_action_plan": [
                    {
                        "notes": "linked to concern_20 only",
                        "action_type": "wrong_prefix_match",
                        "required_artifact": "wrong action",
                        "supporting_case_ids": ["wrong"],
                        "requires_author_confirmation": True,
                    },
                    {
                        "action_type": "correct_index_fallback",
                        "required_artifact": "correct action",
                        "supporting_case_ids": ["right"],
                        "requires_author_confirmation": True,
                    },
                ]
            },
        },
    }

    report = compose_final_user_report(trace)

    assert report["comment_cards"][1]["recommended_action"] == "correct action"
    assert report["comment_cards"][1]["supporting_case_ids"] == ["right"]


def test_final_report_accepts_malformed_optional_integrity_sections():
    from peer_review_skills.agents.final_report import compose_final_user_report

    trace = {
        "query_unit_id": "case_001",
        "agent_intermediate_outputs": {
            "reviewer_understanding_agent": {
                "concern_map": [
                    {
                        "concern_id": "concern_001",
                        "concern_type": "methodological_transparency",
                        "surface_request": "clarify dataset split",
                        "text_evidence": "dataset split is unclear",
                        "confidence": "high",
                    }
                ]
            },
            "integrity_adequacy_checker": {
                "response_adequacy": None,
                "provenance_checks": [],
                "responsible_use_warnings": ["assistant_only"],
            },
        },
    }

    report = compose_final_user_report(trace)

    assert report["recommended_rebuttal_outline"]
    assert "assistant_only" in report["responsible_use_warnings"]


def test_final_report_ignores_non_dict_concern_items():
    from peer_review_skills.agents.final_report import compose_final_user_report

    trace = {
        "query_unit_id": "case_001",
        "agent_intermediate_outputs": {
            "reviewer_understanding_agent": {
                "concern_map": [
                    "malformed concern",
                    {
                        "concern_id": "concern_001",
                        "concern_type": "methodological_transparency",
                        "surface_request": "clarify dataset split",
                        "text_evidence": "dataset split is unclear",
                        "confidence": "high",
                    },
                ]
            }
        },
    }

    report = compose_final_user_report(trace)

    assert len(report["comment_cards"]) == 1
    assert report["comment_cards"][0]["comment_id"] == "comment_001"
    assert report["comment_cards"][0]["surface_request"] == "clarify dataset split"


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
    final_report_path = output_dir / "final_user_report.json"
    final_markdown_path = output_dir / "final_user_report.md"
    assert final_report_path.exists()
    assert final_markdown_path.exists()
    final_report = json.loads(final_report_path.read_text(encoding="utf-8"))
    assert summary["final_user_report_json"] == str(final_report_path)
    assert summary["final_user_report_markdown"] == str(final_markdown_path)
    assert final_report["report_type"] == "author_rebuttal_assistant_report"
    assert final_report["not_final_submission_text"] is True
    assert "assistant_only" in final_report["responsible_use_warnings"]
    assert "最终作者回应辅助报告" in final_markdown_path.read_text(encoding="utf-8")


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


def test_rebuttal_lens_dag_failure_trace_preserves_partial_state(tmp_path):
    manuscript = tmp_path / "manuscript.md"
    manuscript.write_text("## Methods\n\nWe used an 80/10/10 split.\n", encoding="utf-8")
    output_dir = tmp_path / "rebuttal_lens_dag_failure_output"

    with pytest.raises(RuntimeError, match="simulated provider failure"):
        run_rebuttal_lens_workflow(
            project_root=Path.cwd(),
            review_text="The dataset split is unclear.",
            manuscript_path=manuscript,
            model_client=RebuttalLensFailingLLMClient(fail_on_call=3),
            retrieved_cases=[{"unit_id": "case_001", "score": 0.8}],
            taxonomies={},
            config={
                "output_dir": output_dir,
                "agent_max_retries": 1,
                "workflow_engine": "dag",
                "dag_parallel": False,
            },
        )

    failure_trace = json.loads(
        (output_dir / "rebuttal_lens_failure_trace.json").read_text(encoding="utf-8")
    )
    assert failure_trace["status"] == "failed"
    assert failure_trace["partial_trace"]["message_bus"]
    assert failure_trace["partial_trace"]["execution_trace"]
    assert failure_trace["partial_trace"]["agent_intermediate_outputs"]
    assert "api_key" not in json.dumps(failure_trace).lower()


def test_rebuttal_lens_workflow_writes_failure_trace_on_final_report_error(
    tmp_path,
    monkeypatch,
):
    import peer_review_skills.agents.rebuttal_lens_workflow as workflow

    manuscript = tmp_path / "manuscript.md"
    manuscript.write_text("## Methods\n\nWe used an 80/10/10 split.\n", encoding="utf-8")
    output_dir = tmp_path / "rebuttal_lens_report_failure_output"

    def fail_final_report(trace):
        raise RuntimeError("simulated final report failure")

    monkeypatch.setattr(workflow, "compose_final_user_report", fail_final_report)

    with pytest.raises(RuntimeError, match="simulated final report failure"):
        run_rebuttal_lens_workflow(
            project_root=Path.cwd(),
            review_text="The dataset split is unclear.",
            manuscript_path=manuscript,
            model_client=RebuttalLensMockLLMClient(),
            retrieved_cases=[{"unit_id": "case_001", "score": 0.8}],
            taxonomies={},
            config={"output_dir": output_dir},
        )

    failure_trace_path = output_dir / "rebuttal_lens_failure_trace.json"
    assert failure_trace_path.exists()
    failure_trace = json.loads(failure_trace_path.read_text(encoding="utf-8"))
    assert failure_trace["status"] == "failed"
    assert (output_dir / "rebuttal_lens_trace.json").exists()
    assert failure_trace["partial_trace"]["agent_intermediate_outputs"]
    assert failure_trace["partial_trace"]["workflow_version"] == "rebuttal_lens_v1"


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


def test_run_rebuttal_lens_workflow_can_use_dag_committee_and_strategy(tmp_path):
    manuscript = tmp_path / "manuscript.md"
    manuscript.write_text("## Methods\n\nWe used a random paper-level split.\n", encoding="utf-8")
    output_dir = tmp_path / "dag_output"

    summary = run_rebuttal_lens_workflow(
        project_root=Path.cwd(),
        review_text="The temporal split is unclear.",
        response_text="We will clarify.",
        manuscript_path=manuscript,
        model_client=RebuttalLensMockLLMClient(),
        retrieved_cases=[{"unit_id": "case_001", "score": 0.8}],
        taxonomies={},
        config={
            "output_dir": output_dir,
            "workflow_engine": "dag",
            "enable_committee": True,
            "enable_strategy_tournament": True,
        },
    )

    trace = json.loads((output_dir / "rebuttal_lens_trace.json").read_text(encoding="utf-8"))
    outputs = trace["agent_intermediate_outputs"]
    assert summary["workflow_engine"] == "dag"
    assert trace["execution_metadata"]["parallel_execution"] is True
    assert "committee_meta_reviewer" in outputs
    assert "strategy_meta_planner" in outputs
    assert (output_dir / "final_user_report.md").exists()
    assert trace["system_name"] == "Nature RebuttalLens"
    assert trace["workflow_version"] == "rebuttal_lens_v1"
    assert trace["manuscript_context"]["mode"] == "manuscript_aware"
    assert trace["responsible_use_boundary"]["no_confidential_upload_recommendation"] is True
    final_report = json.loads((output_dir / "final_user_report.json").read_text(encoding="utf-8"))
    assert "no_confidential_upload_recommendation" in final_report["responsible_use_warnings"]


def test_final_report_comment_cards_include_nature_response_schema(tmp_path):
    manuscript = tmp_path / "manuscript.md"
    manuscript.write_text("## Methods\n\nWe used an 80/10/10 split.\n", encoding="utf-8")
    output_dir = tmp_path / "schema_report_output"

    run_rebuttal_lens_workflow(
        project_root=Path.cwd(),
        review_text="The dataset split is unclear.",
        manuscript_path=manuscript,
        model_client=RebuttalLensMockLLMClient(),
        retrieved_cases=[{"unit_id": "case_001", "score": 0.8}],
        taxonomies={},
        config={"output_dir": output_dir},
    )

    report = json.loads((output_dir / "final_user_report.json").read_text(encoding="utf-8"))
    card = report["comment_cards"][0]

    for field in [
        "severity",
        "category",
        "proposed_action",
        "readiness",
        "risk_level",
        "missing_author_input",
        "evidence_anchor",
    ]:
        assert field in card
    assert report["package_readiness"] in {
        "ready_to_submit",
        "draft_with_placeholders",
        "needs_author_input",
        "blocked",
    }
    assert report["response_package_gate_issues"] == []


def test_final_report_comment_cards_include_data_and_citation_checks(tmp_path):
    manuscript = tmp_path / "manuscript.md"
    manuscript.write_text("## Data Availability\n\nData are available on request.\n", encoding="utf-8")
    output_dir = tmp_path / "adapter_report_output"

    run_rebuttal_lens_workflow(
        project_root=Path.cwd(),
        review_text="Please provide source data, code availability, and relevant citations.",
        manuscript_path=manuscript,
        model_client=RebuttalLensMockLLMClient(),
        retrieved_cases=[{"unit_id": "case_001", "score": 0.8}],
        taxonomies={},
        config={"output_dir": output_dir},
    )

    report = json.loads((output_dir / "final_user_report.json").read_text(encoding="utf-8"))
    card = report["comment_cards"][0]

    assert "data_availability_check" in card
    assert "citation_support_check" in card
    assert "applies" in card["data_availability_check"]
    assert "support_grade" in card["citation_support_check"]


def test_final_report_passes_evidence_refs_to_citation_support_check():
    from peer_review_skills.agents.final_report import compose_final_user_report

    report = compose_final_user_report({
        "query_unit_id": "case_001",
        "agent_intermediate_outputs": {
            "reviewer_understanding_agent": {
                "concern_map": [
                    {
                        "concern_id": "R1.2",
                        "concern_type": "citation_positioning",
                        "surface_request": "Please cite the relevant prior work.",
                        "text_evidence": "prior work citation missing",
                        "confidence": "high",
                    }
                ]
            },
            "manuscript_evidence_locator": {
                "manuscript_evidence_map": [
                    {
                        "concern_id": "R1.2",
                        "status": "supported",
                        "section_id": "section_003",
                        "evidence_refs": ["doi:10.1234/example"],
                        "evidence_anchor": "doi:10.1234/example",
                        "gap": "",
                    }
                ],
            },
            "evidence_action_planner": {
                "evidence_action_plan": [
                    {
                        "concern_id": "R1.2",
                        "action_type": "literature_repositioning",
                        "required_artifact": "add prior-work citation",
                        "requires_author_confirmation": False,
                    }
                ],
            },
        },
    })

    card = report["comment_cards"][0]
    assert card["evidence_refs"] == ["doi:10.1234/example"]
    assert card["citation_support_check"]["support_grade"] == "supplied_anchor"
    assert card["citation_support_check"]["can_be_used_as_evidence"] is True


def test_final_report_markdown_renderer_is_readable_chinese():
    from peer_review_skills.agents.final_report import render_final_user_report_markdown

    markdown = render_final_user_report_markdown({
        "executive_summary": "系统识别出 1 个 reviewer concern。",
        "package_readiness": "needs_author_input",
        "comment_cards": [
            {
                "comment_id": "R1.1",
                "concern_type": "methodological_transparency",
                "surface_request": "clarify split",
                "implicit_risk": "dataset split is unclear",
                "evidence_status": "partially_supported",
                "manuscript_section": "section_002",
                "evidence_gap": "random seed missing",
                "recommended_action": "dataset split protocol",
                "author_input_required": True,
                "proposed_action": "AUTHOR_INPUT_NEEDED",
                "readiness": "needs_author_input",
                "risk_level": "high",
                "missing_author_input": ["dataset split protocol"],
                "evidence_anchor": "section_002",
                "safe_response_language": "We will clarify after author confirmation.",
                "unsafe_language_to_avoid": "Avoid claiming fully resolved.",
            }
        ],
        "recommended_rebuttal_outline": [],
        "author_confirmation_questions": [],
        "responsible_use_warnings": [],
        "unsafe_claims": [],
    })

    assert "最终作者回应辅助报告" in markdown
    assert "Package readiness" in markdown
    assert "AUTHOR_INPUT_NEEDED" in markdown
    assert "鐨" not in markdown
    assert "锛" not in markdown


def test_nature_response_action_taxonomy_is_loadable():
    path = Path.cwd() / "data/processed/taxonomies/nature_response_action_taxonomy.v1.json"
    taxonomy = json.loads(path.read_text(encoding="utf-8"))

    assert taxonomy["taxonomy_name"] == "nature_response_action_taxonomy"
    assert "AUTHOR_INPUT_NEEDED" in taxonomy["action_labels"]
    assert "blocked" in taxonomy["readiness_states"]


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


def test_optional_rebuttal_lens_agents_apply_per_agent_runtime_config():
    from peer_review_skills.agents.rebuttal_lens_workflow import (
        _create_optional_rebuttal_lens_agents,
    )

    agents = _create_optional_rebuttal_lens_agents(
        RebuttalLensMockLLMClient(),
        {
            "enable_committee": True,
            "enable_strategy_tournament": True,
            "agents": {
                "methodology_committee_reviewer": {
                    "temperature": 0.2,
                    "max_retries": 4,
                },
                "strategy_tournament_agent": {
                    "model": "deepseek-reasoner",
                    "temperature": 0.3,
                    "max_retries": 2,
                },
            },
        },
    )

    committee_agent = agents["methodology_committee_reviewer"]
    strategy_agent = agents["strategy_tournament_agent"]
    assert committee_agent.temperature == 0.2
    assert committee_agent.max_retries == 4
    assert strategy_agent.client.model == "deepseek-reasoner"
    assert strategy_agent.temperature == 0.3
    assert strategy_agent.max_retries == 2


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


def test_merged_rebuttal_lens_config_promotes_public_rebuttal_lens_flags(tmp_path):
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    (config_dir / "multi_agent_config.yaml").write_text(
        """
workflow:
  mode: "rebuttal_lens"
  engine: "dag"

rebuttal_lens:
  enable_committee: true
  enable_strategy_tournament: true
""".strip(),
        encoding="utf-8",
    )

    from peer_review_skills.agents.rebuttal_lens_workflow import (
        _merged_rebuttal_lens_config,
    )

    config = _merged_rebuttal_lens_config(tmp_path, {})

    assert config["workflow_engine"] == "dag"
    assert config["enable_committee"] is True
    assert config["enable_strategy_tournament"] is True


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


def test_reviewer_understanding_prompt_requests_stable_comment_schema():
    from peer_review_skills.agents.specialized_agents import ReviewerUnderstandingAgent

    agent = ReviewerUnderstandingAgent(
        "reviewer_understanding_agent",
        RebuttalLensMockLLMClient(),
    )
    prompt = agent.build_prompt({
        "review_text": "Reviewer 1: The dataset split is unclear.",
        "taxonomies": {},
    })
    system_prompt = prompt[0]["content"]

    assert '"concern_id"' in system_prompt
    assert '"severity"' in system_prompt
    assert '"category"' in system_prompt
    assert "minor|major|blocking|unclear" in system_prompt


def test_manuscript_evidence_prompt_requests_evidence_refs():
    agent = ManuscriptEvidenceLocatorAgent(
        "manuscript_evidence_locator",
        RebuttalLensMockLLMClient(),
    )
    prompt = agent.build_prompt({
        "review_text": "The dataset split is unclear.",
        "concern_map": {"concern_map": [{"concern_id": "R1.1"}]},
        "manuscript_context": {
            "mode": "manuscript_aware",
            "sections": [
                {
                    "section_id": "section_001",
                    "heading": "Methods",
                    "text": "split",
                }
            ],
        },
    })

    assert '"evidence_refs"' in prompt[0]["content"]
    assert '"evidence_anchor"' in prompt[0]["content"]


def test_evidence_action_prompt_includes_nature_action_labels():
    agent = EvidenceActionPlannerAgent(
        "evidence_action_planner",
        RebuttalLensMockLLMClient(),
    )
    prompt = agent.build_prompt({
        "concern_map": {},
        "risk_interpretation": {},
        "retrieved_cases": [],
        "manuscript_evidence": {},
        "case_interpretation": {},
        "taxonomies": {},
    })
    system_prompt = prompt[0]["content"]

    for label in [
        "ACCEPT_TEXT",
        "ACCEPT_ANALYSIS",
        "SOFTEN_CLAIM",
        "AUTHOR_INPUT_NEEDED",
        "BLOCKING",
    ]:
        assert label in system_prompt
    assert '"nature_action_hint"' in system_prompt
    assert '"missing_author_input"' in system_prompt


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


def test_cli_parser_accepts_dag_committee_strategy_flags():
    parser = build_parser()

    args = parser.parse_args([
        "run-rebuttal-lens",
        "--review-file",
        "examples/rebuttal_lens/reviewer_comment.txt",
        "--workflow-engine",
        "dag",
        "--enable-committee",
        "--enable-strategy-tournament",
    ])

    assert args.workflow_engine == "dag"
    assert args.enable_committee is True
    assert args.enable_strategy_tournament is True


def test_cli_omits_unset_rebuttal_lens_flags_so_yaml_defaults_can_apply(monkeypatch):
    captured = {}

    def fake_run_rebuttal_lens_workflow(**kwargs):
        captured.update(kwargs)
        return {"ok": True}

    monkeypatch.setenv("PEER_REVIEW_API_KEY", "test-api-key")
    monkeypatch.setattr(
        "peer_review_skills.agents.rebuttal_lens_workflow.run_rebuttal_lens_workflow",
        fake_run_rebuttal_lens_workflow,
    )

    main([
        "run-rebuttal-lens",
        "--review-file",
        "examples/rebuttal_lens/reviewer_comment.txt",
    ])

    workflow_config = captured["config"]
    assert "workflow_engine" not in workflow_config
    assert "enable_committee" not in workflow_config
    assert "enable_strategy_tournament" not in workflow_config


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
        "final_user_report.json",
        "final_user_report.md",
        "--workflow-engine dag",
        "--enable-committee",
        "--enable-strategy-tournament",
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
