"""Offline CLI to exercise the graph without the API/console. $0, no keys needed.

  python -m app.cli                       # default 30-bed memory-care scenario
  python -m app.cli --plant TRAP-NC-001   # plant a violation and watch it get caught
  python -m app.cli --budget 150000       # tight budget -> triggers budget swaps
"""
from __future__ import annotations

import argparse

from .runner import run_plan
from .schema import PlanRequest

C = {"g": "\033[92m", "r": "\033[91m", "y": "\033[93m", "b": "\033[94m", "d": "\033[2m", "x": "\033[0m"}
VC = {"PASS": C["g"] + "PASS " + C["x"], "VIOLATION": C["r"] + "VIOLATION" + C["x"],
      "ABSTAIN": C["y"] + "ABSTAIN" + C["x"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--request", default="Opening a 30-bed memory-care wing in 60 days. Equip resident "
                    "rooms, nursing station, and common areas, compliant with CMS Life-Safety.")
    ap.add_argument("--budget", type=float, default=480_000)
    ap.add_argument("--plant", default=None, help="SKU to inject as a planted violation")
    ap.add_argument("--contract", default="DSSI-DIRECT")
    args = ap.parse_args()

    req = PlanRequest(request=args.request, budget_usd=args.budget,
                      contract_id=args.contract, plant_violation_sku=args.plant)
    res = run_plan(req)

    print(f"\n{C['b']}=== Sentinel plan {res.plan_id} ({res.status}) ==={C['x']}")
    print(f"{C['d']}models: {res.metrics.get('models')} | real_models={res.metrics.get('using_real_models')}{C['x']}")
    print(f"\nSpec: {res.spec.summary if res.spec else '-'}")
    print(f"Cart: {len(res.cart)} lines across {len({l.category for l in res.cart})} categories")

    b = res.budget
    if b:
        flag = C['g'] + 'within budget' + C['x'] if b.within_budget else C['r'] + 'OVER BUDGET' + C['x']
        print(f"Budget: ${b.subtotal_usd:,.0f} / ${b.budget_usd:,.0f}  [{flag}]  "
              f"(saved ${b.savings_vs_list_usd:,.0f} vs list; {len(b.swaps)} swaps)")

    print(f"\n{C['b']}Compliance ({res.violations} violations, {res.abstentions} abstentions):{C['x']}")
    for f in res.findings:
        if f.verdict == "PASS":
            continue  # show only the interesting ones
        cite = f.citations[0].citation if f.citations else "(no citation)"
        print(f"  {VC[f.verdict]}  {f.name[:42]:42}  {C['d']}{cite}{C['x']}")
        print(f"           {C['d']}{f.rationale[:110]}{C['x']}")
    passes = sum(1 for f in res.findings if f.verdict == 'PASS')
    print(f"  {C['g']}+ {passes} PASS{C['x']} (grounded citations)")

    m = res.metrics
    print(f"\n{C['b']}Operate metrics:{C['x']}")
    print(f"  cost: ${m['total_cost_usd']:.5f} / ceiling ${m['cost_ceiling_usd']}  "
          f"(over_budget={m['over_budget']})")
    print(f"  latency: {m['total_latency_ms']:.0f} ms total | tool success {m['tool_success_rate']*100:.0f}%")
    print(f"  per-node: " + ", ".join(f"{k} {v['latency_ms']:.0f}ms" for k, v in m['by_node'].items()))
    print()


if __name__ == "__main__":
    main()
