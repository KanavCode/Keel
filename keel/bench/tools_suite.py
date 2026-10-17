"""Suite 2: pick the right tool and fill its arguments. Native function-calling is never used."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..agent import STEP_SCHEMA, Agent, Tool
from .common import MODES, Outcome, norm, run_mode

NAME = "tools"
SUITE_MODES = ("raw", "extract", "keel")

_ISO_DATE = {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"}


def _tool(name: str, description: str, props: dict) -> Tool:
    schema = {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}
    return Tool(name, description, schema, fn=lambda **_: "ok")  # never executed in the benchmark


TOOLS = [
    _tool(
        "get_weather",
        "Current weather for a city.",
        {"city": {"type": "string"}, "unit": {"enum": ["celsius", "fahrenheit"]}},
    ),
    _tool(
        "convert_currency",
        "Convert an amount between currencies, using ISO 4217 codes.",
        {
            "amount": {"type": "number"},
            "from_currency": {"type": "string", "pattern": r"^[A-Z]{3}$"},
            "to_currency": {"type": "string", "pattern": r"^[A-Z]{3}$"},
        },
    ),
    _tool(
        "search_issues",
        "Search a GitHub repository's issues by label.",
        {
            "repo": {"type": "string", "pattern": r"^[\w.-]+/[\w.-]+$", "description": "owner/name"},
            "label": {"type": "string"},
            "limit": {"type": "integer", "minimum": 1, "maximum": 50},
        },
    ),
    _tool(
        "create_event",
        "Create a calendar event.",
        {
            "title": {"type": "string"},
            "date": {**_ISO_DATE, "description": "YYYY-MM-DD"},
            "attendees": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        },
    ),
    _tool(
        "send_message",
        "Send a message to a person or channel.",
        {
            "channel": {"enum": ["email", "sms", "slack"]},
            "recipient": {"type": "string"},
            "body": {"type": "string"},
        },
    ),
]


@dataclass
class ToolTask:
    id: str
    request: str
    tool: str
    args: dict = field(default_factory=dict)  # only the arguments that are unambiguous; free text is not scored


TASKS: list[ToolTask] = [
    ToolTask("weather-f", "What's the temperature in Mumbai right now, in Fahrenheit?", "get_weather", {"city": "Mumbai", "unit": "fahrenheit"}),
    ToolTask("fx-usd-inr", "Convert 250 US dollars to Indian rupees.", "convert_currency", {"amount": 250, "from_currency": "USD", "to_currency": "INR"}),
    ToolTask("issues-react", "Show me up to 5 issues labelled 'bug' in the repository facebook/react.", "search_issues", {"repo": "facebook/react", "label": "bug", "limit": 5}),
    ToolTask("event-review", "Schedule 'Design review' on 2026-11-05 with Neha and Omar.", "create_event", {"title": "Design review", "date": "2026-11-05", "attendees": ["Neha", "Omar"]}),
    ToolTask("slack-release", "Post to the #releases channel on Slack that build 42 is green.", "send_message", {"channel": "slack", "recipient": "#releases"}),
    ToolTask("weather-c", "Weather in Pune in celsius please.", "get_weather", {"city": "Pune", "unit": "celsius"}),
    ToolTask("fx-eur-usd", "How much is 1,200 euros in US dollars?", "convert_currency", {"amount": 1200, "from_currency": "EUR", "to_currency": "USD"}),
    ToolTask("issues-gfi", "Find 20 issues labelled good-first-issue in vadodara/navra.", "search_issues", {"repo": "vadodara/navra", "label": "good-first-issue", "limit": 20}),
    ToolTask("sms-aman", "Text Aman that the meeting moved to 4pm.", "send_message", {"channel": "sms", "recipient": "Aman"}),
    ToolTask("event-demo", "Put 'Hacktoberfest demo' on the calendar for 2026-10-31 with Riya.", "create_event", {"title": "Hacktoberfest demo", "date": "2026-10-31", "attendees": ["Riya"]}),
    ToolTask("fx-gbp-eur", "Convert 99.5 GBP into EUR.", "convert_currency", {"amount": 99.5, "from_currency": "GBP", "to_currency": "EUR"}),
    ToolTask("email-priya", "Email priya@example.com saying the invoice is attached.", "send_message", {"channel": "email", "recipient": "priya@example.com"}),
]


def run_task(backend, mode: str, task: ToolTask) -> Outcome:
    assert mode in MODES
    agent = Agent(backend, TOOLS)
    prompt, system = agent.step_request(task.request)
    value, calls, latency = run_mode(backend, mode, prompt, STEP_SCHEMA, system=system, verify=agent.verify_step)

    valid = isinstance(value, dict) and "tool" in value and agent.verify_step(value) is None
    correct = False
    if valid and value["tool"] == task.tool:
        args = value["arguments"]
        correct = all(k in args and norm(args[k]) == norm(v) for k, v in task.args.items())
    return Outcome(valid, correct, calls, latency, {"tool": value.get("tool") if isinstance(value, dict) else None})
