"""A small tool-using agent loop built on `structured`, independent of native tool-calling."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any, Callable, Sequence

from jsonschema import Draft202012Validator

from .client import Backend
from .harness import Attempt, Result, schema_errors, structured


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict  # JSON Schema for the arguments object
    fn: Callable[..., Any]


@dataclass
class Step:
    tool: str
    arguments: dict
    observation: str
    attempts: list[Attempt]


@dataclass
class AgentRun:
    ok: bool
    final: str | None
    steps: list[Step] = field(default_factory=list)
    reason: str = ""
    calls: int = 0  # total model calls, including repair retries


STEP_SCHEMA = {
    "type": "object",
    "properties": {"tool": {"type": "string"}, "arguments": {"type": "object"}, "final": {"type": "string"}},
    "additionalProperties": False,
}


class Agent:
    def __init__(
        self,
        backend: Backend,
        tools: list[Tool],
        *,
        max_steps: int = 6,
        max_attempts: int = 3,
        system: str | None = None,
    ) -> None:
        self.backend = backend
        self.tools = {t.name: t for t in tools}
        self._validators = {t.name: Draft202012Validator(t.parameters) for t in tools}
        self.max_steps = max_steps
        self.max_attempts = max_attempts
        self.system = system

    def _catalog(self) -> str:
        lines = []
        for t in self.tools.values():
            lines.append(
                f"- {t.name}: {t.description}\n  arguments schema: {json.dumps(t.parameters)}"
            )
        return "\n".join(lines)

    def verify_step(self, value: Any) -> str | None:
        if not isinstance(value, dict):
            return "reply must be a JSON object"
        has_final = "final" in value
        has_tool = "tool" in value
        if has_final == has_tool:
            return 'reply must contain exactly one of "final" or "tool"'
        if has_final:
            return None
        name = value["tool"]
        if name not in self.tools:
            return f"unknown tool {name!r}; available tools: {', '.join(self.tools)}"
        if "arguments" not in value:
            return f'missing "arguments" for tool {name!r}'
        errs = schema_errors(self._validators[name], value["arguments"])
        if errs:
            return f"arguments for {name!r} are invalid: " + "; ".join(errs[:5])
        return None

    def step_request(self, task: str, history: Sequence[str] = ()) -> tuple[str, str]:
        """The (prompt, system) pair for one step. The benchmark's raw baseline reuses it."""
        instructions = (
            "Solve the task by calling tools, then give the answer.\n"
            'To call a tool reply {"tool": "<name>", "arguments": {...}}.\n'
            'When done reply {"final": "<answer>"}.\n\nTools:\n' + self._catalog()
        )
        prompt = f"Task: {task}\n"
        if history:
            prompt += "\nSteps so far:\n" + "\n".join(history) + "\n"
        prompt += "\nWhat is the next step?"
        return prompt, (self.system + "\n\n" if self.system else "") + instructions

    def next_step(self, task: str, history: Sequence[str] = ()) -> Result:
        """Ask the model for one validated step ({"tool", "arguments"} or {"final"}) without running it."""
        prompt, system = self.step_request(task, history)
        return structured(
            self.backend,
            prompt,
            STEP_SCHEMA,
            system=system,
            max_attempts=self.max_attempts,
            verify=self.verify_step,
        )

    def run(self, task: str) -> AgentRun:
        run = AgentRun(ok=False, final=None)
        history: list[str] = []
        for _ in range(self.max_steps):
            result = self.next_step(task, history)
            run.calls += result.calls
            if not result.ok:
                run.reason = "model could not produce a valid step"
                return run

            value = result.value
            if "final" in value:
                run.ok, run.final = True, value["final"]
                return run

            tool = self.tools[value["tool"]]
            try:
                observation = json.dumps(tool.fn(**value["arguments"]), default=str)
            except Exception as exc:  # tool errors are observations, not crashes
                observation = f"ERROR: {type(exc).__name__}: {exc}"
            run.steps.append(Step(tool.name, value["arguments"], observation, result.attempts))
            history.append(
                f"- called {tool.name}({json.dumps(value['arguments'])}) -> {observation}"
            )

        run.reason = f"no final answer within {self.max_steps} steps"
        return run
