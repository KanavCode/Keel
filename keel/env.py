"""Tiny .env loader so users can just paste their key into a file."""

from __future__ import annotations

import os
from pathlib import Path


def _parse_line(line: str) -> tuple[str, str] | None:
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        return None
    if line.startswith("export "):
        line = line[len("export ") :]
    key, _, value = line.partition("=")
    key, value = key.strip(), value.strip()
    if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
        value = value[1:-1]
    return (key, value) if key else None


def load_dotenv(start: Path | None = None) -> Path | None:
    """Load the nearest .env (cwd, then parents) into os.environ without overriding real env vars."""
    here = (start or Path.cwd()).resolve()
    for directory in (here, *here.parents):
        candidate = directory / ".env"
        if candidate.is_file():
            for raw in candidate.read_text(encoding="utf-8-sig").splitlines():
                parsed = _parse_line(raw)
                if parsed and parsed[1]:
                    os.environ.setdefault(parsed[0], parsed[1])
            return candidate
    return None
