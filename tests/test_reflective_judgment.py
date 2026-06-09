from peer_review_skills.agents.kantian_categories import CategoryRegistry, CategoryStatus
from peer_review_skills.agents.reflective_judgment import judge_reviewer_concern


def test_low_similarity_defers_decision_and_drafts_unverified_category(tmp_path):
    registry = CategoryRegistry(tmp_path / "categories.json")
    registry.upsert(
        "citation_positioning",
        description="citation prior work novelty positioning",
        status=CategoryStatus.APPROVED,
    )

    judgment = judge_reviewer_concern(
        "Reviewer requests temporally held-out validation and near-duplicate removal.",
        registry,
        run_id="run-001",
        similarity_threshold=0.45,
    )

    assert judgment["judgment_type"] == "reflective_judgment"
    assert judgment["readiness"] == "decision_deferred"
    assert judgment["matched_category"] is None
    assert judgment["category_invention_draft"]["verification_status"] == "unverified"
    assert judgment["category_invention_draft"]["status"] == "draft"
    assert registry.get(judgment["category_invention_draft"]["name"]).status == CategoryStatus.DRAFT


def test_high_similarity_uses_determining_judgment_without_inventing_category(tmp_path):
    registry = CategoryRegistry(tmp_path / "categories.json")
    registry.upsert(
        "temporal_leakage",
        description="temporal leakage held-out validation near duplicate removal",
        status=CategoryStatus.APPROVED,
    )

    judgment = judge_reviewer_concern(
        "Reviewer requests temporally held-out validation and near-duplicate removal.",
        registry,
        run_id="run-002",
        similarity_threshold=0.2,
    )

    assert judgment["judgment_type"] == "determining_judgment"
    assert judgment["readiness"] == "ready_for_category_application"
    assert judgment["matched_category"]["name"] == "temporal_leakage"
    assert judgment["category_invention_draft"] is None
