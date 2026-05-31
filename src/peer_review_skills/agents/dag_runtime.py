"""Small dependency-aware workflow runtime for RebuttalLens."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Callable


class WorkflowExecutionError(RuntimeError):
    """Workflow failure that preserves the partial graph trace."""

    def __init__(
        self,
        message: str,
        *,
        partial_trace: dict[str, Any],
        original_error: BaseException,
    ):
        super().__init__(message)
        self.partial_trace = partial_trace
        self.original_error = original_error


@dataclass(frozen=True)
class WorkflowNode:
    """A single executable node in a workflow graph."""

    node_id: str
    agent_id: str
    depends_on: list[str] = field(default_factory=list)
    optional: bool = False
    parallel_group: str | None = None
    skip_when: str | None = None


class WorkflowGraph:
    """Validated DAG of workflow nodes."""

    def __init__(self, nodes: list[WorkflowNode]):
        self.nodes = nodes
        self.node_by_id = {node.node_id: node for node in nodes}
        if len(self.node_by_id) != len(nodes):
            raise ValueError("workflow graph contains duplicate node_id")

    def validate(self) -> None:
        for node in self.nodes:
            for dependency in node.depends_on:
                if dependency not in self.node_by_id:
                    raise ValueError(f"Node {node.node_id} has missing dependency {dependency}")

    def execution_levels(self) -> list[list[str]]:
        self.validate()
        remaining = set(self.node_by_id)
        completed: set[str] = set()
        levels: list[list[str]] = []
        while remaining:
            ready = sorted(
                node_id
                for node_id in remaining
                if all(dep in completed for dep in self.node_by_id[node_id].depends_on)
            )
            if not ready:
                raise ValueError("workflow graph contains a dependency cycle")
            levels.append(ready)
            completed.update(ready)
            remaining.difference_update(ready)
        return levels


def run_workflow_graph(
    graph: WorkflowGraph,
    node_runner: Callable[[WorkflowNode, dict[str, Any]], dict[str, Any]],
    *,
    initial_context: dict[str, Any] | None = None,
    parallel: bool = False,
    max_workers: int | None = None,
) -> dict[str, Any]:
    """Run a graph in dependency order and return an auditable trace."""
    context: dict[str, Any] = dict(initial_context or {})
    outputs: dict[str, Any] = {}
    trace = []
    for level_index, node_ids in enumerate(graph.execution_levels(), start=1):
        level_entry: dict[str, Any] = {
            "level": level_index,
            "nodes": node_ids,
            "started_at": datetime.now().isoformat(),
            "success_count": 0,
            "error_count": 0,
            "errors": [],
            "parallel_groups": _parallel_groups(graph, node_ids),
        }
        try:
            if parallel and len(node_ids) > 1:
                _run_level_parallel(
                    graph,
                    node_ids,
                    node_runner,
                    context,
                    outputs,
                    level_entry,
                    max_workers=max_workers,
                )
            else:
                _run_level_sequential(
                    graph,
                    node_ids,
                    node_runner,
                    context,
                    outputs,
                    level_entry,
                )
        except Exception as exc:
            level_entry["finished_at"] = datetime.now().isoformat()
            trace.append(level_entry)
            raise WorkflowExecutionError(
                str(exc),
                partial_trace=_workflow_trace_payload(
                    graph,
                    outputs,
                    trace,
                    parallel=parallel,
                ),
                original_error=exc,
            ) from exc
        level_entry["finished_at"] = datetime.now().isoformat()
        trace.append(level_entry)
    return _workflow_trace_payload(
        graph,
        outputs,
        trace,
        parallel=parallel,
    )


def _workflow_trace_payload(
    graph: WorkflowGraph,
    outputs: dict[str, Any],
    trace: list[dict[str, Any]],
    *,
    parallel: bool,
) -> dict[str, Any]:
    return {
        "outputs": outputs,
        "execution_trace": trace,
        "execution_metadata": {
            "levels_executed": len(trace),
            "nodes_executed": len(outputs),
            "graph_node_count": len(graph.nodes),
            "parallel_execution": parallel,
        },
    }


def _run_level_sequential(
    graph: WorkflowGraph,
    node_ids: list[str],
    node_runner: Callable[[WorkflowNode, dict[str, Any]], dict[str, Any]],
    context: dict[str, Any],
    outputs: dict[str, Any],
    level_entry: dict[str, Any],
) -> None:
    for node_id in node_ids:
        node = graph.node_by_id[node_id]
        node_context = {**context, "outputs": dict(outputs)}
        try:
            outputs[node_id] = node_runner(node, node_context)
            level_entry["success_count"] += 1
        except Exception as exc:
            level_entry["error_count"] += 1
            level_entry["errors"].append({"node_id": node_id, "error": str(exc)})
            if not node.optional:
                raise


def _run_level_parallel(
    graph: WorkflowGraph,
    node_ids: list[str],
    node_runner: Callable[[WorkflowNode, dict[str, Any]], dict[str, Any]],
    context: dict[str, Any],
    outputs: dict[str, Any],
    level_entry: dict[str, Any],
    *,
    max_workers: int | None,
) -> None:
    level_snapshot = dict(outputs)
    worker_count = max_workers or len(node_ids)
    with ThreadPoolExecutor(max_workers=max(1, worker_count)) as executor:
        future_to_node_id = {
            executor.submit(
                node_runner,
                graph.node_by_id[node_id],
                {**context, "outputs": level_snapshot},
            ): node_id
            for node_id in node_ids
        }
        level_outputs: dict[str, Any] = {}
        first_required_error: BaseException | None = None
        for future in as_completed(future_to_node_id):
            node_id = future_to_node_id[future]
            node = graph.node_by_id[node_id]
            try:
                level_outputs[node_id] = future.result()
                level_entry["success_count"] += 1
            except Exception as exc:
                level_entry["error_count"] += 1
                level_entry["errors"].append({"node_id": node_id, "error": str(exc)})
                if not node.optional and first_required_error is None:
                    first_required_error = exc
        for node_id in node_ids:
            if node_id in level_outputs:
                outputs[node_id] = level_outputs[node_id]
        if first_required_error is not None:
            raise first_required_error


def _parallel_groups(graph: WorkflowGraph, node_ids: list[str]) -> dict[str, list[str]]:
    groups: dict[str, list[str]] = {}
    for node_id in node_ids:
        group = graph.node_by_id[node_id].parallel_group
        if group:
            groups.setdefault(group, []).append(node_id)
    return groups
