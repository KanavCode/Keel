"""Chat backends: OpenAI-compatible servers, and the native Gemini API (which serves Gemma)."""

from __future__ import annotations

import os
import time
from typing import Protocol, Sequence

import httpx

from .env import load_dotenv

DEFAULT_BASE_URL = "https://inference.do-ai.run/v1"
DEFAULT_MODEL = "llama3.3-70b-instruct"
GEMINI_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"
DEFAULT_GEMINI_MODEL = "gemma-4-26b-a4b-it"

Message = dict[str, str]

_RETRY_STATUS = {429, 500, 502, 503, 504}


class BackendError(RuntimeError):
    """The model server could not be reached or returned an unusable response."""


class Backend(Protocol):
    """Anything that turns chat messages into text. Tests use a scripted fake."""

    def chat(
        self,
        messages: Sequence[Message],
        *,
        temperature: float = 0.2,
        max_tokens: int = 1024,
    ) -> str: ...


class _Throttle:
    """Spaces requests out to stay under a requests-per-minute quota."""

    def __init__(self, rpm: float | None) -> None:
        self.interval = 60.0 / rpm if rpm else 0.0
        self._next = 0.0

    def wait(self) -> None:
        if not self.interval:
            return
        now = time.monotonic()
        start = max(now, self._next)
        self._next = start + self.interval
        if start > now:
            time.sleep(start - now)


def _retry_delay(resp: httpx.Response, attempt: int) -> float:
    header = resp.headers.get("retry-after", "")
    if header.replace(".", "", 1).isdigit():
        return min(float(header), 90.0)
    if resp.status_code == 429:
        return min(5.0 * 2**attempt, 60.0)
    return 0.5 * 2**attempt


class _HttpBackend:
    model: str

    def __init__(self, *, headers: dict[str, str], timeout: float, retries: int, rpm: float | None) -> None:
        self._http = httpx.Client(headers={"Content-Type": "application/json", **headers}, timeout=timeout)
        self.retries = retries
        self._throttle = _Throttle(rpm)

    def _send(self, method: str, url: str, **kwargs) -> dict:
        last = ""
        for attempt in range(self.retries):
            self._throttle.wait()
            delay = 0.5 * 2**attempt
            try:
                resp = self._http.request(method, url, **kwargs)
            except httpx.HTTPError as exc:
                last = f"{type(exc).__name__}: {exc}"
            else:
                if resp.status_code < 400:
                    return resp.json()
                last = f"{resp.status_code} {resp.text[:300]}"
                if resp.status_code not in _RETRY_STATUS:
                    break
                delay = _retry_delay(resp, attempt)
            if attempt < self.retries - 1:
                time.sleep(delay)
        raise BackendError(f"{method} {url} failed: {last}")


class OpenAICompatBackend(_HttpBackend):
    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        api_key: str = "",
        model: str = DEFAULT_MODEL,
        timeout: float = 60.0,
        retries: int = 4,
        rpm: float | None = None,
    ) -> None:
        headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
        super().__init__(headers=headers, timeout=timeout, retries=retries, rpm=rpm)
        self.base_url = base_url.rstrip("/")
        self.model = model

    def chat(self, messages: Sequence[Message], *, temperature: float = 0.2, max_tokens: int = 1024) -> str:
        payload = {
            "model": self.model,
            "messages": list(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        data = self._send("POST", f"{self.base_url}/chat/completions", json=payload)
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise BackendError(f"Unexpected response shape: {str(data)[:300]}") from exc
        return content or ""

    def models(self) -> list[str]:
        data = self._send("GET", f"{self.base_url}/models")
        return [m["id"] for m in data.get("data", [])]


class GeminiBackend(_HttpBackend):
    """Native Gemini API (generateContent). Serves Gemini and Gemma models."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = DEFAULT_GEMINI_MODEL,
        thinking: str | None = None,
        timeout: float = 120.0,
        retries: int = 6,
        rpm: float | None = None,
        base_url: str = GEMINI_BASE_URL,
    ) -> None:
        super().__init__(headers={"x-goog-api-key": api_key}, timeout=timeout, retries=retries, rpm=rpm)
        self.base_url = base_url.rstrip("/")
        self.model = model
        # Structured output does not benefit from long reasoning; keep it minimal for Gemma 4.
        self.thinking = thinking if thinking is not None else ("minimal" if model.startswith("gemma-4") else None)

    def chat(self, messages: Sequence[Message], *, temperature: float = 0.2, max_tokens: int = 1024) -> str:
        system = "\n\n".join(m["content"] for m in messages if m["role"] == "system")
        contents = [
            {"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
            for m in messages
            if m["role"] != "system"
        ]
        config: dict = {"temperature": temperature, "maxOutputTokens": max_tokens}
        if self.thinking:
            config["thinkingConfig"] = {"thinkingLevel": self.thinking}
        body: dict = {"contents": contents, "generationConfig": config}
        if system:
            body["systemInstruction"] = {"parts": [{"text": system}]}
        data = self._send("POST", f"{self.base_url}/models/{self.model}:generateContent", json=body)

        candidates = data.get("candidates") or []
        if not candidates:
            reason = (data.get("promptFeedback") or {}).get("blockReason", "no candidates")
            raise BackendError(f"Gemini returned no answer ({reason})")
        parts = (candidates[0].get("content") or {}).get("parts") or []
        return "".join(p.get("text", "") for p in parts if not p.get("thought"))

    def models(self) -> list[str]:
        data = self._send("GET", f"{self.base_url}/models?pageSize=1000")
        return sorted(
            m["name"].removeprefix("models/")
            for m in data.get("models", [])
            if "generateContent" in m.get("supportedGenerationMethods", [])
        )


def _env_float(name: str) -> float | None:
    value = os.environ.get(name, "").strip()
    return float(value) if value else None


def backend_from_env(model: str | None = None) -> OpenAICompatBackend | GeminiBackend:
    """Build a backend from KEEL_* / GEMINI_API_KEY variables (a .env file is loaded if present).

    KEEL_PROVIDER: "gemini" (native Gemini API, serves Gemma) or "openai" (any compatible server).
    When unset, a Gemini/Google key selects gemini, otherwise openai.
    """
    load_dotenv()
    env = os.environ
    gemini_key = env.get("KEEL_API_KEY") or env.get("GEMINI_API_KEY") or env.get("GOOGLE_API_KEY") or ""
    provider = env.get("KEEL_PROVIDER", "").lower()
    if not provider:
        has_gemini_key = bool(env.get("GEMINI_API_KEY") or env.get("GOOGLE_API_KEY"))
        provider = "gemini" if has_gemini_key and not env.get("KEEL_BASE_URL") else "openai"
    rpm = _env_float("KEEL_RPM")

    if provider == "gemini":
        if not gemini_key:
            raise BackendError("No Gemini key found. Put GEMINI_API_KEY=... in your .env file.")
        return GeminiBackend(
            api_key=gemini_key,
            model=model or env.get("KEEL_MODEL", DEFAULT_GEMINI_MODEL),
            thinking=env.get("KEEL_THINKING") or None,
            rpm=rpm if rpm is not None else 12.0,  # stay under the ~15 RPM free tier
        )
    if provider != "openai":
        raise BackendError(f"Unknown KEEL_PROVIDER {provider!r}; use 'gemini' or 'openai'.")

    base_url = env.get("KEEL_BASE_URL", DEFAULT_BASE_URL)
    api_key = env.get("KEEL_API_KEY") or env.get("MODEL_ACCESS_KEY", "")
    if not api_key and base_url.rstrip("/") == DEFAULT_BASE_URL:
        raise BackendError(
            "No API key found. Set KEEL_API_KEY to a DigitalOcean model access key, "
            "or set GEMINI_API_KEY to use the Gemini API, or point KEEL_BASE_URL at a local server."
        )
    return OpenAICompatBackend(
        base_url=base_url, api_key=api_key, model=model or env.get("KEEL_MODEL", DEFAULT_MODEL), rpm=rpm
    )
