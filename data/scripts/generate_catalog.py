"""
Generate a representative senior-care equipment catalog for Sentinel.

Honest framing: this is a *representative* catalog with realistic senior-care
taxonomies (beds, mobility, fall-prevention, nurse-call, furnishings, life-safety
casework) and *synthesized* GPO contract pricing. With Direct Supply's real DSSI
catalog + contracts this gets far richer; the schema and compliance attributes are
the part that matters for the demo.

Outputs (committed to the repo, consumed by the C# catalog service seeder):
  data/catalog/catalog.json          ~300 SKUs with compliance attributes
  data/catalog/contracts.json        GPO contracts + per-SKU contract pricing
  data/catalog/compliance_rules.json attribute -> required regulation citation

Deterministic (seeded) so re-running reproduces the same catalog.
"""
import json
import os
import random
from pathlib import Path

random.seed(20260626)

OUT = Path(__file__).resolve().parents[1] / "catalog"
OUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Category templates. `traps` lists deliberately non-compliant variants used by
# the planted-violation demo + eval harness. Each trap names the reg it violates.
# ---------------------------------------------------------------------------
CATEGORIES = [
    {
        "category": "resident_bed",
        "subcats": ["Long-Term Care Bed", "Bariatric Bed", "Low Bed (Fall Mitigation)", "Memory-Care Bed"],
        "vendors": ["RestWell", "CareFrame", "Stryker-equiv", "Invacare-equiv"],
        "price_range": (1800, 5200),
        "unit": "each",
        "compliant_attrs": {"entrapment_compliant": True, "astm_f1858": True, "adjustable_height": True, "cleanable_surface": True},
        "rooms": ["resident_room"],
    },
    {
        "category": "mattress",
        "subcats": ["Pressure-Redistribution Foam", "Low-Air-Loss", "Gel-Hybrid", "Standard Innerspring"],
        "vendors": ["RestWell", "MediCushion", "AirCare"],
        "price_range": (220, 1400),
        "unit": "each",
        "compliant_attrs": {"cleanable_surface": True, "fluid_proof_cover": True},
        "rooms": ["resident_room"],
    },
    {
        "category": "bed_rail",
        "subcats": ["Assist Bar (Half Rail)", "Transfer Handle", "Quarter Rail"],
        "vendors": ["CareFrame", "SafeAssist"],
        "price_range": (90, 380),
        "unit": "pair",
        "compliant_attrs": {"entrapment_compliant": True, "astm_f1858": True},
        "rooms": ["resident_room"],
    },
    {
        "category": "nurse_call",
        "subcats": ["Bedside Call Station", "Pull-Cord Station", "Wireless Call Pendant", "Dome Light + Station"],
        "vendors": ["Rauland-equiv", "Ascom-equiv", "TekTone-equiv"],
        "price_range": (160, 900),
        "unit": "each",
        "compliant_attrs": {"covers_bedside": True, "covers_toilet_bath": True, "relays_to_staff": True},
        "rooms": ["resident_room", "bathroom"],
    },
    {
        "category": "flooring",
        "subcats": ["Resilient Sheet Vinyl", "Slip-Resistant LVT", "Carpet Tile (Low-Pile)"],
        "vendors": ["FloorSafe", "Tarkett-equiv"],
        "price_range": (3, 9),  # per sq ft
        "unit": "sq_ft",
        "compliant_attrs": {"slip_resistant": True, "cleanable_surface": True, "non_porous": True},
        "rooms": ["resident_room", "corridor", "bathroom", "common_area"],
    },
    {
        "category": "casework_door",
        "subcats": ["Resident Room Door (Bed-Movement)", "Bathroom Door", "Corridor Door (Latching)"],
        "vendors": ["BuildRight", "DoorTech"],
        "price_range": (380, 1500),
        "unit": "each",
        "compliant_attrs": {"clear_width_in": 44, "positive_latching": True, "self_closing": True},
        "rooms": ["resident_room", "corridor", "bathroom"],
    },
    {
        "category": "furniture",
        "subcats": ["Wardrobe w/ Closet", "Overbed Table", "Nightstand", "Recliner (Wipeable)", "Resident Chair"],
        "vendors": ["CareFurnish", "ComfortLine"],
        "price_range": (140, 1300),
        "unit": "each",
        "compliant_attrs": {"cleanable_surface": True, "non_porous": True, "individual_closet": True},
        "rooms": ["resident_room"],
    },
    {
        "category": "bathroom_safety",
        "subcats": ["ADA Grab Bar Set", "Shower Chair", "Raised Toilet Seat", "Bedside Commode"],
        "vendors": ["SafeAssist", "AquaCare"],
        "price_range": (40, 420),
        "unit": "each",
        "compliant_attrs": {"grab_bar_height_in": 34, "slip_resistant": True, "weight_capacity_lb": 350},
        "rooms": ["bathroom"],
    },
    {
        "category": "fall_prevention",
        "subcats": ["Bedside Floor Mat", "Fall-Alert Sensor Pad", "Low-Bed Conversion Kit"],
        "vendors": ["SafeAssist", "GuardCare"],
        "price_range": (45, 600),
        "unit": "each",
        "compliant_attrs": {"slip_resistant": True, "cleanable_surface": True},
        "rooms": ["resident_room"],
    },
    {
        "category": "mobility",
        "subcats": ["Ceiling Lift", "Sit-to-Stand Lift", "Wheelchair (Transport)", "Rollator Walker"],
        "vendors": ["Invacare-equiv", "Hoyer-equiv", "Drive-equiv"],
        "price_range": (160, 6800),
        "unit": "each",
        "compliant_attrs": {"weight_capacity_lb": 400, "cleanable_surface": True},
        "rooms": ["resident_room", "common_area"],
    },
    {
        "category": "common_area",
        "subcats": ["Dining Table (Wheelchair-Height)", "Lounge Seating", "Activity Table", "Wall TV + Mount"],
        "vendors": ["ComfortLine", "CareFurnish"],
        "price_range": (220, 2400),
        "unit": "each",
        "compliant_attrs": {"cleanable_surface": True, "wheelchair_accessible": True},
        "rooms": ["common_area"],
    },
    {
        "category": "nursing_station",
        "subcats": ["Medication Cart (Locking)", "Clinical Workstation", "Vitals Monitor", "Documentation Cart"],
        "vendors": ["MedTech", "CareFurnish"],
        "price_range": (700, 4200),
        "unit": "each",
        "compliant_attrs": {"lockable": True, "cleanable_surface": True},
        "rooms": ["nursing_station"],
    },
]

# Deterministically planted non-compliant SKUs (the "trap" items). Each violates a
# specific, citable rule so the Compliance Agent + eval harness can be exercised.
TRAPS = [
    {
        "sku": "TRAP-NC-001", "name": "ValueCall Bedside-Only Call Station", "category": "nurse_call",
        "subcategory": "Bedside Call Station", "vendor": "BudgetMed", "unit": "each", "list_price": 110.0,
        "attributes": {"covers_bedside": True, "covers_toilet_bath": False, "relays_to_staff": True},
        "violation": {"rule_id": "call_system_coverage", "citation": "42 CFR §483.90(g)",
                      "reason": "Call station does not extend to toilet and bathing facilities as required."},
    },
    {
        "sku": "TRAP-NC-002", "name": "BuildRight 36\" Resident Room Door", "category": "casework_door",
        "subcategory": "Resident Room Door (Bed-Movement)", "vendor": "BuildRight", "unit": "each", "list_price": 340.0,
        "attributes": {"clear_width_in": 36, "positive_latching": True, "self_closing": True},
        "violation": {"rule_id": "egress_door_clear_width", "citation": "NFPA 101 (2012) §18.2.3.6",
                      "reason": "Clear width 36 in is below the 41.5 in required for bed-movement egress doors."},
    },
    {
        "sku": "TRAP-NC-003", "name": "EconoRest Fixed-Frame LTC Bed (Legacy Rails)", "category": "resident_bed",
        "subcategory": "Long-Term Care Bed", "vendor": "BudgetMed", "unit": "each", "list_price": 1290.0,
        "attributes": {"entrapment_compliant": False, "astm_f1858": False, "adjustable_height": True, "cleanable_surface": True},
        "violation": {"rule_id": "bed_entrapment", "citation": "FDA Hospital Bed Entrapment Guidance (2006) / ASTM F1858",
                      "reason": "Legacy rail geometry does not document entrapment-zone conformance."},
    },
    {
        "sku": "TRAP-NC-004", "name": "GlossFinish Porous Lounge Seating", "category": "common_area",
        "subcategory": "Lounge Seating", "vendor": "ComfortLine", "unit": "each", "list_price": 510.0,
        "attributes": {"cleanable_surface": False, "non_porous": False, "wheelchair_accessible": True},
        "violation": {"rule_id": "cleanable_surfaces", "citation": "42 CFR §483.80 / F880",
                      "reason": "Porous, non-cleanable upholstery is unsuitable for infection control in resident areas."},
    },
    {
        "sku": "TRAP-NC-005", "name": "SlickShine Resident Room Vinyl (Non-Slip-Rated)", "category": "flooring",
        "subcategory": "Resilient Sheet Vinyl", "vendor": "FloorSafe", "unit": "sq_ft", "list_price": 4.0,
        "attributes": {"slip_resistant": False, "cleanable_surface": True, "non_porous": True},
        "violation": {"rule_id": "slip_resistant_flooring", "citation": "42 CFR §483.25(d) / F689",
                      "reason": "Flooring is not slip-resistant, increasing avoidable fall risk."},
    },
]

# ---------------------------------------------------------------------------
def gen_catalog():
    products = []
    sku_n = 1000
    for cat in CATEGORIES:
        # ~24 SKUs per category -> ~290 + traps ~= 300
        n = 24
        for _ in range(n):
            sub = random.choice(cat["subcats"])
            vendor = random.choice(cat["vendors"])
            lo, hi = cat["price_range"]
            price = round(random.uniform(lo, hi), 2)
            attrs = dict(cat["compliant_attrs"])
            # add a little realistic variation
            attrs["weight_capacity_lb"] = attrs.get("weight_capacity_lb", random.choice([300, 350, 400, 600]))
            sku_n += 1
            products.append({
                "sku": f"DS-{cat['category'][:3].upper()}-{sku_n}",
                "name": f"{vendor} {sub}",
                "category": cat["category"],
                "subcategory": sub,
                "vendor": vendor,
                "unit": cat["unit"],
                "list_price": price,
                "applicable_rooms": cat["rooms"],
                "attributes": attrs,
                "compliant": True,
            })
    for t in TRAPS:
        products.append({
            "sku": t["sku"], "name": t["name"], "category": t["category"],
            "subcategory": t["subcategory"], "vendor": t["vendor"], "unit": t["unit"],
            "list_price": t["list_price"],
            "applicable_rooms": next(c["rooms"] for c in CATEGORIES if c["category"] == t["category"]),
            "attributes": t["attributes"], "compliant": False,
            "known_violation": t["violation"],
        })
    return products


def gen_contracts(products):
    contracts = [
        {"id": "GPO-PREMIER", "gpo_name": "Premier Inc (representative)", "discount": 0.18},
        {"id": "GPO-VIZIENT", "gpo_name": "Vizient (representative)", "discount": 0.14},
        {"id": "DSSI-DIRECT", "gpo_name": "Direct Supply DSSI (representative)", "discount": 0.22},
    ]
    prices = []
    for p in products:
        # each product priced under 1-2 contracts
        chosen = random.sample(contracts, k=random.choice([1, 2]))
        for c in chosen:
            jitter = random.uniform(-0.03, 0.03)
            disc = max(0.05, c["discount"] + jitter)
            prices.append({
                "sku": p["sku"],
                "contract_id": c["id"],
                "price": round(p["list_price"] * (1 - disc), 2),
            })
    return {"contracts": contracts, "contract_prices": prices}


def gen_rules():
    # attribute-level compliance rules consumed by the MCP validate_item tool.
    return [
        {"rule_id": "call_system_coverage", "category": "nurse_call",
         "predicate": {"covers_bedside": True, "covers_toilet_bath": True},
         "citation": "42 CFR §483.90(g)", "reg_id": "cfr-483.90-g",
         "message": "Resident call system must reach both bedside and toilet/bathing facilities."},
        {"rule_id": "egress_door_clear_width", "category": "casework_door",
         "predicate": {"clear_width_in_min": 41.5}, "applies_when": {"subcategory": "Resident Room Door (Bed-Movement)"},
         "citation": "NFPA 101 (2012) §18.2.3.6", "reg_id": "nfpa101-2012-18.2.3.6-door",
         "message": "Bed-movement egress doors require >= 41.5 in clear width."},
        {"rule_id": "bed_entrapment", "category": "resident_bed",
         "predicate": {"entrapment_compliant": True},
         "citation": "FDA Hospital Bed Entrapment Guidance (2006) / ASTM F1858", "reg_id": "fda-bed-entrapment-2006",
         "message": "Beds/rails must document entrapment-zone conformance (FDA 2006 / ASTM F1858)."},
        {"rule_id": "cleanable_surfaces", "category": "*",
         "predicate": {"cleanable_surface": True},
         "applies_when": {"category_in": ["furniture", "flooring", "mattress", "common_area", "fall_prevention"]},
         "citation": "42 CFR §483.80 / F880", "reg_id": "cms-infection-surfaces-f880",
         "message": "Resident-area surfaces must be cleanable/non-porous for infection control."},
        {"rule_id": "slip_resistant_flooring", "category": "flooring",
         "predicate": {"slip_resistant": True},
         "citation": "42 CFR §483.25(d) / F689", "reg_id": "som-app-pp-f689-accidents",
         "message": "Resident-area flooring must be slip-resistant to mitigate fall risk."},
        {"rule_id": "grab_bar_height", "category": "bathroom_safety",
         "predicate": {"grab_bar_height_in_range": [33, 36]}, "applies_when": {"subcategory": "ADA Grab Bar Set"},
         "citation": "2010 ADA Standards §609", "reg_id": "ada-2010-604-grab-bars",
         "message": "Grab bars at water closets must be mounted 33-36 in above the floor."},
    ]


def main():
    products = gen_catalog()
    contracts = gen_contracts(products)
    rules = gen_rules()
    (OUT / "catalog.json").write_text(json.dumps(products, indent=2), encoding="utf-8")
    (OUT / "contracts.json").write_text(json.dumps(contracts, indent=2), encoding="utf-8")
    (OUT / "compliance_rules.json").write_text(json.dumps(rules, indent=2), encoding="utf-8")
    print(f"Wrote {len(products)} products, {len(contracts['contract_prices'])} contract prices, {len(rules)} rules.")
    print(f"  -> {OUT/'catalog.json'}")


if __name__ == "__main__":
    main()
