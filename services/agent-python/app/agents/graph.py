"""The LangGraph multi-agent graph: Planner -> Sourcing -> Compliance -> Budget ->
Audit, with re-source loops (compliance violation or over-budget) and an HITL
interrupt before order placement (handled at the API layer via status).

Each node records latency + model/token cost to the CostMeter so the whole run is
observable. The Compliance node enforces citation-or-abstain + the hallucination gate.
"""
from __future__ import annotations

import datetime as dt
from typing import Any, Optional, TypedDict

from langgraph.graph import END, StateGraph

from ..compliance import evaluate_item_rules
from ..schema import (AuditEntry, BudgetReport, CartLine, Citation,
                      ComplianceFinding, ProcurementSpec, RoomSpec)
from .context import AgentContext

MAX_RESOURCE_LOOPS = 2
ABSTAIN_THRESHOLD = 0.45  # min retrieval score to assert PASS without an explicit rule

# per-category quantity relative to a room's count, and a sqft estimate for flooring
QTY_MULTIPLIER = {
    "resident_bed": 1, "mattress": 1, "nurse_call": 1, "furniture": 2, "casework_door": 1,
    "fall_prevention": 1, "bathroom_safety": 2, "mobility": 1, "common_area": 4,
    "nursing_station": 3, "bed_rail": 1, "flooring": 250,  # sq ft per room
}


class GState(TypedDict, total=False):
    request: str
    facility: str
    state: str
    care_type: str
    budget: float
    contract_id: Optional[str]
    plant_violation_sku: Optional[str]
    spec: dict
    cart: list[dict]
    findings: list[dict]
    budget_report: dict
    audit: list[dict]
    resource_loops: int
    swap_skus: list[str]
    applied_swaps: list[dict]
    status: str


def _now() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


def _reg_index(ctx: AgentContext) -> dict:
    chunks = getattr(ctx.retriever, "chunks", [])
    return {c.id: c for c in chunks}


# ---------------------------------------------------------------------------
# NODES
# ---------------------------------------------------------------------------
def planner_node(ctx: AgentContext):
    def run(state: GState) -> GState:
        with ctx.meter.node("Planner"):
            spec, model, ti, to = ctx.router.plan_spec(
                state["request"], state.get("care_type", "memory_care"), state["budget"])
            ctx.meter.model_call("Planner", model, ti, to, "decompose request -> procurement spec")
            spec["budget_usd"] = state["budget"]
            audit = state.get("audit", []) + [AuditEntry(
                agent="Planner", ts=_now(),
                decision={"rooms": len(spec.get("rooms", [])),
                          "summary": spec.get("summary", "")}).model_dump()]
        return {"spec": spec, "audit": audit, "resource_loops": 0}
    return run


def sourcing_node(ctx: AgentContext):
    def run(state: GState) -> GState:
        with ctx.meter.node("Sourcing"):
            spec = state["spec"]
            contract = state.get("contract_id")
            swap = set(state.get("swap_skus", []))
            existing = state.get("cart", [])

            if swap and existing:
                # re-source loop: replace flagged SKUs with compliant substitutions
                new_cart = []
                for line in existing:
                    if line["sku"] in swap:
                        subs = ctx.catalog.substitutions(line["sku"], limit=3)
                        ctx.meter.tool("Sourcing", "find_substitution", bool(subs),
                                       f"{line['sku']} -> {subs[0]['sku'] if subs else 'none'}")
                        if subs:
                            s = subs[0]
                            new_cart.append(_line_from_product(s, line["room_type"], line["qty"], contract))
                            continue
                    new_cart.append(line)
                return {"cart": new_cart, "swap_skus": []}

            # initial sourcing
            cart: list[dict] = []
            for room in spec.get("rooms", []):
                rt, count = room["room_type"], int(room.get("count", 1))
                for cat in room.get("categories", []):
                    items = ctx.catalog.search(category=cat, room=rt, limit=20)
                    ctx.meter.tool("Sourcing", "catalog_search", bool(items), f"{cat}@{rt}: {len(items)} hits")
                    compliant = [i for i in items if i.get("compliant", True)]
                    pool = sorted(compliant or items, key=lambda d: d.get("bestPrice", d.get("listPrice", 0)))
                    if not pool:
                        continue
                    # pick a median-quality item (not the rock-bottom one) so the Budget
                    # agent has genuine optimization room to swap down toward the budget
                    pick = pool[len(pool) // 2]
                    qty = max(1, QTY_MULTIPLIER.get(cat, 1) * count)
                    cart.append(_line_from_product(pick, rt, qty, contract))

            # demo hook: plant a known non-compliant SKU so the gate has something to catch
            pv = state.get("plant_violation_sku")
            if pv:
                p = ctx.catalog.get(pv)
                if p and not any(l["sku"] == pv for l in cart):
                    qty = max(1, QTY_MULTIPLIER.get(p["category"], 1))
                    cart.append(_line_from_product(p, p.get("applicableRooms", ["resident_room"])[0], qty, contract))
                    ctx.meter.tool("Sourcing", "plant_violation", True, f"injected {pv} for demo")

            audit = state.get("audit", []) + [AuditEntry(
                agent="Sourcing", ts=_now(),
                decision={"lines": len(cart), "categories": len({l['category'] for l in cart})}).model_dump()]
            return {"cart": cart, "audit": audit}
    return run


def _line_from_product(p: dict, room_type: str, qty: int, contract: Optional[str]) -> dict:
    return CartLine(
        sku=p["sku"], name=p["name"], category=p["category"],
        subcategory=p.get("subcategory", ""), room_type=room_type, qty=qty,
        unit_price=float(p.get("bestPrice", p.get("listPrice", 0))),
        list_price=float(p.get("listPrice", p.get("list_price", 0))),
        contract_id=p.get("bestContractId"),
        attributes=p.get("attributes", {}),
    ).model_dump()


def compliance_node(ctx: AgentContext):
    reg_index = _reg_index(ctx)

    def run(state: GState) -> GState:
        with ctx.meter.node("Compliance"):
            findings: list[dict] = []
            for line in state["cart"]:
                item = {"sku": line["sku"], "name": line["name"], "category": line["category"],
                        "subcategory": line.get("subcategory", ""), "attributes": line.get("attributes", {}),
                        "applicable_rooms": [line["room_type"]]}
                finding = _validate_one(ctx, reg_index, item, line["room_type"])
                # for a violation, surface a compliant alternative (re-source tool) but
                # keep the item flagged for the human — compliance issues are not silently fixed
                if finding.verdict == "VIOLATION":
                    subs = ctx.catalog.substitutions(line["sku"], limit=1)
                    ctx.meter.tool("Compliance", "find_substitution", bool(subs),
                                   f"{line['sku']} -> {subs[0]['sku'] if subs else 'none'}")
                    if subs:
                        finding.recommended_substitution = {
                            "sku": subs[0]["sku"], "name": subs[0]["name"],
                            "price": subs[0].get("bestPrice", subs[0].get("listPrice"))}
                findings.append(finding.model_dump())

            violations = sum(1 for f in findings if f["verdict"] == "VIOLATION")
            abstentions = sum(1 for f in findings if f["verdict"] == "ABSTAIN")
            blocked = sum(1 for f in findings if f.get("gate_blocked"))
            ctx.meter.gate("Compliance",
                           f"{violations} violation(s) caught, {abstentions} abstention(s) "
                           f"({blocked} blocked by hallucination gate), "
                           f"{sum(1 for f in findings if f['grounded'])} grounded citations")
            audit = state.get("audit", []) + [AuditEntry(
                agent="Compliance", ts=_now(),
                decision={"violations": violations, "abstentions": abstentions,
                          "gate_blocked": blocked, "checked": len(findings)}).model_dump()]
            # compliance violations are held for HITL (not auto-swapped); only budget re-sources
            return {"findings": findings, "audit": audit, "swap_skus": []}
    return run


def _validate_one(ctx: AgentContext, reg_index: dict, item: dict, room_type: str) -> ComplianceFinding:
    rule_results = evaluate_item_rules(item, ctx.rules)
    failed = [r for r in rule_results if not r.passed]

    # ---- explicit attribute rule: deterministic, grounded by construction ----
    if failed or rule_results:
        if failed:
            rule, verdict = failed[0].rule, "VIOLATION"
        else:
            rule, verdict = rule_results[0].rule, "PASS"
        chunk = reg_index.get(rule.reg_id)
        citation = _cite(chunk, rule.citation)
        rationale, model, ti, to = ctx.router.compliance_rationale(
            item, verdict, citation.quote if citation else "", rule.message)
        ctx.meter.model_call("Compliance", model, ti, to, f"reason: {item['sku']} -> {verdict}")
        # optional independent cross-check when real models are configured
        if ctx.router.openai is not None and citation:
            g, gm, gti, gto = ctx.router.grounding_check(rationale, citation.quote)
            ctx.meter.model_call("Compliance", gm, gti, gto, "grounding cross-check")
        return ComplianceFinding(sku=item["sku"], name=item["name"], room_type=room_type,
                                 verdict=verdict, rule_id=rule.rule_id, rationale=rationale,
                                 citations=[citation] if citation else [], grounded=bool(citation))

    # ---- no explicit rule -> RAG + citation-or-abstain + hallucination gate ----
    query = f"{item['name']} {item['category']} {room_type}"
    hits = ctx.retriever.search(query, categories=[item["category"], room_type], k=3)
    ctx.meter.tool("Compliance", "reg_search", bool(hits),
                   f"{item['category']}: top={hits[0].score if hits else 0}")
    if not hits or hits[0].score < ABSTAIN_THRESHOLD:
        return ComplianceFinding(sku=item["sku"], name=item["name"], room_type=room_type,
                                 verdict="ABSTAIN",
                                 rationale="No sufficiently relevant regulation retrieved; abstaining "
                                 "and flagging for human review (citation-or-abstain).",
                                 citations=[], grounded=False)
    top = hits[0]
    citation = Citation(reg_id=top.chunk.id, source=top.chunk.source, citation=top.chunk.citation,
                        quote=top.chunk.content, score=top.score)
    rationale, model, ti, to = ctx.router.compliance_rationale(item, "PASS", citation.quote,
                                                               "Reviewed against retrieved regulation.")
    ctx.meter.model_call("Compliance", model, ti, to, f"reason: {item['sku']} -> PASS")

    # hallucination gate: the asserted claim must be grounded in the retrieved quote
    claim = f"{item['name']} ({item['category']}) complies with {citation.citation}"
    grounded, gmodel, gti, gto = ctx.router.grounding_check(claim, citation.quote)
    if gti or gto:
        ctx.meter.model_call("Compliance", gmodel, gti, gto, "grounding cross-check")
    if not grounded:
        ctx.meter.gate("Compliance", f"hallucination gate BLOCKED ungrounded claim on {item['sku']} -> ABSTAIN")
        return ComplianceFinding(sku=item["sku"], name=item["name"], room_type=room_type,
                                 verdict="ABSTAIN", rationale="Retrieved regulation did not directly "
                                 "support a compliance assertion; blocked by the hallucination gate and "
                                 "flagged for human review.",
                                 citations=[citation], grounded=False, gate_blocked=True)
    return ComplianceFinding(sku=item["sku"], name=item["name"], room_type=room_type,
                             verdict="PASS", rationale=rationale,
                             citations=[citation], grounded=True)


def _cite(chunk, fallback_citation: str) -> Optional[Citation]:
    if chunk is None:
        return None
    return Citation(reg_id=chunk.id, source=chunk.source, citation=chunk.citation,
                    quote=chunk.content, score=1.0)


def budget_node(ctx: AgentContext):
    def run(state: GState) -> GState:
        with ctx.meter.node("Budget"):
            cart = state["cart"]
            skus = [l["sku"] for l in cart]
            prices = {p["sku"]: p for p in ctx.catalog.price(skus, state.get("contract_id"))}
            ctx.meter.tool("Budget", "get_contract_price", bool(prices), f"{len(prices)} priced")
            subtotal = 0.0
            list_total = 0.0
            for l in cart:
                pr = prices.get(l["sku"])
                if pr:
                    l["unit_price"] = pr["bestPrice"]
                    l["contract_id"] = pr["contractId"]
                    l["list_price"] = pr["listPrice"]
                subtotal += l["unit_price"] * l["qty"]
                list_total += l["list_price"] * l["qty"]
            budget = state["budget"]
            within = subtotal <= budget
            loops = state.get("resource_loops", 0)
            applied = list(state.get("applied_swaps", []))

            swaps: list[dict] = []
            out: GState = {"cart": cart}
            if not within and loops < MAX_RESOURCE_LOOPS:
                # propose swapping the most expensive lines for cheaper compliant subs
                over = subtotal - budget
                for l in sorted(cart, key=lambda x: x["unit_price"] * x["qty"], reverse=True):
                    subs = ctx.catalog.substitutions(l["sku"], limit=5)
                    cheaper = [s for s in subs if s["bestPrice"] < l["unit_price"]]
                    if cheaper:
                        swaps.append({"from": l["sku"], "to": cheaper[0]["sku"],
                                      "saves": round((l["unit_price"] - cheaper[0]["bestPrice"]) * l["qty"], 2)})
                        over -= (l["unit_price"] - cheaper[0]["bestPrice"]) * l["qty"]
                    if over <= 0:
                        break
                if swaps:
                    out["swap_skus"] = [s["from"] for s in swaps]
                    out["resource_loops"] = loops + 1
                    out["applied_swaps"] = applied + swaps

            report = BudgetReport(budget_usd=budget, subtotal_usd=round(subtotal, 2),
                                  savings_vs_list_usd=round(list_total - subtotal, 2),
                                  within_budget=within, swaps=applied + swaps).model_dump()
            audit = state.get("audit", []) + [AuditEntry(
                agent="Budget", ts=_now(),
                decision={"subtotal": round(subtotal, 2), "within_budget": within,
                          "swaps": len(swaps)}).model_dump()]
            out["budget_report"] = report
            out["audit"] = audit
            return out
    return run


def audit_node(ctx: AgentContext):
    def run(state: GState) -> GState:
        with ctx.meter.node("Audit"):
            findings = state.get("findings", [])
            audit = state.get("audit", []) + [AuditEntry(
                agent="Audit", ts=_now(),
                decision={"plan_finalized": True,
                          "violations": sum(1 for f in findings if f["verdict"] == "VIOLATION"),
                          "abstentions": sum(1 for f in findings if f["verdict"] == "ABSTAIN"),
                          "lines": len(state.get("cart", []))}).model_dump()]
            ctx.meter.gate("Audit", "immutable decision record written")
        return {"audit": audit, "status": "AWAITING_APPROVAL"}
    return run


# ---------------------------------------------------------------------------
# ROUTING
# ---------------------------------------------------------------------------
def after_compliance(state: GState) -> str:
    return "Sourcing" if state.get("swap_skus") else "Budget"


def after_budget(state: GState) -> str:
    return "Sourcing" if state.get("swap_skus") else "Audit"


def build_graph(ctx: AgentContext):
    g = StateGraph(GState)
    g.add_node("Planner", planner_node(ctx))
    g.add_node("Sourcing", sourcing_node(ctx))
    g.add_node("Compliance", compliance_node(ctx))
    g.add_node("Budget", budget_node(ctx))
    g.add_node("Audit", audit_node(ctx))

    g.set_entry_point("Planner")
    g.add_edge("Planner", "Sourcing")
    g.add_edge("Sourcing", "Compliance")
    g.add_conditional_edges("Compliance", after_compliance, {"Sourcing": "Sourcing", "Budget": "Budget"})
    g.add_conditional_edges("Budget", after_budget, {"Sourcing": "Sourcing", "Audit": "Audit"})
    g.add_edge("Audit", END)
    return g.compile()
