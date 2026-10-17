from keel import Agent, Tool

ADD = Tool(
    name="add",
    description="Add two integers.",
    parameters={
        "type": "object",
        "properties": {"a": {"type": "integer"}, "b": {"type": "integer"}},
        "required": ["a", "b"],
        "additionalProperties": False,
    },
    fn=lambda a, b: a + b,
)


def test_tool_then_final(scripted):
    backend = scripted(
        ['{"tool": "add", "arguments": {"a": 2, "b": 3}}', '{"final": "5"}']
    )
    run = Agent(backend, [ADD]).run("What is 2+3?")
    assert run.ok and run.final == "5"
    assert run.steps[0].observation == "5"
    assert run.calls == 2


def test_bad_arguments_are_repaired_within_the_step(scripted):
    backend = scripted(
        [
            '{"tool": "add", "arguments": {"a": "two", "b": 3}}',
            '{"tool": "add", "arguments": {"a": 2, "b": 3}}',
            '{"final": "5"}',
        ]
    )
    run = Agent(backend, [ADD]).run("What is 2+3?")
    assert run.ok and run.calls == 3
    assert "arguments for 'add' are invalid" in backend.calls[1][-1]["content"]


def test_unknown_tool_is_rejected_with_the_tool_list(scripted):
    backend = scripted(
        ['{"tool": "multiply", "arguments": {}}', '{"final": "done"}']
    )
    run = Agent(backend, [ADD]).run("anything")
    assert run.ok
    assert "available tools: add" in backend.calls[1][-1]["content"]


def test_tool_exception_becomes_an_observation(scripted):
    boom = Tool("boom", "Always fails.", {"type": "object"}, lambda: 1 / 0)
    backend = scripted(['{"tool": "boom", "arguments": {}}', '{"final": "gave up"}'])
    run = Agent(backend, [boom]).run("try it")
    assert run.ok
    assert run.steps[0].observation.startswith("ERROR: ZeroDivisionError")


def test_step_budget_is_enforced(scripted):
    call = '{"tool": "add", "arguments": {"a": 1, "b": 1}}'
    backend = scripted([call] * 3)
    run = Agent(backend, [ADD], max_steps=3).run("loop forever")
    assert not run.ok and "3 steps" in run.reason
