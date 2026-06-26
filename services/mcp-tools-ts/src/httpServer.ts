/**
 * HTTP wrapper around the same tools — lets the Python agent (MCP_URL) and the
 * React console call the agent-legible tools over REST. Same Zod validation as the
 * MCP stdio surface, so the contract is identical in both transports.
 */
import cors from "cors";
import express from "express";
import {
  CostCalcInput, RegSearchInput, ValidateItemInput, ValidateLayoutInput,
} from "./schemas.js";
import { ComplianceTools } from "./tools.js";

const tools = new ComplianceTools();
const app = express();
app.use(cors());
app.use(express.json());

const PORT = Number(process.env.PORT ?? 7100);

app.get("/health", (_req, res) =>
  res.json({ status: "ok", service: "mcp-tools-ts", tools: ["reg_search", "validate_item", "validate_layout", "cost_calc"] }));

// generic, schema-validated dispatch
const handlers: Record<string, { schema: any; run: (a: any) => unknown }> = {
  reg_search: { schema: RegSearchInput, run: (a) => tools.regSearch(a) },
  validate_item: { schema: ValidateItemInput, run: (a) => tools.validateItem(a) },
  validate_layout: { schema: ValidateLayoutInput, run: (a) => tools.validateLayout(a) },
  cost_calc: { schema: CostCalcInput, run: (a) => tools.costCalc(a) },
};

app.post("/tools/:name", (req, res) => {
  const h = handlers[req.params.name];
  if (!h) return res.status(404).json({ error: `unknown tool ${req.params.name}` });
  const parsed = h.schema.safeParse(req.body);
  if (!parsed.success) return res.status(400).json({ error: "invalid input", issues: parsed.error.issues });
  try {
    return res.json(h.run(parsed.data));
  } catch (e: any) {
    return res.status(500).json({ error: String(e?.message ?? e) });
  }
});

app.get("/tools", (_req, res) => res.json({ tools: Object.keys(handlers) }));

app.listen(PORT, () => console.log(`[sentinel-mcp] HTTP tool server on :${PORT}`));
