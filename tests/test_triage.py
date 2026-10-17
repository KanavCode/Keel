import httpx
import pytest

from keel.client import BackendError
from keel.plan import PlanReport, PlannedFile
from keel.triage import Issue, TriageRow, fetch_issues, parse_repo, render_table


def test_parse_repo_variants():
    assert parse_repo("https://github.com/psf/requests") == ("psf", "requests")
    assert parse_repo("https://github.com/psf/requests.git") == ("psf", "requests")
    assert parse_repo("git@github.com:psf/requests.git") == ("psf", "requests")
    with pytest.raises(ValueError):
        parse_repo("https://example.com/nothing")


def test_fetch_issues_skips_pull_requests_and_respects_limit():
    payload = [
        {"number": 1, "title": "A", "body": None, "html_url": "u1"},
        {"number": 2, "title": "PR", "body": "x", "html_url": "u2", "pull_request": {}},
        {"number": 3, "title": "C", "body": "body", "html_url": "u3"},
        {"number": 4, "title": "D", "body": "", "html_url": "u4"},
    ]
    seen = {}

    def handler(request: httpx.Request):
        seen["params"] = dict(request.url.params)
        return httpx.Response(200, json=payload)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    issues = fetch_issues("o", "r", "good first issue", 2, client=client)
    assert [i.number for i in issues] == [1, 3]
    assert issues[0].body == ""  # null body tolerated
    assert seen["params"]["labels"] == "good first issue" and seen["params"]["state"] == "open"


def test_fetch_issues_reports_api_errors():
    client = httpx.Client(transport=httpx.MockTransport(lambda r: httpx.Response(403, text="rate limited")))
    with pytest.raises(BackendError, match="403"):
        fetch_issues("o", "r", "x", 3, client=client)


def _report(files, ripple, ok=True, grounded=True):
    r = PlanReport("issue", ok, grounded=grounded)
    r.files = [PlannedFile(p, "r", [], ripple) for p in files]
    return r


def test_ranking_prefers_small_ripple_then_fewer_files_and_puts_failures_last():
    big = TriageRow(Issue(1, "big", "", "u1"), _report(["a.py"], ["x.py", "y.py", "z.py"]))
    small = TriageRow(Issue(2, "small", "", "u2"), _report(["b.py"], []))
    two_files = TriageRow(Issue(3, "two", "", "u3"), _report(["c.py", "d.py"], []))
    failed = TriageRow(Issue(4, "failed", "", "u4"), PlanReport("issue", False))
    ranked = sorted([failed, big, two_files, small], key=lambda r: r.sort_key)
    assert [r.issue.number for r in ranked] == [2, 3, 1, 4]


def test_render_table_marks_status():
    rows = [
        TriageRow(Issue(2, "small | pipe", "", "http://u2"), _report(["b.py"], [])),
        TriageRow(Issue(5, "shaky", "", "http://u5"), _report(["q.py"], [], grounded=False)),
        TriageRow(Issue(4, "failed", "", "http://u4"), PlanReport("issue", False)),
    ]
    text = render_table(rows)
    assert "[#2](http://u2)" in text and "small / pipe" in text and "verified" in text
    assert "unverified" in text and "no plan" in text
