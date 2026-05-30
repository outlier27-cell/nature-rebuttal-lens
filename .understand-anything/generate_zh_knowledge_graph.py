import ast
import json
import subprocess
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / ".understand-anything"
SRC = ROOT / "src" / "peer_review_skills"


LAYER_RULES = [
    (
        "layer:public-interface",
        "公开入口与命令行层",
        "负责 package metadata、CLI 子命令、README 首页说明、示例入口和用户可见运行方式。",
        lambda p: p == "README.md"
        or p == "pyproject.toml"
        or p.startswith("examples/")
        or p.startswith("src/peer_review_skills/cli/")
        or p.startswith("config/"),
    ),
    (
        "layer:rebuttal-lens-agents",
        "Nature RebuttalLens 多智能体层",
        "实现 manuscript-aware 的 12-agent workflow，包括审稿理解、隐性风险、证据定位、案例解释、回应规划、跨学科镜头与完整性检查。",
        lambda p: p.startswith("src/peer_review_skills/agents/"),
    ),
    (
        "layer:data-processing",
        "数据处理与知识库构建层",
        "把 Nature 公开审稿互动数据加工为 normalized papers、review/response units、alignment、taxonomy、skill cards、KB 和 release-safe artifacts。",
        lambda p: any(
            p.startswith(prefix)
            for prefix in [
                "src/peer_review_skills/normalize/",
                "src/peer_review_skills/segment/",
                "src/peer_review_skills/annotate/",
                "src/peer_review_skills/align/",
                "src/peer_review_skills/taxonomy/",
                "src/peer_review_skills/skills/",
                "src/peer_review_skills/indexing/",
                "src/peer_review_skills/sample/",
                "src/peer_review_skills/execution/",
                "src/peer_review_skills/io/",
                "src/peer_review_skills/schemas/",
            ]
        ),
    ),
    (
        "layer:model-api-and-evaluation",
        "模型 API、评测与发布门禁层",
        "封装 OpenAI-compatible API、handoff/review、retrieval baseline、simulation、diagnostics、judge、readiness 和 release validation。",
        lambda p: any(
            p.startswith(prefix)
            for prefix in [
                "src/peer_review_skills/api/",
                "src/peer_review_skills/evaluation/",
                "src/peer_review_skills/judge/",
                "src/peer_review_skills/readiness/",
            ]
        ),
    ),
    (
        "layer:documentation-and-governance",
        "研究文档、伦理边界与发布治理层",
        "记录跨学科研究框架、数据边界、Responsible Use、agent card、evaluation protocol、系统流程图和发布审计。",
        lambda p: p.startswith("docs/") or p in {"codex.md", "UPGRADE.md", "LICENSE"},
    ),
    (
        "layer:tests",
        "测试与回归保护层",
        "覆盖 acceptance、multi-agent、RebuttalLens workflow、README release surface、文档可读性、API 边界和格式支持。",
        lambda p: p.startswith("tests/"),
    ),
]


FILE_SUMMARY_OVERRIDES = {
    "README.md": "项目首页，定义 Nature RebuttalLens 的定位、12-agent workflow、安装、PDF extra、Quick Start、数据边界和 Responsible Use。",
    "pyproject.toml": "Python 包元数据，定义 nature-rebuttal-lens 包、console scripts、pytest 配置和 pdfplumber PDF extra。",
    "src/peer_review_skills/cli/main.py": "命令行入口，连接数据处理、v0.1 构建校验、多智能体运行和 run-rebuttal-lens 用户命令。",
    "src/peer_review_skills/agents/manuscript_context.py": "manuscript context 解析模块，支持文本、Markdown、LaTeX、pdfplumber 可抽取 PDF 文本、DOCX XML 和 LibreOffice/soffice 旧 DOC 转换边界。",
    "src/peer_review_skills/agents/rebuttal_lens_workflow.py": "Nature RebuttalLens 主 workflow，把 reviewer comment、manuscript、draft response 和 case analogies 组织成可追踪多智能体执行。",
    "src/peer_review_skills/agents/rebuttal_lens_agents.py": "前端 manuscript-aware agents，负责 manuscript context extraction、evidence location 和 Nature case interpretation。",
    "src/peer_review_skills/agents/multi_agent_orchestrator.py": "多智能体编排器，控制层级执行、消息传递、依赖顺序、refinement 和 trace 保存。",
    "src/peer_review_skills/agents/specialized_agents.py": "审稿理解、隐性关切、制度信号、证据规划、作者定位等核心 specialized agents。",
    "src/peer_review_skills/agents/specialized_agents_part2.py": "tone/commitment、actor-network、cross-disciplinary lens、integrity/adequacy 等后半段 agents。",
    "src/peer_review_skills/api/openai_compatible.py": "OpenAI-compatible chat client，封装外部模型调用、错误处理、JSON 提取和环境变量配置。",
    "src/peer_review_skills/execution/build_naturereview_v01.py": "v0.1 release artifact 生成器，构建 schema、taxonomy、KB、evaluation、docs 和 README。",
    "tests/test_rebuttal_lens_workflow.py": "RebuttalLens workflow 回归测试，覆盖 manuscript loading、PDF/DOCX/DOC 解析边界、CLI、README release guard 和核心公共中文文档可读性。",
    "tests/test_naturereview_v01_acceptance.py": "NatureReview v0.1 acceptance tests，保护非训练、跨学科、Responsible Use 和发布边界。",
    "tests/test_multi_agent.py": "多智能体基础测试，覆盖独立 agent、orchestrator、依赖/refinement 和 workflow integration。",
}


def rel(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def run_git_hash() -> str:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


def file_type(path: str) -> str:
    if path.endswith((".md", ".txt")):
        return "document"
    if path.endswith((".yaml", ".yml", ".toml", ".json")):
        if "schema" in path:
            return "schema"
        return "config"
    return "file"


def file_summary(path: str) -> str:
    if path in FILE_SUMMARY_OVERRIDES:
        return FILE_SUMMARY_OVERRIDES[path]
    if path.startswith("src/peer_review_skills/agents/"):
        return "多智能体与审稿互动推理相关模块，支撑 Author Rebuttal Assistant workflow。"
    if path.startswith("src/peer_review_skills/evaluation/"):
        return "评测、抽样、baseline、simulation 或 report 生成模块，用于把项目从 demo 转成可评估任务。"
    if path.startswith("src/peer_review_skills/"):
        return "peer_review_skills Python 包中的项目模块，服务于 Nature 审稿互动数据处理、知识库构建或 agent workflow。"
    if path.startswith("docs/"):
        return "项目文档，记录研究计划、跨学科价值、数据边界、评测协议、Responsible Use 或发布状态。"
    if path.startswith("tests/"):
        return "测试文件，用于保护核心 workflow、发布边界和回归行为。"
    return "项目文件。"


def tags_for_path(path: str) -> list[str]:
    tags = []
    if "rebuttal_lens" in path or "rebuttal-lens" in path:
        tags.append("rebuttal-lens")
    if path.startswith("src/peer_review_skills/agents/"):
        tags.append("multi-agent")
    if path.startswith("src/peer_review_skills/api/"):
        tags.append("api")
    if path.startswith("src/peer_review_skills/evaluation/"):
        tags.append("evaluation")
    if path.startswith("docs/"):
        tags.append("documentation")
    if path.startswith("tests/"):
        tags.append("tests")
    if "build_naturereview_v01" in path:
        tags.append("release-artifacts")
    return tags or ["project"]


def iter_project_files() -> list[Path]:
    files: list[Path] = []
    include_dirs = ["src", "tests", "config", "examples"]
    for directory in include_dirs:
        base = ROOT / directory
        if base.exists():
            files.extend(
                path
                for path in base.rglob("*")
                if path.is_file()
                and "__pycache__" not in path.parts
                and path.suffix in {".py", ".yaml", ".yml", ".toml", ".json", ".txt", ".md"}
            )
    for path in [
        ROOT / "README.md",
        ROOT / "pyproject.toml",
        ROOT / "UPGRADE.md",
        ROOT / "codex.md",
        ROOT / "LICENSE",
        ROOT / "docs" / "REBUTTAL_LENS_WORKFLOW_zh.md",
        ROOT / "docs" / "RESPONSIBLE_USE_zh.md",
        ROOT / "docs" / "DATA_CARD_zh.md",
        ROOT / "docs" / "AGENT_CARD_zh.md",
        ROOT / "docs" / "EVALUATION_PROTOCOL_zh.md",
        ROOT / "docs" / "DATA_RELEASE_BOUNDARY_zh.md",
        ROOT / "docs" / "MODEL_AND_AGENT_LIMITATIONS_zh.md",
        ROOT / "docs" / "INTERDISCIPLINARY_SYSTEM_FRAME_zh.md",
        ROOT / "docs" / "PDF_DERIVED_DESIGN_LENSES_zh.md",
        ROOT / "docs" / "2026-05-26-open-source-review-interaction-agent-full-plan-zh.md",
        ROOT / "docs" / "assets" / "rebuttal-lens-workflow.svg",
    ]:
        if path.exists():
            files.append(path)
    return sorted(set(files), key=lambda p: rel(p))


def parse_python(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[str]]:
    text = path.read_text(encoding="utf-8", errors="ignore")
    rel_path = rel(path)
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    imports: list[str] = []
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return nodes, edges, imports

    file_id = node_id_for_file(rel_path)

    for item in ast.walk(tree):
        if isinstance(item, ast.Import):
            for alias in item.names:
                imports.append(alias.name)
        elif isinstance(item, ast.ImportFrom):
            if item.module:
                imports.append(item.module)
        elif isinstance(item, ast.ClassDef):
            class_id = f"class:{rel_path}:{item.name}"
            nodes.append(
                {
                    "id": class_id,
                    "type": "class",
                    "name": item.name,
                    "filePath": rel_path,
                    "summary": f"`{item.name}` 类，位于 {rel_path}，参与项目的审稿互动数据处理或 agent 工作流实现。",
                    "tags": tags_for_path(rel_path) + ["class"],
                    "startLine": item.lineno,
                    "endLine": getattr(item, "end_lineno", item.lineno),
                }
            )
            edges.append(edge(file_id, class_id, "contains", 1.0, "文件包含该类定义。"))
        elif isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if item.name.startswith("_") and item.name not in {"__init__", "__repr__"}:
                continue
            fn_type = "method" if isinstance(parent_class_name(tree, item), str) else "function"
            fn_id = f"{fn_type}:{rel_path}:{item.name}"
            nodes.append(
                {
                    "id": fn_id,
                    "type": "function" if fn_type == "function" else "function",
                    "name": item.name,
                    "filePath": rel_path,
                    "summary": f"`{item.name}` 函数/方法，位于 {rel_path}，是项目工作流、数据处理、API、测试或发布门禁的一部分。",
                    "tags": tags_for_path(rel_path) + ["function"],
                    "startLine": item.lineno,
                    "endLine": getattr(item, "end_lineno", item.lineno),
                }
            )
            edges.append(edge(file_id, fn_id, "contains", 1.0, "文件包含该函数定义。"))
    return nodes, edges, imports


def parent_class_name(tree: ast.AST, target: ast.AST) -> str | None:
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for child in node.body:
                if child is target:
                    return node.name
    return None


def node_id_for_file(rel_path: str) -> str:
    return f"{file_type(rel_path)}:{rel_path}"


def edge(source: str, target: str, type_: str, weight: float, description: str) -> dict[str, Any]:
    return {
        "source": source,
        "target": target,
        "type": type_,
        "weight": weight,
        "description": description,
    }


def import_to_file(import_name: str) -> str | None:
    if not import_name.startswith("peer_review_skills"):
        return None
    parts = import_name.split(".")
    candidate = ROOT / "src" / ("/".join(parts) + ".py")
    if candidate.exists():
        return rel(candidate)
    package_init = ROOT / "src" / "/".join(parts) / "__init__.py"
    if package_init.exists():
        return rel(package_init)
    return None


def layer_for_path(path: str) -> str:
    for layer_id, _, _, predicate in LAYER_RULES:
        if predicate(path):
            return layer_id
    return "layer:documentation-and-governance"


def build_graph() -> dict[str, Any]:
    files = iter_project_files()
    nodes: list[dict[str, Any]] = []
    edges: list[dict[str, Any]] = []
    imports_by_file: dict[str, list[str]] = {}
    file_ids: set[str] = set()

    for path in files:
        rel_path = rel(path)
        file_id = node_id_for_file(rel_path)
        file_ids.add(file_id)
        nodes.append(
            {
                "id": file_id,
                "type": file_type(rel_path),
                "name": rel_path,
                "filePath": rel_path,
                "summary": file_summary(rel_path),
                "tags": tags_for_path(rel_path),
                "languageNotes": "该节点摘要使用中文生成，技术模块名保留英文以便对应源码。",
            }
        )
        if path.suffix == ".py":
            child_nodes, child_edges, imports = parse_python(path)
            nodes.extend(child_nodes)
            edges.extend(child_edges)
            imports_by_file[rel_path] = imports

    for rel_path, imports in imports_by_file.items():
        source_id = node_id_for_file(rel_path)
        for import_name in imports:
            target_path = import_to_file(import_name)
            if not target_path:
                continue
            target_id = node_id_for_file(target_path)
            if target_id in file_ids and target_id != source_id:
                edges.append(edge(source_id, target_id, "imports", 0.7, f"{rel_path} 导入 {import_name}。"))

    concept_nodes = [
        (
            "concept:review-interaction-learning",
            "审稿互动学习",
            "项目核心概念：从 Nature 公开同行评审互动中学习 reviewer concern、author strategy、evidence action、tone/commitment 与 editor signal 的结构关系。",
            ["concept", "research-frame"],
        ),
        (
            "concept:responsible-author-assistance",
            "负责任作者回应辅助",
            "系统定位为 assistant：帮助作者理解、组织、检查回应，而不是代写、预测接收率或编造实验和证据。",
            ["concept", "responsible-ai"],
        ),
        (
            "concept:cross-disciplinary-lenses",
            "跨学科解释镜头",
            "把 tacit knowledge、institutional dependence、actor-network、fast/slow correction、tone/commitment 和 author agency 显式纳入 trace。",
            ["concept", "interdisciplinary"],
        ),
    ]
    for node_id, name, summary, tags in concept_nodes:
        nodes.append({"id": node_id, "type": "concept", "name": name, "summary": summary, "tags": tags})

    def link_if_exists(source_path: str, target: str, type_: str, description: str) -> None:
        source = node_id_for_file(source_path)
        if source in file_ids:
            edges.append(edge(source, target, type_, 0.6, description))

    link_if_exists("README.md", "concept:review-interaction-learning", "documents", "README 说明项目的审稿互动学习定位。")
    link_if_exists("docs/RESPONSIBLE_USE_zh.md", "concept:responsible-author-assistance", "documents", "Responsible Use 文档定义负责任使用边界。")
    link_if_exists("docs/INTERDISCIPLINARY_SYSTEM_FRAME_zh.md", "concept:cross-disciplinary-lenses", "documents", "跨学科系统框架文档定义解释镜头。")
    link_if_exists("src/peer_review_skills/agents/rebuttal_lens_workflow.py", "concept:review-interaction-learning", "implements", "RebuttalLens workflow 将审稿互动学习落到可执行 trace。")
    link_if_exists("src/peer_review_skills/agents/specialized_agents_part2.py", "concept:cross-disciplinary-lenses", "implements", "specialized_agents_part2 实现跨学科 lens 与 integrity gate。")
    link_if_exists("src/peer_review_skills/agents/specialized_agents_part2.py", "concept:responsible-author-assistance", "validates", "IntegrityAdequacyChecker 保护证据、承诺和可追溯边界。")

    layer_members: dict[str, list[str]] = defaultdict(list)
    for node in nodes:
        if node["type"] in {"file", "config", "document", "schema"}:
            layer_members[layer_for_path(node.get("filePath", ""))].append(node["id"])

    layers = [
        {
            "id": layer_id,
            "name": name,
            "description": description,
            "nodeIds": sorted(layer_members.get(layer_id, [])),
        }
        for layer_id, name, description, _ in LAYER_RULES
        if layer_members.get(layer_id)
    ]

    tour = [
        {
            "order": 1,
            "title": "从项目定位开始",
            "description": "先阅读 README、open-source plan 和 workflow 文档，理解项目不是普通 RAG 或自动代写，而是审稿互动学习与可追踪 assistant workflow。",
            "nodeIds": [
                "document:README.md",
                "document:docs/2026-05-26-open-source-review-interaction-agent-full-plan-zh.md",
                "document:docs/REBUTTAL_LENS_WORKFLOW_zh.md",
            ],
            "languageLesson": "中文图谱中保留 RebuttalLens、workflow、agent 等术语，便于和源码命名对齐。",
        },
        {
            "order": 2,
            "title": "理解用户入口",
            "description": "查看 pyproject console scripts 和 CLI main，理解用户如何运行 run-rebuttal-lens 以及 v0.1 build/validate 命令。",
            "nodeIds": ["config:pyproject.toml", "file:src/peer_review_skills/cli/main.py"],
        },
        {
            "order": 3,
            "title": "追踪 12-agent 主流程",
            "description": "从 rebuttal_lens_workflow 进入，沿 manuscript context、review understanding、case retrieval、evidence planning、tone calibration、cross-disciplinary lens 和 integrity gate 阅读。",
            "nodeIds": [
                "file:src/peer_review_skills/agents/rebuttal_lens_workflow.py",
                "file:src/peer_review_skills/agents/rebuttal_lens_agents.py",
                "file:src/peer_review_skills/agents/specialized_agents.py",
                "file:src/peer_review_skills/agents/specialized_agents_part2.py",
            ],
        },
        {
            "order": 4,
            "title": "理解数据到知识库的构建链",
            "description": "阅读 normalize、segment、annotate、align、taxonomy、execution build 模块，理解 v2709 案例如何转成 release-safe schema、taxonomy、KB、evaluation artifacts。",
            "nodeIds": [
                "file:src/peer_review_skills/execution/build_naturereview_v01.py",
                "file:src/peer_review_skills/align/pipeline.py",
                "file:src/peer_review_skills/taxonomy/pipeline.py",
                "file:src/peer_review_skills/schemas/interaction_unit.py",
            ],
        },
        {
            "order": 5,
            "title": "检查模型 API 和安全边界",
            "description": "查看 OpenAI-compatible client、responsible-use 文档和 limitation 文档，确认外部模型调用、API key、confidential manuscript 和 unsupported commitment 的边界。",
            "nodeIds": [
                "file:src/peer_review_skills/api/openai_compatible.py",
                "document:docs/RESPONSIBLE_USE_zh.md",
                "document:docs/MODEL_AND_AGENT_LIMITATIONS_zh.md",
            ],
        },
        {
            "order": 6,
            "title": "用测试理解发布门禁",
            "description": "最后阅读 tests，确认 README release surface、agent workflow、v0.1 acceptance、中文文档可读性和 API 边界都有回归保护。",
            "nodeIds": [
                "file:tests/test_rebuttal_lens_workflow.py",
                "file:tests/test_naturereview_v01_acceptance.py",
                "file:tests/test_multi_agent.py",
            ],
        },
    ]

    existing_node_ids = {node["id"] for node in nodes}
    for step in tour:
        step["nodeIds"] = [node_id for node_id in step["nodeIds"] if node_id in existing_node_ids]

    project = {
        "name": "Nature RebuttalLens",
        "languages": ["Python", "YAML", "Markdown"],
        "frameworks": ["OpenAI-compatible API", "pytest", "setuptools src-layout", "CodeGraph"],
        "description": "基于 Nature 透明同行评审互动案例的 manuscript-aware、跨学科 Author Rebuttal Assistant workflow。系统把审稿意见、作者回应、文本/Markdown/LaTeX/PDF/DOCX/DOC 原稿证据、证据动作、语气/承诺、编辑信号和 Responsible Use 组织成可记录、可追溯、可评估的多智能体流程。",
        "analyzedAt": datetime.now(timezone.utc).isoformat(),
        "gitCommitHash": run_git_hash(),
    }
    graph = {
        "version": "1.0.0",
        "project": project,
        "nodes": dedupe_nodes(nodes),
        "edges": dedupe_edges(edges),
        "layers": layers,
        "tour": tour,
    }
    return graph


def dedupe_nodes(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id: dict[str, dict[str, Any]] = {}
    for node in nodes:
        by_id.setdefault(node["id"], node)
    return list(by_id.values())


def dedupe_edges(edges: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen = set()
    output = []
    for item in edges:
        key = (item["source"], item["target"], item["type"])
        if key in seen:
            continue
        seen.add(key)
        output.append(item)
    return output


def write_summary(graph: dict[str, Any]) -> None:
    type_counts = Counter(node["type"] for node in graph["nodes"])
    edge_counts = Counter(edge["type"] for edge in graph["edges"])
    lines = [
        "# Nature RebuttalLens 中文知识图谱摘要",
        "",
        "由 `understand-anything:understand --full --language zh` 目标流程生成，主图文件为 `.understand-anything/knowledge-graph.json`。",
        "",
        "## 项目定位",
        "",
        graph["project"]["description"],
        "",
        "## 图谱统计",
        "",
        f"- 节点数：{len(graph['nodes'])}",
        f"- 边数：{len(graph['edges'])}",
        f"- 架构层：{len(graph['layers'])}",
        f"- 导览步骤：{len(graph['tour'])}",
        f"- 节点类型：{dict(type_counts)}",
        f"- 边类型：{dict(edge_counts)}",
        "",
        "## 架构层",
        "",
    ]
    for layer in graph["layers"]:
        lines.append(f"- **{layer['name']}**：{layer['description']}（{len(layer['nodeIds'])} 个文件级节点）")
    lines.extend(["", "## 推荐阅读路径", ""])
    for step in graph["tour"]:
        lines.append(f"{step['order']}. **{step['title']}**：{step['description']}")
    (OUT_DIR / "knowledge-graph-zh.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    OUT_DIR.mkdir(exist_ok=True)
    graph = build_graph()
    (OUT_DIR / "knowledge-graph.json").write_text(json.dumps(graph, ensure_ascii=False, indent=2), encoding="utf-8")
    (OUT_DIR / "config.json").write_text(
        json.dumps({"autoUpdate": False, "outputLanguage": "zh"}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    meta = {
        "lastAnalyzedAt": graph["project"]["analyzedAt"],
        "gitCommitHash": graph["project"]["gitCommitHash"],
        "version": graph["version"],
        "analyzedFiles": sum(1 for node in graph["nodes"] if node["type"] in {"file", "config", "document", "schema"}),
    }
    (OUT_DIR / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    write_summary(graph)
    print(
        json.dumps(
            {
                "knowledgeGraph": str(OUT_DIR / "knowledge-graph.json"),
                "summary": str(OUT_DIR / "knowledge-graph-zh.md"),
                "nodes": len(graph["nodes"]),
                "edges": len(graph["edges"]),
                "layers": len(graph["layers"]),
                "tour": len(graph["tour"]),
            },
            ensure_ascii=False,
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
