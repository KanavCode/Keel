<!-- Real output of: keel plan <requests> "<issue>" --compare  (gemma-4-26b-a4b-it via the Gemini API, 2026-10-17). Plans vary slightly between runs. -->

### Without Keel (one unguided call)

- ✗ `session.py`  (does not exist in this repo)
- ✗ `adapter.py`  (does not exist in this repo)
- ✗ `tests/test_session.py`  (does not exist in this repo)

**3 of 3 cited files do not exist.**

### With Keel (graph-grounded)

## Plan: Add a default timeout setting on Session so users do not have to pass timeout= on every request

Implement a default timeout mechanism by adding a timeout attribute to the Session class and ensuring it is propagated through the request lifecycle to the adapters.

**Grounding:** every cited file exists in the code graph (1 model call(s), graph of 1320 nodes)
**Ripple risk:** low (1 other file(s) depend on what this touches)

### Files to change

- `src/requests/sessions.py`: To add a 'timeout' attribute to the Session class and ensure it is passed to the .request() method when not explicitly provided by the user.
  - symbols: `Session`, `.request()`
- `src/requests/adapters.py`: To ensure the timeout value passed from the Session or the request is correctly handled during the connection and sending process.
  - symbols: `HTTPAdapter`, `.send()`
- `tests/test_requests.py`: To add unit tests verifying that a timeout set on a Session is respected by individual requests and that explicit request timeouts override the session default.
  - symbols: `TestRequests`

### Check these too (they depend on the code above)

- `src/requests/api.py`


