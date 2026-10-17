"""Suite 1: structured extraction from short texts. Gold answers are unambiguous by design."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .common import MODES, Outcome, is_valid, norm, run_mode

NAME = "extract"
SUITE_MODES = ("raw", "extract", "keel")

_STR = {"type": "string"}
_INT = {"type": "integer"}
_NUM = {"type": "number"}
_BOOL = {"type": "boolean"}


def _obj(props: dict) -> dict:
    return {"type": "object", "properties": props, "required": list(props), "additionalProperties": False}


@dataclass
class ExtractTask:
    id: str
    text: str
    schema: dict
    gold: dict


TASKS: list[ExtractTask] = [
    ExtractTask(
        "contact",
        "Hi, I'm Priya Nair, reach me at priya.nair@example.com or +91 98250 12345. I work at Navra Community.",
        _obj({"name": _STR, "email": _STR, "phone": _STR, "org": _STR}),
        {"name": "Priya Nair", "email": "priya.nair@example.com", "phone": "+91 98250 12345", "org": "Navra Community"},
    ),
    ExtractTask(
        "event",
        "The Hacktoberfest Hack Day will be held on 18 October 2026 in Vadodara, starting at 10:30 and lasting 8 hours.",
        _obj(
            {
                "title": _STR,
                "date": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$", "description": "ISO date YYYY-MM-DD"},
                "city": _STR,
                "start_time": {"type": "string", "pattern": r"^\d{2}:\d{2}$", "description": "24h HH:MM"},
                "duration_hours": _INT,
            }
        ),
        {"title": "Hacktoberfest Hack Day", "date": "2026-10-18", "city": "Vadodara", "start_time": "10:30", "duration_hours": 8},
    ),
    ExtractTask(
        "invoice",
        "Invoice #INV-2041 dated 2026-09-03 from Lotus Stationers. Items: 4 notebooks at 120 each, 2 pens at 15 each. "
        "Total due: 510 INR.",
        _obj(
            {
                "invoice_id": _STR,
                "vendor": _STR,
                "currency": {"enum": ["INR", "USD", "EUR"]},
                "total": _INT,
                "line_items": {"type": "array", "items": _obj({"qty": _INT, "unit_price": _INT})},
            }
        ),
        {
            "invoice_id": "INV-2041",
            "vendor": "Lotus Stationers",
            "currency": "INR",
            "total": 510,
            "line_items": [{"qty": 4, "unit_price": 120}, {"qty": 2, "unit_price": 15}],
        },
    ),
    ExtractTask(
        "incident",
        "Production outage: the checkout service returns HTTP 500 for every customer since the 3.2 release. "
        "No workaround is known.",
        _obj(
            {
                "severity": {"enum": ["low", "medium", "high", "critical"], "description": "critical = outage affecting all users"},
                "affects_all_users": _BOOL,
                "has_workaround": _BOOL,
            }
        ),
        {"severity": "critical", "affects_all_users": True, "has_workaround": False},
    ),
    ExtractTask(
        "review",
        "The battery lasts two days, but the camera is disappointing.",
        _obj({"battery": {"enum": ["positive", "negative", "neutral"]}, "camera": {"enum": ["positive", "negative", "neutral"]}}),
        {"battery": "positive", "camera": "negative"},
    ),
    ExtractTask(
        "recipe",
        "Pancakes: mix 200 g flour, 2 eggs, 300 ml milk; cook 3 minutes per side.",
        _obj({"dish": _STR, "egg_count": _INT, "flour_grams": _INT, "milk_ml": _INT, "cook_minutes_per_side": _INT}),
        {"dish": "Pancakes", "egg_count": 2, "flour_grams": 200, "milk_ml": 300, "cook_minutes_per_side": 3},
    ),
    ExtractTask(
        "address",
        "Ship to Rahul Mehta, 14 Alkapuri Society, Vadodara, Gujarat 390007, India.",
        _obj(
            {
                "recipient": _STR,
                "street": _STR,
                "city": _STR,
                "state": _STR,
                "postal_code": {"type": "string", "pattern": r"^\d{6}$"},
                "country": _STR,
            }
        ),
        {
            "recipient": "Rahul Mehta",
            "street": "14 Alkapuri Society",
            "city": "Vadodara",
            "state": "Gujarat",
            "postal_code": "390007",
            "country": "India",
        },
    ),
    ExtractTask(
        "actions",
        "Action items: Asha will send the report by Friday; Dev will fix the login bug by Tuesday.",
        _obj(
            {
                "items": {
                    "type": "array",
                    "items": _obj(
                        {
                            "owner": _STR,
                            "due": {"enum": ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]},
                        }
                    ),
                }
            }
        ),
        {"items": [{"owner": "Asha", "due": "Friday"}, {"owner": "Dev", "due": "Tuesday"}]},
    ),
    ExtractTask(
        "parcel",
        "The package weighs 2.5 kilograms and measures 30 by 20 by 10 centimeters (length by width by height).",
        _obj({"weight_kg": _NUM, "dimensions_cm": _obj({"length": _NUM, "width": _NUM, "height": _NUM})}),
        {"weight_kg": 2.5, "dimensions_cm": {"length": 30, "width": 20, "height": 10}},
    ),
    ExtractTask(
        "flight",
        "Flight AI 812 departs Vadodara (BDQ) at 06:45 and arrives in Delhi (DEL) at 08:20 on 2026-10-20.",
        _obj(
            {
                "flight_number": _STR,
                "origin_code": {"type": "string", "pattern": r"^[A-Z]{3}$"},
                "destination_code": {"type": "string", "pattern": r"^[A-Z]{3}$"},
                "departure": {"type": "string", "pattern": r"^\d{2}:\d{2}$"},
                "arrival": {"type": "string", "pattern": r"^\d{2}:\d{2}$"},
                "date": {"type": "string", "pattern": r"^\d{4}-\d{2}-\d{2}$"},
            }
        ),
        {
            "flight_number": "AI 812",
            "origin_code": "BDQ",
            "destination_code": "DEL",
            "departure": "06:45",
            "arrival": "08:20",
            "date": "2026-10-20",
        },
    ),
    ExtractTask(
        "settings",
        "The user does not want email notifications but does want SMS. Dark mode is off.",
        _obj({"email_notifications": _BOOL, "sms_notifications": _BOOL, "dark_mode": _BOOL}),
        {"email_notifications": False, "sms_notifications": True, "dark_mode": False},
    ),
    ExtractTask(
        "team",
        "Team: Isha (backend), Kabir (frontend), Meera (backend), Tarun (design).",
        _obj(
            {
                "backend_count": _INT,
                "frontend_count": _INT,
                "design_count": _INT,
                "backend_members": {"type": "array", "items": _STR},
            }
        ),
        {"backend_count": 2, "frontend_count": 1, "design_count": 1, "backend_members": ["Isha", "Meera"]},
    ),
]


def score(value: Any, gold: dict) -> tuple[bool, float]:
    """(whole object matches, fraction of top-level fields that match)."""
    if not isinstance(value, dict):
        return False, 0.0
    hits = sum(1 for k, v in gold.items() if k in value and norm(value[k]) == norm(v))
    return hits == len(gold) and set(value) == set(gold), hits / len(gold)


def run_task(backend, mode: str, task: ExtractTask) -> Outcome:
    assert mode in MODES
    prompt = f"Extract the requested fields from this text:\n\n{task.text}"
    value, calls, latency = run_mode(backend, mode, prompt, task.schema)
    valid = is_valid(task.schema, value)
    exact, field_acc = score(value, task.gold)
    return Outcome(valid, valid and exact, calls, latency, {"field_accuracy": round(field_acc, 3)})
