# Graph Report - keel  (2026-10-17)

## Corpus Check
- 42 files · ~21,436 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 4 file(s) not represented in the graph (top: (none) 2, .example 1, .log 1)

## Summary
- 398 nodes · 945 edges · 11 communities (9 shown, 2 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 60 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `b977a372`
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
- .claude/CLAUDE.md
- Keel build notes
- keel-harness

## God Nodes (most connected - your core abstractions)
1. `structured()` - 31 edges
2. `CodeGraph` - 26 edges
3. `BackendError` - 24 edges
4. `plan_change()` - 22 edges
5. `Backend` - 19 edges
6. `extract_json()` - 18 edges
7. `Agent` - 17 edges
8. `backend_from_env()` - 17 edges
9. `run_mode()` - 16 edges
10. `GeminiBackend` - 16 edges

## Surprising Connections (you probably didn't know these)
- `Notes` --references--> `structured()`  [INFERRED]
  skills/keel-structured-output/SKILL.md → keel/harness.py
- `Notes` --references--> `verify()`  [INFERRED]
  skills/keel-structured-output/SKILL.md → keel/graph.py
- `chat()` --calls--> `BackendError`  [EXTRACTED]
  tests/test_bench.py → keel/client.py
- `test_fetch_issues_reports_api_errors()` --uses--> `BackendError`  [INFERRED]
  tests/test_triage.py → keel/client.py
- `test_multiple_candidates_are_all_yielded()` --calls--> `iter_json()`  [EXTRACTED]
  tests/test_extract.py → keel/extract.py

## Import Cycles
- None detected.

## Communities (11 total, 2 thin omitted)

### Community 0 - "test_bench.py"
Cohesion: 0.07
Nodes (30): is_valid(), naive_parse(), norm(), Outcome, run_mode(), ExtractTask, run_task(), score() (+22 more)

### Community 1 - "client.py"
Cohesion: 0.08
Nodes (24): backend_from_env(), BackendError, _env_float(), GeminiBackend, _HttpBackend, OpenAICompatBackend, _retry_delay(), _Throttle (+16 more)

### Community 2 - "structured"
Cohesion: 0.06
Nodes (27): Agent, AgentRun, Step, Tool, _tool(), _balanced_spans(), iter_json(), _parse() (+19 more)

### Community 3 - "CodeGraph"
Cohesion: 0.06
Nodes (21): build_prompt(), IssueTask, load_graph(), run_task(), score(), canonical_symbol(), check_plan(), CodeGraph (+13 more)

### Community 4 - "plan.py"
Cohesion: 0.11
Nodes (26): QueryNode, relevant_files(), repo_map(), plan_change(), PlannedFile, PlanReport, render_markdown(), fetch_issues() (+18 more)

### Community 5 - "keel/__init__.py"
Cohesion: 0.12
Nodes (16): extract_json(), ExtractError, scripted(), ScriptedBackend, test_braces_inside_strings_do_not_break_scanning(), test_markdown_fence(), test_multiple_candidates_are_all_yielded(), test_no_json_raises() (+8 more)

### Community 6 - "cli.py"
Cohesion: 0.11
Nodes (20): _frac(), render(), _ask(), _bench_report(), _bench_run(), progress(), save(), _describe() (+12 more)

### Community 7 - "Keel"
Cohesion: 0.05
Nodes (36): extract, gemma-4-26b-a4b-it, Keel benchmark report, tools, gemma-4-26b-a4b-it, grounding-files, grounding-none, Keel benchmark report (+28 more)

### Community 11 - "Keel build notes"
Cohesion: 0.50
Nodes (3): Keel build notes, Not done, Status

## Knowledge Gaps
- **1 isolated node(s):** `keel-harness`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 129 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **2 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `structured()` connect `structured` to `test_bench.py`, `CodeGraph`, `plan.py`, `cli.py`, `Keel`?**
  _High betweenness centrality (0.172) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `structured()` (e.g. with `Backend` and `.chat()`) actually correct?**
  _`structured()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `keel-harness` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_bench.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06821787414066631 - nodes in this community are weakly interconnected._
- **Why does `Notes` connect `Keel` to `structured`?**
  _High betweenness centrality (0.095) - this node is a cross-community bridge._
- **Are the 6 inferred relationships involving `CodeGraph` (e.g. with `build_prompt()` and `load_graph()`) actually correct?**
  _`CodeGraph` has 6 INFERRED edges - model-reasoned connections that need verification._
- **Should `client.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07918552036199095 - nodes in this community are weakly interconnected._