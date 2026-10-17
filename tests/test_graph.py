from keel import structured
from keel.graph import CHANGE_PLAN_SCHEMA, CodeGraph, grounded_plan_verifier, normalize_path


def _node(id_, label, file, file_type="code"):
    return {
        "id": id_,
        "label": label,
        "norm_label": label.lower(),
        "file_type": file_type,
        "source_file": file,
        "source_location": "L1",
    }


def _edge(src, tgt, relation="calls"):
    return {"source": src, "target": tgt, "relation": relation, "confidence": "EXTRACTED"}


# Labels mirror real Graphify output: classes "Agent", functions "name()", methods ".name()",
# plus docstring nodes (file_type "rationale") whose label is prose.
# run_cli() -> Agent -> structured() -> iter_json()
GRAPH = CodeGraph.from_dict(
    {
        "nodes": [
            _node("cli_run", "run_cli()", "keel/cli.py"),
            _node("agent_run", "Agent", "keel/agent.py"),
            _node("agent_method", ".run()", "keel/agent.py"),
            _node("harness_structured", "structured()", "keel/harness.py"),
            _node("extract_iter", "iter_json()", "keel/extract.py"),
            _node("harness_doc", "The core loop: generate then repair.", "keel/harness.py", "rationale"),
        ],
        "links": [
            _edge("cli_run", "agent_run"),
            _edge("agent_run", "harness_structured"),
            _edge("harness_structured", "extract_iter"),
            _edge("agent_run", "cli_run", relation="contains"),  # structural: must be ignored
        ],
    }
)


def test_normalize_path():
    assert normalize_path(".\\keel\\agent.py") == "keel/agent.py"


def test_find_is_case_insensitive_and_file_scoped():
    assert GRAPH.find("STRUCTURED")[0]["id"] == "harness_structured"
    assert GRAPH.find("structured", file="keel/agent.py") == []


def test_blast_radius_walks_callers_transitively():
    result = GRAPH.blast_radius("iter_json", depth=3)
    assert result["defined_in"] == ["keel/extract.py"]
    assert result["affected_files"] == ["keel/agent.py", "keel/cli.py", "keel/harness.py"]
    assert [a["distance"] for a in result["affected"]] == [1, 2, 3]


def test_find_matches_graphify_label_shapes_and_skips_docstring_nodes():
    assert GRAPH.find("iter_json")[0]["id"] == "extract_iter"  # label is "iter_json()"
    assert GRAPH.find("run", file="keel/agent.py")[0]["id"] == "agent_method"  # label is ".run()"
    assert GRAPH.find("The core loop: generate then repair.") == []


def test_find_understands_qualified_names():
    # Regression: models write "Agent.run" or "agent.run", the graph stores class "Agent" and method ".run()".
    assert GRAPH.find("Agent.run", file="keel/agent.py")[0]["id"] == "agent_method"
    assert GRAPH.find("agent.run", file="keel/agent.py")[0]["id"] == "agent_method"  # module qualifier
    assert GRAPH.find("keel.agent.Agent.run")[0]["id"] == "agent_method"
    assert GRAPH.find("Nonexistent.run", file="keel/agent.py") == []
    assert GRAPH.find("Agent.missing", file="keel/agent.py") == []


def test_blast_radius_respects_depth_and_ignores_structural_edges():
    result = GRAPH.blast_radius("iter_json", depth=1)
    assert result["affected_files"] == ["keel/harness.py"]
    assert GRAPH.blast_radius("run_cli")["affected"] == []


def test_suggestions():
    assert "keel/harness.py" in GRAPH.suggest_files("keel/harnes.py")
    assert "structured" in GRAPH.suggest_symbols("structurd")


def test_grounded_verifier_rejects_hallucinated_file_with_suggestion():
    verify = grounded_plan_verifier(GRAPH)
    problem = verify({"summary": "x", "files": [{"path": "keel/harnes.py", "reason": "r"}]})
    assert "does not exist" in problem and "keel/harness.py" in problem


def test_grounded_verifier_rejects_unknown_symbol():
    verify = grounded_plan_verifier(GRAPH)
    plan = {"summary": "x", "files": [{"path": "keel/harness.py", "reason": "r", "symbols": ["structurd"]}]}
    assert "not defined in" in verify(plan) and "structured" in verify(plan)


def test_grounded_verifier_accepts_real_plan():
    verify = grounded_plan_verifier(GRAPH)
    plan = {"summary": "x", "files": [{"path": ".\\keel\\harness.py", "reason": "r", "symbols": ["Structured"]}]}
    assert verify(plan) is None


def test_end_to_end_repair_of_hallucinated_path(scripted):
    bad = '{"summary": "Fix retry", "files": [{"path": "keel/harnes.py", "reason": "retry logic"}]}'
    good = '{"summary": "Fix retry", "files": [{"path": "keel/harness.py", "reason": "retry logic"}]}'
    backend = scripted([bad, good])
    result = structured(backend, "Plan the change", CHANGE_PLAN_SCHEMA, verify=grounded_plan_verifier(GRAPH))
    assert result.ok and result.calls == 2
    assert result.attempts[0].stage == "verify"
    assert "keel/harness.py" in backend.calls[1][-1]["content"]
