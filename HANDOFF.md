# HANDOFF — Sentinel (Direct Supply demo)
**Created 2026-06-25. Start a NEW chat in this folder to build it.**

## Why this exists
Direct Supply gave Ethan his **first interview** from the job search: **AI Engineer**, Durham NC, onsite, REQ-2026-2440 (verified live, 15 days old at handoff). This project is the **agentic AI demo Ethan will build and present in that interview**. The job-search/scanning work continues in the *other* chat — this folder is build-only.

## The role (verified from the live JD)
- **Stack ("What We Work In"):** Python, C#, TypeScript, PostgreSQL · frontier model ecosystems & agent frameworks (Anthropic, OpenAI) · Docker, Terraform, AWS.
- **Mandate:** "design, ship, and **operate** AI systems in customer-facing production"; own the full lifecycle (discovery → experimentation → evaluation → deployment → monitoring).
- **Telling phrases:** "code bases **legible to agents** and other developers; drive tooling"; "integrating AI into **existing, established products**"; nice-to-have: "operating AI in prod with attention to **evaluation, cost, and performance** tradeoffs"; "**healthcare/regulated** data."
- **Min quals:** 2+ yrs SWE or applied AI (Ethan ~1.5 yr + 3 deployed apps — position outcomes over years).
- Company: 100% employee-owned; senior living & healthcare; product lines **DSSI** (procurement), **TELS** (facilities/compliance), **Attainia** (capital-equipment planning).

## The decision (what we're building)
**Sentinel** — a multi-agent Procurement & Compliance Copilot. A facility manager asks to equip a new care wing within budget and compliant with CMS/Life-Safety; a LangGraph graph (Planner → Sourcing → Compliance → Budget → Audit + human approval) sources equipment via a **C# system-of-record service**, validates each item against **real CMS Appendix PP / NFPA 101** with citations (citation-or-abstain), keeps it in budget, and emits an auditable plan — wrapped in an eval harness + cost/latency monitoring.

It fuses DSSI + TELS + Attainia, and it's the **CredAgent architecture re-skinned**, so Ethan can say "I've shipped this exact pattern in production for credit underwriting."

## What's already done
- ✅ **BUILD-PLAN.md** — full in-depth spec: polyglot architecture (§3), agent graph (§4), operate/eval layer (§5), real data (§6), stack-coverage matrix (§7), repo layout (§8), phased timeline (§9), demo script (§10), interview framing (§11), **$0 free-resource map (§12b)**.
- ✅ **ARCHITECTURE-DIAGRAMS.md** — 8 Mermaid diagrams (container, agent state machine, request sequence with the live violation-catch, ERD, citation-or-abstain flow, free deployment topology, model routing/cost, eval-gated CI).
- ❌ **No code yet.**

## Next steps (in the new chat)
1. Confirm interview date/format → decide full build vs. "minimum demoable cut" (BUILD-PLAN §9).
2. **Phase 0:** `docker-compose` up — C# catalog API + Neon Postgres + seed a ~300-SKU catalog; Python FastAPI skeleton; TS console shell. Download CMS Appendix PP + NFPA refs to **D:**.
3. **Phase 1:** LangGraph graph end-to-end on one scenario (Anthropic wired).
4. **Phase 2:** TS MCP server + pgvector RAG (OpenAI or local BGE embeddings) + citation-or-abstain gate.
5. **Phase 3:** eval harness (compliance recall, grounding rate) + cost/latency monitoring (Langfuse) ← the differentiator.
6. **Phase 4:** React console + Terraform deploy.

## The interview-winning narrative (don't lose this)
> "Direct Supply sits where senior-care procurement meets a regulated environment — so I built Sentinel on your exact stack (C# + Python + TypeScript on Postgres, Anthropic + OpenAI, Docker + Terraform + AWS), with the eval harness and cost monitoring you'd need to actually *operate* it. Same multi-agent + RAG-over-policy + audit architecture I shipped in CredAgent for credit underwriting."

The demo's wow moment: **plant a non-compliant item live and watch the Compliance Agent catch it with a citation while the hallucination gate blocks an ungrounded claim.** Never cut that.

## Constraints to carry over
$0 (free tiers), real data (caches on D:), use every stack element, never fabricate citations, honest framing. Full detail in CLAUDE.md + BUILD-PLAN.md.
