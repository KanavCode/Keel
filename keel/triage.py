"""keel triage: rank a repo's open issues by how small and safe the change looks."""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from pathlib import Path

import httpx

from .client import Backend, BackendError
from .graphify import build_graph
from .plan import PlanReport, plan_change

_REPO_URL = re.compile(r"github\.com[/:](?P<owner>[\w.-]+)/(?P<name>[\w.-]+?)(?:\.git)?/?$")


@dataclass
class Issue:
    number: int
    title: str
    body: str
    url: str

    @property
    def text(self) -> str:
        return f"{self.title}\n\n{self.body[:1500]}".strip()


@dataclass
class TriageRow:
    issue: Issue
    report: PlanReport

    @property
    def sort_key(self) -> tuple:
        # Unusable plans last; then smallest ripple, then fewest files to touch.
        usable = self.report.ok and bool(self.report.files)
        return (not usable, len(self.report.ripple_files), len(self.report.files), self.issue.number)


def parse_repo(url: str) -> tuple[str, str]:
    m = _REPO_URL.search(url.strip())
    if not m:
        raise ValueError(f"not a GitHub repository URL: {url!r}")
    return m["owner"], m["name"]


def fetch_issues(owner: str, name: str, label: str, limit: int, *, client: httpx.Client | None = None) -> list[Issue]:
    """Open issues with `label` (pull requests excluded), via the unauthenticated GitHub API."""
    if client is None:
        headers = {"Accept": "application/vnd.github+json"}
        token = os.environ.get("GITHUB_TOKEN")
        if token:  # optional: lifts the unauthenticated limit of 60 requests per hour
            headers["Authorization"] = f"Bearer {token}"
        client = httpx.Client(timeout=20.0, headers=headers)
    http = client
    resp = http.get(
        f"https://api.github.com/repos/{owner}/{name}/issues",
        params={"labels": label, "state": "open", "per_page": min(limit * 2, 100)},
    )
    if resp.status_code >= 400:
        raise BackendError(f"GitHub API {resp.status_code}: {resp.text[:200]}")
    issues = [
        Issue(i["number"], i["title"], i.get("body") or "", i["html_url"])
        for i in resp.json()
        if "pull_request" not in i
    ]
    return issues[:limit]


def triage(backend: Backend, repo: Path, issues: list[Issue], *, on_row=None) -> list[TriageRow]:
    graph_path = build_graph(repo)  # once, shared by every issue
    rows: list[TriageRow] = []
    for issue in issues:
        row = TriageRow(issue, plan_change(backend, repo, issue.text, graph_path=graph_path))
        rows.append(row)
        if on_row:
            on_row(row)
    return sorted(rows, key=lambda r: r.sort_key)


def render_table(rows: list[TriageRow]) -> str:
    lines = [
        "| # | Issue | Files to change | Ripple | Plan |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        rep = r.report
        usable = rep.ok and bool(rep.files)
        files = ", ".join(f"`{f.path}`" for f in rep.files) if usable else "-"
        ripple = f"{rep.risk} ({len(rep.ripple_files)})" if usable else "-"
        status = "verified" if usable and rep.grounded else "unverified" if usable else "no plan"
        title = r.issue.title.replace("|", "/")[:70]
        lines.append(f"| [#{r.issue.number}]({r.issue.url}) | {title} | {files} | {ripple} | {status} |")
    return "\n".join(lines)
