import { describe, expect, it } from "vitest";
import { ComplianceTools } from "./tools.js";

const t = new ComplianceTools();

describe("reg_search", () => {
  it("returns grounded citations for a call-system query", () => {
    const r = t.regSearch({ query: "resident call system bedside toilet", k: 3 });
    expect(r.results.length).toBeGreaterThan(0);
    expect(r.results[0].citation).toContain("483.90(g)");
  });
});

describe("validate_item (citation-or-abstain)", () => {
  it("catches the bedside-only call station as a VIOLATION", () => {
    const v = t.validateItem({
      name: "ValueCall Bedside-Only Call Station", category: "nurse_call",
      subcategory: "Bedside Call Station", room_type: "resident_room",
      attributes: { covers_bedside: true, covers_toilet_bath: false, relays_to_staff: true },
    });
    expect(v.verdict).toBe("VIOLATION");
    expect(v.citation?.citation).toContain("483.90(g)");
    expect(v.grounded).toBe(true);
  });

  it("passes a compliant bed", () => {
    const v = t.validateItem({
      name: "RestWell LTC Bed", category: "resident_bed", subcategory: "Long-Term Care Bed",
      room_type: "resident_room",
      attributes: { entrapment_compliant: true, astm_f1858: true, cleanable_surface: true },
    });
    expect(v.verdict).toBe("PASS");
  });

  it("does not false-positive on a missing attribute", () => {
    // nurse_call item without cleanable_surface must not be flagged by the cleanable rule
    const v = t.validateItem({
      name: "Dome Station", category: "nurse_call", subcategory: "Dome Light + Station",
      room_type: "resident_room",
      attributes: { covers_bedside: true, covers_toilet_bath: true, relays_to_staff: true },
    });
    expect(v.verdict).not.toBe("VIOLATION");
  });
});

describe("validate_layout", () => {
  it("flags small room, narrow corridor, and overfull smoke compartment", () => {
    const lay = t.validateLayout({
      room_type: "resident_room", occupancy: 1, area_sqft: 90,
      corridor_clear_width_in: 72, beds_per_smoke_compartment: 34,
    });
    expect(lay.findings.find((f) => f.check.includes("square footage"))?.pass).toBe(false);
    expect(lay.findings.find((f) => f.check.includes("corridor"))?.pass).toBe(false);
    expect(lay.findings.find((f) => f.check.includes("smoke"))?.pass).toBe(false);
  });
});

describe("cost_calc", () => {
  it("computes subtotal and over-budget", () => {
    const cc = t.costCalc({ lines: [{ unit_price: 1000, qty: 30 }, { unit_price: 500, qty: 30 }], budget: 40000 });
    expect(cc.subtotal).toBe(45000);
    expect(cc.within_budget).toBe(false);
    expect(cc.over_by).toBe(5000);
  });
});
