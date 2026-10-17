"""Shared pieces: the four modes, naive parsing for the baseline, value normalisation."""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from typing import Any

from jsonschema import Draft202012Validator

from ..client import Backend
from ..harness import Verifier, build_messages, schema_errors, structured

# raw     one call, plain json.loads (after stripping a markdown fence): what most apps do today
# extract one call, Keel's tolerant JSON extraction, no retries
# repair  up to 3 calls, schema errors fed back to the model
# keel    up to 3 calls, schema errors AND the suite's semantic check fed back
MODES = ("raw", "extract", "repair", "keel")
MAX_ATTEMPTS = {"extract": 1, "repair": 3, "keel": 3}
WORST_CASE_CALLS = {"raw": 1, "extract": 1, "repair": 3, "keel": 3}


@dataclass
class Outcome:
    valid: bool
    correct: bool
    calls: int
    latency_s: float
    detail: dict = field(default_factory=dict)


def norm(value: Any) -> Any:
    """Normalise for comparison: ignore case, whitespace and hyphens in strings; numbers as floats."""
    if isinstance(value, bool):
        return ("bool", value)  # tagged: in Python True == 1.0, which must not count as a match
    if isinstance(value, str):
        return re.sub(r"[\s\-]+", "", value).casefold()
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, list):
        return [norm(v) for v in value]
    if isinstance(value, dict):
        return {k: norm(v) for k, v in value.items()}
    return value


def naive_parse(text: str) -> Any | None:
    """What a typical app does: strip one markdown fence, then json.loads. No other forgiveness."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        lines = lines[1:]
        if lines and lines[-1].strip().startswith("```"):
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    try:
        return json.loads(text)
    except ValueError:
        return None


def run_mode(
    backend: Backend,
    mode: str,
    prompt: str,
    schema: dict,
    *,
    system: str | None = None,
    verify: Verifier | None = None,
) -> tuple[Any | None, int, float]:
    """Run one task in one mode. Returns (final value or None, model calls, seconds)."""
    if mode == "raw":
        started = time.perf_counter()
        text = backend.chat(build_messages(prompt, schema, system), temperature=0.2, max_tokens=1024)
        return naive_parse(text), 1, time.perf_counter() - started
    if mode not in MAX_ATTEMPTS:
        raise ValueError(f"unknown mode {mode!r}")
    result = structured(
        backend,
        prompt,
        schema,
        system=system,
        max_attempts=MAX_ATTEMPTS[mode],
        verify=verify if mode == "keel" else None,
    )
    return result.value, result.calls, sum(a.latency_s for a in result.attempts)


def is_valid(schema: dict, value: Any) -> bool:
    return value is not None and not schema_errors(Draft202012Validator(schema), value)
