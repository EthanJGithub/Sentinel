# CLAUDE.md — Sentinel (Direct Supply interview demo build)

## What this project is
**Sentinel** — an agentic **Procurement & Compliance Copilot for senior care**. It's a portfolio/interview demo Ethan Jones is building to present in his **Direct Supply AI Engineer** interview (Durham, NC; his first interview from the job search). Read `HANDOFF.md` first, then `BUILD-PLAN.md` (the full spec) and `ARCHITECTURE-DIAGRAMS.md` (8 Mermaid diagrams).

## Who the owner is
Ethan Jones — AI/ML Software Engineer, ~1.5 yrs at Credence, B.S. CS (Georgia Southern), Atlanta GA. Three live portfolio apps on real data: **CredAgent** (5-agent LangGraph loan underwriter), **FraudPulse** (XGBoost+IsolationForest, PR-AUC 0.88), **VisionLog** (browser YOLO26 + LangGraph text-to-SQL). Sentinel is deliberately the **CredAgent pattern re-skinned** (multi-agent + RAG-over-policy + decision + audit) onto Direct Supply's domain.

## The goal (definition of done)
A working, demoable system that:
1. Takes a natural-language procurement request ("equip a 30-bed memory-care wing, $480K, compliant").
2. Runs a LangGraph multi-agent graph (Planner → Sourcing → Compliance → Budget → Audit) with a human-in-the-loop approval.
3. Validates every item against **real CMS / Life-Safety regulation with citations** (citation-or-abstain; a hallucination gate).
4. Ships with the **eval harness + cost/latency monitoring** that proves it can be *operated* in production.
5. Has a live "plant-a-violation-and-watch-it-get-caught" demo moment.

## Hard constraints
- **Use every technology in Direct Supply's stack** (this is the whole point): **Python, C#, TypeScript, PostgreSQL · Anthropic + OpenAI · Docker, Terraform, AWS.** See `BUILD-PLAN.md §3` for where each lives and §7 for the coverage matrix.
- **$0 budget.** Free tiers only: Neon (Postgres+pgvector), Render/Fly/HF Spaces (services), Vercel (console), Langfuse (tracing), Ollama/Groq/Gemini-free (dev/eval models), Terraform→LocalStack or AWS Free Tier, GitHub Actions. Anthropic/OpenAI only for the actual demo run (pennies, inside new-account credits). See `BUILD-PLAN.md §12b`.
- **Real data** (Ethan prefers real over synthetic): CMS State Operations Manual Appendix PP, NFPA 101 refs, CMS Care Compare. Cache downloads to **D:** (C: is tight).
- **Never fabricate compliance citations.** Every compliance claim must be grounded in retrieved regulation text, or abstain.
- **Honest framing** in the demo: it's a prototype on public data + a representative catalog; the edge is the architecture, full-stack execution, and the "operate" story.

## Repo layout to build toward (BUILD-PLAN §8)
```
services/catalog-csharp/   ASP.NET Core + EF Core  (system of record)
services/agent-python/     FastAPI + LangGraph
services/mcp-tools-ts/     MCP tool server (agent-legible tooling)
web/console-ts/            React/Vite operator console
eval/                      golden scenarios + harness
data/                      CMS Appendix PP, NFPA, catalog seed
infra/                     Terraform (ECS/RDS/S3/ECR/CloudWatch or LocalStack)
docker-compose.yml · AGENTS.md · README.md
```

## Build order (BUILD-PLAN §9)
Phase 0 scaffold → 1 agent core → 2 MCP + RAG → 3 operate layer (eval/monitoring) → 4 console + deploy. Each phase keeps the demo runnable. Minimum demoable cut = Phases 0–2 + a hand-run eval report. **Never cut the live violation-catch.**

## Current state
**Planning complete; nothing coded yet.** Start at Phase 0. Confirm Direct Supply's product lines (DSSI / TELS / Attainia) and the interview date/format (onsite vs screen-share) before deep build.
