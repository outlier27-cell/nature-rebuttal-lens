"""Deterministic data/code/material availability checks for RebuttalLens."""

from __future__ import annotations

from typing import Any


DATA_TOKENS = {
    "data",
    "dataset",
    "source data",
    "code",
    "repository",
    "accession",
    "materials",
    "availability",
}


def build_data_availability_check(card: dict[str, Any]) -> dict[str, Any]:
    text = " ".join(
        str(card.get(key, ""))
        for key in [
            "category",
            "surface_request",
            "recommended_action",
            "evidence_gap",
        ]
    ).lower()
    applies = card.get("category") == "data_code_materials" or any(
        token in text for token in DATA_TOKENS
    )
    if not applies:
        return {"applies": False, "required_fields": [], "readiness_impact": "none"}
    return {
        "applies": True,
        "required_fields": [
            "repository_or_access_route",
            "persistent_identifier",
            "license_or_restriction_reason",
            "dataset_to_figure_or_table_mapping",
            "metadata_readme_or_data_dictionary",
        ],
        "fair_checks": [
            "findable_identifier",
            "accessible_conditions",
            "interoperable_formats_or_metadata",
            "reusable_license_provenance_methods",
        ],
        "readiness_impact": "needs_author_input",
    }
