# Keel benchmark report

Keel 0.1.0 - 2026-10-17 - backend: GeminiBackend - repeats: 1

Modes: **raw** = one call + plain `json.loads`; **extract** = one call + Keel's tolerant extraction; **repair** = up to 3 calls with schema errors fed back; **keel** = up to 3 calls with schema and semantic/graph checks fed back. Rates exclude backend errors, which are listed separately.

## gemma-4-26b-a4b-it

### extract

| mode | valid JSON | correct | avg calls | median latency | errors |
|---|---|---|---|---|---|
| raw | 12/12 (100%) | 12/12 (100%) | 1.00 | 5.2s | 0 |
| extract | 11/11 (100%) | 11/11 (100%) | 1.00 | 5.1s | 1 |
| keel | 11/11 (100%) | 11/11 (100%) | 1.00 | 5.0s | 1 |

### tools

| mode | valid JSON | correct | avg calls | median latency | errors |
|---|---|---|---|---|---|
| raw | 11/11 (100%) | 11/11 (100%) | 1.00 | 5.2s | 1 |
| extract | 12/12 (100%) | 12/12 (100%) | 1.00 | 5.2s | 0 |
| keel | 11/11 (100%) | 11/11 (100%) | 1.00 | 5.0s | 1 |

`correct` means: extract = every field matches the gold answer; tools = right tool and every pinned argument; grounding = valid plan, every cited file exists, and at least half of the gold files are cited.

\* Graph nodes are functions, classes and methods, so a legitimate mention of a parameter or flag counts as a miss here. This column is informational and is not part of `correct`.
