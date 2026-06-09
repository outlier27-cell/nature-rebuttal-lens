from peer_review_skills.agents.universalization_gate import (
    UniversalizationDecision,
    check_universalization,
)


def test_decision_vocabulary_includes_defer():
    assert UniversalizationDecision.ALLOW.value == "allow"
    assert UniversalizationDecision.WARN.value == "warn"
    assert UniversalizationDecision.BLOCK.value == "block"
    assert UniversalizationDecision.DEFER.value == "defer"


def test_blocks_universalized_deceptive_suggestions():
    checks = [
        check_universalization({"suggestion": "Exaggerate the novelty beyond the evidence."}),
        check_universalization({"suggestion": "Hide the limitation in the appendix."}),
        check_universalization({"suggestion": "Fabricate an ablation we did not run."}),
        check_universalization({"suggestion": "Make up a robustness result."}),
        check_universalization({"suggestion": "Pretend the authors already confirmed the data split."}),
    ]

    assert [check["decision"] for check in checks] == ["block"] * 5
    assert all(check["universalizable"] is False for check in checks)


def test_defers_decision_deferred_or_high_risk_author_input_needed():
    deferred_readiness = check_universalization(
        {
            "comment_id": "R1.1",
            "proposed_action": "ACCEPT_ANALYSIS",
            "readiness": "decision_deferred",
            "risk_level": "medium",
        }
    )
    high_risk_author_input = check_universalization(
        {
            "comment_id": "R1.2",
            "proposed_action": "AUTHOR_INPUT_NEEDED",
            "readiness": "needs_author_input",
            "risk_level": "high",
        }
    )

    assert deferred_readiness["decision"] == "defer"
    assert high_risk_author_input["decision"] == "defer"
    assert deferred_readiness["requires_author_decision"] is True
    assert high_risk_author_input["requires_author_decision"] is True


def test_allows_bounded_non_deceptive_action_labels():
    for action in [
        "SOFTEN_CLAIM",
        "CLARIFY_EXISTING",
        "ACCEPT_ANALYSIS",
        "ACCEPT_TEXT",
    ]:
        check = check_universalization({"comment_id": action, "proposed_action": action})
        assert check["decision"] == "allow"
        assert check["universalizable"] is True


def test_warns_for_unrecognized_or_partial_actions():
    check = check_universalization(
        {
            "comment_id": "R1.3",
            "proposed_action": "ADD_CITATION",
            "suggestion": "Add a related work citation if supported.",
        }
    )

    assert check["decision"] == "warn"
    assert check["universalizable"] is None


def test_does_not_block_when_overstatement_is_only_diagnostic_context():
    check = check_universalization(
        {
            "comment_id": "R1.4",
            "proposed_action": "AUTHOR_INPUT_NEEDED",
            "readiness": "needs_author_input",
            "risk_level": "low",
            "recommended_action": "Run a temporally held-out split before broad claims.",
            "evidence_gap": "The current generalization claim may be overstated.",
            "unsafe_language_to_avoid": "Avoid overstating implications beyond the evidence.",
        }
    )

    assert check["decision"] == "warn"
    assert check["universalizable"] is None


def test_does_not_block_safe_avoid_overstating_action_text():
    check = check_universalization(
        {
            "comment_id": "R1.5",
            "proposed_action": "SOFTEN_CLAIM",
            "readiness": "ready_to_submit",
            "risk_level": "low",
            "suggestion": "Avoid overstating implications beyond the supplied evidence.",
        }
    )

    assert check["decision"] == "allow"
    assert check["universalizable"] is True
