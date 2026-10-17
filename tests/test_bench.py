"""Offline checks of the benchmark itself: tasks are well-formed and scoring behaves.

No numbers here come from a real model; these tests only prove the harness measures what it claims.
"""

import json

import pytest
from jsonschema import Draft202012Validator

from keel.bench import extract_suite, grounding_suite, tools_suite
from keel.bench.common import naive_parse, norm
from keel.bench.report import render
from keel.bench.runner import results_payload, run_bench, suite_specs, worst_case_calls
from keel.client import BackendError


class OracleBackend:
    """Answers every benchmark prompt with the gold answer. `flaky` makes each first attempt junk."""

    def __init__(self, flaky: bool = False) -> None:
        self.flaky = flaky
        self.calls = 0

    def _gold(self, text: str) -> str:
        for t in extract_suite.TASKS:
            if t.text in text:
                return json.dumps(t.gold)
        for t in tools_suite.TASKS:
            if t.request in text:
                args = dict(t.args)
                for tool in tools_suite.TOOLS:  # fill unscored free-text arguments
                    if tool.name == t.tool:
                        for k in tool.parameters["properties"]:
                            args.setdefault(k, "text")
                return json.dumps({"tool": t.tool, "arguments": args})
        for t in grounding_suite.TASKS:
            if t.issue in text:
                return json.dumps(
                    {"summary": "s", "files": [{"path": p, "reason": "r"} for p in t.gold_files]}
                )
        raise AssertionError("unrecognised prompt")

    def chat(self, messages, *, temperature=0.2, max_tokens=1024):
        self.calls += 1
        text = messages[1]["content"] if len(messages) > 1 else messages[0]["content"]
        if self.flaky and len(messages) == 2:  # first attempt of every conversation is junk
            return "Sure! Here is the answer, I hope it helps."
        return "```json\n" + self._gold(text) + "\n```"


def test_extract_gold_is_valid_and_scores_perfectly():
    for task in extract_suite.TASKS:
        assert not list(Draft202012Validator(task.schema).iter_errors(task.gold)), task.id
        assert extract_suite.score(task.gold, task.gold) == (True, 1.0)


def test_extract_score_rejects_wrong_and_extra_fields():
    task = extract_suite.TASKS[0]
    wrong = {**task.gold, "name": "Someone Else"}
    assert extract_suite.score(wrong, task.gold)[0] is False
    assert extract_suite.score({**task.gold, "extra": 1}, task.gold)[0] is False


def test_tools_gold_args_fit_their_tool_schema():
    by_name = {t.name: t for t in tools_suite.TOOLS}
    for task in tools_suite.TASKS:
        props = by_name[task.tool].parameters["properties"]
        assert set(task.args) <= set(props), task.id
        for key, value in task.args.items():
            assert not list(Draft202012Validator(props[key]).iter_errors(value)), (task.id, key)


def test_grounding_gold_files_exist_in_the_fixture_graph():
    graph = grounding_suite.load_graph()
    for task in grounding_suite.TASKS:
        for path in task.gold_files:
            assert graph.has_file(path), (task.id, path)


def test_grounding_prompt_differs_by_context():
    graph = grounding_suite.load_graph()
    task = grounding_suite.TASKS[0]
    assert "keel/client.py" in grounding_suite.build_prompt(task, "files", graph)
    assert "keel/client.py" not in grounding_suite.build_prompt(task, "none", graph)


def test_naive_parse_is_strict_but_strips_one_fence():
    assert naive_parse('```json\n{"a": 1}\n```') == {"a": 1}
    assert naive_parse('Here: {"a": 1}') is None
    assert naive_parse('{"a": 1,}') is None


def test_norm_ignores_case_space_and_hyphen_but_not_bool_vs_int():
    assert norm("Good-First Issue") == norm("goodfirstissue")
    assert norm(5) == norm(5.0)
    assert norm(True) != norm(1)


def test_every_suite_and_mode_scores_correct_with_an_oracle():
    records = run_bench(["oracle"], list(suite_specs()), lambda m: OracleBackend())
    assert records and not [r for r in records if r.error]
    wrong = [(r.suite, r.mode, r.task_id) for r in records if not r.correct]
    assert wrong == []


def test_keel_recovers_where_raw_and_extract_fail():
    records = run_bench(["flaky"], ["extract", "tools"], lambda m: OracleBackend(flaky=True))
    by_mode = {}
    for r in records:
        by_mode.setdefault(r.mode, []).append(r)
    assert not any(r.correct for r in by_mode["raw"])
    assert not any(r.correct for r in by_mode["extract"])
    assert all(r.correct and r.calls == 2 for r in by_mode["keel"])


def test_grounded_repair_beats_schema_only_repair():
    """A backend that cites a made-up file first; only the graph check can catch it."""

    class Hallucinator(OracleBackend):
        def chat(self, messages, *, temperature=0.2, max_tokens=1024):
            if len(messages) == 2:
                return json.dumps({"summary": "s", "files": [{"path": "keel/madeup.py", "reason": "r"}]})
            return super().chat(messages)

    task = grounding_suite.TASKS[0]
    repair = grounding_suite.run_task(Hallucinator(), "repair", task, "none")
    keel = grounding_suite.run_task(Hallucinator(), "keel", task, "none")
    assert repair.valid and not repair.correct and repair.detail["bad_paths"] == 1
    assert keel.correct and keel.calls == 2 and keel.detail["bad_paths"] == 0


def test_runner_aborts_after_consecutive_backend_errors():
    class Down:
        def chat(self, *a, **k):
            raise BackendError("401 unauthorized")

    with pytest.raises(BackendError, match="in a row"):
        run_bench(["m"], ["extract"], lambda m: Down(), max_consecutive_errors=3)


def test_worst_case_budget():
    budget = worst_case_calls(["extract", "tools", "grounding-none"], limit=None, repeats=1)
    assert budget == {"extract": 12 * (1 + 1 + 3), "tools": 12 * (1 + 1 + 3), "grounding-none": 10 * (1 + 1 + 3 + 3)}
    assert worst_case_calls(["extract"], limit=2, repeats=2) == {"extract": 2 * 2 * 5}


def test_report_renders_counts_and_hallucination_column():
    records = run_bench(["oracle"], ["extract", "grounding-none"], lambda m: OracleBackend(), limit=2)
    payload = results_payload(records, models=["oracle"], suites=["extract", "grounding-none"], limit=2, repeats=1, backend_kind="Oracle")
    text = render(payload)
    assert "## oracle" in text and "### grounding-none" in text
    assert "2/2 (100%)" in text
    assert "cited paths that don't exist" in text
