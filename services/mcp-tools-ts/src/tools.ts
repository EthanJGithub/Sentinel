import { loadRegs, loadRules, regIndex, type RegChunk, type Rule } from "./data.js";
import { KeywordRetriever } from "./retriever.js";
import type {
  TCostCalcInput, TRegSearchInput, TValidateItemInput, TValidateLayoutInput,
} from "./schemas.js";

const ABSTAIN_THRESHOLD = 0.45;

export class ComplianceTools {
  private regs: RegChunk[];
  private rules: Rule[];
  private retriever: KeywordRetriever;
  private index: Record<string, RegChunk>;

  constructor() {
    this.regs = loadRegs();
    this.rules = loadRules();
    this.retriever = new KeywordRetriever(this.regs);
    this.index = regIndex(this.regs);
  }

  // ----- reg_search: RAG over CMS Appendix PP / 42 CFR 483.90 / NFPA 101 -----
  regSearch(input: TRegSearchInput) {
    const hits = this.retriever.search(input.query, input.categories ?? [], input.k ?? 4);
    return {
      results: hits.map((h) => ({
        reg_id: h.chunk.id, source: h.chunk.source, citation: h.chunk.citation,
        title: h.chunk.title, quote: h.chunk.content, score: h.score,
      })),
    };
  }

  private applies(rule: Rule, item: TValidateItemInput): boolean {
    if (rule.category !== "*" && rule.category !== item.category) return false;
    const aw = rule.applies_when ?? {};
    if (aw.subcategory && aw.subcategory !== item.subcategory) return false;
    if (aw.category_in && !aw.category_in.includes(item.category)) return false;
    if (aw.applicable_rooms_includes && item.room_type !== aw.applicable_rooms_includes) return false;
    return true;
  }

  private checkPredicate(pred: Record<string, any>, attrs: Record<string, any>): [boolean, string] {
    for (const [key, expected] of Object.entries(pred)) {
      // missing attribute = not assessable (never a false-positive violation)
      if (key.endsWith("_min")) {
        const a = key.slice(0, -4); const v = attrs[a];
        if (v == null) continue;
        if (Number(v) < Number(expected)) return [false, `${a}=${v} < min ${expected}`];
      } else if (key.endsWith("_range")) {
        const a = key.slice(0, -6); const v = attrs[a];
        if (v == null) continue;
        const [lo, hi] = expected as [number, number];
        if (!(lo <= Number(v) && Number(v) <= hi)) return [false, `${a}=${v} outside [${lo},${hi}]`];
      } else {
        const v = attrs[key];
        if (v == null) continue;
        if (v !== expected) return [false, `${key}=${v} (expected ${expected})`];
      }
    }
    return [true, "all attribute checks passed"];
  }

  // ----- validate_item: rule check + grounded citation (citation-or-abstain) -----
  validateItem(item: TValidateItemInput) {
    const applicable = this.rules.filter((r) => this.applies(r, item));
    const evaluated = applicable.map((r) => {
      const [ok, detail] = this.checkPredicate(r.predicate, item.attributes);
      return { rule: r, ok, detail };
    });
    const failed = evaluated.find((e) => !e.ok);

    if (failed || evaluated.length) {
      const rule = (failed ?? evaluated[0]).rule;
      const verdict = failed ? "VIOLATION" : "PASS";
      const chunk = this.index[rule.reg_id];
      return {
        verdict, rule_id: rule.rule_id,
        citation: chunk ? {
          reg_id: chunk.id, source: chunk.source, citation: chunk.citation,
          title: chunk.title, quote: chunk.content, score: 1.0,
        } : null,
        rationale: failed
          ? `${rule.message} Item does not satisfy this requirement (${(failed as any).detail}).`
          : `${rule.message} Item satisfies this requirement per the cited regulation.`,
        grounded: !!chunk,
      };
    }

    // no explicit rule -> RAG + citation-or-abstain
    const hits = this.retriever.search(`${item.name} ${item.category} ${item.room_type}`,
      [item.category, item.room_type], 3);
    if (!hits.length || hits[0].score < ABSTAIN_THRESHOLD) {
      return {
        verdict: "ABSTAIN", rule_id: null, citation: null, grounded: false,
        rationale: "No sufficiently relevant regulation retrieved; abstaining and flagging for human review.",
      };
    }
    const c = hits[0].chunk;
    return {
      verdict: "PASS", rule_id: null,
      citation: { reg_id: c.id, source: c.source, citation: c.citation, title: c.title, quote: c.content, score: hits[0].score },
      rationale: `Reviewed against retrieved regulation ${c.citation}.`,
      grounded: true,
    };
  }

  // ----- validate_layout: room/building-level checks (sq ft, corridor, smoke comp) -----
  validateLayout(input: TValidateLayoutInput) {
    const findings: any[] = [];
    const cite = (id: string) => this.index[id]?.citation ?? id;

    if (input.area_sqft != null) {
      const req = input.occupancy > 1 ? 80 * input.occupancy : 100;
      findings.push({
        check: "resident room square footage", pass: input.area_sqft >= req,
        reg_id: "cfr-483.90-e-1-ii", citation: cite("cfr-483.90-e-1-ii"),
        detail: `${input.area_sqft} sqft vs required ${req} (${input.occupancy > 1 ? `80/resident x${input.occupancy}` : "100 single"})`,
      });
    }
    if (input.corridor_clear_width_in != null) {
      findings.push({
        check: "exit-access corridor clear width", pass: input.corridor_clear_width_in >= 96,
        reg_id: "nfpa101-2012-18.2.3.4-corridor", citation: cite("nfpa101-2012-18.2.3.4-corridor"),
        detail: `${input.corridor_clear_width_in} in vs required 96 in (8 ft)`,
      });
    }
    if (input.beds_per_smoke_compartment != null) {
      findings.push({
        check: "residents per smoke compartment", pass: input.beds_per_smoke_compartment <= 30,
        reg_id: "nfpa101-2012-18.3.7-smoke", citation: cite("nfpa101-2012-18.3.7-smoke"),
        detail: `${input.beds_per_smoke_compartment} vs max 30`,
      });
    }
    if (input.has_window != null) {
      findings.push({
        check: "window to the outside", pass: input.has_window === true,
        reg_id: "cfr-483.90-e-1-vi", citation: cite("cfr-483.90-e-1-vi"),
        detail: input.has_window ? "window present" : "no exterior window",
      });
    }
    if (input.direct_exit_access != null) {
      findings.push({
        check: "direct access to exit corridor", pass: input.direct_exit_access === true,
        reg_id: "cfr-483.90-e-1-iii", citation: cite("cfr-483.90-e-1-iii"),
        detail: input.direct_exit_access ? "direct exit access" : "no direct exit-corridor access",
      });
    }
    return { findings, violations: findings.filter((f) => !f.pass).length };
  }

  // ----- cost_calc: budget math (the Budget agent's constraint check) -----
  costCalc(input: TCostCalcInput) {
    const subtotal = input.lines.reduce((s, l) => s + l.unit_price * l.qty, 0);
    return {
      subtotal: Math.round(subtotal * 100) / 100,
      budget: input.budget,
      within_budget: subtotal <= input.budget,
      over_by: Math.round(Math.max(0, subtotal - input.budget) * 100) / 100,
      headroom: Math.round(Math.max(0, input.budget - subtotal) * 100) / 100,
    };
  }
}
