"""Observability backend — turns the in-app cost/latency monitoring into real,
externally-consumable telemetry:

  - Prometheus metrics at /metrics (scrapeable; $0, no account needed)
  - structured JSON logs to stdout (CloudWatch / Loki / any log pipeline ingest these)
  - Langfuse trace export when LANGFUSE_* keys are set (real, no-op otherwise)

So "operate in production with attention to cost/performance" has an actual sink,
not just an in-memory dashboard.
"""
from __future__ import annotations

import json
import logging
import sys
import time
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from .config import get_settings


# ---------------------------------------------------------------------------
# structured JSON logging
# ---------------------------------------------------------------------------
class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        base = {"ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime(record.created)),
                "level": record.levelname, "logger": record.name, "msg": record.getMessage()}
        if hasattr(record, "extra_fields"):
            base.update(record.extra_fields)  # type: ignore[attr-defined]
        return json.dumps(base)


_log_configured = False


def get_logger() -> logging.Logger:
    global _log_configured
    logger = logging.getLogger("sentinel")
    if not _log_configured:
        h = logging.StreamHandler(sys.stdout)
        h.setFormatter(JsonFormatter())
        logger.addHandler(h)
        logger.setLevel(logging.INFO)
        logger.propagate = False
        _log_configured = True
    return logger


def log_event(event: str, **fields: Any) -> None:
    rec = logging.LogRecord("sentinel", logging.INFO, "", 0, event, None, None)
    rec.extra_fields = fields  # type: ignore[attr-defined]
    get_logger().handle(rec)


# ---------------------------------------------------------------------------
# Prometheus-style metrics registry
# ---------------------------------------------------------------------------
@dataclass
class Metrics:
    lock: Lock = field(default_factory=Lock)
    plans_total: int = 0
    orders_total: int = 0
    violations_total: int = 0
    abstentions_total: int = 0
    gate_blocked_total: int = 0
    cost_usd_total: float = 0.0
    latency_ms_total: float = 0.0
    tool_calls_total: int = 0
    tool_failures_total: int = 0
    by_tenant_plans: dict[str, int] = field(default_factory=dict)
    by_model_cost: dict[str, float] = field(default_factory=dict)
    last_latency_ms: float = 0.0

    def record_run(self, result_metrics: dict, violations: int, abstentions: int, tenant: str) -> None:
        with self.lock:
            self.plans_total += 1
            self.violations_total += violations
            self.abstentions_total += abstentions
            self.cost_usd_total += result_metrics.get("total_cost_usd", 0.0)
            self.latency_ms_total += result_metrics.get("total_latency_ms", 0.0)
            self.last_latency_ms = result_metrics.get("total_latency_ms", 0.0)
            self.tool_calls_total += result_metrics.get("tool_calls", 0)
            self.tool_failures_total += result_metrics.get("tool_failures", 0)
            self.by_tenant_plans[tenant] = self.by_tenant_plans.get(tenant, 0) + 1
            for model, v in (result_metrics.get("by_model") or {}).items():
                self.by_model_cost[model] = self.by_model_cost.get(model, 0.0) + v.get("cost", 0.0)

    def record_order(self) -> None:
        with self.lock:
            self.orders_total += 1

    def prometheus(self) -> str:
        def line(name, val, help_, typ="counter", labels=""):
            return f"# HELP {name} {help_}\n# TYPE {name} {typ}\n{name}{labels} {val}\n"
        out = []
        out.append(line("sentinel_plans_total", self.plans_total, "Plans generated"))
        out.append(line("sentinel_orders_total", self.orders_total, "Orders placed (HITL-approved)"))
        out.append(line("sentinel_violations_total", self.violations_total, "Compliance violations caught"))
        out.append(line("sentinel_abstentions_total", self.abstentions_total, "Citation-or-abstain abstentions"))
        out.append(line("sentinel_cost_usd_total", round(self.cost_usd_total, 6), "Cumulative model cost (USD)"))
        out.append(line("sentinel_tool_calls_total", self.tool_calls_total, "Tool calls"))
        out.append(line("sentinel_tool_failures_total", self.tool_failures_total, "Tool failures"))
        out.append(line("sentinel_last_latency_ms", round(self.last_latency_ms, 1),
                        "Latency of the most recent plan (ms)", typ="gauge"))
        for tenant, n in self.by_tenant_plans.items():
            out.append(f'sentinel_plans_by_tenant_total{{tenant="{tenant}"}} {n}\n')
        for model, c in self.by_model_cost.items():
            out.append(f'sentinel_model_cost_usd_total{{model="{model}"}} {round(c, 6)}\n')
        return "".join(out)


METRICS = Metrics()


# ---------------------------------------------------------------------------
# Langfuse export (real when configured; no-op otherwise)
# ---------------------------------------------------------------------------
class _LangfuseExporter:
    def __init__(self):
        self.client = None
        s = get_settings()
        if s.langfuse_public_key and s.langfuse_secret_key:
            try:
                from langfuse import Langfuse  # lazy

                self.client = Langfuse(public_key=s.langfuse_public_key,
                                       secret_key=s.langfuse_secret_key, host=s.langfuse_host)
            except Exception:
                self.client = None

    @property
    def enabled(self) -> bool:
        return self.client is not None

    def export(self, plan_id: str, result_metrics: dict, tenant: str) -> None:
        if not self.client:
            return
        try:
            trace = self.client.trace(name="sentinel.plan", id=plan_id,
                                      metadata={"tenant": tenant, "cost_usd": result_metrics.get("total_cost_usd")})
            for node, v in (result_metrics.get("by_node") or {}).items():
                trace.span(name=node, metadata={"latency_ms": v.get("latency_ms"), "cost_usd": v.get("cost")})
            self.client.flush()
        except Exception:
            pass


_exporter: _LangfuseExporter | None = None


def get_exporter() -> _LangfuseExporter:
    global _exporter
    if _exporter is None:
        _exporter = _LangfuseExporter()
    return _exporter


def record_run(plan_id: str, result_metrics: dict, violations: int, abstentions: int, tenant: str) -> None:
    METRICS.record_run(result_metrics, violations, abstentions, tenant)
    get_exporter().export(plan_id, result_metrics, tenant)
    log_event("plan.completed", plan_id=plan_id, tenant=tenant, violations=violations,
              abstentions=abstentions, cost_usd=result_metrics.get("total_cost_usd"),
              latency_ms=result_metrics.get("total_latency_ms"))
