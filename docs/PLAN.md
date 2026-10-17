# Keel build plan

Prize targets, Hacktoberfest Hack Day Vadodara x Navra Community:

1. **Best Open-Source AI Project** (DigitalOcean): open-weight AI is central, public repo, open license.
2. **Best Use of Graphify**: the code knowledge graph is central to the headline feature.
3. Stretch: **Best Use of Gemma 4**, if Gemma 4 is the model behind the demo (check the rules allow
   one project in several categories).

## Inference without DigitalOcean credits

Keel talks to any OpenAI-compatible endpoint, so credits are not required. Candidates, cheapest first:

| Backend | Cost | Notes |
|---|---|---|
| Ollama, local | Free | Offline, slow on CPU, fine for a 4-12B model |
| Gemini API free tier | Free | Hosts Gemma (the Gemma 4 prize wording says it is reachable there). Confirm the model id with `keel ping`. |
| DigitalOcean Gradient | Credits | Switch on later by changing `KEEL_BASE_URL`, no code change |

## Phases

| Phase | Goal | Done when |
|---|---|---|
| 0 | Lock the idea | Done |
| 1 | Core loop | Done: extract, validate, verify, repair, agent loop, CLI, skill, 22 tests |
| 1.5 | Graphify integration | Done: `keel.graph` (CodeGraph, blast radius, grounded verifier), checked against real Graphify output |
| 2 | Live model | Code done: Gemini backend (serves Gemma 4), `.env` loading, throttle and 429 backoff, `keel ping`, `keel models`. **Waiting on:** a live `keel ping` with the real key |
| 3 | Proof | Code done: `keel bench run/report`, 4 suites, 4 modes, oracle-tested offline. **Waiting on:** the live run. Headline metrics: valid-JSON rate, correct-tool rate, **cited-path hallucination rate with vs without graph grounding** |
| 4 | Demo | `keel plan <repo> "<issue>"`: graphify the repo, plan the change with a grounded open model, print files and blast radius. Hacktoberfest first-issue use case. Hosted demo. 2-minute video |
| 5 | Submit | Rules checklist, DEV post, submission form, Graphify skill wiring shown in the video |

## Rules checklist

- [x] Open-weight AI is central (the harness exists to make open models reliable)
- [x] Original implementation (own extract, repair, agent loop, graph grounding)
- [x] Open-source license (MIT)
- [x] Agent skill follows the Agent Skills specification
- [x] Graphify is central to a feature, not decoration
- [ ] Public GitHub repository
- [ ] Live demo URL
- [ ] Benchmarks with real numbers
- [ ] Graphify installed into a coding agent and shown working in the demo video
