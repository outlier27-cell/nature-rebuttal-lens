from peer_review_skills.agents.unknowability_ledger import build_unknowability_ledger


def test_unknowability_ledger_blocks_future_acceptance_and_reviewer_motive():
    trace = {
        "agent_intermediate_outputs": {
            "strategy_meta_planner": {
                "merged_plan": {
                    "actions": [
                        {
                            "detail": "This will satisfy the reviewer and guarantee acceptance."
                        }
                    ]
                }
            },
            "reviewer_understanding_agent": {
                "concern_map": [
                    {
                        "surface_request": "The reviewer probably wants us to hide the limitation."
                    }
                ]
            },
        }
    }

    payload = build_unknowability_ledger(
        trace=trace,
        config={"enable_unknowability_ledger": True},
    )

    assert payload["enabled"] is True
    assert any(item["boundary_type"] == "future_editorial_outcome" for item in payload["boundaries"])
    assert any(item["boundary_type"] == "reviewer_inner_motive" for item in payload["boundaries"])
    assert len(payload["blocked_inferences"]) >= 2
    assert any("不能预测接收" in question for question in payload["author_questions"])


def test_unknowability_ledger_is_conservative_when_no_trigger():
    payload = build_unknowability_ledger(
        trace={"agent_intermediate_outputs": {}},
        config={"enable_unknowability_ledger": True},
    )

    assert payload["enabled"] is True
    assert payload["boundaries"]
    assert all(item["status"] in {"standing_boundary", "triggered"} for item in payload["boundaries"])
