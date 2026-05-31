"""Declarative workflow graph for Nature RebuttalLens."""

from __future__ import annotations

from peer_review_skills.agents.dag_runtime import WorkflowGraph, WorkflowNode


def build_rebuttal_lens_graph(
    *,
    enable_committee: bool = False,
    enable_strategy_tournament: bool = False,
) -> WorkflowGraph:
    """Build the RebuttalLens dependency graph."""
    nodes = [
        WorkflowNode("manuscript_context", "manuscript_context_extractor"),
        WorkflowNode("reviewer_understanding", "reviewer_understanding_agent", ["manuscript_context"]),
        WorkflowNode("tacit_concern", "tacit_concern_interpreter", ["reviewer_understanding"]),
        WorkflowNode("manuscript_evidence", "manuscript_evidence_locator", ["reviewer_understanding"]),
        WorkflowNode("institutional_signal", "institutional_signal_interpreter", ["manuscript_evidence"]),
        WorkflowNode("case_interpretation", "case_retrieval_interpreter", ["tacit_concern", "manuscript_evidence"]),
        WorkflowNode("evidence_action", "evidence_action_planner", ["case_interpretation", "manuscript_evidence"]),
        WorkflowNode("author_positioning", "author_positioning_agent", ["institutional_signal", "evidence_action"]),
        WorkflowNode("tone_commitment", "tone_commitment_calibrator", ["author_positioning", "evidence_action"]),
        WorkflowNode("actor_network", "actor_network_mapper", ["tone_commitment"]),
        WorkflowNode("cross_disciplinary_lens", "cross_disciplinary_lens_interpreter", ["actor_network"]),
    ]
    if enable_committee:
        nodes.extend([
            WorkflowNode(
                "committee_methodology_review",
                "methodology_committee_reviewer",
                ["manuscript_evidence", "evidence_action"],
                parallel_group="reviewer_committee",
            ),
            WorkflowNode(
                "committee_claim_review",
                "claim_committee_reviewer",
                ["manuscript_evidence", "evidence_action"],
                parallel_group="reviewer_committee",
            ),
            WorkflowNode(
                "committee_tone_review",
                "tone_committee_reviewer",
                ["manuscript_evidence", "evidence_action"],
                parallel_group="reviewer_committee",
            ),
            WorkflowNode(
                "committee_meta_review",
                "committee_meta_reviewer",
                [
                    "committee_methodology_review",
                    "committee_claim_review",
                    "committee_tone_review",
                ],
            ),
        ])
    if enable_strategy_tournament:
        strategy_dependencies = ["evidence_action", "tone_commitment"]
        if enable_committee:
            strategy_dependencies.append("committee_meta_review")
        nodes.extend([
            WorkflowNode("strategy_tournament", "strategy_tournament_agent", strategy_dependencies),
            WorkflowNode("meta_synthesis", "strategy_meta_planner", ["strategy_tournament"]),
        ])
    integrity_dependencies = ["cross_disciplinary_lens"]
    if enable_committee:
        integrity_dependencies.append("committee_meta_review")
    if enable_strategy_tournament:
        integrity_dependencies.append("meta_synthesis")
    nodes.extend([
        WorkflowNode("integrity", "integrity_adequacy_checker", integrity_dependencies),
        WorkflowNode("final_user_report", "final_user_report_composer", ["integrity"]),
    ])
    return WorkflowGraph(nodes)
