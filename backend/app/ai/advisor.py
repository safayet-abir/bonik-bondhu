"""Advisor tool loop (F12; AI doc §8). The model may call read-only tools
for up to 3 rounds, then must answer; the caller checks grounding and
forbidden phrases and falls back to a template answer. Vendor-neutral."""
from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from .provider import AIUnavailable, Provider

PROMPT = (Path(__file__).parent / "prompts" / "advisor_v1.txt").read_text(encoding="utf-8")
MAX_TOOL_ROUNDS = 3


@dataclass
class Answer:
    text: str
    provider: str
    model: str
    tools_used: list[str] = field(default_factory=list)
    tool_outputs: list[str] = field(default_factory=list)
    input_tokens: int = 0
    output_tokens: int = 0
    latency_ms: int = 0


def run(provider: Provider, system: str, history: list[dict], message: str, specs: list[dict],
        execute: Callable[[str, dict], str]) -> Answer:
    msgs = [{"role": "system", "content": system}]
    msgs += [{"role": h["role"], "content": h["text"]} for h in history]
    msgs.append({"role": "user", "content": message})
    ans = Answer("", provider.name, provider.model)
    for round_no in range(MAX_TOOL_ROUNDS + 1):
        reply = provider.chat(msgs, tools=specs if round_no < MAX_TOOL_ROUNDS else None)
        ans.input_tokens += reply.input_tokens or 0
        ans.output_tokens += reply.output_tokens or 0
        ans.latency_ms += reply.latency_ms
        if not reply.tool_calls:
            ans.text = reply.text.strip()
            return ans
        msgs.append(reply.assistant_message or {"role": "assistant", "content": reply.text or None, "tool_calls": [
            {"id": c["id"], "type": "function",
             "function": {"name": c["name"], "arguments": json.dumps(c["arguments"])}}
            for c in reply.tool_calls]})
        for c in reply.tool_calls:
            out = execute(c["name"], c["arguments"])
            ans.tools_used.append(c["name"])
            ans.tool_outputs.append(out)
            msgs.append({"role": "tool", "tool_call_id": c["id"], "content": out})
    raise AIUnavailable("no_answer")
