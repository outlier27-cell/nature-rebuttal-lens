import pytest
import time

from peer_review_skills.agents.dag_runtime import (
    WorkflowGraph,
    WorkflowNode,
    run_workflow_graph,
)


def test_workflow_graph_orders_nodes_by_dependencies():
    graph = WorkflowGraph([
        WorkflowNode(node_id="a", agent_id="agent_a", depends_on=[]),
        WorkflowNode(node_id="b", agent_id="agent_b", depends_on=["a"]),
        WorkflowNode(node_id="c", agent_id="agent_c", depends_on=["a"]),
        WorkflowNode(node_id="d", agent_id="agent_d", depends_on=["b", "c"]),
    ])

    levels = graph.execution_levels()

    assert levels == [["a"], ["b", "c"], ["d"]]


def test_workflow_graph_rejects_missing_dependency():
    with pytest.raises(ValueError, match="missing dependency"):
        WorkflowGraph([
            WorkflowNode(node_id="b", agent_id="agent_b", depends_on=["a"]),
        ]).validate()


def test_workflow_graph_rejects_cycle():
    with pytest.raises(ValueError, match="cycle"):
        WorkflowGraph([
            WorkflowNode(node_id="a", agent_id="agent_a", depends_on=["b"]),
            WorkflowNode(node_id="b", agent_id="agent_b", depends_on=["a"]),
        ]).execution_levels()


def test_run_workflow_graph_executes_dependency_levels():
    calls = []

    def run_node(node, context):
        calls.append(node.node_id)
        return {"node": node.node_id, "seen": sorted(context["outputs"])}

    graph = WorkflowGraph([
        WorkflowNode(node_id="a", agent_id="agent_a", depends_on=[]),
        WorkflowNode(node_id="b", agent_id="agent_b", depends_on=["a"]),
    ])

    trace = run_workflow_graph(graph, run_node, initial_context={"unit_id": "u1"})

    assert calls == ["a", "b"]
    assert trace["outputs"]["a"]["node"] == "a"
    assert trace["outputs"]["b"]["seen"] == ["a"]
    assert trace["execution_metadata"]["levels_executed"] == 2


def test_run_workflow_graph_can_execute_ready_nodes_in_parallel():
    calls = []

    def run_node(node, context):
        time.sleep(0.2)
        calls.append(node.node_id)
        return {"node": node.node_id}

    graph = WorkflowGraph([
        WorkflowNode(node_id="a", agent_id="agent_a", depends_on=[]),
        WorkflowNode(node_id="b", agent_id="agent_b", depends_on=[]),
    ])

    started = time.perf_counter()
    trace = run_workflow_graph(
        graph,
        run_node,
        initial_context={"unit_id": "u1"},
        parallel=True,
        max_workers=2,
    )
    elapsed = time.perf_counter() - started

    assert sorted(calls) == ["a", "b"]
    assert elapsed < 0.35
    assert trace["execution_metadata"]["parallel_execution"] is True


def test_run_workflow_graph_error_preserves_partial_trace():
    def run_node(node, context):
        if node.node_id == "b":
            raise RuntimeError("boom")
        return {"node": node.node_id}

    graph = WorkflowGraph([
        WorkflowNode(node_id="a", agent_id="agent_a", depends_on=[]),
        WorkflowNode(node_id="b", agent_id="agent_b", depends_on=["a"]),
    ])

    with pytest.raises(RuntimeError) as exc_info:
        run_workflow_graph(graph, run_node, initial_context={"unit_id": "u1"})

    partial_trace = getattr(exc_info.value, "partial_trace", {})
    assert partial_trace["outputs"]["a"] == {"node": "a"}
    assert partial_trace["execution_trace"][0]["success_count"] == 1
    assert partial_trace["execution_trace"][1]["error_count"] == 1


def test_rebuttal_lens_graph_exposes_parallel_ready_committee_slots():
    from peer_review_skills.agents.rebuttal_lens_graph import build_rebuttal_lens_graph

    graph = build_rebuttal_lens_graph(
        enable_committee=True,
        enable_strategy_tournament=True,
    )
    node_ids = [node.node_id for node in graph.nodes]

    assert "manuscript_context" in node_ids
    assert "reviewer_understanding" in node_ids
    assert "manuscript_evidence" in node_ids
    assert "committee_methodology_review" in node_ids
    assert "committee_tone_review" in node_ids
    assert "strategy_tournament" in node_ids
    assert "meta_synthesis" in node_ids
    assert "final_user_report" in node_ids

    levels = graph.execution_levels()
    committee_level = next(
        level for level in levels if "committee_methodology_review" in level
    )
    assert "committee_tone_review" in committee_level
