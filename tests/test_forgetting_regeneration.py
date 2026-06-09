from peer_review_skills.agents.forgetting_regeneration import (
    regenerate_categories_from_forgetting_ledger,
)


def test_regenerates_derived_forgettable_candidates_from_structural_patterns():
    ledger = [
        {
            "memory_class": "strategy_preference",
            "action": "forgotten",
            "pattern_hint": "temporal leakage and near duplicate evaluation pattern",
            "reason": "Past preference is forgotten, but this abstract risk pattern is reusable.",
            "strategy": "defend_without_revision",
        },
        {
            "memory_class": "reasoning_trace",
            "pattern_hint": "citation positioning lacks direct support pattern",
            "reason": "Reasoning summary preserves an auditable review pattern.",
        },
        {
            "memory_class": "audit_trace",
            "reason": "Repeated readiness gate failure after missing data availability checks.",
        },
    ]

    regenerated = regenerate_categories_from_forgetting_ledger(ledger, run_id="run-003")

    assert regenerated["blocked_memory_classes"] == []
    names = {candidate["name"] for candidate in regenerated["derived_forgettable"]}
    assert "temporal_leakage_and_near_duplicate_evaluation_pattern" in names
    assert "citation_positioning_lacks_direct_support_pattern" in names
    assert "repeated_readiness_gate_failure_after_missing_data" in names
    assert {
        candidate["status"] for candidate in regenerated["derived_forgettable"]
    } == {"derived_forgettable"}
    assert all(candidate["source_run_id"] == "run-003" for candidate in regenerated["derived_forgettable"])


def test_blocks_concrete_forgotten_memory_classes_without_reconstructing_content():
    ledger = [
        {
            "memory_class": "author_decision",
            "pattern_hint": "author promised to run Experiment 7",
            "reason": "Author agency must be renewed each run.",
        },
        {
            "memory_class": "final_wording",
            "final_wording": "We have completed all requested validation.",
            "reason": "Prior final phrasing must not be reused.",
        },
        {
            "memory_class": "latent_commitment",
            "latent_commitment": "Commit to releasing all data next week.",
            "reason": "Latent commitments are not portable.",
        },
        {
            "memory_class": "unsafe_claim",
            "unsafe_claim": "The model generalizes across all domains.",
            "reason": "Unsafe claims require fresh evidence.",
        },
    ]

    regenerated = regenerate_categories_from_forgetting_ledger(ledger)

    assert regenerated["derived_forgettable"] == []
    assert regenerated["blocked_memory_classes"] == [
        "author_decision",
        "final_wording",
        "latent_commitment",
        "unsafe_claim",
    ]
    rendered = repr(regenerated)
    assert "Experiment 7" not in rendered
    assert "completed all requested validation" not in rendered
    assert "releasing all data" not in rendered
    assert "generalizes across all domains" not in rendered
