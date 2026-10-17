# Keel

**Open models make up file paths. Keel stops that, using a Graphify code graph as ground truth.**

Keel is a reliability harness for open-weight models. It sits between your code and the model
(Gemma 4 via the Gemini API, or anything OpenAI-compatible such as DigitalOcean Gradient, Ollama
or vLLM) and turns unreliable output into verified results. Its flagship use is
[`keel plan`](#keel-plan): give it a repo and an issue, and an open model plans the change with
every file it cites **checked against the repo's [Graphify](https://github.com/Graphify-Labs/graphify)
code graph**.

```
$ keel plan https://github.com/psf/requests "Add a default timeout setting on Session so users do not have to pass timeout= on every request"

**Grounding:** every cited file exists in the code graph (1 model call(s), graph of 1320 nodes)
**Ripple risk:** low (1 other file(s) depend on what this touches)

### Files to change
- `src/requests/sessions.py`: add a 'timeout' attribute to Session, passed as the default in .request()
  - symbols: `Session`, `.request()`
- `src/requests/adapters.py`: make sure the adapter applies the timeout during .send()
  - symbols: `HTTPAdapter`, `.send()`
- `tests/test_requests.py`: add tests that a Session timeout is respected and per-request timeouts override it

### Check these too (they depend on the code above)
- `src/requests/api.py`
```

That is real output, abridged (the unedited text is in [docs/demo-requests.md](docs/demo-requests.md)):
Gemma 4 26B, one call, files verified against the graph, and `api.py` flagged because `requests.get()` calls
into `Session`.

## The problem

A small open model asked "which files should I change?" in a repo it has not seen will happily name
files that do not exist. In our benchmark (below) that is the norm, not the exception. For an
agent or a first-time contributor, a plausible-looking wrong path wastes the most time.

## How Graphify is used

Graphify is central here, not decoration. It is used in five places:

1. **Map the repo.** `graphify update .` builds `graph.json` from tree-sitter, with no LLM and no API cost
   (1,320 nodes for `psf/requests` in about 3 seconds).
2. **Retrieve context.** `graphify query "<issue>"` returns the subgraph relevant to the issue. Keel feeds
   that to the model instead of the whole repo, so it scales to large repositories.
3. **Verify the answer.** Every file the model cites is checked against the graph. A made-up path is sent back
   with `did you mean 'keel/harness.py'?` and a list of files that exist, and the model repairs it.
4. **Estimate the ripple.** Reverse-walk `calls`, `inherits` and `uses` edges to find other files that depend on
   the planned change. (Following imports and doc links flagged 15 unrelated files for one change on `requests`;
   following calls found the 1 that matters. See `RIPPLE_RELATIONS` in [graph.py](keel/graph.py).)
5. **Connect it to a coding agent.** This repo is wired to Claude Code with `graphify install --project`
   ([.claude/](.claude/), [CLAUDE.md](CLAUDE.md)), and Keel's own graph is committed:
   [graphify-out/graph.html](graphify-out/graph.html) (interactive) and
   [GRAPH_REPORT.md](graphify-out/GRAPH_REPORT.md). A second
   [Agent Skill](skills/keel-plan-change/SKILL.md) lets any agent call `keel plan`.

## keel plan

```bash
pip install -e ".[graph]"          # includes Graphify
copy .env.example .env             # add GEMINI_API_KEY (free key: aistudio.google.com/apikey)
keel plan <local-path-or-github-url> "<issue text>"
```

## keel triage (Hacktoberfest)

Rank a repo's open "good first issue" tickets by how small and safe the change looks:

```bash
keel triage https://github.com/python-poetry/poetry --label "good first issue" --limit 4
```

Real output (Gemma 4 26B, 79 seconds, every cited file verified against the graph;
full file: [docs/demo-triage-poetry.md](docs/demo-triage-poetry.md)):

| # | Issue | Files to change | Ripple |
|---|---|---|---|
| #3060 | Documentation contributions | `docs/community.md`, `docs/pyproject.md`, `docs/faq.md`, `docs/contributing.md` | low (0) |
| #8864 | `poetry init --author` doesn't allow multiple authors on Windows | `src/poetry/console/commands/init.py`, `docs/cli.md`, `tests/console/commands/test_init.py` | medium (6) |
| #3061 | First time contributors | docs plus 5 test files | high (28) |
| #3155 | Test Suite Cleanup: Permanent Issue | 3 test files, `base_env.py`, `authenticator.py` | high (41) |

Three of these four are umbrella issues rather than specific bugs, so their plans are broad. The ranking
still does what it should: docs-only work has no ripple, and the real bug (#8864) is a contained change
to one command.

## Results

Gemma 4 26B (`gemma-4-26b-a4b-it`) through the Gemini API. The task: given an issue, plan which files to change
in Keel's own repository (10 issues, one run, Graphify graph as ground truth). Full report:
[bench/results/grounding-gemma-4-26b-a4b-it.md](bench/results/grounding-gemma-4-26b-a4b-it.md).

**When the model is not shown the repo's files** (a realistic case for an agent in an unfamiliar codebase):

| mode | plans that are valid and correct | cited files that don't exist | avg model calls |
|---|---|---|---|
| raw (one call, plain `json.loads`) | 1/10 | **25/26 (96%)** | 1.0 |
| extract (Keel's tolerant JSON parsing, one call) | 0/10 | 25/26 (96%) | 1.0 |
| repair (retry on schema errors only) | 0/10 | 26/27 (96%) | 1.0 |
| **keel** (retry on schema errors **and graph check**) | **8/10** | **0/22 (0%)** | 2.0 |

The model is not bad at JSON. It simply cannot know the repo's file names, so it invents plausible ones.
Format fixes (extract, repair) do nothing for that. Checking each path against the Graphify graph and telling
the model what exists does.

**When the model is given the file list**, invented files vanish for every mode (0 of about 25 citations), and
Keel ties raw (9/10 vs 9/10). Grounding helps most when the model lacks the repo map, which is the common case
for large repositories.

**Extraction and tool use:** Gemma 4 26B already scores 100% in raw mode on both
([report](bench/results/extract-tools-gemma-4-26b-a4b-it.md)), so Keel adds nothing there for this model.

Caveats: 10 tasks, one run per cell, one model. The "symbols not in graph" column in the full report was
computed before Keel learned to read qualified names like `Agent.run`, so it overstates symbol misses. It is
informational and not part of `correct`. Details in [Limitations](#limitations).

## How the harness works

```
prompt + schema ──► model ──► extract JSON ──► schema check ──► verify callback ──► value
                      ▲                              │ fail           │ fail
                      └────── precise repair message ◄────────────────┘
```

- **Extract**: recovers JSON from fences, prose, a leading `<think>` block, trailing commas and Python literals.
- **Validate**: JSON Schema with path-level errors the model can act on.
- **Verify**: a callback for semantic checks a schema cannot express (here: "does this file exist in the graph?").
- **Repair**: the exact error goes back to the model within a call budget.
- **Agent loop**: tool use on the same loop, with no dependence on native function-calling.

```python
from keel import backend_from_env, structured

backend = backend_from_env()
schema = {"type": "object", "properties": {"name": {"type": "string"}, "age": {"type": "integer"}},
          "required": ["name", "age"]}
result = structured(backend, "Extract the person: Asha, 30, Vadodara", schema)
print(result.ok, result.value, f"{result.calls} call(s)")
```

## Open models

Everything runs on open-weight models. The benchmark uses Gemma 4 (`gemma-4-26b-a4b-it` and
`gemma-4-31b-it`) through the Gemini API's free tier. Any OpenAI-compatible server works by changing
`KEEL_BASE_URL`, including DigitalOcean Gradient serverless inference and a local Ollama
(see [.env.example](.env.example)).

## Agent skills

Both follow the [Agent Skills specification](https://agentskills.io/specification):
[`keel-structured-output`](skills/keel-structured-output/SKILL.md) and
[`keel-plan-change`](skills/keel-plan-change/SKILL.md).

## Reproduce

```bash
python -m venv .venv && .venv\Scripts\activate
pip install -e ".[dev,graph]"
pytest                                          # offline, no key needed
keel bench run --dry-run                        # prints the worst-case call count first
keel bench run --models gemma-4-26b-a4b-it --suites grounding-none,grounding-files --repeats 2
```

The grounding benchmark plans changes in Keel's own repository, mapped by Graphify
([keel/bench/data/keel_graph.json](keel/bench/data/keel_graph.json)). Backend errors are listed
separately and never counted as model mistakes.

## Limitations

- **Small benchmark.** The grounding suite is 10 hand-written issues in one repository (Keel itself), run on
  Gemma 4 through one API, mostly with a single repeat. There are no confidence intervals. Treat it as strong
  evidence for one failure mode, not a general leaderboard.
- **Keel adds nothing where the model is already perfect.** On extraction and tool use, Gemma 4 26B scored
  100% even with plain `json.loads` ([report](bench/results/extract-tools-gemma-4-26b-a4b-it.md)), so there was
  nothing to repair. The value shows up in grounding. We expect larger gains on smaller models but have not tested it.
- **Grounded is not the same as right.** Checking that a file exists stops invented paths. It does not prove the
  model picked the best file. That is why `correct` also requires at least half of the gold files to be cited.
- **The metric changed after the first run.** The first version also counted cited symbols that were not graph
  nodes as errors. Error analysis showed these were mostly parameters and flags, which Graphify does not model, so
  file grounding became the headline and symbol misses are reported in a separate column. The same analysis found
  and fixed a real bug in our own JSON extractor (see commit history).
- **An earlier, larger run was stopped** because the free tier made it too slow and the runner only saved at the
  end. Its per-record log is kept as [run-a-progress.log](bench/results/run-a-progress.log) (outcome and call
  count per record; hallucination counts were not saved). The runner now saves after every record.
- **Ripple is a static estimate.** It follows `calls`, `inherits` and `uses` edges from Graphify's tree-sitter
  graph. It misses dynamic dispatch, reflection, other languages and runtime configuration.
- **Repair costs calls.** Hard cases take about twice as many model calls as a single shot.
- **`keel plan` writes `graphify-out/`** into the target repository.
- **`keel triage`** depends on the repo's labels and on GitHub's unauthenticated rate limit (set `GITHUB_TOKEN` to lift it).

## License

MIT
