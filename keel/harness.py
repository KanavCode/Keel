"""The core loop: generate -> extract -> validate -> verify -> repair."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, Sequence

from jsonschema import Draft202012Validator

from .client import Backend, Message
from .extract import iter_json

# verify(value) returns None / "" when fine, otherwise a human-readable problem.
Verifier = Callable[[Any], Optional[str]]

_SYSTEM = (
    "You are a precise JSON generator. Reply with a single JSON value and nothing else: "
    "no prose, no markdown fences, no comments."
)


@dataclass
class Attempt:
    n: int
    raw: str
    stage: str  # "ok" | "parse" | "schema" | "verify"
    problem: str | None
    latency_s: float


@dataclass
class Result:
    ok: bool
    value: Any
    attempts: list[Attempt] = field(default_factory=list)

    @property
    def calls(self) -> int:
        return len(self.attempts)


def schema_errors(validator: Draft202012Validator, value: Any) -> list[str]:
    errs = sorted(validator.iter_errors(value), key=lambda e: [str(p) for p in e.absolute_path])
    return [
        f"{'/'.join(str(p) for p in e.absolute_path) or '<root>'}: {e.message}" for e in errs
    ]


def _check(raw: str, validator: Draft202012Validator, verify: Verifier | None):
    """Return (value, stage, problem). Picks the first candidate that passes everything."""
    first_bad: tuple[Any, str, str] | None = None
    found_any = False
    for value in iter_json(raw):
        found_any = True
        errs = schema_errors(validator, value)
        if errs:
            first_bad = first_bad or (value, "schema", "; ".join(errs[:5]))
            continue
        if verify is not None:
            problem = verify(value)
            if problem:
                first_bad = first_bad or (value, "verify", problem)
                continue
        return value, "ok", None
    if first_bad:
        return first_bad
    if not found_any:
        return None, "parse", "no JSON object or array found in your reply"
    return None, "schema", "no candidate matched the schema"  # pragma: no cover


def _repair_message(stage: str, problem: str) -> str:
    return (
        f"Your reply was rejected ({stage} check): {problem}\n"
        "Fix exactly that and reply with only the corrected JSON."
    )


def build_messages(prompt: str, schema: dict, system: str | None = None) -> list[Message]:
    """The exact prompt Keel sends. The benchmark's raw baseline reuses it, so the prompt is not a variable."""
    sys_text = _SYSTEM if not system else f"{_SYSTEM}\n\n{system}"
    return [
        {"role": "system", "content": sys_text},
        {
            "role": "user",
            "content": f"{prompt}\n\nThe JSON must conform to this JSON Schema:\n"
            f"{json.dumps(schema, indent=2)}",
        },
    ]


def structured(
    backend: Backend,
    prompt: str,
    schema: dict,
    *,
    system: str | None = None,
    max_attempts: int = 3,
    verify: Verifier | None = None,
    temperature: float = 0.2,
    max_tokens: int = 1024,
) -> Result:
    """Get a schema-valid (and optionally semantically verified) JSON value from a model."""
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)

    messages = build_messages(prompt, schema, system)

    attempts: list[Attempt] = []
    last_value: Any = None
    for n in range(1, max_attempts + 1):
        started = time.perf_counter()
        raw = backend.chat(
            messages,
            temperature=temperature if n == 1 else 0.0,
            max_tokens=max_tokens,
        )
        latency = time.perf_counter() - started
        value, stage, problem = _check(raw, validator, verify)
        attempts.append(Attempt(n, raw, stage, problem, latency))
        if value is not None:
            last_value = value
        if stage == "ok":
            return Result(True, value, attempts)
        messages.append({"role": "assistant", "content": raw})
        messages.append({"role": "user", "content": _repair_message(stage, problem or "")})

    return Result(False, last_value, attempts)
