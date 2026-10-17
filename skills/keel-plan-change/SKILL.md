---
name: keel-plan-change
description: Plan a code change for an issue using a Graphify code graph and an open-weight model, with every cited file and symbol verified against the graph and a ripple report of what else may break. Use when asked how to fix an issue, which files to touch, how risky a change is, or to triage Hacktoberfest "good first issue" tickets in an unfamiliar repository.
license: MIT
compatibility: Requires Python 3.10+, the keel-harness and graphifyy packages, git, and a model key (GEMINI_API_KEY for Gemma 4, or an OpenAI-compatible endpoint).
metadata:
  author: keel-contributors
  version: "0.1"
---

# Plan a change with Keel and Graphify

Graphify maps the repository into a code graph (no LLM needed for code). Keel asks an open model for a
change plan, then checks every file and symbol the model names against that graph. A made-up path is
sent back to the model with "did you mean ...?" until the plan only cites code that exists.

## When to use

- You are new to a repository and need to know where an issue should be fixed.
- You want to know how risky a change is before starting.
- You are choosing between several issues and want the one with the smallest ripple.

## Steps

1. Run the planner with a local path or a GitHub URL, and the issue text:

   ```bash
   keel plan https://github.com/psf/requests "Session.request should give a clearer error when the URL has no scheme"
   ```

2. Read the three parts of the output:
   - **Files to change**: path, reason and symbols, all verified to exist in the graph.
   - **Ripple risk**: low, medium or high, from how many other files depend on the code being changed.
   - **Check these too**: files that depend on the planned change; read or test them after editing.

3. Optional: use `--json` for machine-readable output, `--no-rebuild` to reuse an existing
   `graphify-out/graph.json`, and `--model` to pick a model.

## Exit codes

- `0`: a plan was produced and every citation was verified against the graph.
- `1`: the model produced no plan, or some citations could not be verified. Do not trust unverified paths.
- `2`: Graphify, git or the model endpoint failed. Check `graphify --help` and the API key.

## Notes

- `keel plan` writes `graphify-out/` inside the target repo. Add it to `.gitignore`.
- The plan is guidance, not a patch. Read the cited code before editing it.
