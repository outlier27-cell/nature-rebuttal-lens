from peer_review_skills.agents.organic_quality import build_organic_quality


def test_organic_quality_scores_grounded_reflective_category():
    runtime = {
        "reflective_judgment": {
            "mode": "reflective_judgment",
            "readiness": "decision_deferred",
            "category_invention_draft": {
                "draft_id": "draft_temporal_validation",
                "requires_independent_confirmation": True,
            },
        },
        "heteronomy_boundary": {
            "derived_categories_are_forgetting_eligible": True,
            "category_generation_requires_author_confirmation": True,
        },
    }
    report = {
        "comment_cards": [
            {
                "comment_id": "comment_001",
                "evidence_gap": "temporal validation missing",
                "proposed_action": "AUTHOR_INPUT_NEEDED",
                "readiness": "decision_deferred",
            }
        ],
        "universalization_checks": [{"decision": "defer", "universalizable": True}],
    }

    payload = build_organic_quality(
        runtime=runtime,
        report=report,
        config={"enable_organic_quality": True},
    )

    assert payload["enabled"] is True
    assert payload["score"] >= 0.8
    assert all(check["passed"] for check in payload["checks"])


def test_organic_quality_penalizes_ungrounded_category():
    runtime = {
        "reflective_judgment": {
            "mode": "reflective_judgment",
            "category_invention_draft": {"draft_id": "draft_without_boundary"},
        },
        "heteronomy_boundary": {},
    }
    report = {"comment_cards": [], "universalization_checks": []}

    payload = build_organic_quality(
        runtime=runtime,
        report=report,
        config={"enable_organic_quality": True},
    )

    assert payload["enabled"] is True
    assert payload["score"] < 0.8
    assert any(not check["passed"] for check in payload["checks"])
