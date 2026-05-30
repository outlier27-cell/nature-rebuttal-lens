import json
import sys
from pathlib import Path


REQUIRED_TOP_LEVEL = {"version", "project", "nodes", "edges", "layers", "tour"}
REQUIRED_NODE = {"id", "type", "name", "summary", "tags"}
REQUIRED_EDGE = {"source", "target", "type"}
REQUIRED_LAYER = {"id", "name", "description", "nodeIds"}
REQUIRED_TOUR = {"order", "title", "description", "nodeIds"}


def main() -> int:
    graph_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path(".understand-anything/knowledge-graph.json")
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    issues: list[str] = []

    missing_top = REQUIRED_TOP_LEVEL - set(graph)
    if missing_top:
        issues.append(f"missing top-level fields: {sorted(missing_top)}")

    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    layers = graph.get("layers", [])
    tour = graph.get("tour", [])
    if not isinstance(nodes, list):
        issues.append("nodes is not a list")
        nodes = []
    if not isinstance(edges, list):
        issues.append("edges is not a list")
        edges = []
    if not isinstance(layers, list):
        issues.append("layers is not a list")
        layers = []
    if not isinstance(tour, list):
        issues.append("tour is not a list")
        tour = []

    node_ids: set[str] = set()
    for index, node in enumerate(nodes):
        missing = REQUIRED_NODE - set(node)
        if missing:
            issues.append(f"node[{index}] missing fields: {sorted(missing)}")
        node_id = node.get("id")
        if node_id in node_ids:
            issues.append(f"duplicate node id: {node_id}")
        if node_id:
            node_ids.add(node_id)
        if not node.get("summary"):
            issues.append(f"node[{index}] has empty summary")
        if not node.get("tags"):
            issues.append(f"node[{index}] has empty tags")

    for index, edge in enumerate(edges):
        missing = REQUIRED_EDGE - set(edge)
        if missing:
            issues.append(f"edge[{index}] missing fields: {sorted(missing)}")
        if edge.get("source") not in node_ids:
            issues.append(f"edge[{index}] source not found: {edge.get('source')}")
        if edge.get("target") not in node_ids:
            issues.append(f"edge[{index}] target not found: {edge.get('target')}")

    assigned_file_nodes: set[str] = set()
    for index, layer in enumerate(layers):
        missing = REQUIRED_LAYER - set(layer)
        if missing:
            issues.append(f"layer[{index}] missing fields: {sorted(missing)}")
        for node_id in layer.get("nodeIds", []):
            if node_id not in node_ids:
                issues.append(f"layer[{index}] references missing node: {node_id}")
            assigned_file_nodes.add(node_id)

    for index, step in enumerate(tour):
        missing = REQUIRED_TOUR - set(step)
        if missing:
            issues.append(f"tour[{index}] missing fields: {sorted(missing)}")
        for node_id in step.get("nodeIds", []):
            if node_id not in node_ids:
                issues.append(f"tour[{index}] references missing node: {node_id}")

    file_level_types = {"file", "config", "document", "service", "pipeline", "table", "schema", "resource", "endpoint"}
    for node in nodes:
        if node.get("type") in file_level_types and node["id"] not in assigned_file_nodes:
            issues.append(f"file-level node is not assigned to any layer: {node['id']}")

    text_blob = json.dumps(graph, ensure_ascii=False)
    if "审稿" not in text_blob or "作者回应" not in text_blob:
        issues.append("graph does not contain expected Chinese project terms")

    if issues:
        print(json.dumps({"ok": False, "issues": issues[:50], "issueCount": len(issues)}, ensure_ascii=False, indent=2))
        return 1

    stats = {
        "ok": True,
        "nodeCount": len(nodes),
        "edgeCount": len(edges),
        "layerCount": len(layers),
        "tourStepCount": len(tour),
    }
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
