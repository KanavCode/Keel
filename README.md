# Keel

**A reliability harness that makes small open-weight models dependable at structured output and tool use.**

Open models are cheap and fast, but they wrap JSON in prose, drift from schemas, and pick tools that
do not exist. Keel sits between your code and any OpenAI-compatible endpoint (DigitalOcean Gradient,
Ollama, vLLM) and turns unreliable output into validated values.

> Status: the harness and benchmark are built and tested offline (54 tests). No accuracy numbers
> are claimed until the benchmark has been run against a live model; results will be committed
> to `bench/results/` with the exact command used.

## How it works

```
prompt + schema ──► model ──► extract JSON ──► schema check ──► verify callback ──► value
                      ▲                              │ fail           │ fail
                      └────── precise repair message ◄────────────────┘
```

- **Extract**: recovers JSON from fences, prose, `<think>` blocks, trailing commas, Python literals.
- **Validate**: JSON Schema (draft 2020-12) with path-level errors the model can act on.
- **Verify**: optional semantic check for things a schema cannot express.
- **Repair**: the exact error goes back to the model, at temperature 0, within a call budget.
- **Agent loop**: tool use built on the same loop, so it needs no native function-calling support.

## Graphify: grounding models in the real codebase

[Graphify](https://github.com/Graphify-Labs/graphify) maps a repository into a knowledge graph
(`graphify-out/graph.json`) with no LLM needed for code. Keel reads that graph and uses it two ways:

- **Grounded verification**: when a model plans a change, every file and symbol it cites is checked
  against the graph. A hallucinated `keel/harnes.py` is rejected with
  `did you mean 'keel/harness.py'?` and the model repairs it, instead of the error reaching you.
- **Blast radius**: reverse-walk `calls`/`imports`/`uses` edges to list what a change can break.

```bash
graphify update .        # build graphify-out/graph.json (no LLM, code only)
```

```python
from keel import CodeGraph, CHANGE_PLAN_SCHEMA, grounded_plan_verifier, structured

graph = CodeGraph.load("graphify-out/graph.json")
plan = structured(backend, "Plan a fix for: retries ignore the call budget",
                  CHANGE_PLAN_SCHEMA, verify=grounded_plan_verifier(graph))
print(graph.blast_radius("structured")["affected_files"])
```

## Quick start

```bash
python -m venv .venv && .venv\Scripts\activate    # Windows
pip install -e ".[dev]"
copy .env.example .env                            # add GEMINI_API_KEY (free key: aistudio.google.com/apikey)
keel ping                                         # checks the key and runs a structured-output smoke test
```

Backends: the native Gemini API (serves Gemma 4, free tier) or any OpenAI-compatible server
(DigitalOcean Gradient, Ollama, vLLM). See [`.env.example`](.env.example).

```python
from keel import backend_from_env, structured

backend = backend_from_env()
schema = {
    "type": "object",
    "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
    "required": ["name", "age"],
}
result = structured(backend, "Extract the person: Asha, 30, Vadodara", schema)
print(result.ok, result.value, f"{result.calls} call(s)")
```

## Benchmark: raw model vs Keel

```bash
keel bench run --dry-run            # print the worst-case number of model calls first
keel bench run --models gemma-4-26b-a4b-it,gemma-4-31b-it --repeats 2
```

Each task runs in four modes: **raw** (one call, plain `json.loads`), **extract** (one call, Keel's
tolerant extraction), **repair** (up to 3 calls, schema errors fed back) and **keel** (up to 3 calls,
schema plus semantic or graph checks fed back). Same prompt in every mode, so the prompt is not a variable.

| Suite | Tasks | Measures |
|---|---|---|
| `extract` | 12 | Schema-valid JSON and exact-match fields from short texts |
| `tools` | 12 | Right tool and right arguments, no native function-calling used |
| `grounding-none` / `grounding-files` | 10 each | Plans a change in Keel's own repo (mapped by Graphify): how often are cited files and symbols made up? |

Results land in `bench/results/` as JSON plus a Markdown report. Reports show counts (k/n), not just
percentages, and backend errors are listed separately instead of being counted as model mistakes.

## Agent skill

[`skills/keel-structured-output`](skills/keel-structured-output/SKILL.md) follows the
[Agent Skills specification](https://agentskills.io/specification), so any compatible agent can
delegate structured sub-tasks to an open model through Keel.

## Development

```bash
pytest
```

## License

MIT
