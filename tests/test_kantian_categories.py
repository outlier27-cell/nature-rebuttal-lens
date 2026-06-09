import json
from pathlib import Path

from peer_review_skills.agents.kantian_categories import (
    CategoryRegistry,
    CategoryStatus,
    KantianCategory,
)


def test_category_registry_persists_and_promotes_after_three_independent_confirmations(tmp_path):
    path = tmp_path / "categories.json"
    registry = CategoryRegistry(path)

    category = registry.upsert(
        "temporal_leakage",
        description="Reviewer concern about temporal leakage in evaluation.",
        status=CategoryStatus.CANDIDATE,
        run_id="run-a",
    )
    assert category.status == CategoryStatus.CANDIDATE

    registry.record_confirmation("temporal_leakage", "run-a")
    registry.record_confirmation("temporal_leakage", "run-b")
    category = registry.record_confirmation("temporal_leakage", "run-c")

    assert category.status == CategoryStatus.APPROVED
    assert category.confirmed_run_ids == ["run-a", "run-b", "run-c"]

    registry.save()
    loaded = CategoryRegistry.load(path)

    assert loaded.get("temporal_leakage").status == CategoryStatus.APPROVED
    assert loaded.get("temporal_leakage").description == category.description


def test_record_confirmation_counts_distinct_run_ids_only(tmp_path):
    registry = CategoryRegistry(tmp_path / "categories.json")
    registry.upsert("duplicate_eval", run_id="run-a")

    registry.record_confirmation("duplicate_eval", "run-a")
    registry.record_confirmation("duplicate_eval", "run-a")
    category = registry.record_confirmation("duplicate_eval", "run-b")

    assert category.status == CategoryStatus.CANDIDATE
    assert category.confirmed_run_ids == ["run-a", "run-b"]


def test_match_returns_best_approved_category_above_threshold(tmp_path):
    registry = CategoryRegistry(tmp_path / "categories.json")
    registry.upsert(
        "temporal_leakage",
        description="temporal leakage held-out validation duplicate evaluation",
        status=CategoryStatus.APPROVED,
    )
    registry.upsert(
        "editorial_clarity",
        description="minor wording and presentation clarity",
        status=CategoryStatus.APPROVED,
    )

    match = registry.match("Reviewer asks for temporally held-out validation leakage checks.")

    assert match is not None
    assert match.category.name == "temporal_leakage"
    assert match.similarity >= 0.2


def test_match_ignores_retired_and_forgettable_categories_by_default(tmp_path):
    registry = CategoryRegistry(tmp_path / "categories.json")
    registry.upsert(
        "stale_preference",
        description="temporally held-out validation leakage checks",
        status=CategoryStatus.DERIVED_FORGETTABLE,
    )
    registry.upsert(
        "retired_pattern",
        description="temporally held-out validation leakage checks",
        status=CategoryStatus.RETIRED,
    )

    assert registry.match("temporally held-out validation leakage checks") is None


def test_category_status_includes_required_lifecycle_values():
    assert {status.value for status in CategoryStatus} == {
        "draft",
        "candidate",
        "approved",
        "derived_forgettable",
        "retired",
    }


def test_kantian_category_id_is_persisted_and_usable_for_confirmations(tmp_path):
    path = tmp_path / "categories.json"
    registry = CategoryRegistry(path=path, confirmation_threshold=3)
    registry.upsert(
        KantianCategory(
            category_id="cat_temporal_validation",
            name="Temporal validation before broad generalization",
            description="Use temporal holdout evidence before broad peer-review claims.",
            triggers=["temporal split", "temporal leakage", "generalization"],
            strategy_family="acknowledge_and_fix",
            status=CategoryStatus.CANDIDATE,
            source="successful_author_confirmed_strategy",
        )
    )

    registry.record_confirmation("cat_temporal_validation", "paper_a", "author_confirmed")
    registry.record_confirmation("cat_temporal_validation", "paper_b", "author_confirmed")
    assert registry.get("cat_temporal_validation").status == CategoryStatus.CANDIDATE

    registry.record_confirmation("cat_temporal_validation", "paper_c", "author_confirmed")
    category = registry.get("cat_temporal_validation")

    assert category.status == CategoryStatus.APPROVED
    assert category.category_id == "cat_temporal_validation"
    assert category.forgetting_eligible is True
    assert category.strategy_family == "acknowledge_and_fix"
    assert registry.get("Temporal validation before broad generalization") is category

    registry.save()
    payload = json.loads(path.read_text(encoding="utf-8"))

    assert payload["categories"][0]["category_id"] == "cat_temporal_validation"
    assert payload["categories"][0]["forgetting_eligible"] is True
    assert payload["categories"][0]["triggers"] == [
        "temporal split",
        "temporal leakage",
        "generalization",
    ]


def test_kantian_category_triggers_participate_in_matching(tmp_path):
    registry = CategoryRegistry(path=tmp_path / "categories.json")
    registry.upsert(
        KantianCategory(
            category_id="cat_temporal_validation",
            name="Temporal validation before broad generalization",
            description="Use evidence boundaries for broad peer-review claims.",
            triggers=["temporally held-out split", "near duplicate removal"],
            strategy_family="acknowledge_and_fix",
            status=CategoryStatus.APPROVED,
        )
    )

    match = registry.match(
        "Reviewer requests a temporally held-out split and near-duplicate removal.",
        threshold=0.2,
    )
    candidates = registry.match_candidates(
        "Reviewer requests a temporally held-out split and near-duplicate removal.",
        min_similarity=0.2,
    )

    assert match is not None
    assert match.category.category_id == "cat_temporal_validation"
    assert candidates[0]["category_id"] == "cat_temporal_validation"
    assert candidates[0]["strategy_family"] == "acknowledge_and_fix"
