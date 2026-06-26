"""Builds the graph, runs a plan request, assembles a PlanResult, and holds the
in-memory run store + HITL approval. Used by both the FastAPI app and the eval harness."""
from __future__ import annotations

import json
import uuid
from typing import Callable, Optional

from .agents.context import AgentContext
from .agents.graph import build_graph
from .config import get_settings
from .monitoring import CostMeter
from .persistence import get_store
from .schema import (AuditEntry, BudgetReport, CartLine, ComplianceFinding,
                     PlanRequest, PlanResult, ProcurementSpec, TraceEvent)

# in-memory cache; Postgres (when configured) is the durable store of record
RUNS: dict[str, PlanResult] = {}


def run_plan(req: PlanRequest, on_event: Optional[Callable] = None,
             user_email: Optional[str] = None, tenant_id: str = "cedarwood") -> PlanResult:
    settings = get_settings()
    meter = CostMeter(ceiling_usd=settings.per_request_cost_ceiling_usd)
    if on_event:
        meter.on_event(on_event)
    ctx = AgentContext.build(settings, meter)
    graph = build_graph(ctx)

    plan_id = "plan_" + uuid.uuid4().hex[:10]
    init = {
        "request": req.request, "facility": req.facility_name, "state": req.state,
        "care_type": req.care_type, "budget": req.budget_usd, "contract_id": req.contract_id,
        "plant_violation_sku": req.plant_violation_sku, "audit": [],
    }
    final = graph.invoke(init, {"recursion_limit": 25})

    findings = [ComplianceFinding(**f) for f in final.get("findings", [])]
    result = PlanResult(
        plan_id=plan_id,
        status=final.get("status", "AWAITING_APPROVAL"),
        spec=ProcurementSpec(**final["spec"]) if final.get("spec") else None,
        cart=[CartLine(**c) for c in final.get("cart", [])],
        findings=findings,
        budget=BudgetReport(**final["budget_report"]) if final.get("budget_report") else None,
        audit=[AuditEntry(**a) for a in final.get("audit", [])],
        trace=meter.events,
        metrics={**meter.summary(), "models": ctx.router.active_models(),
                 "using_real_models": ctx.router.using_real_models},
        abstentions=sum(1 for f in findings if f.verdict == "ABSTAIN"),
        violations=sum(1 for f in findings if f.verdict == "VIOLATION"),
    )
    result.metrics["tenant_id"] = tenant_id
    RUNS[plan_id] = result
    # durable persistence (Postgres when configured; no-op offline)
    try:
        get_store().save_run(json.loads(result.model_dump_json()), user_email, tenant_id)
    except Exception:
        pass
    # observability: metrics + structured log + Langfuse export
    try:
        from .observability import record_run as _obs_record
        _obs_record(plan_id, result.metrics, result.violations, result.abstentions, tenant_id)
    except Exception:
        pass
    return result


def get_run(plan_id: str, tenant_id: Optional[str] = None) -> Optional[PlanResult]:
    """tenant_id None = no scoping (admin); otherwise enforce tenant isolation."""
    res = RUNS.get(plan_id)
    if res:
        if tenant_id is not None and res.metrics.get("tenant_id", "cedarwood") != tenant_id:
            return None
        return res
    payload = get_store().load_run(plan_id, tenant_id)
    return PlanResult(**payload) if payload else None


def approve_plan(plan_id: str, approver_email: Optional[str] = None,
                 tenant_id: Optional[str] = None, bearer: Optional[str] = None,
                 facility: str = "Sentinel demo") -> dict:
    res = get_run(plan_id, tenant_id)
    if not res:
        return {"error": "unknown plan_id or not in your tenant"}
    settings = get_settings()
    ctx = AgentContext.build(settings, CostMeter())
    lines = [{"sku": c.sku, "qty": c.qty, "contractId": c.contract_id}
             for c in res.cart
             if not any(f.sku == c.sku and f.verdict == "VIOLATION" for f in res.findings)]
    # forward the approver's bearer token so the C# system-of-record authorizes the order too
    order = ctx.catalog.place_order(res.plan_id, facility, lines, bearer=bearer)
    res.status = "ORDERED"
    RUNS[plan_id] = res
    get_store().update_status(plan_id, "ORDERED")
    try:
        from .observability import METRICS, log_event
        METRICS.record_order()
        log_event("order.placed", plan_id=plan_id, approved_by=approver_email,
                  total=order.get("total"), tenant=tenant_id)
    except Exception:
        pass
    return {"plan_id": plan_id, "status": "ORDERED", "order": order, "approved_by": approver_email}
