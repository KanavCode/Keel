# Demo guide (5 minutes)

## One sentence

Open models invent file paths when they plan code changes. Keel checks every path against a Graphify
code graph and sends the model back to fix it, so the plan only cites code that exists.

## Before going on stage

- [ ] `cd D:\Hacktoberfest\keel` and `.venv\Scripts\activate`; terminal font large (at least 20 pt), dark theme.
- [ ] `keel ping` shows `smoke: structured output ok` (proves the key and network work).
- [ ] `psf/requests` is already cloned in `~/.keel/repos` (the first `keel plan` run does this; run it once beforehand).
- [ ] Browser tabs open and ready: `graphify-out/graph.html`, the GitHub repo, `docs/demo-compare-requests.md`.
- [ ] Do one full dry run of the live command. Record the screen once as a video fallback.
- [ ] Do not run `keel triage` live: it takes about 80 seconds. Show `docs/demo-triage-poetry.md` instead.

## Script

| Time | Do | Say |
|---|---|---|
| 0:00 | Slide or README top | "Ask a small open model which files to change for an issue, in a repo it has never seen. It answers confidently and wrongly. In our benchmark, 96% of the files Gemma 4 cited did not exist." |
| 0:30 | Run the command below | "Same model, same issue. First, one plain call, then Keel." |
| 1:00 | While it runs (about 17 s), point at the output | "Left half: three files, all invented. `session.py` does not exist, the real file is `src/requests/sessions.py`." |
| 1:45 | Scroll to the Keel half | "Now Keel. Graphify mapped the repo into 1,320 nodes in 3 seconds, with no LLM. Keel asked for a plan and checked every file against that graph. Anything made up goes back to the model with 'did you mean' and the list of real files." |
| 2:30 | Point at **Ripple risk** and **Check these too** | "It also tells you what else depends on the change: `api.py` calls into `Session`, so check it. This comes from the graph's call edges." |
| 3:00 | Open `graph.html` | "That graph is Graphify's output for Keel's own code. This repo is also connected to Claude Code through Graphify, so an agent queries the graph before it greps." |
| 3:40 | Show the results table in the README | "Without the file list: 1 of 10 correct plans raw, 8 of 10 with Keel. Invented files 96% down to 0%. With the file list there is no gain, and I say so in the README." |
| 4:20 | Show `docs/demo-triage-poetry.md` | "For Hacktoberfest: `keel triage` ranks good-first-issue tickets by ripple. Docs-only work scores zero; the real `poetry init` bug is a contained change." |
| 4:50 | Close | "Open model, open graph, one rule: never trust a path the graph cannot see." |

The command:

```
keel plan https://github.com/psf/requests "Add a default timeout setting on Session so users do not have to pass timeout= on every request" --compare
```

## If something fails

- **API or network down, or rate-limited:** open `docs/demo-compare-requests.md` and narrate the saved real output ("this is a real run from earlier today").
  Say so out loud; do not pretend it is live.
- **Output differs from the saved one:** that is expected. The model is not deterministic, so files and risk can vary.
  The point is unchanged: the left half cites files that are not in the repo.
- **The unguided half happens to cite real files:** say "this time it got lucky; across 10 issues it invented 25 of 26 paths", then show the table.
- **Slow:** the free Gemini tier is rate limited. Keep the video fallback ready.

## Where each prize track shows up

| Track | Where it is in the project | What to show |
|---|---|---|
| **Best Open-Source AI Project** | An original model harness (`keel/harness.py`, `extract.py`, `agent.py`) that makes open-weight models dependable; MIT licence; public repo; two Agent Skills in `skills/` that pass the official `skills-ref` validator. Runs on any OpenAI-compatible server, including DigitalOcean Gradient and Ollama. | The repo, the skills folder, the `.env.example` showing the backend switch |
| **Best Use of Gemma 4** | Every benchmark and demo runs on `gemma-4-26b-a4b-it` through the Gemini API (native `generateContent` backend in `keel/client.py`, with thinking level handled). It is a focused tool: planning code changes. | The `backend:` line from `keel ping`, the benchmark report |
| **Best Use of Graphify** | Graphify is the ground truth: it maps the repo, `graphify query` selects context, the graph verifies every cited file, and call edges give the ripple. The repo is wired to Claude Code with `graphify install --project`, and Keel's own graph is committed. | `keel plan` output, `graph.html`, `.claude/` and `CLAUDE.md` |

## Questions you may get

- **"Isn't this just JSON validation?"** No. Format fixes (extract, repair) scored 0 of 10 on the no-file-list task,
  the same as raw. The gain comes from checking the answer against the graph.
- **"What if the file exists but is the wrong one?"** Then Keel does not catch it. Grounded is not the same as right.
  That is why correctness also requires at least half of the expected files to be cited (8 of 10, not 10 of 10).
- **"Did you tune the benchmark?"** Once, and it is disclosed. The first version counted parameter names as errors;
  we found they were false positives, made file grounding the headline and kept the symbol column separate. The same
  analysis found a real bug in our own extractor, now fixed with a regression test.
- **"Why no gain with the file list?"** The model already sees the real paths, so it has nothing to invent. Grounding
  matters most when it lacks the repo map, as in a large unfamiliar codebase.
- **"Did you use DigitalOcean?"** Not deployed there; no credits were available. The harness talks to any
  OpenAI-compatible endpoint, so DigitalOcean Gradient is a one-variable switch, but that path is tested with
  mocks only.
- **"Only one model?"** Yes: Gemma 4 26B. The 31B model was too slow on the free tier in the time we had.
  We expect larger gains on smaller models but have not tested it.
