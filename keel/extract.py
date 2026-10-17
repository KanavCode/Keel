"""Pull JSON out of the messy text small models actually produce."""

from __future__ import annotations

import ast
import json
import re
from typing import Any, Iterator

_THINK = re.compile(r"<think>.*?</think>", re.S | re.I)
_FENCE = re.compile(r"```[a-zA-Z0-9_-]*\s*(.*?)```", re.S)
_TRAILING_COMMA = re.compile(r",\s*([}\]])")
_SMART_QUOTES = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'"})


class ExtractError(ValueError):
    """No JSON object or array could be recovered from the text."""


def _balanced_spans(text: str) -> Iterator[str]:
    """Yield each top-level balanced {...} or [...] span, respecting double-quoted strings."""
    i, n = 0, len(text)
    while i < n:
        if text[i] in "{[":
            end = _span_end(text, i)
            if end is not None:
                yield text[i : end + 1]
                i = end + 1
                continue
        i += 1


def _span_end(text: str, start: int) -> int | None:
    closers = {"{": "}", "[": "]"}
    stack: list[str] = []
    in_str = False
    escaped = False
    for j in range(start, len(text)):
        c = text[j]
        if in_str:
            if escaped:
                escaped = False
            elif c == "\\":
                escaped = True
            elif c == '"':
                in_str = False
            continue
        if c == '"':
            in_str = True
        elif c in closers:
            stack.append(closers[c])
        elif c in "}]":
            if not stack or stack.pop() != c:
                return None
            if not stack:
                return j
    return None


def _parse(blob: str) -> Any:
    """Parse strict JSON first, then forgive the usual small-model slips."""
    blob = blob.strip().translate(_SMART_QUOTES)
    try:
        return json.loads(blob)
    except json.JSONDecodeError:
        pass
    try:
        return json.loads(_TRAILING_COMMA.sub(r"\1", blob))
    except json.JSONDecodeError:
        pass
    # Python-style literals: single quotes, True/False/None.
    return ast.literal_eval(blob)


def iter_json(text: str) -> Iterator[Any]:
    """Yield every JSON object/array recoverable from `text`, most-likely first."""
    text = _THINK.sub("", text)
    blobs = [text]
    blobs += [m.group(1) for m in _FENCE.finditer(text)]
    blobs += list(_balanced_spans(text))
    seen: set[str] = set()
    for blob in blobs:
        blob = blob.strip()
        if not blob or blob in seen:
            continue
        seen.add(blob)
        try:
            value = _parse(blob)
        except (ValueError, SyntaxError, MemoryError, RecursionError):
            continue
        if isinstance(value, (dict, list)):
            yield value


def extract_json(text: str) -> Any:
    """Return the first JSON object/array found in `text`, or raise ExtractError."""
    for value in iter_json(text):
        return value
    raise ExtractError("no JSON object or array found in model output")
