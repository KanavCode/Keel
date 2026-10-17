"""Suite 3: plan a code change. Does the model cite files and symbols that really exist?

The repository under test is Keel itself, mapped by Graphify (keel/bench/data/keel_graph.json).
Two contexts: "none" (the model only knows the issue, like an agent without a repo map) and
"files" (the model is given the file list). `grounded` means every cited FILE exists.

Cited symbols are checked too and reported separately. Graph nodes are functions, classes and
methods, so a legitimate mention of a parameter or flag counts as a miss. An earlier run counted
those as errors; error analysis showed they were false positives, so file grounding is the headline
metric and symbol misses are shown on the side.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..graph import CHANGE_PLAN_SCHEMA, CodeGraph, check_plan, grounded_plan_verifier, normalize_path
from .common import MODES, Outcome, is_valid, run_mode

NAME = "grounding"
SUITE_MODES = ("raw", "extract", "repair", "keel")
CONTEXTS = ("none", "files")
GRAPH_PATH = Path(__file__).parent / "data" / "keel_graph.json"


@dataclass
class IssueTask:
    id: str
    issue: str
    gold_files: tuple[str, ...]


TASKS: list[IssueTask] = [
    IssueTask("retry-after", "Retries after an HTTP 429 should wait as long as the server's Retry-After header says.", ("keel/client.py",)),
    IssueTask("think-tags", "Replies from reasoning models that start with a <think> block break JSON parsing.", ("keel/extract.py",)),
    IssueTask("cli-temperature", "Add a --temperature flag to the `keel ask` command.", ("keel/cli.py",)),
    IssueTask("agent-loop", "The agent should stop early when it repeats the same tool call with identical arguments.", ("keel/agent.py",)),
    IssueTask("repair-prompt", "The repair message should remind the model of the schema, not only the error.", ("keel/harness.py",)),
    IssueTask("blast-tests", "blast_radius should report affected test files separately from source files.", ("keel/graph.py",)),
    IssueTask("ping-latency", "`keel ping` should print how long the test request took.", ("keel/cli.py",)),
    IssueTask("dotenv", "API keys should be loaded from a .env file in the project directory.", ("keel/env.py",)),
    IssueTask("gemini-thinking", "Let users choose the Gemini thinking level through an environment variable.", ("keel/client.py",)),
    IssueTask(
        "rename-verify",
        "Rename the `verify` parameter of structured() to `check` everywhere it is used.",
        ("keel/harness.py", "keel/agent.py", "keel/graph.py"),
    ),
]


@lru_cache(maxsize=1)
def load_graph() -> CodeGraph:
    return CodeGraph.load(GRAPH_PATH)


def build_prompt(task: IssueTask, context: str, graph: CodeGraph) -> str:
    if context == "files":
        listing = "Files in the repository:\n" + "\n".join(f"- {p}" for p in sorted(graph.files()))
    elif context == "none":
        listing = "You have not been shown the repository's file listing."
    else:
        raise ValueError(f"unknown context {context!r}")
    return (
        "Repository: Keel, a Python reliability harness for open-weight language models.\n"
        f"{listing}\n\n"
        f"Issue: {task.issue}\n\n"
        "Plan the change. List every file that must be modified (path relative to the repository root), "
        "why, and the key functions, classes or methods involved."
    )


def score(value: Any, task: IssueTask, graph: CodeGraph) -> dict:
    valid = is_valid(CHANGE_PLAN_SCHEMA, value)
    if not valid:
        return {"valid": False, "grounded": False, "recall": 0.0, "bad_paths": 0, "total_paths": 0, "bad_symbols": 0, "total_symbols": 0}
    check = check_plan(graph, value)
    cited = {normalize_path(f["path"]) for f in value["files"]}
    recall = len(cited & set(task.gold_files)) / len(task.gold_files)
    return {
        "valid": True,
        "grounded": check.bad_paths == 0,  # every cited FILE exists; symbols are reported separately
        "strict_grounded": check.grounded,  # files and symbols (parameters/flags are not graph nodes)
        "recall": round(recall, 3),
        "bad_paths": check.bad_paths,
        "total_paths": check.total_paths,
        "bad_symbols": check.bad_symbols,
        "total_symbols": check.total_symbols,
    }


def run_task(backend, mode: str, task: IssueTask, context: str) -> Outcome:
    assert mode in MODES
    graph = load_graph()
    prompt = build_prompt(task, context, graph)
    value, calls, latency = run_mode(
        backend, mode, prompt, CHANGE_PLAN_SCHEMA, verify=grounded_plan_verifier(graph, strict_symbols=False)
    )
    detail = score(value, task, graph)
    correct = detail["grounded"] and detail["recall"] >= 0.5
    return Outcome(detail["valid"], correct, calls, latency, detail)
