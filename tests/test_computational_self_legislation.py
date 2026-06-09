from peer_review_skills.agents.computational_self_legislation import (
    build_self_legislation,
)


def test_self_legislation_declares_author_boundary():
    payload = build_self_legislation(
        trace={
            "workflow_engine": "dag",
            "agent_intermediate_outputs": {
                "evidence_action_planner": {
                    "evidence_action_plan": [
                        {
                            "required_artifact": "temporal holdout validation result",
                            "requires_author_confirmation": True,
                        }
                    ]
                }
            },
        },
        config={"enable_self_legislation": True},
    )

    assert payload["enabled"] is True
    assert payload["system_may_commit_for_author"] is False
    assert "temporal holdout validation result" in payload["author_confirmation_required_for"]
    assert any("不能替作者承诺" in maxim["maxim_zh"] for maxim in payload["maxims"])


def test_self_legislation_can_be_disabled():
    payload = build_self_legislation(trace={}, config={"enable_self_legislation": False})

    assert payload["enabled"] is False
    assert payload["maxims"] == []
