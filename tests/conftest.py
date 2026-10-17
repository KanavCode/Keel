from __future__ import annotations

import pytest


class ScriptedBackend:
    """Replays canned model outputs and records the messages it was sent."""

    def __init__(self, outputs: list[str]) -> None:
        self.outputs = list(outputs)
        self.calls: list[list[dict]] = []

    def chat(self, messages, *, temperature: float = 0.2, max_tokens: int = 1024) -> str:
        self.calls.append(list(messages))
        if not self.outputs:
            raise AssertionError("ScriptedBackend ran out of outputs")
        return self.outputs.pop(0)


@pytest.fixture
def scripted():
    return ScriptedBackend
