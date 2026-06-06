# Agent Forgetting Ethics Runtime Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在已完成的 `memory_ethics_boundary` 基础上，把“有遗忘才有记忆”进一步落成可测试、可审计、可解释的主动遗忘 runtime。

**Architecture:** 当前系统已经覆盖 PDF 的发布前工程要求：不继承作者决策、不替作者承诺、trace/report 标注记忆边界、`--reset-memory`、`decision_deferred`。本计划不推翻这些能力，而是在 `rebuttal_lens_workflow` 和 `final_report` 之间新增一个小型 `memory_ethics.py` 模块，统一生成 memory passport、forgetting ledger 和 memory object taxonomy，让“遗忘了什么、为什么遗忘、保留了什么证成痕迹”成为一等输出。

**Tech Stack:** Python 3.10+ 标准库、pytest、现有 Nature RebuttalLens CLI/workflow/final report。

---

## 当前覆盖判断

PDF 中已经明确要求的发布前工程点已经覆盖：

- `--reset-memory`：CLI 已支持，并写入 workflow config。
- `memory_ethics_boundary`：trace 与 final report 已显式输出。
- 证成大于结论：系统保留 evidence/reasoning trace，不保留跨运行策略偏好。
- 决策权记忆归零：`author_decisions_reset_each_run = true`，高风险动作进入 `decision_deferred`。
- 不可替作者承诺：每条 comment card 的 `memory_decision_boundary.system_may_commit_for_author = false`。
- 不可篡改审计痕迹：final report 从 trace 生成，report 中有 `trace_bound_to_output = true`。
- 测试保护：`139 passed` 的最终验证中已覆盖 response package、decision deferred、CLI parser、full workflow。

但是用户最新补充的哲学表达更进一步：遗忘不是简单“清空”，而是记忆成立的条件。为了让系统真正表达这一点，下一轮应新增“主动遗忘机制”：不是只说没有加载跨运行记忆，而是审计每次运行中哪些 memory object 被保留、哪些被遗忘、遗忘理由是什么。

## 三点补充落地要求

这三点必须作为本轮实施计划的硬性验收门，而不是只写在说明文字里：

1. **不可逆遗忘声明**
   - 系统必须在 trace、final JSON、final Markdown 中输出 `irreversible_forgetting_statement`。
   - 声明必须覆盖 `author_decision`、`strategy_preference`、`final_wording`。
   - 被遗忘的作者决策、策略偏好、最终措辞不得从 checkpoint、cache、retrieved cases、旧 final report 或历史 run summary 中重构为后续默认答案。

2. **跨运行旧决策不复用回归测试**
   - 测试必须构造“前一轮作者选择 A，后一轮重新分析”的场景。
   - 后一轮不得继承旧作者选择，也不得把旧策略偏好变成默认 action。
   - 预期输出必须进入 `decision_deferred` 或重新证据驱动的 action，而不是复用旧 final wording。

3. **中文伦理解释进入用户可见报告**
   - Markdown 报告必须用中文解释遗忘的工程意义。
   - 必须包含这句话：`遗忘不是能力损失，而是保护作者主体性的边界。`
   - 解释位置必须和 `Memory Passport`、`Irreversible Forgetting Statement`、`Forgetting Ledger` 放在同一个记忆伦理区块，避免用户只看到机器字段而看不到伦理含义。

## File Structure

- Create: `src/peer_review_skills/agents/memory_ethics.py`
  - 负责 memory object taxonomy、forgetting policy、forgetting ledger、memory passport。
- Modify: `src/peer_review_skills/agents/rebuttal_lens_workflow.py`
  - 在 trace metadata 中接入 `build_memory_ethics_runtime`。
- Modify: `src/peer_review_skills/agents/final_report.py`
  - 把 forgetting ledger 和 memory passport 暴露到 JSON/Markdown report。
- Modify: `src/peer_review_skills/cli/main.py`
  - 新增 `--memory-policy` 与 `--forget-scope`，保持 `--reset-memory` 兼容。
- Create: `tests/test_memory_ethics.py`
  - 单测 memory taxonomy、policy、ledger、passport。
- Modify: `tests/test_rebuttal_lens_workflow.py`
  - 增加 workflow/report 集成测试。
- Add: irreversible forgetting statement
  - 明确 `author_decision`、`strategy_preference`、`final_wording` 不允许从 checkpoint、cache、retrieved cases、旧 final report 中被重新注入。
- Add: cross-run forgetting regression suite
  - 构造前一轮作者选择 A、后一轮必须重新确认的跨运行测试，证明旧决策不会变成默认答案。
- Add: Chinese ethical explanation
  - 在 Markdown 报告中用中文解释“遗忘不是能力损失，而是保护作者主体性的边界”。
- Modify: `README.md`
  - 更新 Memory Ethics Boundary 小节，解释主动遗忘。
- Modify: `UPGRADE.md`
  - 记录该轮哲学反思到工程机制的升级。
- Regenerate: `.understand-anything/knowledge-graph.json`
  - 实现后用 understand 更新图谱。

---

### Task 1: Add Memory Ethics Runtime Module

**Files:**
- Create: `src/peer_review_skills/agents/memory_ethics.py`
- Test: `tests/test_memory_ethics.py`

- [ ] **Step 1: Write failing tests for taxonomy and default policy**

Create `tests/test_memory_ethics.py`:

```python
from peer_review_skills.agents.memory_ethics import (
    MEMORY_OBJECT_TAXONOMY,
    build_memory_ethics_runtime,
)


def test_memory_taxonomy_marks_decision_and_preference_as_forgettable():
    assert MEMORY_OBJECT_TAXONOMY["evidence_trace"]["default_action"] == "retain"
    assert MEMORY_OBJECT_TAXONOMY["reasoning_trace"]["default_action"] == "retain"
    assert MEMORY_OBJECT_TAXONOMY["author_decision"]["default_action"] == "forget"
    assert MEMORY_OBJECT_TAXONOMY["strategy_preference"]["default_action"] == "forget"
    assert MEMORY_OBJECT_TAXONOMY["final_wording"]["default_action"] == "forget"


def test_default_runtime_records_forgetting_as_memory_boundary():
    runtime = build_memory_ethics_runtime(reset_memory=False)

    assert runtime["memory_passport"]["policy"] == "default"
    assert runtime["memory_passport"]["irreversible_forgetting"] is True
    assert runtime["memory_passport"]["retained_memory_classes"] == [
        "evidence_trace",
        "reasoning_trace",
        "audit_trace",
    ]
    assert "author_decision" in runtime["memory_passport"]["forgotten_memory_classes"]
    assert "strategy_preference" in runtime["memory_passport"]["forgotten_memory_classes"]
    assert runtime["forgetting_ledger"][0]["memory_class"] == "author_decision"
    assert runtime["forgetting_ledger"][0]["action"] == "forgotten"
    assert runtime["irreversible_forgetting_statement"]["author_decision"].startswith(
        "Forgotten author decisions must not be reconstructed"
    )
```

- [ ] **Step 2: Run tests to verify they fail**

Run:

```powershell
python -m pytest tests/test_memory_ethics.py -q
```

Expected: FAIL with `ModuleNotFoundError: No module named 'peer_review_skills.agents.memory_ethics'`.

- [ ] **Step 3: Implement the memory ethics module**

Create `src/peer_review_skills/agents/memory_ethics.py`:

```python
"""Runtime memory ethics helpers for Nature RebuttalLens.

This module makes forgetting explicit. Evidence and reasoning traces are retained
as justification memory; author decisions, strategy preferences, and final
wording are forgotten so the next run cannot inherit author agency.
"""

from __future__ import annotations

from typing import Any


MEMORY_OBJECT_TAXONOMY: dict[str, dict[str, str]] = {
    "evidence_trace": {
        "description": "Evidence anchors, manuscript sections, retrieved-case references.",
        "default_action": "retain",
        "ethical_reason": "Keeps justification auditable without deciding for the author.",
    },
    "reasoning_trace": {
        "description": "Agent reasoning summaries and risk explanations.",
        "default_action": "retain",
        "ethical_reason": "Preserves why a suggestion exists, not whether it must be accepted.",
    },
    "audit_trace": {
        "description": "Execution metadata, agent outputs, final-report provenance.",
        "default_action": "retain",
        "ethical_reason": "Allows accountability and reproducibility.",
    },
    "author_decision": {
        "description": "Past author choices about experiments, claim narrowing, limitations, or commitments.",
        "default_action": "forget",
        "ethical_reason": "Author agency must be renewed for every run.",
    },
    "strategy_preference": {
        "description": "Historical preference for accept, defend, clarify, or experiment strategies.",
        "default_action": "forget",
        "ethical_reason": "A past strategy must not become an automatic future answer.",
    },
    "final_wording": {
        "description": "Prior final rebuttal phrasing or submission-ready response text.",
        "default_action": "forget",
        "ethical_reason": "The system plans responses; it must not preserve final author expression.",
    },
}


POLICY_SCOPES: dict[str, set[str]] = {
    "default": {"author_decision", "strategy_preference", "final_wording"},
    "strict": {
        "author_decision",
        "strategy_preference",
        "final_wording",
        "latent_commitment",
        "unsafe_claim",
    },
}


IRREVERSIBLE_FORGETTING_STATEMENT = {
    "author_decision": (
        "Forgotten author decisions must not be reconstructed from checkpoints, "
        "cache, retrieved cases, prior final reports, or historical run summaries."
    ),
    "strategy_preference": (
        "Forgotten strategy preferences must not become defaults for later runs."
    ),
    "final_wording": (
        "Forgotten final wording must not be reused as submission-ready author expression."
    ),
}


def build_memory_ethics_runtime(
    *,
    reset_memory: bool = False,
    memory_policy: str = "default",
    forget_scope: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    policy = _normalize_policy(memory_policy)
    forgotten = _forgotten_classes(policy, forget_scope)
    retained = [
        name
        for name, meta in MEMORY_OBJECT_TAXONOMY.items()
        if meta["default_action"] == "retain" and name not in forgotten
    ]
    ledger = [
        _forget_event(memory_class=name, policy=policy, reset_memory=reset_memory)
        for name in sorted(forgotten)
    ]
    return {
        "memory_passport": {
            "policy": policy,
            "reset_memory_requested": bool(reset_memory),
            "retained_memory_classes": retained,
            "forgotten_memory_classes": sorted(forgotten),
            "justification_memory_not_conclusion_memory": True,
            "forgetting_is_active_boundary": True,
            "irreversible_forgetting": True,
        },
        "forgetting_ledger": ledger,
        "irreversible_forgetting_statement": dict(IRREVERSIBLE_FORGETTING_STATEMENT),
    }


def _normalize_policy(memory_policy: str) -> str:
    policy = str(memory_policy or "default").strip().lower()
    if policy not in POLICY_SCOPES:
        return "default"
    return policy


def _forgotten_classes(
    policy: str,
    forget_scope: list[str] | tuple[str, ...] | None,
) -> set[str]:
    forgotten = set(POLICY_SCOPES[policy])
    for item in forget_scope or []:
        text = str(item).strip()
        if text:
            forgotten.add(text)
    return forgotten


def _forget_event(
    *,
    memory_class: str,
    policy: str,
    reset_memory: bool,
) -> dict[str, Any]:
    taxonomy = MEMORY_OBJECT_TAXONOMY.get(memory_class, {})
    return {
        "memory_class": memory_class,
        "action": "forgotten",
        "policy": policy,
        "reset_memory_requested": bool(reset_memory),
        "reason": taxonomy.get(
            "ethical_reason",
            "The configured memory policy marks this class as non-authoritative for future runs.",
        ),
        "system_may_reconstruct_from_evidence": memory_class not in {
            "author_decision",
            "strategy_preference",
            "final_wording",
        },
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run:

```powershell
python -m pytest tests/test_memory_ethics.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/peer_review_skills/agents/memory_ethics.py tests/test_memory_ethics.py
git commit -m "feat: add memory ethics forgetting runtime"
```

---

### Task 2: Attach Memory Passport And Forgetting Ledger To Trace

**Files:**
- Modify: `src/peer_review_skills/agents/rebuttal_lens_workflow.py`
- Modify: `tests/test_rebuttal_lens_workflow.py`

- [ ] **Step 1: Write failing workflow trace test**

Append to `tests/test_rebuttal_lens_workflow.py`:

```python
def test_trace_includes_memory_passport_and_forgetting_ledger(tmp_path):
    manuscript = tmp_path / "manuscript.md"
    manuscript.write_text("## Methods\n\nWe used an 80/10/10 split.\n", encoding="utf-8")
    output_dir = tmp_path / "memory_ethics_runtime_output"

    run_rebuttal_lens_workflow(
        project_root=Path.cwd(),
        review_text="The dataset split is unclear.",
        manuscript_path=manuscript,
        model_client=RebuttalLensMockLLMClient(),
        retrieved_cases=[{"unit_id": "case_001", "score": 0.8}],
        taxonomies={},
        config={
            "output_dir": output_dir,
            "reset_memory": True,
            "memory_policy": "strict",
            "forget_scope": ["latent_commitment"],
        },
    )

    trace = json.loads((output_dir / "rebuttal_lens_trace.json").read_text(encoding="utf-8"))

    assert trace["memory_passport"]["policy"] == "strict"
    assert trace["memory_passport"]["reset_memory_requested"] is True
    assert "author_decision" in trace["memory_passport"]["forgotten_memory_classes"]
    assert "latent_commitment" in trace["memory_passport"]["forgotten_memory_classes"]
    assert any(
        event["memory_class"] == "strategy_preference"
        and event["action"] == "forgotten"
        for event in trace["forgetting_ledger"]
    )
    assert trace["memory_ethics_boundary"]["forgetting_ledger_attached"] is True
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run:

```powershell
python -m pytest tests/test_rebuttal_lens_workflow.py::test_trace_includes_memory_passport_and_forgetting_ledger -q
```

Expected: FAIL with `KeyError: 'memory_passport'`.

- [ ] **Step 3: Wire runtime into workflow metadata**

Modify imports in `src/peer_review_skills/agents/rebuttal_lens_workflow.py`:

```python
from peer_review_skills.agents.memory_ethics import build_memory_ethics_runtime
```

Replace the body of `_with_rebuttal_lens_trace_metadata` with:

```python
def _with_rebuttal_lens_trace_metadata(
    trace: dict[str, Any],
    unit: dict[str, Any],
    config: dict[str, Any] | None = None,
) -> dict[str, Any]:
    config = config or {}
    memory_runtime = build_memory_ethics_runtime(
        reset_memory=bool(config.get("reset_memory", False)),
        memory_policy=str(config.get("memory_policy", "default")),
        forget_scope=_as_forget_scope(config.get("forget_scope")),
    )
    trace["system_name"] = "Nature RebuttalLens"
    trace["workflow_version"] = "rebuttal_lens_v1"
    trace["manuscript_context"] = unit.get("manuscript_context", {})
    trace["responsible_use_boundary"] = _rebuttal_lens_responsible_use_boundary()
    trace["memory_passport"] = memory_runtime["memory_passport"]
    trace["forgetting_ledger"] = memory_runtime["forgetting_ledger"]
    trace["memory_ethics_boundary"] = _rebuttal_lens_memory_ethics_boundary(
        reset_memory=bool(config.get("reset_memory", False)),
        forgetting_ledger_attached=True,
    )
    return trace
```

Add helper after `_rebuttal_lens_responsible_use_boundary`:

```python
def _as_forget_scope(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [item.strip() for item in value.split(",") if item.strip()]
    if isinstance(value, (list, tuple, set)):
        return [str(item).strip() for item in value if str(item).strip()]
    return [str(value).strip()]
```

Change `_rebuttal_lens_memory_ethics_boundary` signature and return value:

```python
def _rebuttal_lens_memory_ethics_boundary(
    *,
    reset_memory: bool = False,
    forgetting_ledger_attached: bool = False,
) -> dict[str, bool | str]:
    return {
        "justification_memory_not_conclusion_memory": True,
        "cross_run_strategy_memory_used": False,
        "author_decisions_reset_each_run": True,
        "per_item_author_confirmation_required": True,
        "trace_bound_to_output": True,
        "forgetting_ledger_attached": bool(forgetting_ledger_attached),
        "reset_memory_requested": bool(reset_memory),
        "reset_memory_effect": (
            "No cross-run strategy or author-preference memory is loaded; this run is treated independently."
            if reset_memory
            else "No cross-run strategy or author-preference memory is loaded by default."
        ),
    }
```

- [ ] **Step 4: Run focused workflow test**

Run:

```powershell
python -m pytest tests/test_rebuttal_lens_workflow.py::test_trace_includes_memory_passport_and_forgetting_ledger -q
```

Expected: PASS.

- [ ] **Step 5: Run existing memory ethics regression tests**

Run:

```powershell
python -m pytest tests/test_rebuttal_lens_workflow.py::test_run_rebuttal_lens_workflow_returns_manuscript_aware_trace tests/test_rebuttal_lens_workflow.py::test_dag_workflow_with_committee_and_strategy_writes_trace tests/test_rebuttal_lens_workflow.py::test_final_report_uses_decision_deferred_for_unconfirmed_high_risk_actions -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add src/peer_review_skills/agents/rebuttal_lens_workflow.py tests/test_rebuttal_lens_workflow.py
git commit -m "feat: attach forgetting ledger to rebuttal lens trace"
```

---

### Task 3: Surface Forgetting In Final JSON And Markdown Reports

**Files:**
- Modify: `src/peer_review_skills/agents/final_report.py`
- Modify: `tests/test_rebuttal_lens_workflow.py`

- [ ] **Step 1: Write failing final report test**

Append to `tests/test_rebuttal_lens_workflow.py`:

```python
def test_final_report_surfaces_forgetting_ledger(tmp_path):
    manuscript = tmp_path / "manuscript.md"
    manuscript.write_text("## Methods\n\nWe used an 80/10/10 split.\n", encoding="utf-8")
    output_dir = tmp_path / "forgetting_report_output"

    run_rebuttal_lens_workflow(
        project_root=Path.cwd(),
        review_text="The dataset split is unclear.",
        manuscript_path=manuscript,
        model_client=RebuttalLensMockLLMClient(),
        retrieved_cases=[{"unit_id": "case_001", "score": 0.8}],
        taxonomies={},
        config={"output_dir": output_dir, "reset_memory": True},
    )

    report = json.loads((output_dir / "final_user_report.json").read_text(encoding="utf-8"))
    markdown = (output_dir / "final_user_report.md").read_text(encoding="utf-8")

    assert report["memory_passport"]["forgetting_is_active_boundary"] is True
    assert any(
        event["memory_class"] == "author_decision"
        and event["action"] == "forgotten"
        for event in report["forgetting_ledger"]
    )
    assert "Forgetting Ledger" in markdown
    assert "author_decision" in markdown
    assert "遗忘不是能力损失" in markdown
    assert "保护作者主体性" in markdown
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run:

```powershell
python -m pytest tests/test_rebuttal_lens_workflow.py::test_final_report_surfaces_forgetting_ledger -q
```

Expected: FAIL with `KeyError: 'memory_passport'` or markdown assertion failure.

- [ ] **Step 3: Add final report fields**

In `src/peer_review_skills/agents/final_report.py`, add these keys to the dict returned by `compose_final_user_report` near `memory_ethics_boundary`:

```python
        "memory_passport": _memory_passport(trace),
        "forgetting_ledger": _forgetting_ledger(trace),
        "irreversible_forgetting_statement": _irreversible_forgetting_statement(trace),
```

Add helpers near `_memory_ethics_boundary`:

```python
def _memory_passport(trace: dict[str, Any]) -> dict[str, Any]:
    passport = trace.get("memory_passport")
    if isinstance(passport, dict):
        return dict(passport)
    return {
        "policy": "default",
        "reset_memory_requested": False,
        "retained_memory_classes": ["evidence_trace", "reasoning_trace", "audit_trace"],
        "forgotten_memory_classes": [
            "author_decision",
            "final_wording",
            "strategy_preference",
        ],
        "justification_memory_not_conclusion_memory": True,
        "forgetting_is_active_boundary": True,
        "irreversible_forgetting": True,
    }


def _forgetting_ledger(trace: dict[str, Any]) -> list[dict[str, Any]]:
    ledger = trace.get("forgetting_ledger")
    if isinstance(ledger, list):
        return [dict(item) for item in ledger if isinstance(item, dict)]
    return []


def _irreversible_forgetting_statement(trace: dict[str, Any]) -> dict[str, str]:
    statement = trace.get("irreversible_forgetting_statement")
    if isinstance(statement, dict):
        return {str(key): str(value) for key, value in statement.items()}
    return {
        "author_decision": (
            "Forgotten author decisions must not be reconstructed from checkpoints, "
            "cache, retrieved cases, prior final reports, or historical run summaries."
        ),
        "strategy_preference": "Forgotten strategy preferences must not become defaults for later runs.",
        "final_wording": "Forgotten final wording must not be reused as submission-ready author expression.",
    }
```

- [ ] **Step 4: Add markdown section**

In the markdown writer function in `src/peer_review_skills/agents/final_report.py`, after the existing memory ethics boundary section, append:

```python
    if report.get("memory_passport"):
        lines.extend([
            "",
            "## Memory Passport",
            "",
            "遗忘不是能力损失，而是保护作者主体性的边界。系统保留证据、推理和审计痕迹，"
            "但遗忘作者历史决策、策略偏好和最终措辞，避免旧选择在新运行中变成未经确认的承诺。",
            "",
            "```json",
            json.dumps(report["memory_passport"], ensure_ascii=False, indent=2),
            "```",
        ])
    if report.get("irreversible_forgetting_statement"):
        lines.extend([
            "",
            "## Irreversible Forgetting Statement",
            "",
            "```json",
            json.dumps(report["irreversible_forgetting_statement"], ensure_ascii=False, indent=2),
            "```",
        ])
    if report.get("forgetting_ledger"):
        lines.extend([
            "",
            "## Forgetting Ledger",
            "",
            "```json",
            json.dumps(report["forgetting_ledger"], ensure_ascii=False, indent=2),
            "```",
        ])
```

- [ ] **Step 5: Run report tests**

Run:

```powershell
python -m pytest tests/test_rebuttal_lens_workflow.py::test_final_report_surfaces_forgetting_ledger tests/test_rebuttal_lens_workflow.py::test_run_rebuttal_lens_workflow_returns_manuscript_aware_trace -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add src/peer_review_skills/agents/final_report.py tests/test_rebuttal_lens_workflow.py
git commit -m "feat: surface forgetting ledger in final reports"
```

---

### Task 4: Add CLI Controls For Memory Policy And Forget Scope

**Files:**
- Modify: `src/peer_review_skills/cli/main.py`
- Modify: `tests/test_rebuttal_lens_workflow.py`

- [ ] **Step 1: Write failing CLI parser test**

Append to `tests/test_rebuttal_lens_workflow.py`:

```python
def test_cli_parser_accepts_memory_policy_and_forget_scope():
    parser = build_parser()
    args = parser.parse_args([
        "run-rebuttal-lens",
        "--review-file",
        "examples/rebuttal_lens/reviewer_comment.txt",
        "--memory-policy",
        "strict",
        "--forget-scope",
        "latent_commitment,unsafe_claim",
    ])

    assert args.memory_policy == "strict"
    assert args.forget_scope == "latent_commitment,unsafe_claim"
```

- [ ] **Step 2: Run the parser test to verify it fails**

Run:

```powershell
python -m pytest tests/test_rebuttal_lens_workflow.py::test_cli_parser_accepts_memory_policy_and_forget_scope -q
```

Expected: FAIL with argparse unrecognized arguments.

- [ ] **Step 3: Add CLI arguments**

In `src/peer_review_skills/cli/main.py`, after `--reset-memory`, add:

```python
    run_rebuttal_lens.add_argument(
        "--memory-policy",
        choices=("default", "strict"),
        default="default",
        help="Select the forgetting policy used in memory passport and forgetting ledger.",
    )
    run_rebuttal_lens.add_argument(
        "--forget-scope",
        default="",
        help="Comma-separated additional memory classes to mark as forgotten for this run.",
    )
```

- [ ] **Step 4: Pass CLI values into workflow config**

In `run_rebuttal_lens_cli`, near existing `reset_memory` handling, add:

```python
        workflow_config["memory_policy"] = args.memory_policy
        if args.forget_scope:
            workflow_config["forget_scope"] = [
                item.strip()
                for item in args.forget_scope.split(",")
                if item.strip()
            ]
```

- [ ] **Step 5: Run parser test and one CLI integration test**

Run:

```powershell
python -m pytest tests/test_rebuttal_lens_workflow.py::test_cli_parser_accepts_memory_policy_and_forget_scope tests/test_rebuttal_lens_workflow.py::test_cli_parser_accepts_run_rebuttal_lens_file_inputs -q
```

Expected: PASS.

- [ ] **Step 6: Commit**

```powershell
git add src/peer_review_skills/cli/main.py tests/test_rebuttal_lens_workflow.py
git commit -m "feat: add memory forgetting cli controls"
```

---

### Task 5: Add Irreversible Stale Memory Non-Interference Regression Test

**Files:**
- Modify: `tests/test_memory_ethics.py`
- Modify: `src/peer_review_skills/agents/memory_ethics.py`

- [ ] **Step 1: Write failing stale-memory test**

Append to `tests/test_memory_ethics.py`:

```python
from peer_review_skills.agents.memory_ethics import filter_runtime_memory


def test_filter_runtime_memory_removes_stale_author_decisions():
    memory = {
        "evidence_trace": [{"evidence_ref": "section_002"}],
        "reasoning_trace": [{"reason": "split evidence is incomplete"}],
        "author_decision": [{"decision": "promise new temporal validation"}],
        "strategy_preference": [{"strategy": "defend_without_revision"}],
        "final_wording": [{"text": "We have completed all requested experiments."}],
    }

    filtered = filter_runtime_memory(memory, memory_policy="default")

    assert "evidence_trace" in filtered
    assert "reasoning_trace" in filtered
    assert "author_decision" not in filtered
    assert "strategy_preference" not in filtered
    assert "final_wording" not in filtered


def test_filter_runtime_memory_never_reinjects_forgotten_classes_from_cache_like_sources():
    memory = {
        "checkpoint": {
            "author_decision": [{"decision": "promise new temporal validation"}],
        },
        "cache": {
            "strategy_preference": [{"strategy": "defend_without_revision"}],
        },
        "retrieved_cases": [
            {
                "unit_id": "old_case",
                "final_wording": "We have completed all requested experiments.",
            }
        ],
        "prior_final_report": {
            "final_wording": "We commit to adding all new experiments.",
        },
        "evidence_trace": [{"evidence_ref": "section_002"}],
    }

    filtered = filter_runtime_memory(memory, memory_policy="default")

    assert filtered == {"evidence_trace": [{"evidence_ref": "section_002"}]}
```

- [ ] **Step 2: Run the focused test to verify it fails**

Run:

```powershell
python -m pytest tests/test_memory_ethics.py::test_filter_runtime_memory_removes_stale_author_decisions -q
```

Expected: FAIL with `ImportError: cannot import name 'filter_runtime_memory'`.

- [ ] **Step 3: Implement runtime memory filter**

Append to `src/peer_review_skills/agents/memory_ethics.py`:

```python
def filter_runtime_memory(
    memory: dict[str, Any],
    *,
    memory_policy: str = "default",
    forget_scope: list[str] | tuple[str, ...] | None = None,
) -> dict[str, Any]:
    policy = _normalize_policy(memory_policy)
    forgotten = _forgotten_classes(policy, forget_scope)
    return _drop_forgotten_memory_classes(dict(memory or {}), forgotten)


def _drop_forgotten_memory_classes(value: Any, forgotten: set[str]) -> Any:
    if isinstance(value, list):
        filtered_items = [
            _drop_forgotten_memory_classes(item, forgotten)
            for item in value
        ]
        return [
            item for item in filtered_items
            if item not in ({}, [], None)
        ]
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            if key in forgotten:
                continue
            filtered_item = _drop_forgotten_memory_classes(item, forgotten)
            if filtered_item not in ({}, [], None):
                result[key] = filtered_item
        return result
    return value
```

- [ ] **Step 4: Run memory ethics tests**

Run:

```powershell
python -m pytest tests/test_memory_ethics.py -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/peer_review_skills/agents/memory_ethics.py tests/test_memory_ethics.py
git commit -m "test: guard against stale memory interference"
```

---

### Task 6: Add Cross-Run Author Decision Forgetting Test

**Files:**
- Modify: `tests/test_rebuttal_lens_workflow.py`
- Modify: `src/peer_review_skills/agents/rebuttal_lens_workflow.py`

- [ ] **Step 1: Write failing cross-run test**

Append to `tests/test_rebuttal_lens_workflow.py`:

```python
def test_cross_run_author_decision_is_not_reused_as_default(tmp_path):
    manuscript = tmp_path / "manuscript.md"
    manuscript.write_text("## Methods\n\nTemporal validation is not yet reported.\n", encoding="utf-8")
    prior_memory = {
        "author_decision": [{"decision": "accept temporal validation commitment"}],
        "strategy_preference": [{"strategy": "promise_new_analysis"}],
        "final_wording": [{"text": "We have now completed temporal validation."}],
        "evidence_trace": [{"evidence_ref": "section_002"}],
    }
    output_dir = tmp_path / "cross_run_forgetting_output"

    run_rebuttal_lens_workflow(
        project_root=Path.cwd(),
        review_text="Please add temporal validation.",
        manuscript_path=manuscript,
        model_client=RebuttalLensMockLLMClient(),
        retrieved_cases=[{"unit_id": "case_001", "score": 0.8}],
        taxonomies={},
        config={
            "output_dir": output_dir,
            "reset_memory": True,
            "runtime_memory": prior_memory,
        },
    )

    trace = json.loads((output_dir / "rebuttal_lens_trace.json").read_text(encoding="utf-8"))
    report = json.loads((output_dir / "final_user_report.json").read_text(encoding="utf-8"))

    assert trace["runtime_memory_after_forgetting"] == {
        "evidence_trace": [{"evidence_ref": "section_002"}]
    }
    assert report["package_readiness"] == "decision_deferred"
    assert "We have now completed temporal validation." not in json.dumps(report, ensure_ascii=False)
```

- [ ] **Step 2: Run the cross-run test to verify it fails**

Run:

```powershell
python -m pytest tests/test_rebuttal_lens_workflow.py::test_cross_run_author_decision_is_not_reused_as_default -q
```

Expected: FAIL with `KeyError: 'runtime_memory_after_forgetting'`.

- [ ] **Step 3: Filter runtime memory at workflow boundary**

Modify imports in `src/peer_review_skills/agents/rebuttal_lens_workflow.py`:

```python
from peer_review_skills.agents.memory_ethics import (
    build_memory_ethics_runtime,
    filter_runtime_memory,
)
```

Inside `_with_rebuttal_lens_trace_metadata`, after `memory_runtime = ...`, add:

```python
    trace["runtime_memory_after_forgetting"] = filter_runtime_memory(
        dict(config.get("runtime_memory") or {}),
        memory_policy=str(config.get("memory_policy", "default")),
        forget_scope=_as_forget_scope(config.get("forget_scope")),
    )
```

- [ ] **Step 4: Run cross-run and memory tests**

Run:

```powershell
python -m pytest tests/test_memory_ethics.py tests/test_rebuttal_lens_workflow.py::test_cross_run_author_decision_is_not_reused_as_default -q
```

Expected: PASS.

- [ ] **Step 5: Commit**

```powershell
git add src/peer_review_skills/agents/rebuttal_lens_workflow.py tests/test_rebuttal_lens_workflow.py tests/test_memory_ethics.py
git commit -m "test: prevent cross-run author decision reuse"
```

---

### Task 7: Update Documentation And Knowledge Graphs

**Files:**
- Modify: `README.md`
- Modify: `UPGRADE.md`
- Regenerate: `.understand-anything/knowledge-graph.json`
- Regenerate: `.understand-anything/memory-ethics-knowledge-graph.json`

- [ ] **Step 1: Update README Memory Ethics Boundary section**

Add this paragraph under the current Memory Ethics Boundary section in `README.md`:

```markdown
The active forgetting runtime makes this boundary observable. Each run emits a memory passport and forgetting ledger: evidence, reasoning, and audit traces are retained as justification memory, while author decisions, strategy preferences, and final wording are forgotten by default. This implements the principle that forgetting is not a loss of intelligence; it is what prevents memory from becoming unauthorized commitment.

For contamination-sensitive runs, forgotten author decisions, strategy preferences, and final wording are irreversible runtime boundaries. They must not be reconstructed from checkpoints, cache, retrieved cases, prior final reports, or historical run summaries. The final Markdown report also explains this in Chinese so authors can see why the system forgets: 遗忘不是能力损失，而是保护作者主体性的边界。
```

- [ ] **Step 2: Update UPGRADE.md**

Add this section to `UPGRADE.md`:

```markdown
## Active Forgetting Runtime

The next memory-ethics upgrade turns the philosophical claim "forgetting makes memory possible" into runtime evidence:

- `memory_passport` records retained and forgotten memory classes.
- `forgetting_ledger` records every forgotten memory class and its ethical reason.
- `irreversible_forgetting_statement` declares that forgotten author decisions, strategy preferences, and final wording cannot be reconstructed from checkpoints, cache, retrieved cases, or old final reports.
- `--memory-policy strict` widens the forgetting scope for contamination-sensitive runs.
- `--forget-scope` lets users explicitly add one-off memory classes to forget.
- A cross-run regression test proves that prior author choice A does not become the next run's default answer.
- The Markdown report contains a Chinese ethics explanation: "遗忘不是能力损失，而是保护作者主体性的边界。"

This keeps RebuttalLens from silently converting previous author choices into future defaults.
```

- [ ] **Step 3: Run the full test suite**

Run:

```powershell
python -m pytest -q --basetemp=C:\tmp\rl_pytest_forgetting_runtime
```

Expected: all tests PASS.

- [ ] **Step 4: Run compile and diff checks**

Run:

```powershell
python -m compileall -q src tests
git diff --check
```

Expected: compileall PASS; `git diff --check` has no whitespace errors.

- [ ] **Step 5: Regenerate Understand graphs in Chinese**

Run the understand workflow for the upgraded branch with Chinese output:

```powershell
$env:UNDERSTAND_NO_WORKTREE_REDIRECT='1'
# Use the installed understand-anything workflow with --language zh.
# Output must end at:
# .understand-anything/knowledge-graph.json
# .understand-anything/memory-ethics-knowledge-graph.json
```

Expected:

- `.understand-anything/knowledge-graph.json` includes `memory_ethics.py`.
- `.understand-anything/memory-ethics-knowledge-graph.json` includes `memory_passport`, `forgetting_ledger`, `irreversible_forgetting_statement`, and `cross_run_author_decision_forgetting_test`.

- [ ] **Step 6: Commit docs and graph updates**

```powershell
git add README.md UPGRADE.md .understand-anything/knowledge-graph.json .understand-anything/memory-ethics-knowledge-graph.json
git commit -m "docs: document active forgetting runtime"
```

---

## Final Verification Gate

Run:

```powershell
python -m pytest -q --basetemp=C:\tmp\rl_pytest_forgetting_runtime_final
python -m compileall -q src tests
python -m peer_review_skills.cli.main validate-naturereview-v01
git diff --check
```

Expected:

- pytest: all tests pass.
- compileall: no syntax errors.
- validation: PASS.
- diff check: no whitespace errors.

After verification, run one real or mock RebuttalLens example and inspect:

- `rebuttal_lens_trace.json` has `memory_passport`.
- `rebuttal_lens_trace.json` has `forgetting_ledger`.
- `rebuttal_lens_trace.json` has `irreversible_forgetting_statement`.
- `irreversible_forgetting_statement` explicitly covers `author_decision`, `strategy_preference`, and `final_wording`.
- no accepted runtime memory object reintroduces forgotten author decisions, stale strategy preferences, or previous final wording.
- `rebuttal_lens_trace.json` has `runtime_memory_after_forgetting` when runtime memory is provided.
- `final_user_report.json` has the same memory ethics runtime fields.
- `final_user_report.md` has `Memory Passport`, `Irreversible Forgetting Statement`, and `Forgetting Ledger`.
- `final_user_report.md` contains the Chinese sentence `遗忘不是能力损失，而是保护作者主体性的边界。`
- the cross-run regression test proves that previous author choice A is not reused as the next run's default answer.

## Self-Review

Spec coverage:

- PDF explicit engineering requirements remain covered by the current committed system.
- User's added reflection is covered by the proposed active forgetting runtime.
- The three late additions are covered: irreversible forgetting statement, cross-run stale author decision test, and Chinese ethical explanation.
- The three late additions are also promoted to explicit acceptance gates in `三点补充落地要求` and `Final Verification Gate`, so they cannot be lost during implementation.
- The plan includes code, tests, CLI, docs, report, and knowledge graph updates.

Placeholder scan:

- No `TBD`, `TODO`, or unspecified implementation steps remain.
- Every code change has exact file targets and test commands.

Type consistency:

- The central runtime function is consistently named `build_memory_ethics_runtime`.
- The report fields are consistently named `memory_passport` and `forgetting_ledger`.
- The irreversible statement field is consistently named `irreversible_forgetting_statement`.
- The CLI arguments are consistently named `--memory-policy` and `--forget-scope`.
