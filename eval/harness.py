"""Sentinel eval harness — the "operate" proof.

Runs the golden scenarios and scores:
  - compliance_recall      % of planted violations the system caught
  - citation_accuracy      % of caught violations citing the expected regulation
  - grounding_rate         % of asserted (PASS/VIOLATION) findings backed by a retrieved reg
  - budget_adherence       % of feasible scenarios brought within budget
  - plan_completeness      % of spec categories represented in the cart
  - false_violation_rate   violations raised on clean (no-plant) scenarios
  - cost / latency         aggregate per-run economics

Writes eval/reports/run-<ts>.json + eval/reports/latest.md, prints a summary, and
exits non-zero if any threshold is missed (this is the CI deploy gate).

Runs $0/offline by default (heuristic provider + local RAG); set ANTHROPIC_API_KEY/
OPENAI_API_KEY + PROVIDER_MODE=demo to evaluate the real model path.
"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

# make the agent package importable
REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "services" / "agent-python"))

from app.runner import run_plan  # noqa: E402
from app.schema import PlanRequest  # noqa: E402

SCENARIOS = REPO / "eval" / "scenarios" / "golden.json"
REPORTS = REPO / "eval" / "reports"

# eval-gate thresholds (regressions below these block the deploy)
THRESHOLDS = {
    "compliance_recall": 1.00,      # must catch every planted violation
    "citation_accuracy": 1.00,      # and cite the right regulation
    "grounding_rate": 0.95,         # nearly all assertions grounded (rest abstain)
    "budget_adherence": 1.00,       # every feasible scenario brought in-budget
    "false_violation_rate": 0.00,   # no violations on clean carts
    "plan_completeness": 0.95,
}


def _spec_categories(spec) -> set[str]:
    return {c for r in (spec.rooms if spec else []) for c in r.categories}


def run() -> dict:
    scenarios = json.loads(SCENARIOS.read_text("utf-8"))
    results = []
    planted_total = planted_caught = 0
    citation_total = citation_ok = 0
    asserted = grounded = 0
    feasible_total = feasible_in_budget = 0
    clean_total = false_violations = 0
    completeness_acc = []
    cost_sum = latency_sum = 0.0

    for sc in scenarios:
        req = PlanRequest(
            request=sc["request"], budget_usd=sc["budget_usd"],
            contract_id=sc.get("contract_id"), plant_violation_sku=sc.get("plant_violation_sku"))
        res = run_plan(req)
        exp = sc["expected"]

        caught = [f for f in res.findings if f.verdict == "VIOLATION"]
        caught_skus = {f.sku for f in caught}
        expected_skus = set(exp.get("expected_violation_skus", []))

        # recall on planted violations
        for s in expected_skus:
            planted_total += 1
            if s in caught_skus:
                planted_caught += 1

        # citation accuracy on the planted catch
        cc = exp.get("citation_contains")
        if cc and expected_skus:
            for f in caught:
                if f.sku in expected_skus:
                    citation_total += 1
                    cite_str = f.citations[0].citation if f.citations else ""
                    if cc.lower() in cite_str.lower():
                        citation_ok += 1

        # grounding rate
        for f in res.findings:
            if f.verdict in ("PASS", "VIOLATION"):
                asserted += 1
                if f.grounded:
                    grounded += 1

        # budget adherence
        if exp.get("budget_feasible"):
            feasible_total += 1
            if res.budget and res.budget.within_budget:
                feasible_in_budget += 1

        # false violations on clean scenarios
        if not expected_skus:
            clean_total += 1
            false_violations += len(caught)

        # completeness
        spec_cats = _spec_categories(res.spec)
        cart_cats = {l.category for l in res.cart}
        completeness_acc.append(len(cart_cats & spec_cats) / len(spec_cats) if spec_cats else 1.0)

        cost_sum += res.metrics.get("total_cost_usd", 0.0)
        latency_sum += res.metrics.get("total_latency_ms", 0.0)

        results.append({
            "id": sc["id"], "name": sc["name"], "plan_id": res.plan_id,
            "violations": res.violations, "abstentions": res.abstentions,
            "caught_skus": sorted(caught_skus), "expected_skus": sorted(expected_skus),
            "catch_ok": expected_skus.issubset(caught_skus),
            "within_budget": bool(res.budget and res.budget.within_budget),
            "subtotal_usd": res.budget.subtotal_usd if res.budget else None,
            "budget_usd": sc["budget_usd"],
            "cost_usd": res.metrics.get("total_cost_usd"),
            "latency_ms": res.metrics.get("total_latency_ms"),
        })

    metrics = {
        "compliance_recall": round(planted_caught / planted_total, 4) if planted_total else 1.0,
        "citation_accuracy": round(citation_ok / citation_total, 4) if citation_total else 1.0,
        "grounding_rate": round(grounded / asserted, 4) if asserted else 1.0,
        "budget_adherence": round(feasible_in_budget / feasible_total, 4) if feasible_total else 1.0,
        "false_violation_rate": round(false_violations / clean_total, 4) if clean_total else 0.0,
        "plan_completeness": round(sum(completeness_acc) / len(completeness_acc), 4) if completeness_acc else 1.0,
        "avg_cost_usd": round(cost_sum / len(scenarios), 6),
        "avg_latency_ms": round(latency_sum / len(scenarios), 1),
        "scenarios": len(scenarios),
        "planted_violations": planted_total,
        "planted_caught": planted_caught,
    }

    gate = {}
    for k, thr in THRESHOLDS.items():
        v = metrics[k]
        passed = (v <= thr) if k == "false_violation_rate" else (v >= thr)
        gate[k] = {"value": v, "threshold": thr, "pass": passed}
    metrics["gate_passed"] = all(g["pass"] for g in gate.values())

    return {"generated_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "metrics": metrics, "gate": gate, "results": results}


def write_report(report: dict) -> Path:
    REPORTS.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    (REPORTS / f"run-{ts}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")

    m, g = report["metrics"], report["gate"]
    lines = [
        "# Sentinel — Eval Report",
        f"_Generated {report['generated_at']}_  ·  {m['scenarios']} golden scenarios",
        "",
        f"**Gate: {'PASSED ✅' if m['gate_passed'] else 'FAILED ❌'}**",
        "",
        "| Metric | Value | Threshold | Pass |",
        "|---|---|---|---|",
    ]
    label = {"compliance_recall": "Compliance recall (planted violations caught)",
             "citation_accuracy": "Citation accuracy (correct regulation cited)",
             "grounding_rate": "Citation-grounding rate",
             "budget_adherence": "Budget adherence (feasible scenarios)",
             "false_violation_rate": "False-violation rate (clean carts)",
             "plan_completeness": "Plan completeness"}
    for k, gv in g.items():
        pct = f"{gv['value']*100:.1f}%" if k != "false_violation_rate" else f"{gv['value']:.2f}"
        thr = f"{gv['threshold']*100:.0f}%" if k != "false_violation_rate" else f"{gv['threshold']:.2f}"
        lines.append(f"| {label[k]} | {pct} | {thr} | {'✅' if gv['pass'] else '❌'} |")
    lines += [
        f"| Avg cost / run | ${m['avg_cost_usd']:.5f} | — | — |",
        f"| Avg latency / run | {m['avg_latency_ms']:.0f} ms | — | — |",
        "",
        "## Per-scenario",
        "| Scenario | Caught | Expected | Catch | Budget | Subtotal/Budget |",
        "|---|---|---|---|---|---|",
    ]
    for r in report["results"]:
        lines.append(
            f"| {r['name'][:46]} | {','.join(r['caught_skus']) or '—'} | "
            f"{','.join(r['expected_skus']) or '—'} | {'✅' if r['catch_ok'] else '❌'} | "
            f"{'within' if r['within_budget'] else 'OVER'} | "
            f"${(r['subtotal_usd'] or 0):,.0f} / ${r['budget_usd']:,.0f} |")
    (REPORTS / "latest.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return REPORTS / "latest.md"


def main():
    report = run()
    path = write_report(report)
    m = report["metrics"]
    print("\n=== Sentinel eval ===")
    for k, gv in report["gate"].items():
        mark = "OK " if gv["pass"] else "XX "
        print(f"  {mark}{k:22} {gv['value']} (thr {gv['threshold']})")
    print(f"  avg cost/run ${m['avg_cost_usd']:.5f} | avg latency {m['avg_latency_ms']:.0f}ms")
    print(f"  report -> {path}")
    print(f"\nGATE {'PASSED' if m['gate_passed'] else 'FAILED'}")
    sys.exit(0 if m["gate_passed"] else 1)


if __name__ == "__main__":
    main()
