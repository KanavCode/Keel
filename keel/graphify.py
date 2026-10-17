"""Bridge to the Graphify CLI: build a repo's code graph and retrieve the part relevant to a question."""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

GRAPH_REL = Path("graphify-out") / "graph.json"
_NODE_LINE = re.compile(r"^NODE (?P<label>.+?) \[src=(?P<src>.*?) loc=(?P<loc>.*?) community=(?P<community>.*)\]\s*$")


class GraphifyError(RuntimeError):
    """Graphify is missing or failed."""


def find_graphify() -> str:
    found = shutil.which("graphify")
    if found:
        return found
    sibling = Path(sys.executable).parent / ("graphify.exe" if sys.platform == "win32" else "graphify")
    if sibling.exists():
        return str(sibling)
    raise GraphifyError("graphify not found. Install it with: pip install graphifyy")


def _run(args: list[str], cwd: Path, timeout: int = 600) -> str:
    try:
        proc = subprocess.run(
            [find_graphify(), *args], cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout
        )
    except subprocess.TimeoutExpired as exc:
        raise GraphifyError(f"graphify {' '.join(args)} timed out after {timeout}s") from exc
    return (proc.stdout or "") + (proc.stderr or "")


def build_graph(repo: Path) -> Path:
    """Run `graphify update .` in `repo` (code only, no LLM) and return the graph.json path."""
    out = _run(["update", "."], repo)
    graph = repo / GRAPH_REL
    if not graph.is_file():
        raise GraphifyError(f"graphify did not produce {graph}:\n{out[-500:]}")
    return graph


@dataclass
class QueryNode:
    label: str
    src: str
    loc: str


def query_nodes(graph_path: Path, question: str) -> list[QueryNode]:
    """Nodes of the subgraph Graphify considers relevant to `question`, nearest the match first."""
    out = _run(["query", question, "--graph", str(graph_path), "--budget", "4000"], graph_path.parent.parent)
    nodes = []
    for line in out.splitlines():
        m = _NODE_LINE.match(line)
        if m:
            nodes.append(QueryNode(m["label"], m["src"], m["loc"]))
    return nodes


def relevant_files(nodes: list[QueryNode], max_files: int = 12, max_symbols: int = 8) -> dict[str, list[str]]:
    """Collapse query nodes into {file: [symbols]}, keeping the order Graphify returned them in."""
    files: dict[str, list[str]] = {}
    for n in nodes:
        if not n.src or n.src.startswith("<"):  # external packages have no source file
            continue
        if n.src not in files and len(files) >= max_files:
            continue
        symbols = files.setdefault(n.src, [])
        is_symbol = " " not in n.label and not n.label.endswith((".py", ".js", ".ts", ".go", ".rs", ".java"))
        if is_symbol and len(symbols) < max_symbols:
            symbols.append(n.label)
    return files


def repo_map(files: dict[str, list[str]]) -> str:
    lines = []
    for path, symbols in files.items():
        lines.append(f"- {path}" + (f": {', '.join(symbols)}" if symbols else ""))
    return "\n".join(lines)


def clone_repo(url: str, cache_dir: Path) -> Path:
    """Shallow-clone a GitHub repo into cache_dir (reusing an existing clone)."""
    name = re.sub(r"\.git$", "", url.rstrip("/").split("/")[-1])
    owner = url.rstrip("/").split("/")[-2] if "/" in url else "repo"
    dest = cache_dir / f"{owner}__{name}"
    if not dest.exists():
        cache_dir.mkdir(parents=True, exist_ok=True)
        proc = subprocess.run(["git", "clone", "--depth", "1", url, str(dest)], capture_output=True, text=True)
        if proc.returncode != 0:
            raise GraphifyError(f"git clone failed: {proc.stderr.strip()[:300]}")
    return dest
