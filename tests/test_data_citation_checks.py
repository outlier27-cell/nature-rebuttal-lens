from peer_review_skills.agents.citation_support_checks import grade_citation_support
from peer_review_skills.agents.data_availability_checks import build_data_availability_check


def test_data_availability_check_detects_repository_identifier_license_needs():
    check = build_data_availability_check({
        "comment_id": "R2.1",
        "category": "data_code_materials",
        "surface_request": "Please provide source data and code availability.",
        "recommended_action": "provide repository and accession details",
    })

    assert check["applies"] is True
    assert "repository_or_access_route" in check["required_fields"]
    assert "persistent_identifier" in check["required_fields"]
    assert "license_or_restriction_reason" in check["required_fields"]
    assert check["readiness_impact"] == "needs_author_input"


def test_data_availability_check_does_not_treat_citation_doi_as_data_request():
    check = build_data_availability_check({
        "comment_id": "R2.2",
        "category": "citation_positioning",
        "surface_request": "Please add a DOI for the cited prior work.",
        "recommended_action": "add DOI for the citation",
    })

    assert check["applies"] is False


def test_citation_support_is_conservative_for_title_only_candidate():
    grade = grade_citation_support({
        "comment_id": "R1.2",
        "category": "citation_positioning",
        "supporting_case_ids": ["case_001"],
        "recommended_action": "add relevant citation",
    })

    assert grade["support_grade"] == "needs_verification"
    assert grade["can_be_used_as_evidence"] is False
    assert "verified bibliographic detail" in grade["required_verification"]


def test_citation_support_accepts_verified_supplied_anchor():
    grade = grade_citation_support({
        "comment_id": "R1.2",
        "category": "citation_positioning",
        "evidence_refs": ["doi:10.1234/example"],
        "recommended_action": "add relevant citation",
    })

    assert grade["support_grade"] == "supplied_anchor"
    assert grade["can_be_used_as_evidence"] is True
