---
name: keel-structured-output
description: Get schema-valid JSON from an open-weight model (DigitalOcean Gradient, Ollama, vLLM, any OpenAI-compatible endpoint) with automatic parse, validate and repair retries. Use when a task needs reliable structured output or tool arguments from a small or open model, or when raw model JSON keeps breaking.
license: MIT
compatibility: Requires Python 3.10+, the keel-harness package, and network access to the Gemini API (GEMINI_API_KEY) or an OpenAI-compatible endpoint (KEEL_API_KEY).
metadata:
  author: keel-contributors
  version: "0.1"
---

# Keel structured output

Small open models often wrap JSON in prose, add trailing commas, or drift from the schema.
Keel runs a generate, extract, validate, repair loop so the caller gets a schema-valid value
or a clear failure.

## When to use

- You need JSON that must match a schema (extraction, classification, routing, tool arguments).
- You are delegating a sub-task to an open-weight model and cannot afford malformed output.

## Steps

1. Write the JSON Schema for the answer to a file, for example `schema.json`.
2. Confirm the endpoint works: `keel ping`.
3. Run the request:

   ```bash
   keel ask "Extract the person from: Asha, 30, lives in Vadodara" --schema schema.json --trace
   ```

4. Read stdout for the validated JSON. `--trace` prints every attempt and why a retry happened.

## Exit codes

- `0`: valid JSON printed to stdout.
- `1`: the model never produced valid output within `--max-attempts`. Loosen the schema or
  simplify the prompt before retrying.
- `2`: endpoint or key problem. Check `GEMINI_API_KEY` (or `KEEL_BASE_URL` and `KEEL_API_KEY`) and `KEEL_MODEL`.

## Notes

- Do not trust unvalidated model JSON. Always go through `keel ask` or `keel.structured`.
- Pass a `verify` callback via the Python API for semantic checks the schema cannot express.
