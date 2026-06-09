from peer_review_skills.agents.blackbox_transparency import build_blackbox_transparency


def test_blackbox_transparency_summarizes_inputs_boundaries_and_defer():
    trace = {
        "kant_machine_runtime": {
            "reflective_judgment": {
                "mode": "reflective_judgment",
                "readiness": "decision_deferred",
                "category_invention_draft": {"draft_id": "draft_temporal_split"},
            },
            "memory_passport": {
                "retained_memory_types": ["evidence_trace"],
                "forgotten_memory_types": ["author_decision_history"],
            },
        },
        "agent_intermediate_outputs": {
            "reviewer_understanding_agent": {"concern_map": [{"concern_id": "concern_001"}]},
            "manuscript_evidence_locator": {"manuscript_evidence_map": [{"section_id": "section_004"}]},
        },
    }
    report = {
        "package_readiness": "decision_deferred",
        "comment_cards": [{"comment_id": "comment_001", "readiness": "decision_deferred"}],
        "universalization_checks": [{"comment_id": "comment_001", "decision": "defer"}],
    }

    payload = build_blackbox_transparency(
        trace=trace,
        report=report,
        config={"enable_blackbox_transparency": True},
    )

    assert payload["enabled"] is True
    assert "黑箱" in payload["summary_zh"]
    assert payload["deferred_decisions"] == ["comment_001"]
    assert payload["category_generation_events"][0]["draft_id"] == "draft_temporal_split"
    assert "reviewer_understanding_agent" in payload["evidence_inputs"]


def test_blackbox_transparency_disabled_payload_is_empty():
    payload = build_blackbox_transparency(trace={}, report={}, config={})

    assert payload["enabled"] is False
    assert payload["summary_zh"] == ""
