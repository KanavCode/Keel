"""Run suites x modes x models and collect records."""

from __future__ import annotations

import time
from dataclasses import asdict, dataclass, field
from typing import Callable

from .. import __version__
from ..client import Backend, BackendError
from . import extract_suite, grounding_suite, tools_suite
from .common import WORST_CASE_CALLS, Outcome


@dataclass
class Record:
    suite: str
    model: str
    mode: str
    task_id: str
    repeat: int
    valid: bool
    correct: bool
    calls: int
    latency_s: float
    error: str | None = None
    detail: dict = field(default_factory=dict)


@dataclass
class SuiteSpec:
    name: str
    modes: tuple[str, ...]
    tasks: list
    run: Callable[[Backend, str, object], Outcome]


def suite_specs() -> dict[str, SuiteSpec]:
    specs = {
        "extract": SuiteSpec("extract", extract_suite.SUITE_MODES, extract_suite.TASKS, extract_suite.run_task),
        "tools": SuiteSpec("tools", tools_suite.SUITE_MODES, tools_suite.TASKS, tools_suite.run_task),
    }
    for ctx in grounding_suite.CONTEXTS:
        specs[f"grounding-{ctx}"] = SuiteSpec(
            f"grounding-{ctx}",
            grounding_suite.SUITE_MODES,
            grounding_suite.TASKS,
            lambda backend, mode, task, ctx=ctx: grounding_suite.run_task(backend, mode, task, ctx),
        )
    return specs


def worst_case_calls(suites: list[str], *, limit: int | None, repeats: int) -> dict[str, int]:
    specs = suite_specs()
    out = {}
    for name in suites:
        spec = specs[name]
        n = len(spec.tasks[:limit]) * repeats
        out[name] = n * sum(WORST_CASE_CALLS[m] for m in spec.modes)
    return out


def run_bench(
    models: list[str],
    suites: list[str],
    make_backend: Callable[[str], Backend],
    *,
    limit: int | None = None,
    repeats: int = 1,
    on_record: Callable[[Record], None] | None = None,
    max_consecutive_errors: int = 5,
) -> list[Record]:
    specs = suite_specs()
    records: list[Record] = []
    consecutive_errors = 0
    for model in models:
        backend = make_backend(model)
        for name in suites:
            spec = specs[name]
            for task in spec.tasks[:limit]:
                for repeat in range(repeats):
                    for mode in spec.modes:  # modes interleaved so a quota cut-off hits all of them equally
                        try:
                            out = spec.run(backend, mode, task)
                            rec = Record(name, model, mode, task.id, repeat, out.valid, out.correct, out.calls, round(out.latency_s, 3), None, out.detail)
                            consecutive_errors = 0
                        except BackendError as exc:
                            rec = Record(name, model, mode, task.id, repeat, False, False, 0, 0.0, str(exc)[:300])
                            consecutive_errors += 1
                        records.append(rec)
                        if on_record:
                            on_record(rec)
                        if consecutive_errors >= max_consecutive_errors:
                            raise BackendError(
                                f"{consecutive_errors} backend errors in a row; stopping. Last: {rec.error}"
                            )
    return records


def results_payload(records: list[Record], *, models: list[str], suites: list[str], limit, repeats: int, backend_kind: str) -> dict:
    return {
        "meta": {
            "keel_version": __version__,
            "date": time.strftime("%Y-%m-%d"),
            "models": models,
            "suites": suites,
            "limit": limit,
            "repeats": repeats,
            "backend": backend_kind,
        },
        "records": [asdict(r) for r in records],
    }
