# Graph Report - keel  (2026-10-17)

## Corpus Check
- 44 files · ~23,122 words
- Verdict: corpus is large enough that graph structure adds value.
- Unclassified: 4 file(s) not represented in the graph (top: (none) 2, .example 1, .log 1)

## Summary
- 420 nodes · 981 edges · 20 communities (15 shown, 5 thin omitted)
- Extraction: 94% EXTRACTED · 6% INFERRED · 0% AMBIGUOUS · INFERRED: 63 edges (avg confidence: 0.9)
- Token cost: 0 input · 0 output

## Graph Freshness
- Built from commit: `d634ece0`
- Run `git rev-parse HEAD` and compare to check if the graph is stale.
- Run `graphify update .` after code changes (no API cost).

## Community Hubs (Navigation)
- test_bench.py
- client.py
- keel/__init__.py
- CodeGraph
- plan.py
- keel/__init__.py
- cli.py
- Keel
- .claude/CLAUDE.md
- Agent
- structured
- Keel build notes
- extract.py
- keel-harness
- _bench_run
- Demo guide (5 minutes)
- schema_errors
- ScriptedBackend
- demo-compare-requests.md
- Backend

## God Nodes (most connected - your core abstractions)
1. `structured()` - 32 edges
2. `CodeGraph` - 27 edges
3. `BackendError` - 24 edges
4. `plan_change()` - 22 edges
5. `Backend` - 20 edges
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
- `test_bad_arguments_are_repaired_within_the_step()` --calls--> `Agent`  [EXTRACTED]
  tests/test_agent.py → keel/agent.py
- `test_step_budget_is_enforced()` --calls--> `Agent`  [EXTRACTED]
  tests/test_agent.py → keel/agent.py
- `test_tool_then_final()` --calls--> `Agent`  [EXTRACTED]
  tests/test_agent.py → keel/agent.py

## Import Cycles
- None detected.

## Communities (20 total, 5 thin omitted)

### Community 0 - "test_bench.py"
Cohesion: 0.07
Nodes (34): is_valid(), naive_parse(), norm(), Outcome, run_mode(), ExtractTask, run_task(), score() (+26 more)

### Community 1 - "client.py"
Cohesion: 0.07
Nodes (27): backend_from_env(), BackendError, _env_float(), GeminiBackend, _HttpBackend, OpenAICompatBackend, _retry_delay(), _Throttle (+19 more)

### Community 2 - "keel/__init__.py"
Cohesion: 0.23
Nodes (5): AgentRun, Step, Attempt, _repair_message(), Result

### Community 3 - "CodeGraph"
Cohesion: 0.07
Nodes (16): canonical_symbol(), check_plan(), CodeGraph, _did_you_mean(), grounded_plan_verifier(), _is_symbol(), normalize_path(), PlanCheck (+8 more)

### Community 4 - "plan.py"
Cohesion: 0.17
Nodes (13): PlannedFile, PlanReport, fetch_issues(), Issue, parse_repo(), render_table(), triage(), TriageRow (+5 more)

### Community 5 - "keel/__init__.py"
Cohesion: 0.20
Nodes (13): extract_json(), ExtractError, test_braces_inside_strings_do_not_break_scanning(), test_markdown_fence(), test_no_json_raises(), test_plain_json(), test_prose_around_object(), test_python_literals_repaired() (+5 more)

### Community 6 - "cli.py"
Cohesion: 0.09
Nodes (29): _ask(), _bench_report(), _describe(), main(), _models(), _ping(), _plan(), _triage() (+21 more)

### Community 7 - "Keel"
Cohesion: 0.05
Nodes (36): extract, gemma-4-26b-a4b-it, Keel benchmark report, tools, gemma-4-26b-a4b-it, grounding-files, grounding-none, Keel benchmark report (+28 more)

### Community 9 - "Agent"
Cohesion: 0.24
Nodes (8): Agent, Tool, _tool(), test_bad_arguments_are_repaired_within_the_step(), test_step_budget_is_enforced(), test_tool_exception_becomes_an_observation(), test_tool_then_final(), test_unknown_tool_is_rejected_with_the_tool_list()

### Community 10 - "structured"
Cohesion: 0.23
Nodes (8): build_messages(), structured(), test_first_try_success(), test_gives_up_after_max_attempts(), test_picks_the_schema_valid_candidate_among_several(), test_repairs_schema_violation_and_feeds_back_the_error(), test_repairs_unparseable_reply(), test_semantic_verifier_triggers_repair()

### Community 11 - "Keel build notes"
Cohesion: 0.50
Nodes (3): Keel build notes, Not done, Status

### Community 12 - "extract.py"
Cohesion: 0.24
Nodes (5): _balanced_spans(), iter_json(), _parse(), _span_end(), test_multiple_candidates_are_all_yielded()

### Community 14 - "_bench_run"
Cohesion: 0.29
Nodes (6): _frac(), render(), _bench_run(), progress(), save(), progress()

### Community 15 - "Demo guide (5 minutes)"
Cohesion: 0.25
Nodes (7): Before going on stage, Demo guide (5 minutes), If something fails, One sentence, Questions you may get, Script, Where each prize track shows up

### Community 18 - "demo-compare-requests.md"
Cohesion: 0.33
Nodes (5): Check these too (they depend on the code above), Files to change, Plan: Add a default timeout setting on Session so users do not have to pass timeout= on every request, With Keel (graph-grounded), Without Keel (one unguided call)

## Knowledge Gaps
- **1 isolated node(s):** `keel-harness`
  These have ≤1 connection - possible missing edges or undocumented components. (Counts symbols only; 141 node(s) total have ≤1 connection when file, concept and rationale nodes are included.)
- **5 thin communities (<3 nodes) omitted from report** — run `graphify query` to explore isolated nodes.

## Suggested Questions
_Questions this graph is uniquely positioned to answer:_

- **Why does `structured()` connect `structured` to `test_bench.py`, `keel/__init__.py`, `CodeGraph`, `cli.py`, `Keel`, `schema_errors`, `Backend`?**
  _High betweenness centrality (0.162) - this node is a cross-community bridge._
- **Are the 3 inferred relationships involving `structured()` (e.g. with `Backend` and `.chat()`) actually correct?**
  _`structured()` has 3 INFERRED edges - model-reasoned connections that need verification._
- **What connects `keel-harness` to the rest of the system?**
  _1 weakly-connected nodes found - possible documentation gaps or missing edges._
- **Should `test_bench.py` be split into smaller, more focused modules?**
  _Cohesion score 0.06672519754170325 - nodes in this community are weakly interconnected._
- **Why does `Notes` connect `Keel` to `structured`?**
  _High betweenness centrality (0.088) - this node is a cross-community bridge._
- **Are the 7 inferred relationships involving `CodeGraph` (e.g. with `build_prompt()` and `load_graph()`) actually correct?**
  _`CodeGraph` has 7 INFERRED edges - model-reasoned connections that need verification._
- **Should `client.py` be split into smaller, more focused modules?**
  _Cohesion score 0.07272727272727272 - nodes in this community are weakly interconnected._