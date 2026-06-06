from peer_review_skills.agents.memory_ethics import (
    MEMORY_OBJECT_TAXONOMY,
    build_memory_ethics_runtime,
    filter_runtime_memory,
)


def test_memory_taxonomy_marks_decision_and_preference_as_forgettable():
    assert MEMORY_OBJECT_TAXONOMY["evidence_trace"]["default_action"] == "retain"
    assert MEMORY_OBJECT_TAXONOMY["reasoning_trace"]["default_action"] == "retain"
    assert MEMORY_OBJECT_TAXONOMY["author_decision"]["default_action"] == "forget"
    assert MEMORY_OBJECT_TAXONOMY["strategy_preference"]["default_action"] == "forget"
    assert MEMORY_OBJECT_TAXONOMY["final_wording"]["default_action"] == "forget"


def test_default_runtime_records_forgetting_as_memory_boundary():
    runtime = build_memory_ethics_runtime(reset_memory=False)

    assert runtime["memory_passport"]["policy"] == "default"
    assert runtime["memory_passport"]["irreversible_forgetting"] is True
    assert runtime["memory_passport"]["retained_memory_classes"] == [
        "evidence_trace",
        "reasoning_trace",
        "audit_trace",
    ]
    assert "author_decision" in runtime["memory_passport"]["forgotten_memory_classes"]
    assert "strategy_preference" in runtime["memory_passport"]["forgotten_memory_classes"]
    assert runtime["forgetting_ledger"][0]["memory_class"] == "author_decision"
    assert runtime["forgetting_ledger"][0]["action"] == "forgotten"
    assert runtime["irreversible_forgetting_statement"]["author_decision"].startswith(
        "Forgotten author decisions must not be reconstructed"
    )


def test_filter_runtime_memory_removes_stale_author_decisions():
    memory = {
        "evidence_trace": [{"evidence_ref": "section_002"}],
        "reasoning_trace": [{"reason": "split evidence is incomplete"}],
        "author_decision": [{"decision": "promise new temporal validation"}],
        "strategy_preference": [{"strategy": "defend_without_revision"}],
        "final_wording": [{"text": "We have completed all requested experiments."}],
    }

    filtered = filter_runtime_memory(memory, memory_policy="default")

    assert "evidence_trace" in filtered
    assert "reasoning_trace" in filtered
    assert "author_decision" not in filtered
    assert "strategy_preference" not in filtered
    assert "final_wording" not in filtered


def test_filter_runtime_memory_never_reinjects_forgotten_classes_from_cache_like_sources():
    memory = {
        "checkpoint": {
            "author_decision": [{"decision": "promise new temporal validation"}],
        },
        "cache": {
            "strategy_preference": [{"strategy": "defend_without_revision"}],
        },
        "retrieved_cases": [
            {
                "unit_id": "old_case",
                "final_wording": "We have completed all requested experiments.",
            }
        ],
        "prior_final_report": {
            "final_wording": "We commit to adding all new experiments.",
        },
        "evidence_trace": [{"evidence_ref": "section_002"}],
    }

    filtered = filter_runtime_memory(memory, memory_policy="default")

    assert filtered == {"evidence_trace": [{"evidence_ref": "section_002"}]}
