# Keel build notes

Prize targets, Hacktoberfest Hack Day Vadodara x Navra Community:

1. **Best Open-Source AI Project** (DigitalOcean): open-weight AI is central, public repo, open license.
2. **Best Use of Graphify**: the code graph is central to the headline feature.
3. **Best Use of Gemma 4**: all benchmarks and demos run on Gemma 4 through the Gemini API.

## Status

| Piece | State |
|---|---|
| Harness (extract, validate, verify, repair, agent loop) | Done, tested offline |
| Backends: Gemini API (Gemma 4), OpenAI-compatible (DigitalOcean Gradient, Ollama, vLLM) | Done. Gemini path verified live; the OpenAI-compatible path is tested with mocks only |
| Graphify integration (graph reader, grounded verifier, ripple, query-based context) | Done, checked against real Graphify output |
| `keel plan`, `keel triage` | Done, run live on psf/requests and python-poetry/poetry |
| Benchmark | Done for Gemma 4 26B (grounding, extract, tools). Gemma 4 31B not run: too slow for the free tier in the time available |
| Agent Skills | Two, both pass `skills-ref validate` |
| Graphify connected to Claude Code | Done at project level (`.claude/`, `CLAUDE.md`), graph committed |

## Not done

- Benchmark on smaller models, where reliability gaps should be larger.
- Hosted demo (the CLI and committed outputs stand in for it).
- DigitalOcean deployment: no credits were available. The backend is one environment variable away.
