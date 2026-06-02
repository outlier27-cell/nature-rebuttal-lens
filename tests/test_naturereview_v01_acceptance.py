import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from peer_review_skills.execution import build_naturereview_v01 as builder
from peer_review_skills.cli.main import build_parser
from peer_review_skills.agents.orchestrator import AnnotationAgent, run_agent_workflow
from peer_review_skills.agents.providers import DEFAULT_OPENAI_COMPATIBLE_MODEL, ExternalAPIProvider, RuleBasedProvider


@pytest.fixture(scope="session", autouse=True)
def regenerate_naturereview_v01_outputs():
    env = os.environ.copy()
    src_path = str(ROOT / "src")
    env["PYTHONPATH"] = src_path + os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else src_path
    subprocess.run(
        [sys.executable, "-m", "peer_review_skills.cli.main", "build-naturereview-v01"],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    subprocess.run(
        [sys.executable, "-m", "peer_review_skills.cli.main", "validate-naturereview-v01"],
        cwd=ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )


def read_json(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def read_jsonl(path: str):
    return [
        json.loads(line)
        for line in (ROOT / path).read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_evaluation_protocol_defines_each_task_contract():
    required_sections = [
        "Review concern extraction",
        "Risk point classification",
        "Author response strategy retrieval",
        "Evidence recommendation",
        "Rebuttal outline generation",
        "Tone / structure revision",
        "Decision-aware case retrieval",
        "Tacit concern interpretation",
        "Institutional positioning assessment",
        "Actor-network case retrieval",
        "Cognitive trace quality assessment",
    ]
    tasks = {task["name"]: task for task in builder.EVALUATION_TASKS}

    for section in required_sections:
        assert section in tasks
    for task in tasks.values():
        for field in ["input", "output", "supervision", "automatic", "human", "baselines", "failures"]:
            assert task.get(field)


def test_retrieval_report_contains_required_plan_metrics_and_p1_comparison():
    summary = read_json("data/evaluation/retrieval_v2/retrieval_v2_summary.json")
    metrics = summary["metrics"]
    for metric in [
        "strategy_recall_at_1",
        "strategy_recall_at_3",
        "strategy_recall_at_5",
        "concern_match_at_5",
        "joint_strategy_concern_at_5",
        "case_diversity_at_5",
        "provenance_completeness",
    ]:
        assert metric in metrics
    assert "p1_baseline_comparison" in summary
    assert "improvement_attribution" in summary
    assert "p1_baseline_comparison" in summary
    assert "strategy_recall_at_1" in json.dumps(summary, ensure_ascii=False)
    assert "provenance_completeness" in json.dumps(summary, ensure_ascii=False)
    advice_boundary_text = json.dumps(summary["improvement_attribution"], ensure_ascii=False).lower()
    for marker in ["keyword", "lexical-overlap", "rule-based", "rule matching", "规则匹配"]:
        assert marker not in advice_boundary_text


def test_validation_covers_plan_critical_acceptance_criteria():
    validation = read_json("data/evaluation/naturereview_v01_validation_summary.json")
    checks = {check["name"]: check["status"] for check in validation["checks"]}
    for required_check in [
        "Evaluation protocol task contracts are complete",
        "Retrieval report includes P1 comparison",
        "Retrieval metrics include R@1 R@3 and provenance completeness",
        "README includes public license and boundary notes",
        "Workflow traces include agent intermediate outputs",
        "API seed review results are complete",
        "Non-training open-source scope is explicit",
        "Cross-disciplinary design lenses are documented",
        "Workflow traces include cross-disciplinary lens map",
        "Simulation traces include cross-disciplinary evaluation",
        "Agnes workflow advice path has no rule or lexical leakage",
    ]:
        assert checks.get(required_check) == "PASS"
    assert validation["api_handoff_status"] == "executed"
    assert validation["counts"]["cross_disciplinary_lens_trace_count"] == 50


def test_workflow_traces_include_agent_intermediate_outputs():
    traces = read_jsonl("data/evaluation/workflow_v2/workflow_traces.jsonl")
    assert traces
    for trace in traces:
        outputs = trace.get("agent_intermediate_outputs")
        assert isinstance(outputs, dict)
        for agent in [
            "reviewer_understanding_agent",
            "tacit_concern_interpreter",
            "institutional_signal_interpreter",
            "evidence_action_planner",
            "author_positioning_agent",
            "tone_commitment_calibrator",
            "actor_network_mapper",
            "integrity_adequacy_checker",
        ]:
            assert agent in outputs


def test_mojibake_scan_covers_generator_and_readme(monkeypatch):
    source_file = ROOT / "src/peer_review_skills/execution/build_naturereview_v01.py"
    readme = ROOT / "README.md"

    monkeypatch.setattr(builder, "_iter_text_files", lambda roots: [source_file, readme])
    monkeypatch.setattr(builder, "MOJIBAKE_MARKERS", ["import ", "Nature RebuttalLens"])

    hits = builder._scan_mojibake_hits()
    files = {hit["file"] for hit in hits}

    assert "src/peer_review_skills/execution/build_naturereview_v01.py" in files
    assert "README.md" in files


def test_secret_scan_covers_source_and_tests(monkeypatch):
    captured_roots = []

    def fake_iter_text_files(roots):
        captured_roots.extend(Path(root).relative_to(ROOT).as_posix() for root in roots)
        return []

    monkeypatch.setattr(builder, "_iter_text_files", fake_iter_text_files)

    assert builder._scan_secret_hits() == []
    assert "src/peer_review_skills" in captured_roots
    assert "tests" in captured_roots


def test_public_agent_cli_defaults_to_model_provider_not_rule_provider():
    parser = build_parser()
    args = parser.parse_args(["run-agents"])

    assert args.provider == "external-api"
    assert DEFAULT_OPENAI_COMPATIBLE_MODEL == "deepseek-v3"


def test_public_agent_cli_rejects_rule_provider():
    parser = build_parser()

    with pytest.raises(SystemExit):
        parser.parse_args(["run-agents", "--provider", "rule-based"])


def test_legacy_annotation_agent_does_not_run_under_public_model_provider(tmp_path):
    provider = ExternalAPIProvider(base_url="https://xh.v1api.cc", api_key_env="PEER_REVIEW_API_KEY", model="deepseek-v3")

    with pytest.raises(ValueError, match="legacy annotation"):
        AnnotationAgent(provider).run(tmp_path, "mvp")


def test_external_api_provider_reads_timeout_retry_count(monkeypatch):
    monkeypatch.setenv("PEER_REVIEW_API_KEY", "test-key")
    monkeypatch.setenv("PEER_REVIEW_API_TIMEOUT_SECONDS", "45")
    monkeypatch.setenv("PEER_REVIEW_API_TIMEOUT_RETRY_COUNT", "2")

    provider = ExternalAPIProvider(
        base_url="https://xh.v1api.cc",
        api_key_env="PEER_REVIEW_API_KEY",
        model="deepseek-v3",
    )
    client = provider.create_client()

    assert client.timeout_seconds == 45
    assert client.timeout_retry_count == 2


def test_external_api_provider_rejects_invalid_timeout_retry_count(monkeypatch):
    monkeypatch.setenv("PEER_REVIEW_API_KEY", "test-key")
    monkeypatch.setenv("PEER_REVIEW_API_TIMEOUT_RETRY_COUNT", "-1")

    provider = ExternalAPIProvider(
        base_url="https://xh.v1api.cc",
        api_key_env="PEER_REVIEW_API_KEY",
        model="deepseek-v3",
    )

    with pytest.raises(ValueError, match="PEER_REVIEW_API_TIMEOUT_RETRY_COUNT"):
        provider.create_client()


def test_python_agent_workflow_requires_explicit_legacy_baseline_flag(tmp_path):
    with pytest.raises(ValueError, match="allow_legacy_baseline"):
        run_agent_workflow(
            tmp_path,
            provider=RuleBasedProvider(),
            skip_normalize=True,
            skip_segment=True,
            skip_annotate=True,
        )


def test_python_agent_workflow_allows_explicit_legacy_baseline_for_research(tmp_path):
    (tmp_path / "data/processed/annotations").mkdir(parents=True)
    (tmp_path / "data/processed/interaction_units").mkdir(parents=True)
    (tmp_path / "data/processed/annotations/reviewer_annotations.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "data/processed/annotations/author_annotations.jsonl").write_text("", encoding="utf-8")
    (tmp_path / "data/processed/interaction_units/interaction_units.jsonl").write_text("", encoding="utf-8")

    result = run_agent_workflow(
        tmp_path,
        provider=RuleBasedProvider(),
        skip_normalize=True,
        skip_segment=True,
        skip_annotate=True,
        allow_legacy_baseline=True,
    )

    assert result["provider"] == "rule_based"


def test_api_handoff_manifest_reflects_executed_seed_review():
    manifest = read_json("data/evaluation/api_handoff/naturereview_v01/manifest.json")
    assert manifest["status"] == "executed"
    assert manifest["result_count"] == 200
    assert manifest["error_count"] == 0
    assert manifest["label_status"] == "model_assisted_not_human_gold"


def test_legacy_model_assisted_training_seed_export_is_optional_not_core():
    summary = read_json("data/training/author_rebuttal_agent/v2709/training_seed_summary.json")
    rows = read_jsonl("data/training/author_rebuttal_agent/v2709/model_assisted_training_seed_200.jsonl")

    assert summary["row_count"] == 200
    assert summary["label_status"] == "model_assisted_not_human_gold"
    assert summary["core_release_scope"] == "legacy_optional_non_core"
    assert summary["provenance_complete_rate"] == 1.0
    assert rows
    for field in [
        "training_example_id",
        "input",
        "targets",
        "learning_tasks",
        "provenance",
        "label_source",
        "label_status",
        "safety_boundaries",
    ]:
        assert field in rows[0]
    assert "response_adequacy" in rows[0]["targets"]
    assert "unsupported_commitment_detection" in rows[0]["learning_tasks"]


def test_generated_readme_uses_nature_rebuttal_lens_public_name():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    assert readme.startswith("# Nature RebuttalLens")
    assert "Nature RebuttalLens is a manuscript-aware" in readme
    assert "not affiliated with, endorsed by, or operated by Nature Portfolio or Springer Nature" in readme
    assert "run-rebuttal-lens" in readme
    assert "NatureReview-Interact is a non-training" not in readme


def test_retrieval_predictions_include_case_explanations_without_strategy_leakage():
    predictions = read_jsonl("data/evaluation/retrieval_v2/predictions.jsonl")
    assert predictions
    first = predictions[0]
    assert "query_strategy_label_used_for_ranking" in first
    assert first["query_strategy_label_used_for_ranking"] is False
    assert "case_explanations" in first
    assert len(first["case_explanations"]) == len(first["top_k"])
    explanation = first["case_explanations"][0]
    for field in [
        "unit_id",
        "why_relevant",
        "matched_signals",
        "transferable_pattern",
        "provenance",
    ]:
        assert field in explanation
    assert "response_strategy" not in explanation["matched_signals"].get("ranking_features", [])


def test_workflow_traces_have_case_specific_planning_and_adequacy_checks():
    traces = read_jsonl("data/evaluation/workflow_v2/workflow_traces.jsonl")
    assert traces
    trace = traces[0]
    cognitive = trace["cognitive_trace"]

    assert "case_explanations" in trace
    assert trace["case_explanations"]
    assert "rebuttal_plan" in cognitive["output"]
    assert "author_confirmation_questions" in cognitive["evidence_plan"]
    assert "response_adequacy" in cognitive["integrity_check"]

    evidence_item = cognitive["evidence_plan"]["evidence_action_plan"][0]
    for field in ["action_type", "required_artifact", "feasibility", "author_must_confirm", "overclaim_risk"]:
        assert field in evidence_item
    assert evidence_item["action_type"] != "unknown"

    adequacy = cognitive["integrity_check"]["response_adequacy"]
    for field in ["coverage_status", "unresolved_concerns", "missing_evidence_actions", "adequacy_rationale"]:
        assert field in adequacy
    assert adequacy["coverage_status"] in {"covered", "partially_covered", "not_covered", "needs_author_confirmation"}

    plan_sections = cognitive["output"]["rebuttal_plan"]["sections"]
    assert plan_sections
    assert any("reviewer concern" in section["purpose"].lower() for section in plan_sections)
    assert trace["outline"] != [
        "Acknowledge the concern.",
        "State what evidence or revision addresses it.",
        "Clarify remaining limitations without overclaiming.",
    ]


def test_workflow_traces_include_cross_disciplinary_lens_map():
    traces = read_jsonl("data/evaluation/workflow_v2/workflow_traces.jsonl")
    assert traces
    required_lenses = [
        "tacit_knowledge_boundary",
        "institutional_dependence",
        "actor_network_alignment",
        "fast_slow_cognitive_correction",
        "emotion_tone_commitment_calibration",
        "author_agency_gate",
    ]
    for trace in traces:
        lens_map = trace.get("cross_disciplinary_lens_map")
        assert isinstance(lens_map, dict)
        for lens in required_lenses:
            assert lens in lens_map
            item = lens_map[lens]
            for field in ["source_pdf", "observable_trace", "system_action", "boundary", "evaluation_question"]:
                assert item.get(field), (lens, field)
            boundary = item["boundary"]
            assert (
                "Do not infer" in boundary
                or "confirmation" in boundary
                or "does not replace" in boundary
                or "Do not generate" in boundary
                or "Do not diagnose" in boundary
                or "Do not predict" in boundary
                or "Do not reconstruct" in boundary
            )


def test_executed_api_results_are_applied_after_regeneration():
    manifest = read_json("data/evaluation/api_handoff/naturereview_v01/manifest.json")
    seed_summary = read_json("data/evaluation/seed_set/v1/seed_model_reviewed_summary.json")
    kb_summary = read_json("data/processed/review_interaction_kb/v1/kb_summary.json")
    if manifest["status"] != "executed":
        pytest.skip("API seed review has not been executed in this workspace")

    assert seed_summary["label_source_counts"] == {"model_assisted": 200}
    assert kb_summary["label_source_counts"]["model_assisted"] >= 200


def test_retrieval_v2_ranking_does_not_use_query_strategy_label(monkeypatch):
    fake_p1_summary = {
        "best_by_metric": {},
        "methods": {},
    }
    monkeypatch.setattr(builder, "_read_json", lambda path: fake_p1_summary)

    def unit(unit_id, review_text, concern, institutional_signal, strategy):
        return {
            "unit_id": unit_id,
            "paper_id": unit_id,
            "review_text": review_text,
            "concern_type": concern,
            "institutional_signal": institutional_signal,
            "response_strategy": strategy,
            "evidence_action": "clarification",
            "provenance": {"source_file": f"{unit_id}.json"},
        }

    units = [
        unit("query", "alpha beta", "clarity_presentation", "presentation_standard", "same_strategy"),
        unit("same_strategy_low_text_match", "alpha", "baseline_comparison", "community_norm_expectation", "same_strategy"),
        unit("different_strategy_high_text_match", "alpha beta", "clarity_presentation", "presentation_standard", "different_strategy"),
    ]

    predictions, summary = builder._build_retrieval_v2(units)
    first_prediction = predictions[0]

    assert first_prediction["top_k"][0]["unit_id"] == "different_strategy_high_text_match"
    assert all("response_strategy bonus" not in note for note in first_prediction["retrieval_signal_notes"])
    assert "response_strategy bonus" not in json.dumps(summary["improvement_attribution"])
    assert "lexical" not in json.dumps(first_prediction["case_explanations"]).lower()


def test_case_explanation_does_not_claim_label_match_when_labels_differ():
    query = {
        "unit_id": "query",
        "paper_id": "paper-query",
        "concern_type": "clarity_presentation",
        "risk_type": "communication_clarity",
        "institutional_signal": "presentation_standard",
    }
    candidate = {
        "unit_id": "candidate",
        "paper_id": "paper-candidate",
        "concern_type": "baseline_comparison",
        "risk_type": "comparative_validity",
        "institutional_signal": "community_norm_expectation",
        "response_strategy": "add_new_analysis",
        "evidence_action": "new_analysis",
        "author_positioning": "accept_and_revise",
        "tone_commitment": {},
        "actor_links": [],
        "provenance": {"source_file": "candidate.json"},
    }

    explanation = builder._case_explanation(query, candidate)

    assert explanation["matched_signals"]["concern_type"] is None
    assert explanation["matched_signals"]["institutional_signal"] is None
    assert "shares concern" not in explanation["why_relevant"]
    assert "shares institutional_signal" not in explanation["why_relevant"]
    assert "no label match is claimed" in explanation["why_relevant"]


def test_advice_evidence_action_does_not_use_keyword_fallback():
    unit = {
        "unit_id": "query",
        "paper_id": "paper-query",
        "review_text": "The word baseline appears here, but the reviewed model label did not identify an evidence action.",
        "response_text": "The response mentions code and data only as background words.",
        "concern_type": "clarity_presentation",
        "risk_type": "communication_clarity",
        "response_strategy": "acknowledge_and_fix",
        "evidence_action": "unknown",
        "label_source": "model_assisted",
        "author_positioning": "accept_and_revise",
        "tone_commitment": {"tone": "cooperative", "commitment_level": "completed_change", "risk_flags": ["none"]},
        "actor_links": [],
        "provenance": {"source_file": "paper-query.json"},
    }
    pred = {
        "case_explanations": [
            {
                "unit_id": "case-1",
                "transferable_pattern": {"evidence_action": "new_analysis", "label_source": "model_assisted"},
                "matched_signals": {"concern_type": "clarity_presentation"},
            },
            {
                "unit_id": "case-2",
                "transferable_pattern": {"evidence_action": "new_analysis", "label_source": "model_assisted"},
                "matched_signals": {"risk_type": "communication_clarity"},
            },
        ]
    }

    evidence_plan = builder._build_evidence_action_plan(unit, pred)
    item = evidence_plan[0]

    assert item["action_type"] == "new_analysis"
    assert item["decision_basis"]["basis_type"] == "case_derived"
    assert "baseline" not in json.dumps(item["decision_basis"]).lower()
    assert "keyword" not in json.dumps(item).lower()
    assert "rule" not in json.dumps(item).lower()


def test_response_adequacy_does_not_mark_covered_from_term_hits_only():
    unit = {
        "unit_id": "query",
        "concern_type": "baseline_comparison",
        "response_strategy": "acknowledge_and_fix",
        "evidence_action": "unknown",
        "response_text": "We mention baseline, table, code, data, figure and experiment, but no model-reviewed adequacy field exists.",
    }
    evidence_plan = [
        {
            "action_type": "new_analysis",
            "decision_basis": {"basis_type": "case_derived", "supporting_case_ids": ["case-1", "case-2"]},
        }
    ]

    adequacy = builder._assess_response_adequacy(unit, evidence_plan)

    assert adequacy["coverage_status"] == "needs_author_confirmation"
    assert adequacy["decision_basis"]["basis_type"] == "insufficient_model_or_case_adequacy_signal"
    assert "checked whether response text contains cues" not in adequacy["adequacy_rationale"]
    assert "keyword" not in json.dumps(adequacy).lower()
    assert "rule" not in json.dumps(adequacy).lower()


def test_workflow_advice_traces_do_not_expose_lexical_or_rule_basis():
    traces = read_jsonl("data/evaluation/workflow_v2/workflow_traces.jsonl")
    assert traces
    advice_text = "\n".join(
        json.dumps(
            {
                "case_explanations": trace.get("case_explanations"),
                "case_selection_basis": trace.get("case_selection_basis"),
                "cognitive_trace": trace.get("cognitive_trace"),
                "outline": trace.get("outline"),
                "cross_disciplinary_lens_map": trace.get("cross_disciplinary_lens_map"),
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        for trace in traces
    ).lower()

    forbidden = [
        "lexical_overlap",
        "lexical or fallback retrieval signal",
        "text_similarity_signal",
        "checked whether response text contains cues",
        "keyword",
        "rule-based",
        "rule matching",
    ]
    for marker in forbidden:
        assert marker not in advice_text


def test_api_seed_review_result_merges_as_model_assisted_not_human_gold():
    seed = {
        "seed_review_id": "seed_review_v1_0001",
        "concern_type": "clarity_presentation",
        "response_strategy": "acknowledge_and_fix",
        "evidence_action": "unknown",
        "tacit_concern": "presentation_as_epistemic_signal",
        "institutional_signal": "presentation_standard",
        "author_positioning": "accept_and_revise",
        "tone_commitment": {"tone": "cooperative", "commitment_level": "completed_change", "risk_flags": ["none"]},
        "actor_links": [],
        "label_source": "heuristic_model_ready",
        "human_confirmation_status": "needs_human_confirmation",
    }
    api_record = {
        "request_id": "naturereview_seed_review::seed_review_v1_0001",
        "model": "deepseek-v3",
        "model_result": {
            "alignment_correct": "yes",
            "usable_for_retrieval": "yes",
            "usable_for_evaluation": "yes",
            "revised_concern_type": "baseline_comparison",
            "revised_tacit_concern": "community_standard_fit",
            "revised_institutional_signal": "community_norm_expectation",
            "revised_response_strategy": "add_new_analysis",
            "revised_evidence_action": "new_analysis",
            "revised_author_positioning": "accept_and_revise",
            "tone_commitment": {"tone": "cooperative", "commitment_level": "completed_change", "risk_flags": ["none"]},
            "actor_links": [
                {"actor_type": "benchmark", "role_in_interaction": "community-standard comparison object", "evidence": "baseline"}
            ],
            "rationale": "The reviewer asks for a stronger baseline comparison and the response adds analysis.",
        },
    }

    merged = builder._merge_seed_api_review_result(seed, api_record)

    assert merged["label_source"] == "model_assisted"
    assert merged["human_confirmation_status"] == "needs_human_confirmation"
    assert merged["api_review_status"] == "reviewed"
    assert merged["api_review_model"] == "deepseek-v3"
    assert merged["concern_type"] == "baseline_comparison"
    assert merged["response_strategy"] == "add_new_analysis"
    assert merged["evidence_action"] == "new_analysis"
    assert merged["model_rationale"].startswith("The reviewer asks")
    assert merged["actor_links"][0]["actor_type"] == "benchmark"


def test_seed_api_runner_writes_results_with_fake_client(monkeypatch, tmp_path):
    requests_dir = tmp_path / "handoff"
    results_dir = tmp_path / "results"
    requests_dir.mkdir(parents=True)
    request = {
        "request_id": "naturereview_seed_review::seed_review_v1_0001",
        "task": "review_interaction_seed_cross_disciplinary_review",
        "input": {
            "seed_review_id": "seed_review_v1_0001",
            "pair_id": "pair-1",
            "paper_id": "paper-1",
            "review_text": "Please add a stronger baseline.",
            "response_text": "We added a baseline comparison.",
            "candidate_labels": {},
        },
        "expected_output_schema": {},
        "safety_constraints": [],
    }
    (requests_dir / "seed_review_requests.jsonl").write_text(json.dumps(request, ensure_ascii=False) + "\n", encoding="utf-8")

    class FakeClient:
        def create_chat_completion(self, messages, *, response_format=None, temperature=0.0):
            return {
                "alignment_correct": "yes",
                "usable_for_retrieval": "yes",
                "usable_for_evaluation": "yes",
                "revised_concern_type": "baseline_comparison",
                "revised_tacit_concern": "community_standard_fit",
                "revised_institutional_signal": "community_norm_expectation",
                "revised_response_strategy": "add_new_analysis",
                "revised_evidence_action": "new_analysis",
                "revised_author_positioning": "accept_and_revise",
                "tone_commitment": {"tone": "cooperative", "commitment_level": "completed_change", "risk_flags": ["none"]},
                "actor_links": [
                    {"actor_type": "benchmark", "role_in_interaction": "community-standard comparison object", "evidence": "baseline"}
                ],
                "rationale": "The review asks for stronger baseline comparison.",
            }

    monkeypatch.setattr(builder, "NATUREREVIEW_API_HANDOFF_DIR", requests_dir)
    monkeypatch.setattr(builder, "NATUREREVIEW_API_RESULTS_DIR", results_dir)

    summary = builder._run_naturereview_seed_api_review(FakeClient(), model="deepseek-v3", limit=1)
    results = read_jsonl(str(results_dir.relative_to(ROOT) / "seed_review_results.jsonl")) if results_dir.is_relative_to(ROOT) else [
        json.loads(line) for line in (results_dir / "seed_review_results.jsonl").read_text(encoding="utf-8").splitlines()
    ]

    assert summary["new_result_count"] == 1
    assert summary["new_error_count"] == 0
    assert results[0]["model_result"]["revised_concern_type"] == "baseline_comparison"


def test_seed_api_normalizer_accepts_nested_model_result():
    nested = {
        "result": {
            "alignment_correct": "yes",
            "usable_for_retrieval": "yes",
            "usable_for_evaluation": "yes",
            "revised_concern_type": "baseline_comparison",
            "revised_tacit_concern": "community_standard_fit",
            "revised_institutional_signal": "community_norm_expectation",
            "revised_response_strategy": "add_new_analysis",
            "revised_evidence_action": "new_analysis",
            "revised_author_positioning": "accept_and_revise",
            "tone_commitment": {"tone": "cooperative", "commitment_level": "completed_change", "risk_flags": ["none"]},
            "actor_links": [],
            "rationale": "Grounded in observable text.",
        }
    }

    result = builder._normalize_seed_review_result(nested)

    assert result["revised_concern_type"] == "baseline_comparison"


def test_successful_seed_api_retry_removes_stale_error(monkeypatch, tmp_path):
    requests_dir = tmp_path / "handoff"
    results_dir = tmp_path / "results"
    requests_dir.mkdir(parents=True)
    request = {
        "request_id": "naturereview_seed_review::seed_review_v1_0001",
        "task": "review_interaction_seed_cross_disciplinary_review",
        "input": {"seed_review_id": "seed_review_v1_0001", "pair_id": "pair-1", "paper_id": "paper-1"},
        "expected_output_schema": {},
        "safety_constraints": [],
    }
    (requests_dir / "seed_review_requests.jsonl").write_text(json.dumps(request, ensure_ascii=False) + "\n", encoding="utf-8")
    (results_dir / "seed_review_errors.jsonl").parent.mkdir(parents=True)
    (results_dir / "seed_review_errors.jsonl").write_text(
        json.dumps({"request_id": request["request_id"], "error": "old failure"}, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    class FakeClient:
        def create_chat_completion(self, messages, *, response_format=None, temperature=0.0):
            return {
                "alignment_correct": "yes",
                "usable_for_retrieval": "yes",
                "usable_for_evaluation": "yes",
                "revised_concern_type": "baseline_comparison",
                "revised_tacit_concern": "community_standard_fit",
                "revised_institutional_signal": "community_norm_expectation",
                "revised_response_strategy": "add_new_analysis",
                "revised_evidence_action": "new_analysis",
                "revised_author_positioning": "accept_and_revise",
                "tone_commitment": {"tone": "cooperative", "commitment_level": "completed_change", "risk_flags": ["none"]},
                "actor_links": [],
                "rationale": "Grounded in observable text.",
            }

    monkeypatch.setattr(builder, "NATUREREVIEW_API_HANDOFF_DIR", requests_dir)
    monkeypatch.setattr(builder, "NATUREREVIEW_API_RESULTS_DIR", results_dir)

    summary = builder._run_naturereview_seed_api_review(FakeClient(), model="deepseek-v3", limit=1)
    errors = [json.loads(line) for line in (results_dir / "seed_review_errors.jsonl").read_text(encoding="utf-8").splitlines() if line]

    assert summary["cumulative_result_count"] == 1
    assert summary["cumulative_error_count"] == 0
    assert errors == []
