import { z } from "zod";

// Zod schemas = typed tool I/O end-to-end. These mirror the Python Pydantic models
// and the C# DTOs, so a request is validated the same way in all three languages.

export const RegSearchInput = z.object({
  query: z.string().describe("Free-text description of the item/room to find regulation for"),
  categories: z.array(z.string()).optional().describe("Equipment/room categories to boost"),
  k: z.number().int().min(1).max(10).default(4),
});

export const CitationSchema = z.object({
  reg_id: z.string(),
  source: z.string(),
  citation: z.string(),
  title: z.string(),
  quote: z.string(),
  score: z.number(),
});

export const ValidateItemInput = z.object({
  name: z.string(),
  category: z.string(),
  subcategory: z.string().default(""),
  room_type: z.string().default("resident_room"),
  attributes: z.record(z.any()).default({}),
});

export const ValidateItemOutput = z.object({
  verdict: z.enum(["PASS", "VIOLATION", "ABSTAIN"]),
  rule_id: z.string().nullable(),
  citation: CitationSchema.nullable(),
  rationale: z.string(),
  grounded: z.boolean(),
});

export const ValidateLayoutInput = z.object({
  room_type: z.string().default("resident_room"),
  occupancy: z.number().int().min(1).default(1).describe("Residents per room (1=single)"),
  area_sqft: z.number().optional().describe("Floor area of the room in sq ft"),
  corridor_clear_width_in: z.number().optional(),
  beds_per_smoke_compartment: z.number().optional(),
  has_window: z.boolean().optional(),
  direct_exit_access: z.boolean().optional(),
});

export const LayoutFindingSchema = z.object({
  check: z.string(),
  pass: z.boolean(),
  citation: z.string(),
  reg_id: z.string(),
  detail: z.string(),
});

export const CostCalcInput = z.object({
  lines: z.array(z.object({ unit_price: z.number(), qty: z.number().int() })),
  budget: z.number(),
});

export type TRegSearchInput = z.infer<typeof RegSearchInput>;
export type TValidateItemInput = z.infer<typeof ValidateItemInput>;
export type TValidateLayoutInput = z.infer<typeof ValidateLayoutInput>;
export type TCostCalcInput = z.infer<typeof CostCalcInput>;
