import json

import keel.plan as plan_mod
from keel.graph import CodeGraph
from keel.graphify import QueryNode, relevant_files, repo_map, _NODE_LINE
from keel.plan import plan_change, render_markdown


def _node(id_, label, file, file_type="code"):
    return {"id": id_, "label": label, "norm_label": label.lower(), "file_type": file_type, "source_file": file, "source_location": "L1"}


GRAPH = {
    "nodes": [
        _node("a", "retry_delay()", "pkg/client.py"),
        _node("b", "send()", "pkg/client.py"),
        _node("c", "main()", "pkg/cli.py"),
        _node("d", "test_send()", "tests/test_client.py"),
    ],
    "links": [
        {"source": "b", "target": "a", "relation": "calls"},
        {"source": "c", "target": "b", "relation": "calls"},
        {"source": "d", "target": "b", "relation": "calls"},
    ],
}


def test_node_line_parsing_and_relevant_files():
    line = "NODE .wait() [src=keel/client.py loc=L46 community=client.py]"
    m = _NODE_LINE.match(line)
    assert (m["label"], m["src"], m["loc"]) == (".wait()", "keel/client.py", "L46")

    nodes = [
        QueryNode("httpx", "", ""),  # external package: no source file
        QueryNode("_retry_delay()", "keel/client.py", "L56"),
        QueryNode("client.py", "keel/client.py", "L1"),  # file node: not a symbol
        QueryNode("Retries wait for the header.", "keel/client.py", "L2"),  # docstring: not a symbol
        QueryNode("main()", "keel/cli.py", "L9"),
    ]
    files = relevant_files(nodes)
    assert files == {"keel/client.py": ["_retry_delay()"], "keel/cli.py": ["main()"]}
    assert "keel/client.py: _retry_delay()" in repo_map(files)


def test_relevant_files_caps_files_but_keeps_symbols_of_included_ones():
    nodes = [QueryNode(f"f{i}()", f"f{i}.py", "L1") for i in range(5)] + [QueryNode("extra()", "f0.py", "L2")]
    files = relevant_files(nodes, max_files=3)
    assert list(files) == ["f0.py", "f1.py", "f2.py"] and files["f0.py"] == ["f0()", "extra()"]


def test_ripple_lists_dependents_outside_the_file():
    graph = CodeGraph.from_dict(GRAPH)
    assert graph.ripple("pkg/client.py", ["retry_delay"]) == ["pkg/cli.py", "tests/test_client.py"]
    assert graph.ripple("pkg/cli.py") == []


def test_ripple_ignores_imports_and_docs():
    # Regression: on psf/requests, following imports and doc references flagged 15 unrelated files.
    data = {
        "nodes": GRAPH["nodes"]
        + [
            _node("e", "importer()", "pkg/other.py"),
            _node("f", "README.md", "README.md", file_type="document"),
        ],
        "links": GRAPH["links"]
        + [
            {"source": "e", "target": "a", "relation": "imports_from"},
            {"source": "f", "target": "a", "relation": "references"},
            {"source": "f", "target": "a", "relation": "calls"},  # even a call from a non-code node is not ripple
        ],
    }
    assert CodeGraph.from_dict(data).ripple("pkg/client.py", ["retry_delay"]) == ["pkg/cli.py", "tests/test_client.py"]


def test_plan_change_end_to_end_with_repaired_hallucination(tmp_path, monkeypatch, scripted):
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(GRAPH), encoding="utf-8")
    monkeypatch.setattr(plan_mod, "query_nodes", lambda path, q: [QueryNode("retry_delay()", "pkg/client.py", "L1")])

    bad = {"summary": "Honor Retry-After", "files": [{"path": "pkg/clinet.py", "reason": "wait", "symbols": ["retry_delay"]}]}
    good = {"summary": "Honor Retry-After", "files": [{"path": "pkg/client.py", "reason": "wait", "symbols": ["retry_delay"]}]}
    backend = scripted([json.dumps(bad), json.dumps(good)])

    report = plan_change(backend, tmp_path, "Retry-After is ignored", graph_path=graph_path)
    assert report.ok and report.grounded and report.calls == 2
    assert report.files[0].path == "pkg/client.py"
    assert report.ripple_files == ["pkg/cli.py", "tests/test_client.py"]
    assert report.risk == "low"
    # the first prompt carried Graphify's relevant subgraph, not the whole repo
    assert "pkg/client.py: retry_delay()" in backend.calls[0][1]["content"]

    text = render_markdown(report)
    assert "every cited file exists" in text and "pkg/cli.py" in text


def test_unverifiable_symbols_are_pruned_not_rejected(tmp_path, monkeypatch, scripted):
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(GRAPH), encoding="utf-8")
    monkeypatch.setattr(plan_mod, "query_nodes", lambda path, q: [])
    plan = {"summary": "s", "files": [{"path": "pkg/client.py", "reason": "r", "symbols": ["retry_delay", "timeout_param"]}]}
    backend = scripted([json.dumps(plan)])
    report = plan_change(backend, tmp_path, "x", graph_path=graph_path)
    assert report.ok and report.calls == 1  # no repair round for a parameter name
    assert report.files[0].symbols == ["retry_delay"] and report.pruned_symbols == 1
    assert "1 unverifiable symbol(s) left out" in render_markdown(report)


def test_unguided_plan_marks_invented_files(tmp_path, scripted):
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(GRAPH), encoding="utf-8")
    plan = {"summary": "s", "files": [{"path": "pkg/client.py", "reason": "r"}, {"path": "src/made_up.py", "reason": "r"}]}
    backend = scripted([json.dumps(plan)])
    result = plan_mod.unguided_plan(backend, graph_path, "x")
    assert result.files == [("pkg/client.py", True), ("src/made_up.py", False)] and result.invented == 1
    assert len(backend.calls) == 1  # one unguided call, no repair
    text = plan_mod.render_unguided(result)
    assert "✓ `pkg/client.py`" in text and "✗ `src/made_up.py`" in text and "1 of 2 cited files do not exist" in text


def test_unguided_plan_survives_garbage(tmp_path, scripted):
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(GRAPH), encoding="utf-8")
    result = plan_mod.unguided_plan(scripted(["no idea"]), graph_path, "x")
    assert not result.ok and "did not produce a usable plan" in plan_mod.render_unguided(result)


def test_plan_report_when_model_never_gives_a_plan(tmp_path, monkeypatch, scripted):
    graph_path = tmp_path / "graph.json"
    graph_path.write_text(json.dumps(GRAPH), encoding="utf-8")
    monkeypatch.setattr(plan_mod, "query_nodes", lambda path, q: [])
    report = plan_change(scripted(["no", "no", "no"]), tmp_path, "x", graph_path=graph_path)
    assert not report.ok and report.files == []
    assert "did not produce a usable plan" in render_markdown(report)
