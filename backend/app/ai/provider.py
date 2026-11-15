"""LLM adapter (AI doc §2.2; SUG-47). The ONLY module that talks to an LLM
vendor. Gemini and Groq both offer an OpenAI-compatible chat API, so one
small httpx client serves both — no vendor SDK. Prompts, schemas and tool
definitions stay vendor-neutral.

Order: LLM_PROVIDER first, the other configured key as the fallback for
text features (purpose, advisor). Receipt photos use Gemini only (vision).
LLM_PROVIDER=none, or no key -> no providers -> every caller uses its
non-AI path. API keys are never logged or returned."""
from __future__ import annotations

import base64
import json
import re
import time
from dataclasses import dataclass, field

import httpx

from ..config import get_settings

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/openai"
GROQ_URL = "https://api.groq.com/openai/v1"


class AIUnavailable(Exception):
    """Timeout, network/HTTP error, provider quota (429) or an unreadable response."""


@dataclass
class Reply:
    text: str
    tool_calls: list[dict]  # [{"id", "name", "arguments": dict}]
    provider: str
    model: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    latency_ms: int = 0
    # The provider's own assistant message, sent back unchanged in the next round: Gemini rejects
    # (400) tool calls that lose their `extra_content.google.thought_signature`.
    assistant_message: dict | None = None


@dataclass
class Provider:
    name: str
    url: str
    key: str = field(repr=False)
    model: str = ""
    timeout: float = 20

    def chat(self, messages: list[dict], tools: list[dict] | None = None, max_tokens: int = 1500) -> Reply:
        body: dict = {"model": self.model, "messages": messages, "max_tokens": max_tokens, "temperature": 0.2}
        if tools:
            body["tools"] = tools
        start = time.monotonic()
        try:
            r = httpx.post(f"{self.url}/chat/completions", json=body, timeout=self.timeout,
                           headers={"Authorization": f"Bearer {self.key}"})
        except httpx.HTTPError as exc:
            raise AIUnavailable(type(exc).__name__) from None
        if r.status_code != 200:
            raise AIUnavailable(f"http_{r.status_code}")
        try:
            data = r.json()
            msg = data["choices"][0]["message"]
        except (ValueError, KeyError, IndexError, TypeError):
            raise AIUnavailable("bad_response") from None
        calls = []
        for tc in msg.get("tool_calls") or []:
            fn = tc.get("function") or {}
            try:
                args = json.loads(fn.get("arguments") or "{}")
            except ValueError:
                args = {}
            calls.append({"id": tc.get("id") or fn.get("name", ""), "name": fn.get("name", ""),
                          "arguments": args if isinstance(args, dict) else {}})
        usage = data.get("usage") or {}
        return Reply(text=msg.get("content") or "", tool_calls=calls, provider=self.name, model=self.model,
                     input_tokens=usage.get("prompt_tokens"), output_tokens=usage.get("completion_tokens"),
                     latency_ms=int((time.monotonic() - start) * 1000),
                     assistant_message={"role": "assistant", "content": msg.get("content"),
                                        "tool_calls": msg["tool_calls"]} if calls else None)


def providers(feature: str) -> list[Provider]:
    """Providers to try, in order, for `feature` (empty list = AI is off)."""
    s = get_settings()
    if s.LLM_PROVIDER == "none":
        return []
    vision = feature == "receipt_extraction"
    gemini = Provider("gemini", GEMINI_URL, s.GEMINI_API_KEY, s.LLM_VISION_MODEL if vision else s.LLM_MODEL,
                      s.LLM_TIMEOUT_SECONDS) if s.GEMINI_API_KEY else None
    groq = Provider("groq", GROQ_URL, s.GROQ_API_KEY, s.GROQ_MODEL, s.LLM_TIMEOUT_SECONDS) \
        if s.GROQ_API_KEY and not vision else None
    order = [gemini, groq] if s.LLM_PROVIDER == "gemini" else [groq, gemini]
    return [p for p in order if p is not None]


def image_part(data: bytes, mime: str) -> dict:
    return {"type": "image_url", "image_url": {"url": f"data:{mime};base64,{base64.b64encode(data).decode()}"}}


def json_object(text: str) -> dict:
    """The {...} block of a model reply (models sometimes add prose or ```json fences)."""
    start, end = text.find("{"), text.rfind("}")
    if start < 0 or end <= start:
        raise ValueError("no JSON object")
    raw = text[start:end + 1]
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        # E2 run: Gemini sometimes writes a broken "\u…" escape inside Bangla text; keep such a
        # backslash as a literal character instead of losing the whole (otherwise valid) answer.
        value = json.loads(re.sub(r'\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})', r"\\\\", raw))
    if not isinstance(value, dict):
        raise ValueError("not an object")
    return value
