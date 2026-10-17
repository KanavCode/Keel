"""keel CLI: ping, models, ask, bench."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from .client import DEFAULT_GEMINI_MODEL, BackendError, backend_from_env
from .env import load_dotenv
from .harness import structured

_PING_SCHEMA = {
    "type": "object",
    "properties": {"word": {"type": "string", "enum": ["pong"]}},
    "required": ["word"],
    "additionalProperties": False,
}


def _describe(backend) -> str:
    return f"{type(backend).__name__} model={backend.model}"


def _ping(args: argparse.Namespace) -> int:
    backend = backend_from_env(args.model)
    print(f"backend: {_describe(backend)}")
    try:
        names = backend.models()
        gemma = [n for n in names if "gemma" in n.lower()]
        print(f"models:  {len(names)} available; gemma: {', '.join(gemma) or 'none listed'}")
        if backend.model not in names:
            print(f"warning: {backend.model!r} not in the model list; try `keel models`")
    except BackendError as exc:
        print(f"models:  listing failed ({exc})")
    result = structured(backend, 'Reply with the word "pong".', _PING_SCHEMA, max_attempts=3)
    status = "ok" if result.ok else "FAILED"
    latency = sum(a.latency_s for a in result.attempts)
    print(f"smoke:   structured output {status} in {result.calls} call(s), {latency:.2f}s")
    if not result.ok:
        for a in result.attempts:
            print(f"  attempt {a.n}: {a.stage}: {a.problem} | raw={a.raw[:120]!r}")
        return 1
    return 0


def _models(args: argparse.Namespace) -> int:
    backend = backend_from_env()
    for name in backend.models():
        if not args.filter or args.filter.lower() in name.lower():
            print(name)
    return 0


def _ask(args: argparse.Namespace) -> int:
    backend = backend_from_env(args.model)
    schema = json.loads(Path(args.schema).read_text(encoding="utf-8"))
    result = structured(backend, args.prompt, schema, max_attempts=args.max_attempts)
    if args.trace:
        for a in result.attempts:
            print(f"[attempt {a.n}] {a.stage} ({a.latency_s:.2f}s) {a.problem or ''}", file=sys.stderr)
    if not result.ok:
        print("keel: model never produced valid output", file=sys.stderr)
        return 1
    print(json.dumps(result.value, indent=2, ensure_ascii=False))
    return 0


def _bench_run(args: argparse.Namespace) -> int:
    from .bench import runner

    all_suites = list(runner.suite_specs())
    suites = args.suites.split(",") if args.suites else all_suites
    unknown = [s for s in suites if s not in all_suites]
    if unknown:
        print(f"keel: unknown suite(s) {unknown}; choose from {all_suites}", file=sys.stderr)
        return 2
    load_dotenv()
    models = args.models.split(",") if args.models else [os.environ.get("KEEL_MODEL", DEFAULT_GEMINI_MODEL)]

    budget = runner.worst_case_calls(suites, limit=args.limit, repeats=args.repeats)
    total = sum(budget.values()) * len(models)
    print(f"models: {', '.join(models)}")
    print("worst-case model calls per model: " + ", ".join(f"{k}={v}" for k, v in budget.items()))
    print(f"worst-case total: {total} calls (typical runs use fewer; free tiers cap requests per day)")
    if args.dry_run:
        return 0

    def progress(rec) -> None:
        mark = "ERR" if rec.error else ("ok " if rec.correct else "bad")
        print(f"  [{rec.model}] {rec.suite:<16} {rec.task_id:<16} {rec.mode:<8} {mark} calls={rec.calls}", file=sys.stderr)

    backend_kind = type(backend_from_env(models[0])).__name__  # fail fast on a missing key
    records = runner.run_bench(
        models, suites, lambda m: backend_from_env(m), limit=args.limit, repeats=args.repeats, on_record=progress
    )
    payload = runner.results_payload(
        records, models=models, suites=suites, limit=args.limit, repeats=args.repeats, backend_kind=backend_kind
    )
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"saved {len(records)} records to {out}")
    from .bench.report import render

    report = out.with_suffix(".md")
    report.write_text(render(payload), encoding="utf-8")
    print(f"report: {report}")
    return 0


def _bench_report(args: argparse.Namespace) -> int:
    from .bench.report import render

    payload = json.loads(Path(args.results).read_text(encoding="utf-8"))
    text = render(payload)
    if args.out:
        Path(args.out).write_text(text, encoding="utf-8")
    else:
        print(text)
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="keel", description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)

    ping = sub.add_parser("ping", help="check key, endpoint and structured-output smoke test")
    ping.add_argument("--model")
    ping.set_defaults(func=_ping)

    models = sub.add_parser("models", help="list models the endpoint offers")
    models.add_argument("--filter", help="substring filter, e.g. gemma")
    models.set_defaults(func=_models)

    ask = sub.add_parser("ask", help="get schema-valid JSON from the model")
    ask.add_argument("prompt")
    ask.add_argument("--schema", required=True, help="path to a JSON Schema file")
    ask.add_argument("--model")
    ask.add_argument("--max-attempts", type=int, default=3)
    ask.add_argument("--trace", action="store_true", help="print each attempt to stderr")
    ask.set_defaults(func=_ask)

    bench = sub.add_parser("bench", help="raw model vs Keel on fixed task suites")
    bsub = bench.add_subparsers(dest="bench_cmd", required=True)
    run = bsub.add_parser("run", help="run the benchmark")
    run.add_argument("--models", help="comma-separated model ids (default: KEEL_MODEL)")
    run.add_argument("--suites", help="comma-separated: extract,tools,grounding-none,grounding-files (default: all)")
    run.add_argument("--limit", type=int, help="only the first N tasks of each suite (smoke test)")
    run.add_argument("--repeats", type=int, default=1, help="repeat each task to average out sampling noise")
    run.add_argument("--out", default="bench/results/results.json")
    run.add_argument("--dry-run", action="store_true", help="print the worst-case call count and exit")
    run.set_defaults(func=_bench_run)
    rep = bsub.add_parser("report", help="render a Markdown report from a results file")
    rep.add_argument("results")
    rep.add_argument("--out")
    rep.set_defaults(func=_bench_report)

    args = parser.parse_args(argv)
    try:
        return args.func(args)
    except BackendError as exc:
        print(f"keel: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
