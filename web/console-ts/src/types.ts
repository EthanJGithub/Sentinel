// Mirrors the Python Pydantic PlanResult schema.
export interface Citation {
  reg_id: string; source: string; citation: string; quote: string; score: number;
}
export type Verdict = "PASS" | "VIOLATION" | "ABSTAIN";
export interface ComplianceFinding {
  sku: string; name: string; room_type: string; verdict: Verdict;
  rule_id: string | null; rationale: string; citations: Citation[];
  grounded: boolean; gate_blocked?: boolean;
  recommended_substitution?: { sku: string; name: string; price: number } | null;
}
export interface CartLine {
  sku: string; name: string; category: string; subcategory: string; room_type: string;
  qty: number; unit_price: number; list_price: number; contract_id: string | null;
}
export interface BudgetReport {
  budget_usd: number; subtotal_usd: number; savings_vs_list_usd: number;
  within_budget: boolean; swaps: { from: string; to: string; saves: number }[];
}
export interface RoomSpec { room_type: string; count: number; categories: string[]; }
export interface ProcurementSpec { summary: string; rooms: RoomSpec[]; constraints: string[]; budget_usd: number; }
export interface AuditEntry { agent: string; decision: Record<string, any>; ts: string; }
export interface TraceEvent {
  node: string; event: string; detail: string; model?: string | null;
  tokens_in: number; tokens_out: number; cost_usd: number; latency_ms: number;
}
export interface PlanResult {
  plan_id: string; status: string; spec: ProcurementSpec | null; cart: CartLine[];
  findings: ComplianceFinding[]; budget: BudgetReport | null; audit: AuditEntry[];
  trace: TraceEvent[]; metrics: Record<string, any>; abstentions: number; violations: number;
}
export interface PlanRequest {
  request: string; facility_name: string; state: string; care_type: string;
  budget_usd: number; contract_id: string | null; plant_violation_sku: string | null;
}
