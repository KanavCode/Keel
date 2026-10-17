# Graph Report - keel  (2026-10-17)

## Corpus Check
- 34 files · ~15,743 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 3 file(s) not represented in the graph (top: (none) 2, .example 1)

## Summary
- 358 nodes · 831 edges · 14 communities (12 shown, 2 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 52 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `bc70d626`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_bench.py
- client.py
- structured
- CodeGraph
- plan.py
- keel/__init__.py
- cli.py
- Keel
- ScriptedBackend
- Plan a change with Keel and Graphify
- gemma-4-26b-a4b-it
- Keel build plan
- Plan: Add a default timeout setting on Session so users do not have to pass timeout= on every request
- keel-harness

## God Nodes (most connected - your core abstractions)
1. `structured()` - 31 edges
2. `CodeGraph` - 25 edges
3. `BackendError` - 20 edges
4. `plan_change()` - 20 edges
5. `extract_json()` - 18 edges
6. `Agent` - 17 edges
7. `Backend` - 17 edges
8. `run_mode()` - 16 edges
9. `GeminiBackend` - 16 edges
10. `backend_from_env()` - 16 edges

## Surprising Connections (you probably didn't know these)
- `Notes` --references--> `structured()`  [INFERRED]
  skills/keel-structured-output/SKILL.md → keel/harness.py
- `Notes` --references--> `verify()`  [INFERRED]
  skills/keel-structured-output/SKILL.md → keel/graph.py
- `test_bad_arguments_are_repaired_within_the_step()` --calls--> `Agent`  [EXTRACTED]
  tests/test_agent.py → keel/agent.py
- `test_step_budget_is_enforced()` --calls--> `Agent`  [EXTRACTED]
  tests/test_agent.py → keel/agent.py
- `test_tool_then_final()` --calls--> `Agent`  [EXTRACTED]
  tests/test_agent.py → keel/agent.py

## Import Cycles
- None detected.

## Communities (14 total, 2 thin omitted)

### Community 0 - "test_bench.py"
Cohesion: 0.07
Nodes (34): is_valid(), naive_parse(), norm(), Outcome, run_mode(), ExtractTask, run_task(), score() (+26 more)

### Community 1 - "client.py"
Cohesion: 0.07
Nodes (26): backend_from_env(), BackendError, _env_float(), GeminiBackend, _HttpBackend, OpenAICompatBackend, _retry_delay(), _Throttle (+18 more)

### Community 2 - "structured"
Cohesion: 0.07
Nodes (25): Agent, AgentRun, Step, Tool, _tool(), Backend, Attempt, build_messages() (+17 more)

### Community 3 - "CodeGraph"
Cohesion: 0.07
Nodes (16): canonical_symbol(), check_plan(), CodeGraph, _did_you_mean(), grounded_plan_verifier(), _is_symbol(), normalize_path(), PlanCheck (+8 more)

### Community 4 - "plan.py"
Cohesion: 0.13
Nodes (18): build_graph(), clone_repo(), find_graphify(), GraphifyError, query_nodes(), QueryNode, relevant_files(), repo_map() (+10 more)

### Community 5 - "keel/__init__.py"
Cohesion: 0.12
Nodes (18): _balanced_spans(), extract_json(), ExtractError, iter_json(), _parse(), _span_end(), test_braces_inside_strings_do_not_break_scanning(), test_markdown_fence() (+10 more)

### Community 6 - "cli.py"
Cohesion: 0.20
Nodes (10): _frac(), render(), _ask(), _bench_report(), _bench_run(), _describe(), main(), _models() (+2 more)

### Community 7 - "Keel"
Cohesion: 0.13
Nodes (13): verify(), Agent skill, Benchmark: raw model vs Keel, Development, How it works, Keel, License, Quick start (+5 more)

### Community 9 - "Plan a change with Keel and Graphify"
Cohesion: 0.33
Nodes (5): Exit codes, Notes, Plan a change with Keel and Graphify, Steps, When to use

### Community 10 - "gemma-4-26b-a4b-it"
Cohesion: 0.40
Nodes (4): extract, gemma-4-26b-a4b-it, Keel benchmark report, tools

### Community 11 - "Keel build plan"
Cohesion: 0.40
Nodes (4): Inference without DigitalOcean credits, Keel build plan, Phases, Rules checklist

### Community 12 - "Plan: Add a default timeout setting on Session so users do not have to pass timeout= on every request"
Cohesion: 0.50
Nodes (3): Check these too (they depend on the code above), Files to change, Plan: Add a default timeout setting on Session so users do not have to pass timeout= on every request

## Knowledge Gaps
- **1 isolated node(s):** `keel-harness`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 118 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `structured()` connect `structured` to `test_bench.py`, `client.py`, `CodeGraph`, `plan.py`, `keel/__init__.py`, `cli.py`, `Keel`?**
  _High betweenness centrality (0.125) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `structured()` (e.g. with `Backend` and `.chat()`) actually correct?**
  _`structured()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `keel-harness` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_bench.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06672519754170325 - nodes in this community are weakly interconnected._
- **Why does `CodeGraph` connect `CodeGraph` to `test_bench.py`, `plan.py`, `keel/__init__.py`?**
  _High betweenness centrality (0.085) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `CodeGraph` (e.g. with `build_prompt()` and `load_graph()`) actually correct?**
  _`CodeGraph` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Should `client.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07207792207792207 - nodes in this community are weakly interconnected._