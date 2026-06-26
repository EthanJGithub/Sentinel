/**
 * Sentinel MCP tool server (stdio) — exposes the compliance/cost tools over the
 * Model Context Protocol with Zod-typed schemas. This is the literal "code bases
 * legible to agents / drive tooling" requirement, in Anthropic's own standard.
 *
 * Run:  npm run mcp     (or add to an MCP client config as a stdio server)
 */
import { McpServer } from "@modelcontextprotocol/sdk/server/mcp.js";
import { StdioServerTransport } from "@modelcontextprotocol/sdk/server/stdio.js";
import {
  CostCalcInput, RegSearchInput, ValidateItemInput, ValidateLayoutInput,
} from "./schemas.js";
import { ComplianceTools } from "./tools.js";

const tools = new ComplianceTools();
const server = new McpServer({ name: "sentinel-compliance-tools", version: "0.1.0" });

const ok = (data: unknown) => ({ content: [{ type: "text" as const, text: JSON.stringify(data, null, 2) }] });

server.tool(
  "reg_search",
  "Search the CMS Appendix PP / 42 CFR §483.90 / NFPA 101 corpus for regulation relevant to an item or room. Returns grounded citations.",
  RegSearchInput.shape,
  async (args) => ok(tools.regSearch(args)),
);

server.tool(
  "validate_item",
  "Validate a single equipment item against compliance rules + retrieved regulation. Returns PASS/VIOLATION/ABSTAIN with a grounded citation (citation-or-abstain).",
  ValidateItemInput.shape,
  async (args) => ok(tools.validateItem(args)),
);

server.tool(
  "validate_layout",
  "Validate room/building-level requirements: resident-room square footage, exit corridor width, residents per smoke compartment, window, direct exit access.",
  ValidateLayoutInput.shape,
  async (args) => ok(tools.validateLayout(args)),
);

server.tool(
  "cost_calc",
  "Compute cart subtotal vs budget; returns within_budget, over_by, and remaining headroom.",
  CostCalcInput.shape,
  async (args) => ok(tools.costCalc(args)),
);

const transport = new StdioServerTransport();
await server.connect(transport);
console.error("[sentinel-mcp] stdio server ready (reg_search, validate_item, validate_layout, cost_calc)");
