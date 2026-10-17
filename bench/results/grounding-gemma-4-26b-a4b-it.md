# Keel benchmark report

Keel 0.1.0 - 2026-10-17 - backend: GeminiBackend - repeats: 1

Modes: **raw** = one call + plain `json.loads`; **extract** = one call + Keel's tolerant extraction; **repair** = up to 3 calls with schema errors fed back; **keel** = up to 3 calls with schema and semantic/graph checks fed back. Rates exclude backend errors, which are listed separately.

## gemma-4-26b-a4b-it

### grounding-none

| mode | valid JSON | correct | cited files that don't exist | cited symbols not in graph* | avg calls | median latency | errors |
|---|---|---|---|---|---|---|---|
| raw | 10/10 (100%) | 1/10 (10%) | 25/26 (96%) | 1/1 (100%) | 1.00 | 6.6s | 0 |
| extract | 10/10 (100%) | 0/10 (0%) | 25/26 (96%) | 1/1 (100%) | 1.00 | 6.4s | 0 |
| repair | 10/10 (100%) | 0/10 (0%) | 26/27 (96%) | 1/1 (100%) | 1.00 | 7.0s | 0 |
| keel | 10/10 (100%) | 8/10 (80%) | 0/22 (0%) | 19/27 (70%) | 2.00 | 11.5s | 0 |

### grounding-files

| mode | valid JSON | correct | cited files that don't exist | cited symbols not in graph* | avg calls | median latency | errors |
|---|---|---|---|---|---|---|---|
| raw | 10/10 (100%) | 9/10 (90%) | 0/25 (0%) | 24/30 (80%) | 1.00 | 5.3s | 0 |
| extract | 10/10 (100%) | 7/10 (70%) | 0/25 (0%) | 21/28 (75%) | 1.00 | 5.7s | 0 |
| repair | 10/10 (100%) | 9/10 (90%) | 0/24 (0%) | 23/32 (72%) | 1.00 | 6.2s | 0 |
| keel | 10/10 (100%) | 9/10 (90%) | 0/26 (0%) | 26/32 (81%) | 1.00 | 5.8s | 0 |

`correct` means: extract = every field matches the gold answer; tools = right tool and every pinned argument; grounding = valid plan, every cited file exists, and at least half of the gold files are cited.

\* Graph nodes are functions, classes and methods, so a legitimate mention of a parameter or flag counts as a miss here. This column is informational and is not part of `correct`.
