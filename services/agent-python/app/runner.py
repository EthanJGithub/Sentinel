"""Builds the graph, runs a plan request, assembles a PlanResult, and holds the
in-memory run store + HITL approval. Used by both the FastAPI app and the eval harness."""
from __future__ import annotations

import uuid
from typing import Callable, Optional

from .agents.context import AgentContext
from .agents.graph import build_graph
from .config import get_settings
from .monitoring import CostMeter
from .schema import (AuditEntry, BudgetReport, CartLine, ComplianceFinding,
                     PlanRequest, PlanResult, ProcurementSpec, TraceEvent)

# in-memory store (Postgres holds the durable audit trail in the full deploy)
RUNS: dict[str, PlanResult] = {}


def run_plan(req: PlanRequest, on_event: Optional[Callable] = None) -> PlanResult:
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
    RUNS[plan_id] = result
    return result


def approve_plan(plan_id: str) -> dict:
    res = RUNS.get(plan_id)
    if not res:
        return {"error": "unknown plan_id"}
    settings = get_settings()
    ctx = AgentContext.build(settings, CostMeter())
    lines = [{"sku": c.sku, "qty": c.qty, "contractId": c.contract_id}
             for c in res.cart
             if not any(f.sku == c.sku and f.verdict == "VIOLATION" for f in res.findings)]
    order = ctx.catalog.place_order(res.plan_id, "Sentinel demo", lines)
    res.status = "ORDERED"
    return {"plan_id": plan_id, "status": "ORDERED", "order": order}
