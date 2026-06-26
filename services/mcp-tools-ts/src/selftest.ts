// Quick offline self-test of the four tools (no network). `npm test`.
import { ComplianceTools } from "./tools.js";

const t = new ComplianceTools();
let fail = 0;
const check = (name: string, cond: boolean, extra = "") => {
  console.log(`${cond ? "PASS" : "FAIL"}  ${name}  ${extra}`);
  if (!cond) fail++;
};

// reg_search returns grounded hits for a call-system query
const rs = t.regSearch({ query: "resident call system bedside toilet", k: 3 });
check("reg_search returns hits", rs.results.length > 0, `top=${rs.results[0]?.citation}`);

// validate_item catches the bedside-only call station (TRAP-NC-001 shape)
const v1 = t.validateItem({
  name: "ValueCall Bedside-Only Call Station", category: "nurse_call", subcategory: "Bedside Call Station",
  room_type: "resident_room", attributes: { covers_bedside: true, covers_toilet_bath: false, relays_to_staff: true },
});
check("validate_item catches call-coverage violation", v1.verdict === "VIOLATION", v1.citation?.citation ?? "");

// validate_item passes a compliant bed
const v2 = t.validateItem({
  name: "RestWell LTC Bed", category: "resident_bed", subcategory: "Long-Term Care Bed",
  room_type: "resident_room", attributes: { entrapment_compliant: true, astm_f1858: true, cleanable_surface: true },
});
check("validate_item passes compliant bed", v2.verdict === "PASS");

// validate_layout flags a narrow corridor + small room
const lay = t.validateLayout({ room_type: "resident_room", occupancy: 1, area_sqft: 90, corridor_clear_width_in: 72, beds_per_smoke_compartment: 34 });
check("validate_layout flags small room", lay.findings.some((f) => f.check.includes("square footage") && !f.pass));
check("validate_layout flags narrow corridor", lay.findings.some((f) => f.check.includes("corridor") && !f.pass));
check("validate_layout flags smoke compartment", lay.findings.some((f) => f.check.includes("smoke") && !f.pass));

// cost_calc
const cc = t.costCalc({ lines: [{ unit_price: 1000, qty: 30 }, { unit_price: 500, qty: 30 }], budget: 40000 });
check("cost_calc computes subtotal + over_budget", cc.subtotal === 45000 && cc.within_budget === false && cc.over_by === 5000, `subtotal=${cc.subtotal} over_by=${cc.over_by}`);

console.log(fail ? `\n${fail} check(s) failed` : "\nAll tool self-tests passed");
process.exit(fail ? 1 : 0);
