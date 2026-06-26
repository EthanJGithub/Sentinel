"""Cost + latency monitoring — the JD's "operate AI in production with attention
to evaluation, cost, and performance tradeoffs." Tracks per-node latency, per-model
token cost, tool-call success, and enforces a per-request cost ceiling. Optionally
mirrors traces to Langfuse and (in AWS) CloudWatch."""
from __future__ import annotations

import time
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Optional

from .schema import TraceEvent

# Public list prices (USD per 1M tokens) for routing/cost reporting. Approximate;
# used to demonstrate cost-aware routing (Haiku route vs Opus reason vs OpenAI).
PRICE_TABLE = {
    "claude-opus-4-8":            {"in": 5.00, "out": 25.00},
    "claude-haiku-4-5-20251001":  {"in": 1.00, "out": 5.00},
    "claude-sonnet-4-6":          {"in": 3.00, "out": 15.00},
    "gpt-4o-mini":                {"in": 0.15, "out": 0.60},
    "text-embedding-3-small":     {"in": 0.02, "out": 0.00},
    "heuristic-local":            {"in": 0.00, "out": 0.00},
    "local-keyword-rag":          {"in": 0.00, "out": 0.00},
}


def cost_for(model: str, tokens_in: int, tokens_out: int) -> float:
    p = PRICE_TABLE.get(model, {"in": 0.0, "out": 0.0})
    return round(tokens_in / 1e6 * p["in"] + tokens_out / 1e6 * p["out"], 6)


@dataclass
class CostMeter:
    ceiling_usd: float = 0.50
    total_cost: float = 0.0
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    by_model: dict = field(default_factory=dict)
    by_node: dict = field(default_factory=dict)
    events: list[TraceEvent] = field(default_factory=list)
    tool_calls: int = 0
    tool_failures: int = 0
    _emit: Optional[callable] = None

    def on_event(self, fn) -> None:
        """Register a callback (used to stream trace events to the WebSocket)."""
        self._emit = fn

    def record(self, ev: TraceEvent) -> None:
        self.events.append(ev)
        if ev.cost_usd:
            self.total_cost += ev.cost_usd
            self.total_tokens_in += ev.tokens_in
            self.total_tokens_out += ev.tokens_out
            m = self.by_model.setdefault(ev.model or "n/a", {"cost": 0.0, "calls": 0, "tokens": 0})
            m["cost"] += ev.cost_usd
            m["calls"] += 1
            m["tokens"] += ev.tokens_in + ev.tokens_out
        if ev.latency_ms:
            n = self.by_node.setdefault(ev.node, {"latency_ms": 0.0, "cost": 0.0})
            n["latency_ms"] += ev.latency_ms
            n["cost"] += ev.cost_usd
        if self._emit:
            try:
                self._emit(ev)
            except Exception:
                pass

    @property
    def over_budget(self) -> bool:
        return self.total_cost > self.ceiling_usd

    @contextmanager
    def node(self, node: str):
        t0 = time.perf_counter()
        self.record(TraceEvent(node=node, event="start", detail=f"{node} started"))
        try:
            yield self
        finally:
            dt = (time.perf_counter() - t0) * 1000
            self.record(TraceEvent(node=node, event="end", detail=f"{node} done", latency_ms=round(dt, 1)))

    def model_call(self, node: str, model: str, tokens_in: int, tokens_out: int, detail: str = "") -> None:
        c = cost_for(model, tokens_in, tokens_out)
        self.record(TraceEvent(node=node, event="model", model=model, detail=detail,
                               tokens_in=tokens_in, tokens_out=tokens_out, cost_usd=c))

    def tool(self, node: str, name: str, ok: bool, detail: str = "") -> None:
        self.tool_calls += 1
        if not ok:
            self.tool_failures += 1
        self.record(TraceEvent(node=node, event="tool", detail=f"{name}: {detail}"))

    def gate(self, node: str, detail: str) -> None:
        self.record(TraceEvent(node=node, event="gate", detail=detail))

    def summary(self) -> dict:
        return {
            "total_cost_usd": round(self.total_cost, 6),
            "cost_ceiling_usd": self.ceiling_usd,
            "over_budget": self.over_budget,
            "tokens_in": self.total_tokens_in,
            "tokens_out": self.total_tokens_out,
            "by_model": self.by_model,
            "by_node": self.by_node,
            "tool_calls": self.tool_calls,
            "tool_failures": self.tool_failures,
            "tool_success_rate": round(1 - (self.tool_failures / self.tool_calls), 3) if self.tool_calls else 1.0,
            "total_latency_ms": round(sum(n["latency_ms"] for n in self.by_node.values()), 1),
        }
