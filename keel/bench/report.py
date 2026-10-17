"""Turn benchmark records into a Markdown report. Shows counts (k/n), not just percentages."""

from __future__ import annotations

import statistics
from collections import defaultdict

from .common import MODES


def _frac(k: int, n: int) -> str:
    return f"{k}/{n} ({100 * k / n:.0f}%)" if n else "-"


def render(payload: dict) -> str:
    meta, records = payload["meta"], payload["records"]
    groups: dict[tuple, list[dict]] = defaultdict(list)
    for r in records:
        groups[(r["model"], r["suite"], r["mode"])].append(r)

    lines = [
        "# Keel benchmark report",
        "",
        f"Keel {meta['keel_version']} - {meta['date']} - backend: {meta['backend']} - repeats: {meta['repeats']}",
        "",
        "Modes: **raw** = one call + plain `json.loads`; **extract** = one call + Keel's tolerant extraction; "
        "**repair** = up to 3 calls with schema errors fed back; **keel** = up to 3 calls with schema and "
        "semantic/graph checks fed back. Rates exclude backend errors, which are listed separately.",
        "",
    ]
    for model in meta["models"]:
        lines += [f"## {model}", ""]
        for suite in meta["suites"]:
            rows = []
            for mode in MODES:
                recs = groups.get((model, suite, mode))
                if not recs:
                    continue
                ok = [r for r in recs if r["error"] is None]
                n = len(ok)
                valid = sum(r["valid"] for r in ok)
                correct = sum(r["correct"] for r in ok)
                calls = statistics.mean(r["calls"] for r in ok) if ok else 0
                lat = statistics.median(r["latency_s"] for r in ok) if ok else 0
                row = [mode, _frac(valid, n), _frac(correct, n), f"{calls:.2f}", f"{lat:.1f}s", str(len(recs) - n)]
                if suite.startswith("grounding"):
                    d = [r["detail"] for r in ok if r["detail"].get("valid")]
                    bad, total = sum(x["bad_paths"] for x in d), sum(x["total_paths"] for x in d)
                    row.insert(3, _frac(bad, total))
                rows.append(row)
            if not rows:
                continue
            grounding = suite.startswith("grounding")
            head = ["mode", "valid JSON", "correct"] + (["cited paths that don't exist"] if grounding else []) + ["avg calls", "median latency", "errors"]
            lines += [f"### {suite}", "", "| " + " | ".join(head) + " |", "|" + "---|" * len(head)]
            lines += ["| " + " | ".join(r) + " |" for r in rows]
            lines.append("")
    lines += [
        "`correct` means: extract = every field matches the gold answer; tools = right tool and every pinned "
        "argument; grounding = valid plan, every cited file and symbol exists, and at least half of the gold files are cited.",
        "",
    ]
    return "\n".join(lines)
