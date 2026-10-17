"""keel plan: turn an issue into a graph-grounded change plan with a blast-radius estimate."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from .client import Backend
from .graph import CHANGE_PLAN_SCHEMA, CodeGraph, check_plan, grounded_plan_verifier
from .graphify import build_graph, query_nodes, relevant_files, repo_map
from .harness import Attempt, structured


@dataclass
class PlannedFile:
    path: str
    reason: str
    symbols: list[str]
    ripple: list[str]  # other files that depend on this change


@dataclass
class PlanReport:
    issue: str
    ok: bool
    summary: str = ""
    files: list[PlannedFile] = field(default_factory=list)
    grounded: bool = False
    calls: int = 0
    attempts: list[Attempt] = field(default_factory=list)
    graph_nodes: int = 0
    pruned_symbols: int = 0  # cited symbols not found in the graph (may be parameters or variables)

    @property
    def ripple_files(self) -> list[str]:
        planned = {f.path for f in self.files}
        return sorted({r for f in self.files for r in f.ripple} - planned)

    @property
    def risk(self) -> str:
        n = len(self.ripple_files)
        return "low" if n <= 2 else "medium" if n <= 6 else "high"


def plan_change(
    backend: Backend,
    repo: Path,
    issue: str,
    *,
    graph_path: Path | None = None,
    rebuild: bool = True,
) -> PlanReport:
    graph_path = graph_path or (build_graph(repo) if rebuild else repo / "graphify-out" / "graph.json")
    graph = CodeGraph.load(graph_path)

    nodes = query_nodes(graph_path, issue)
    files = relevant_files(nodes)
    context = (
        "Most relevant parts of the repository (found by Graphify's code graph):\n" + repo_map(files)
        if files
        else "Files in the repository:\n" + "\n".join(f"- {p}" for p in sorted(graph.files())[:60])
    )
    prompt = (
        f"{context}\n\nIssue: {issue}\n\n"
        "Plan the change. List every file that must be modified (path relative to the repository root), "
        "why, and the key functions, classes or methods involved. Only cite files and symbols that exist."
    )
    result = structured(
        backend,
        prompt,
        CHANGE_PLAN_SCHEMA,
        verify=grounded_plan_verifier(graph, strict_symbols=False),  # files are hard errors, symbols are pruned below
        max_tokens=2048,
    )
    report = PlanReport(issue, result.ok, calls=result.calls, attempts=result.attempts, graph_nodes=len(graph.nodes))
    if not isinstance(result.value, dict) or "files" not in result.value:
        return report

    check = check_plan(graph, result.value)
    report.summary = result.value.get("summary", "")
    report.grounded = check.bad_paths == 0
    report.pruned_symbols = check.bad_symbols
    for item in result.value["files"]:
        symbols = [s for s in item.get("symbols", []) if graph.find(s, file=item["path"])]
        report.files.append(
            PlannedFile(item["path"], item["reason"], symbols, graph.ripple(item["path"], symbols) if graph.has_file(item["path"]) else [])
        )
    return report


@dataclass
class UnguidedPlan:
    """One plain model call with no repo context, checked against the graph afterwards."""

    ok: bool
    files: list[tuple[str, bool]] = field(default_factory=list)  # (cited path, exists in the graph)

    @property
    def invented(self) -> int:
        return sum(1 for _, exists in self.files if not exists)


def unguided_plan(backend: Backend, graph_path: Path, issue: str) -> UnguidedPlan:
    """What a model does without Keel: one call, no repo map, no checking. For side-by-side demos."""
    graph = CodeGraph.load(graph_path)
    prompt = (
        f"Issue: {issue}\n\nYou have not been shown the repository. Plan the change. List every file that "
        "must be modified (path relative to the repository root), why, and the key functions involved."
    )
    result = structured(backend, prompt, CHANGE_PLAN_SCHEMA, max_attempts=1, max_tokens=2048)
    items = result.value.get("files") if isinstance(result.value, dict) else None
    if not isinstance(items, list):
        return UnguidedPlan(False)
    paths = [i["path"] for i in items if isinstance(i, dict) and isinstance(i.get("path"), str)]
    return UnguidedPlan(bool(paths), [(p, graph.has_file(p)) for p in paths])


def render_unguided(plan: UnguidedPlan) -> str:
    if not plan.files:
        return "### Without Keel (one unguided call)\n\nThe model did not produce a usable plan.\n"
    lines = ["### Without Keel (one unguided call)", ""]
    lines += [f"- {'✓' if exists else '✗'} `{path}`" + ("" if exists else "  (does not exist in this repo)") for path, exists in plan.files]
    lines += ["", f"**{plan.invented} of {len(plan.files)} cited files do not exist.**", ""]
    return "\n".join(lines)


def render_markdown(report: PlanReport) -> str:
    lines = [f"## Plan: {report.issue}", ""]
    if not report.files:
        return "\n".join(lines + ["The model did not produce a usable plan.", ""])
    lines += [report.summary, ""]
    status = "every cited file exists in the code graph" if report.grounded else "WARNING: some cited files could not be verified"
    pruned = f"; {report.pruned_symbols} unverifiable symbol(s) left out" if report.pruned_symbols else ""
    lines += [
        f"**Grounding:** {status}{pruned} ({report.calls} model call(s), graph of {report.graph_nodes} nodes)",
        f"**Ripple risk:** {report.risk} ({len(report.ripple_files)} other file(s) depend on what this touches)",
        "",
        "### Files to change",
        "",
    ]
    for f in report.files:
        lines.append(f"- `{f.path}`: {f.reason}")
        if f.symbols:
            lines.append(f"  - symbols: {', '.join(f'`{s}`' for s in f.symbols)}")
    if report.ripple_files:
        lines += ["", "### Check these too (they depend on the code above)", ""]
        lines += [f"- `{p}`" for p in report.ripple_files]
    lines.append("")
    return "\n".join(lines)
