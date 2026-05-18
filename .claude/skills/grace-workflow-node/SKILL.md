---
name: grace-workflow-node
description: Use when the user wants to add, modify, or debug a node in the Grace techspec LangGraph (`src/workflows/techspec/`). Covers the state schema, node signature, conditional-edge routing, and how to thread a new option through CLI → workflow.execute → node. Read-only guidance; the user does the editing.
---

# Add or modify a node in the TechSpec LangGraph

The tech-spec pipeline is a LangGraph state machine in [src/workflows/techspec/workflow.py](src/workflows/techspec/workflow.py). Nodes are pure functions over a TypedDict state. Adding a new stage means: state field → node function → registration → edge routing → CLI flag → propagation.

## When to use

User asks to:
- "Add a step that does X to the techspec pipeline"
- "Why is the workflow going to `output` instead of `mock_server`?"
- "Add a new CLI flag that triggers a new stage"
- "Refactor the conditional edges"

## The pipeline (current shape)

```
START
  ├─ folder set? ─► llm_analysis
  └─ otherwise   ─► collect_urls ─► crawling ─► llm_analysis
                                                    │
                          ┌── enhance flag ──► enhance_spec ─► field_analysis ──┐
                          │                                                       │
                          └── (otherwise) ────────────────────────────────────► (mock_server flag?) ─► output ─► END
```

Source of truth: [src/workflows/techspec/workflow.py:14-95](src/workflows/techspec/workflow.py:14).

## State

Defined in [src/workflows/techspec/states/techspec_state.py](src/workflows/techspec/states/techspec_state.py) as a `TypedDict`.

- **Inputs** populated by `TechspecWorkflow.execute`: `connector_name`, `urls_file`, `folder`, `output_dir`, `mock_server`, `enhance`, `config`, `test_only`, `verbose`.
- **Accumulated by nodes**: `urls`, `visited_urls`, `markdown_files`, `tech_spec`, `enhanced_spec`, `field_analysis`, `mock_server_data`, `final_output`, `validation_results`.
- **Error state**: `errors` (list of accumulated errors per node) and `error` (top-level fatal). Workflow continues past most node failures; check both at the end.
- **Metadata**: free-form dict, kicked off with `workflow_started` and `timestamp`.

If you add a new node that produces data, add a field to `TechspecWorkflowState` for it.

## Node signature

```python
def my_node(state: TechspecWorkflowState) -> TechspecWorkflowState:
    # 1. Read what you need from state
    # 2. Do work — catch exceptions and append to state["errors"], do not raise
    # 3. Return the (mutated) state dict
    return state
```

For async work (like `mock_server`):

```python
async def my_node(state: TechspecWorkflowState) -> TechspecWorkflowState:
    ...
```

Then in `workflow.py`, register with an `asyncio.run` lambda:
```python
workflow.add_node("my_node", lambda state: asyncio.run(my_node(state)))
```

Nodes live in [src/workflows/techspec/nodes/](src/workflows/techspec/nodes/) and are re-exported by [nodes/__init__.py](src/workflows/techspec/nodes/__init__.py). Add the import there too.

## Edges

Three kinds:

1. **Unconditional edge**: `workflow.add_edge("a", "b")` — always go a → b.
2. **Conditional edge**: `workflow.add_conditional_edges("a", router_fn, {"name": "next_node"})`. The router returns a string key matching one of the values.
3. **Terminal**: `workflow.add_edge("end", END)`.

Routers are private methods on `TechspecWorkflow` ([workflow.py:99-136](src/workflows/techspec/workflow.py:99)). Pattern:

```python
def _should_continue_after_my_node(self, state) -> Literal["next_a", "next_b", "end"]:
    if state.get("errors"):
        return "end"
    if state.get("my_flag") and state.get("tech_spec"):
        return "next_a"
    return "next_b"
```

Order conditionals carefully — they short-circuit. Match the existing convention: check error → check feature flag → fall through.

## Adding a new CLI flag

Flag flow: `cli.py` → `run_techspec_workflow` → `TechspecWorkflow.execute` → `initial_state` → node reads `state["my_flag"]`.

1. In [src/cli.py:36](src/cli.py:36) area, add `@click.option('--my-flag', is_flag=True, help='...')` and add the parameter to `techspec(...)`.
2. Pass it to `run_techspec_workflow(...)` in [src/cli.py:70](src/cli.py:70).
3. Plumb it through [src/workflows/__init__.py](src/workflows/__init__.py) into `TechspecWorkflow.execute(...)`.
4. Set it on `initial_state` in [src/workflows/techspec/workflow.py:155](src/workflows/techspec/workflow.py:155).
5. Read it in the conditional edge router or node body.

## Wiring a new node — full checklist

1. [ ] Add field(s) to `TechspecWorkflowState`.
2. [ ] Write `my_node` in `src/workflows/techspec/nodes/my_node.py`.
3. [ ] Export from `nodes/__init__.py`.
4. [ ] Import in `workflow.py` (top of file).
5. [ ] `workflow.add_node("my_node", my_node)` in `_build_workflow_graph`.
6. [ ] Add an incoming edge (or conditional) and an outgoing edge (or conditional).
7. [ ] If gated by a flag: add CLI flag, plumb to `execute`, set on `initial_state`.
8. [ ] If gated by a flag: update the upstream router to branch to `my_node` when the flag is set.
9. [ ] Run `grace techspec ... -v` to smoke-test; check `state["errors"]` and the verbose log.

## Anti-patterns

- **Raising from a node.** Nodes accumulate errors in `state["errors"]`; raising bypasses error handling. Use `try/except` and append.
- **Mutating state via aliases.** LangGraph snapshots state between nodes — assign back to keys explicitly (`state["foo"] = bar`), don't mutate nested objects in place and expect persistence.
- **Adding side effects in routers.** Routers must be pure and fast. They are called between every transition.
- **Skipping the `nodes/__init__.py` re-export.** Imports in `workflow.py` go through `__init__.py`; forgetting this hides the new node.
- **Forgetting `Literal[...]` in router type hints.** LangGraph uses these for graph validation; missing keys are caught at compile time.

## Reference flow for a hypothetical new node

To add a `summarize_spec` node that runs after `llm_analysis` when `--summary` is passed:

1. State: add `spec_summary: Optional[str]` to `TechspecWorkflowState`.
2. CLI: add `@click.option('--summary', is_flag=True)`. Plumb to `execute(summary=summary)`. Set `"summary": summary` in `initial_state`.
3. Node: `nodes/summarize_spec.py` reads `state["tech_spec"]`, calls `AIService().generate(...)`, sets `state["spec_summary"]`.
4. Register: `workflow.add_node("summarize_spec", summarize_spec)`.
5. Router: update `_should_continue_after_llm` to branch to `summarize_spec` when `state.get("summary")` is true.
6. Edge: `workflow.add_edge("summarize_spec", "output")` (or route into existing branches).
7. Smoke test.
