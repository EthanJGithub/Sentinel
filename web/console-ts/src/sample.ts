import type { PlanResult } from "./types";

// Embedded offline sample (the planted-call-coverage scenario) so the deployed
// console always renders the full experience even with no backend reachable.
// Flagged in the UI as "offline sample". Mirrors a real agent run.
export const SAMPLE_RESULT: PlanResult = {
  plan_id: "plan_sample01",
  status: "AWAITING_APPROVAL",
  spec: {
    summary: "Equip a 30-bed memory care wing within $480,000, CMS/Life-Safety compliant.",
    budget_usd: 480000,
    rooms: [
      { room_type: "resident_room", count: 30, categories: ["resident_bed", "mattress", "nurse_call", "furniture", "flooring", "casework_door", "fall_prevention"] },
      { room_type: "bathroom", count: 30, categories: ["bathroom_safety", "nurse_call"] },
      { room_type: "nursing_station", count: 2, categories: ["nursing_station"] },
      { room_type: "common_area", count: 2, categories: ["common_area", "mobility"] },
    ],
    constraints: ["Total budget $480,000", "CMS Appendix PP / 42 CFR §483.90", "NFPA 101 (2012) Life Safety"],
  },
  cart: [
    { sku: "DS-RES-1007", name: "CareFrame Memory-Care Bed", category: "resident_bed", subcategory: "Memory-Care Bed", room_type: "resident_room", qty: 30, unit_price: 2480, list_price: 3050, contract_id: "DSSI-DIRECT" },
    { sku: "DS-MAT-1042", name: "MediCushion Pressure-Redistribution Foam", category: "mattress", subcategory: "Pressure-Redistribution Foam", room_type: "resident_room", qty: 30, unit_price: 620, list_price: 780, contract_id: "DSSI-DIRECT" },
    { sku: "DS-NUR-1061", name: "Ascom-equiv Dome Light + Station", category: "nurse_call", subcategory: "Dome Light + Station", room_type: "resident_room", qty: 30, unit_price: 410, list_price: 520, contract_id: "DSSI-DIRECT" },
    { sku: "DS-CAS-1120", name: "DoorTech Resident Room Door (Bed-Movement)", category: "casework_door", subcategory: "Resident Room Door (Bed-Movement)", room_type: "resident_room", qty: 30, unit_price: 880, list_price: 1090, contract_id: "GPO-PREMIER" },
    { sku: "DS-BAT-1188", name: "SafeAssist ADA Grab Bar Set", category: "bathroom_safety", subcategory: "ADA Grab Bar Set", room_type: "bathroom", qty: 60, unit_price: 96, list_price: 130, contract_id: "DSSI-DIRECT" },
    { sku: "TRAP-NC-001", name: "ValueCall Bedside-Only Call Station", category: "nurse_call", subcategory: "Bedside Call Station", room_type: "resident_room", qty: 1, unit_price: 110, list_price: 110, contract_id: null },
  ],
  findings: [
    { sku: "TRAP-NC-001", name: "ValueCall Bedside-Only Call Station", room_type: "resident_room", verdict: "VIOLATION", rule_id: "call_system_coverage", grounded: true,
      rationale: "Resident call system must reach both bedside and toilet/bathing facilities. The item does not satisfy this requirement; its coverage stops at the bedside.",
      citations: [{ reg_id: "cfr-483.90-g", source: "42 CFR 483.90", citation: "42 CFR §483.90(g)", score: 1, quote: "The facility must be adequately equipped to allow residents to call for staff assistance through a communication system which relays the call directly to a staff member or to a centralized staff work area from (1) each resident's bedside; and (2) toilet and bathing facilities." }],
      recommended_substitution: { sku: "DS-NUR-1061", name: "Ascom-equiv Dome Light + Station", price: 410 } },
    { sku: "DS-RES-1007", name: "CareFrame Memory-Care Bed", room_type: "resident_room", verdict: "PASS", rule_id: "bed_entrapment", grounded: true,
      rationale: "Beds/rails must document entrapment-zone conformance (FDA 2006 / ASTM F1858). Item satisfies this requirement per the cited regulation.",
      citations: [{ reg_id: "fda-bed-entrapment-2006", source: "FDA Hospital Bed System Dimensional Guidance (2006) + ASTM F1858", citation: "FDA Guidance: Hospital Bed System Dimensions and Assessment of Entrapment Risk (March 2006)", score: 1, quote: "FDA dimensional guidance to reduce hospital bed entrapment defines seven entrapment zones; rails and gaps must prevent head/neck entrapment." }] },
    { sku: "DS-CAS-1120", name: "DoorTech Resident Room Door (Bed-Movement)", room_type: "resident_room", verdict: "PASS", rule_id: "egress_door_clear_width", grounded: true,
      rationale: "Bed-movement egress doors require ≥ 41.5 in clear width. Item (44 in) satisfies this requirement.",
      citations: [{ reg_id: "nfpa101-2012-18.2.3.6-door", source: "NFPA 101 (2012), Ch.18", citation: "NFPA 101 (2012) §18.2.3.6 (ref. via 42 CFR §483.90(a))", score: 1, quote: "Doors in the means of egress from sleeping rooms designed for the movement of beds shall provide a clear width of not less than 41.5 in (1055 mm)." }] },
    { sku: "DS-BAT-1188", name: "SafeAssist ADA Grab Bar Set", room_type: "bathroom", verdict: "PASS", rule_id: "grab_bar_height", grounded: true,
      rationale: "Grab bars at water closets must be mounted 33–36 in above the floor. Item (34 in) satisfies this requirement.",
      citations: [{ reg_id: "ada-2010-604-grab-bars", source: "2010 ADA Standards", citation: "2010 ADA Standards §609", score: 1, quote: "Grab bars at water closets must be installed 33 in to 36 in above the floor." }] },
    { sku: "DS-MOB-1209", name: "Hoyer-equiv Sit-to-Stand Lift", room_type: "common_area", verdict: "ABSTAIN", rule_id: null, grounded: false, gate_blocked: true,
      rationale: "Retrieved regulation did not directly support a compliance assertion; blocked by the hallucination gate and flagged for human review.",
      citations: [] },
  ],
  budget: { budget_usd: 480000, subtotal_usd: 284086, savings_vs_list_usd: 58940, within_budget: true, swaps: [] },
  audit: [
    { agent: "Planner", ts: "2026-06-26T04:00:00Z", decision: { rooms: 4, summary: "30-bed memory-care wing" } },
    { agent: "Sourcing", ts: "2026-06-26T04:00:01Z", decision: { lines: 6, categories: 6 } },
    { agent: "Compliance", ts: "2026-06-26T04:00:02Z", decision: { violations: 1, abstentions: 1, gate_blocked: 1, checked: 6 } },
    { agent: "Budget", ts: "2026-06-26T04:00:03Z", decision: { subtotal: 284086, within_budget: true, swaps: 0 } },
    { agent: "Audit", ts: "2026-06-26T04:00:04Z", decision: { plan_finalized: true, violations: 1, lines: 6 } },
  ],
  trace: [],
  metrics: {
    total_cost_usd: 0.0214, cost_ceiling_usd: 0.5, over_budget: false, tokens_in: 4120, tokens_out: 980,
    tool_calls: 11, tool_failures: 0, tool_success_rate: 1, total_latency_ms: 3820,
    by_model: { "claude-haiku-4-5-20251001": { cost: 0.0031, calls: 1, tokens: 900 }, "claude-opus-4-8": { cost: 0.0169, calls: 6, tokens: 3600 }, "gpt-4o-mini": { cost: 0.0014, calls: 6, tokens: 600 } },
    by_node: { Planner: { latency_ms: 410, cost: 0.0031 }, Sourcing: { latency_ms: 720, cost: 0 }, Compliance: { latency_ms: 2210, cost: 0.0183 }, Budget: { latency_ms: 300, cost: 0 }, Audit: { latency_ms: 180, cost: 0 } },
    models: { route: "claude-haiku-4-5-20251001", reason: "claude-opus-4-8", cross_check: "gpt-4o-mini", embed: "text-embedding-3-small" },
    using_real_models: true,
  },
  abstentions: 1,
  violations: 1,
};
