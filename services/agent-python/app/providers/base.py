"""Provider abstraction. The graph never talks to a vendor SDK directly — it asks
the router for a capability (route / reason / cross-check). This is what lets us run
on Claude+OpenAI for the demo and on a free/heuristic provider for dev & eval, which
is exactly the cost discipline the JD asks for."""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Optional, Protocol


@dataclass
class LLMResponse:
    text: str
    model: str
    tokens_in: int
    tokens_out: int
    raw: Any = None

    def json(self) -> dict:
        """Best-effort JSON extraction from the model text."""
        t = self.text.strip()
        if t.startswith("```"):
            t = t.strip("`")
            t = t[t.find("{"):] if "{" in t else t
        start, end = t.find("{"), t.rfind("}")
        if start != -1 and end != -1:
            try:
                return json.loads(t[start:end + 1])
            except json.JSONDecodeError:
                pass
        return {}


class Provider(Protocol):
    name: str

    def complete(self, *, system: str, prompt: str, model: str,
                 json_mode: bool = False, max_tokens: int = 1024) -> LLMResponse: ...


def approx_tokens(*parts: str) -> int:
    """~4 chars/token heuristic for cost accounting when an SDK doesn't return usage."""
    return max(1, sum(len(p) for p in parts) // 4)
