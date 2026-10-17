<!-- Real output of: keel plan https://github.com/psf/requests "<issue>"  (model: gemma-4-26b-a4b-it via the Gemini API, 2026-10-17) -->

## Plan: Add a default timeout setting on Session so users do not have to pass timeout= on every request

Implement a default timeout mechanism by adding a timeout attribute to the Session class and ensuring it is propagated through the request lifecycle to the adapters.

**Grounding:** every cited file exists in the code graph (1 model call(s), graph of 1320 nodes)
**Ripple risk:** low (1 other file(s) depend on what this touches)

### Files to change

- `src/requests/sessions.py`: To add a 'timeout' attribute to the Session class and ensure it is passed as a default value during the .request() method call.
  - symbols: `Session`, `.request()`
- `src/requests/adapters.py`: To ensure the timeout value provided by the Session is correctly handled and passed down to the underlying connection logic during the .send() process.
  - symbols: `HTTPAdapter`, `.send()`
- `tests/test_requests.py`: To add test cases verifying that a timeout set on a Session is respected by subsequent requests and that individual request timeouts still override the session default.
  - symbols: `TestRequests`

### Check these too (they depend on the code above)

- `src/requests/api.py`


