"""Read a Graphify graph.json and use it to ground model output in the real codebase."""

from __future__ import annotations

import difflib
import json
from collections import defaultdict, deque
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .harness import Verifier

# Edge relations meaning "source depends on target". Structural relations
# (contains, method, rationale_for) say nothing about what breaks when code changes.
DEPENDENCY_RELATIONS = frozenset(
    {"calls", "indirect_call", "imports", "imports_from", "uses", "inherits", "references", "re_exports"}
)

CHANGE_PLAN_SCHEMA: dict = {
    "type": "object",
    "properties": {
        "summary": {"type": "string", "minLength": 1},
        "files": {
            "type": "array",
            "minItems": 1,
            "items": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "reason": {"type": "string"},
                    "symbols": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["path", "reason"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["summary", "files"],
    "additionalProperties": False,
}


def canonical_symbol(label: str) -> str:
    """Graphify labels functions `name()` and methods `.name()`; compare on the bare name."""
    label = label.strip()
    if label.endswith("()"):
        label = label[:-2]
    return label.lstrip(".").lower()


def _is_symbol(node: dict) -> bool:
    # Docstring ("rationale") nodes carry prose in `label`; they are not symbols.
    return node.get("file_type") != "rationale" and bool(node.get("label"))


def normalize_path(path: str) -> str:
    path = path.strip().replace("\\", "/")
    while path.startswith("./"):
        path = path[2:]
    return path


class CodeGraph:
    def __init__(self, nodes: list[dict], links: list[dict]) -> None:
        self.nodes: dict[str, dict] = {n["id"]: n for n in nodes}
        self._dependents: dict[str, list[str]] = defaultdict(list)
        for edge in links:
            if edge.get("relation") in DEPENDENCY_RELATIONS:
                self._dependents[edge["target"]].append(edge["source"])
        self._files = {n["source_file"] for n in nodes if n.get("source_file")}

    @classmethod
    def load(cls, path: str | Path) -> "CodeGraph":
        data = json.loads(Path(path).read_text(encoding="utf-8"))
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CodeGraph":
        # networkx node-link format; older/newer writers use "links" or "edges".
        links = data.get("links", data.get("edges", []))
        return cls(data.get("nodes", []), links)

    def files(self) -> set[str]:
        return set(self._files)

    def has_file(self, path: str) -> bool:
        return normalize_path(path) in self._files

    def find(self, name: str, file: str | None = None) -> list[dict]:
        """Nodes whose label matches `name` (case-insensitive), optionally within one file."""
        want = canonical_symbol(name)
        want_file = normalize_path(file) if file else None
        return [
            n
            for n in self.nodes.values()
            if _is_symbol(n)
            and canonical_symbol(n["label"]) == want
            and (want_file is None or n.get("source_file") == want_file)
        ]

    def dependents(self, node_id: str, depth: int = 2) -> list[tuple[dict, int]]:
        """Everything that transitively depends on `node_id`, nearest first, with distance."""
        seen = {node_id}
        queue: deque[tuple[str, int]] = deque([(node_id, 0)])
        out: list[tuple[dict, int]] = []
        while queue:
            current, dist = queue.popleft()
            if dist == depth:
                continue
            for src in self._dependents.get(current, ()):
                if src in seen or src not in self.nodes:
                    continue
                seen.add(src)
                out.append((self.nodes[src], dist + 1))
                queue.append((src, dist + 1))
        return out

    def blast_radius(self, name: str, depth: int = 2) -> dict:
        """What is affected if the symbol(s) called `name` change."""
        targets = self.find(name)
        affected: dict[str, dict] = {}
        for node in targets:
            for dep, dist in self.dependents(node["id"], depth):
                affected.setdefault(dep["id"], {"label": dep["label"], "file": dep.get("source_file"), "distance": dist})
        return {
            "symbol": name,
            "defined_in": sorted({n.get("source_file") for n in targets if n.get("source_file")}),
            "affected": sorted(affected.values(), key=lambda a: (a["distance"], a["file"] or "", a["label"])),
            "affected_files": sorted({a["file"] for a in affected.values() if a["file"]}),
        }

    def suggest_files(self, path: str, n: int = 3) -> list[str]:
        return difflib.get_close_matches(normalize_path(path), self._files, n=n, cutoff=0.5)

    def suggest_symbols(self, name: str, n: int = 3) -> list[str]:
        names = {canonical_symbol(node["label"]) for node in self.nodes.values() if _is_symbol(node)}
        return difflib.get_close_matches(canonical_symbol(name), names, n=n, cutoff=0.6)


@dataclass
class PlanCheck:
    """How well a CHANGE_PLAN_SCHEMA value is grounded in the graph."""

    messages: list[str] = field(default_factory=list)
    total_paths: int = 0
    bad_paths: int = 0
    total_symbols: int = 0
    bad_symbols: int = 0

    @property
    def grounded(self) -> bool:
        return not self.messages


def _did_you_mean(hints: list[str]) -> str:
    return f" (did you mean {', '.join(repr(h) for h in hints)}?)" if hints else ""


def check_plan(graph: CodeGraph, plan: Any, *, list_files: int = 30) -> PlanCheck:
    """Count and describe every file or symbol in `plan` that does not exist in `graph`."""
    check = PlanCheck()
    for item in plan.get("files", []) if isinstance(plan, dict) else []:
        path = item["path"]
        check.total_paths += 1
        if not graph.has_file(path):
            check.bad_paths += 1
            check.messages.append(
                f"file {path!r} does not exist in the repository{_did_you_mean(graph.suggest_files(path))}"
            )
            continue
        for symbol in item.get("symbols", []):
            check.total_symbols += 1
            if not graph.find(symbol, file=path):
                check.bad_symbols += 1
                check.messages.append(
                    f"symbol {symbol!r} is not defined in {path!r}{_did_you_mean(graph.suggest_symbols(symbol))}"
                )
    check.messages = check.messages[:5]
    if check.bad_paths:
        shown = sorted(graph.files())[:list_files]
        check.messages.append("files that exist: " + ", ".join(shown))
    return check


def grounded_plan_verifier(graph: CodeGraph) -> Verifier:
    """Verify a CHANGE_PLAN_SCHEMA value only cites files and symbols that exist in the graph."""

    def verify(plan: Any) -> str | None:
        return "; ".join(check_plan(graph, plan).messages) or None

    return verify
