import json
import os

import httpx
import pytest

import keel.client as client_mod
from keel.client import BackendError, GeminiBackend, OpenAICompatBackend, backend_from_env
from keel.env import load_dotenv


def _mock(backend, handler):
    backend._http = httpx.Client(transport=httpx.MockTransport(handler), headers=backend._http.headers)
    return backend


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    monkeypatch.setattr(client_mod.time, "sleep", lambda s: None)


def _gemini_reply(text, thought=None):
    parts = ([{"text": thought, "thought": True}] if thought else []) + [{"text": text}]
    return {"candidates": [{"content": {"parts": parts}}]}


def test_gemini_request_shape_and_thought_filtering():
    seen = {}

    def handler(request: httpx.Request):
        seen["url"] = str(request.url)
        seen["key"] = request.headers.get("x-goog-api-key")
        seen["body"] = json.loads(request.content)
        return httpx.Response(200, json=_gemini_reply('{"ok": true}', thought="hmm"))

    backend = _mock(GeminiBackend(api_key="SECRET", model="gemma-4-26b-a4b-it"), handler)
    out = backend.chat(
        [
            {"role": "system", "content": "be terse"},
            {"role": "user", "content": "hi"},
            {"role": "assistant", "content": "yo"},
            {"role": "user", "content": "again"},
        ],
        temperature=0.0,
        max_tokens=77,
    )
    assert out == '{"ok": true}'  # thought part removed
    assert seen["url"].endswith("/models/gemma-4-26b-a4b-it:generateContent")
    assert "SECRET" not in seen["url"] and seen["key"] == "SECRET"
    body = seen["body"]
    assert body["systemInstruction"] == {"parts": [{"text": "be terse"}]}
    assert [c["role"] for c in body["contents"]] == ["user", "model", "user"]
    assert body["generationConfig"] == {
        "temperature": 0.0,
        "maxOutputTokens": 77,
        "thinkingConfig": {"thinkingLevel": "minimal"},
    }


def test_gemini_non_gemma_has_no_thinking_config_by_default():
    assert GeminiBackend(api_key="k", model="gemini-3-flash-preview").thinking is None


def test_gemini_blocked_prompt_raises():
    backend = _mock(
        GeminiBackend(api_key="k"),
        lambda r: httpx.Response(200, json={"promptFeedback": {"blockReason": "SAFETY"}}),
    )
    with pytest.raises(BackendError, match="SAFETY"):
        backend.chat([{"role": "user", "content": "x"}])


def test_gemini_models_lists_generate_capable_and_strips_prefix():
    payload = {
        "models": [
            {"name": "models/gemma-4-31b-it", "supportedGenerationMethods": ["generateContent"]},
            {"name": "models/embedding-001", "supportedGenerationMethods": ["embedContent"]},
        ]
    }
    backend = _mock(GeminiBackend(api_key="k"), lambda r: httpx.Response(200, json=payload))
    assert backend.models() == ["gemma-4-31b-it"]


def test_retries_429_then_succeeds():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        if calls["n"] < 3:
            return httpx.Response(429, text="slow down", headers={"retry-after": "1"})
        return httpx.Response(200, json=_gemini_reply("fine"))

    backend = _mock(GeminiBackend(api_key="k"), handler)
    assert backend.chat([{"role": "user", "content": "x"}]) == "fine"
    assert calls["n"] == 3


def test_non_retryable_error_fails_fast():
    calls = {"n": 0}

    def handler(request):
        calls["n"] += 1
        return httpx.Response(400, text="bad request")

    backend = _mock(GeminiBackend(api_key="k"), handler)
    with pytest.raises(BackendError, match="400"):
        backend.chat([{"role": "user", "content": "x"}])
    assert calls["n"] == 1


def test_openai_compat_shape():
    def handler(request):
        body = json.loads(request.content)
        assert body["model"] == "m" and body["messages"][0]["role"] == "user"
        assert request.headers["authorization"] == "Bearer tok"
        return httpx.Response(200, json={"choices": [{"message": {"content": "hello"}}]})

    backend = _mock(OpenAICompatBackend(base_url="http://x/v1", api_key="tok", model="m"), handler)
    assert backend.chat([{"role": "user", "content": "hi"}]) == "hello"


def test_backend_from_env_selection(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # no .env here or above in tmp
    for name in ("KEEL_PROVIDER", "KEEL_BASE_URL", "KEEL_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY", "KEEL_MODEL", "KEEL_RPM"):
        monkeypatch.delenv(name, raising=False)

    with pytest.raises(BackendError):
        backend_from_env()  # nothing configured

    monkeypatch.setenv("GEMINI_API_KEY", "k")
    backend = backend_from_env()
    assert isinstance(backend, GeminiBackend) and backend.model == "gemma-4-26b-a4b-it"
    assert backend_from_env("gemma-4-31b-it").model == "gemma-4-31b-it"

    monkeypatch.setenv("KEEL_PROVIDER", "openai")
    monkeypatch.setenv("KEEL_BASE_URL", "http://localhost:11434/v1")
    assert isinstance(backend_from_env(), OpenAICompatBackend)  # local server needs no key

    monkeypatch.setenv("KEEL_PROVIDER", "nonsense")
    with pytest.raises(BackendError, match="Unknown KEEL_PROVIDER"):
        backend_from_env()


def test_dotenv_loads_without_overriding_real_env(tmp_path):
    (tmp_path / ".env").write_text(
        '# comment\nKEEL_T_A=one\nexport KEEL_T_B="two words"\nKEEL_T_C=\nKEEL_T_KEEP=file\n', encoding="utf-8"
    )
    os.environ["KEEL_T_KEEP"] = "real"
    try:
        assert load_dotenv(tmp_path) == tmp_path / ".env"
        assert os.environ["KEEL_T_A"] == "one"
        assert os.environ["KEEL_T_B"] == "two words"
        assert "KEEL_T_C" not in os.environ  # empty values are ignored
        assert os.environ["KEEL_T_KEEP"] == "real"
    finally:
        for name in ("KEEL_T_A", "KEEL_T_B", "KEEL_T_C", "KEEL_T_KEEP"):
            os.environ.pop(name, None)
