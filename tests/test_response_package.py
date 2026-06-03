from peer_review_skills.agents.response_package import (
    build_response_package_cards,
    infer_category,
    infer_nature_action,
    infer_readiness,
    validate_response_package_cards,
)


def test_infer_nature_action_maps_existing_taxonomy_without_replacing_it():
    assert infer_nature_action(
        action_type="new_analysis",
        evidence_status="partially_supported",
        required_artifact="temporal split validation",
        requires_author_confirmation=True,
    ) == "AUTHOR_INPUT_NEEDED"
    assert infer_nature_action(
        action_type="claim_narrowing",
        evidence_status="missing",
        required_artifact="narrow cross-context claim",
        requires_author_confirmation=False,
    ) == "SOFTEN_CLAIM"
    assert infer_nature_action(
        action_type="method_clarification",
        evidence_status="supported",
        required_artifact="Methods paragraph",
        requires_author_confirmation=False,
    ) == "CLARIFY_EXISTING"


def test_readiness_never_ready_when_author_input_is_required():
    assert infer_readiness(
        proposed_action="AUTHOR_INPUT_NEEDED",
        evidence_status="partially_supported",
        author_input_required=True,
        evidence_anchor="Methods",
    ) == "needs_author_input"


def test_build_response_package_cards_adds_nature_schema_fields():
    cards = build_response_package_cards(
        concern_map=[
            {
                "concern_id": "concern_001",
                "concern_type": "methodological_transparency",
                "surface_request": "clarify split",
                "text_evidence": "dataset split is unclear",
                "confidence": "high",
            }
        ],
        evidence_map=[
            {
                "concern_id": "concern_001",
                "status": "partially_supported",
                "section_id": "section_002",
                "text_evidence": "80/10/10 split",
                "gap": "random seed missing",
            }
        ],
        action_plan=[
            {
                "concern_id": "concern_001",
                "action_type": "method_clarification",
                "required_artifact": "dataset split protocol and random seed",
                "supporting_case_ids": ["case_001"],
                "requires_author_confirmation": True,
            }
        ],
    )

    assert cards[0]["comment_id"] == "concern_001"
    assert cards[0]["severity"] in {"minor", "major", "blocking", "unclear"}
    assert cards[0]["category"] == "methodological"
    assert cards[0]["proposed_action"] == "AUTHOR_INPUT_NEEDED"
    assert cards[0]["readiness"] == "needs_author_input"
    assert cards[0]["risk_level"] == "high"
    assert cards[0]["missing_author_input"] == [
        "dataset split protocol and random seed"
    ]
    assert cards[0]["evidence_anchor"] == "section_002"


def test_infer_category_treats_evaluation_design_as_methodological():
    for concern_type in [
        "experimental_design",
        "evaluation_validity",
        "reproducibility_reporting",
    ]:
        assert infer_category(concern_type, "") == "methodological"


def test_validate_response_package_rejects_ready_with_missing_author_input():
    cards = [
        {
            "comment_id": "R1.1",
            "proposed_action": "ACCEPT_ANALYSIS",
            "readiness": "ready_to_submit",
            "author_input_required": True,
            "missing_author_input": ["sample size"],
            "evidence_anchor": "",
        }
    ]

    issues = validate_response_package_cards(cards)

    assert issues
    assert any("ready_to_submit" in issue for issue in issues)
