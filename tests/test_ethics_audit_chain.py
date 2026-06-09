from peer_review_skills.agents.ethics_audit_chain import build_ethics_audit_chain


def test_ethics_audit_chain_surfaces_required_event_classes():
    cards = [
        {
            "comment_id": "R1.1",
            "proposed_action": "ACCEPT_ANALYSIS",
            "readiness": "ready_to_submit",
            "risk_level": "low",
            "evidence_anchor": "Methods",
        },
        {
            "comment_id": "R1.2",
            "proposed_action": "AUTHOR_INPUT_NEEDED",
            "readiness": "decision_deferred",
            "risk_level": "high",
            "missing_author_input": ["temporal split confirmation"],
            "suggestion": "Run temporal validation only if the authors confirm it.",
        },
        {
            "comment_id": "R1.3",
            "proposed_action": "ACCEPT_TEXT",
            "readiness": "ready_to_submit",
            "risk_level": "low",
            "suggestion": "Hide the limitation while revising the Discussion.",
        },
    ]

    audit = build_ethics_audit_chain(
        response_cards=cards,
        memory_runtime={
            "forgetting_ledger": [
                {"memory_class": "author_decision", "action": "forgotten"}
            ]
        },
    )

    assert audit["mechanical_execution_events"]
    assert audit["organic_generation_events"]
    assert audit["active_forgetting_events"] == [
        {"memory_class": "author_decision", "action": "forgotten"}
    ]
    assert audit["deferred_author_decisions"][0]["comment_id"] == "R1.2"
    assert len(audit["universalization_checks"]) == 3
    assert audit["ethical_blocks"][0]["comment_id"] == "R1.3"
    assert "does not make final author decisions" in audit[
        "heteronomy_transparency_statement"
    ]


def test_ethics_audit_chain_can_derive_forgetting_runtime_from_reset_scope():
    audit = build_ethics_audit_chain(
        response_cards=[],
        reset_memory=True,
        memory_policy="strict",
        forget_scope=["latent_commitment"],
    )

    forgotten_classes = {
        event["memory_class"] for event in audit["active_forgetting_events"]
    }

    assert "author_decision" in forgotten_classes
    assert "strategy_preference" in forgotten_classes
    assert "latent_commitment" in forgotten_classes
    assert audit["mechanical_execution_events"][0]["event_type"] == "audit_chain_started"
