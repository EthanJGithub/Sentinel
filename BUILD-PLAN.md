# Direct Supply — Interview Demo Plan (IN-DEPTH, full-stack)
**Role:** AI Engineer · Durham, NC (onsite) · REQ-2026-2440 · 2+ yrs · onsite
**Strategy:** Walk in with a *working, polyglot, production-shaped* agentic system that uses **every technology in their stack**, wrapped in the **evaluate / operate / monitor** story the JD explicitly asks for.
**Diagrams:** see `direct-supply-architecture-diagrams.md` — 8 in-depth Mermaid diagrams (container, agent state machine, request sequence, ERD, compliance flow, free deployment, model routing, eval-gated CI).
**Cost:** $0 to build and host — see the free-resource map below.

---

## 0. Verified stack (pulled from the live JD — every design choice below maps to this)

**"What We Work In":**
- Languages/DB: **Python, C#, TypeScript, PostgreSQL**
- AI: **Frontier model ecosystems & agent frameworks (Anthropic, OpenAI)**
- Infra: **Docker, Terraform, AWS**

**Three phrases that shape the design (quote these back in the interview):**
1. *"Design, build, and **operate** systems in customer-facing production"* → eval + monitoring + cost layer.
2. *"Code bases that are **legible to agents** and other developers; drive tooling"* → an **MCP tool server** + typed schemas + `AGENTS.md`.
3. *"Integrating AI into **existing, established products**"* → the AI wraps a **C# system-of-record service**, not a greenfield toy.

Min quals: 2+ yrs SWE/applied AI · full-stack AI dev tools · cloud + frontier platforms. Nice-to-have: **operating AI in prod with attention to evaluation, cost, performance** · forward-deployed/customer-proximity · large-scale Python/C#/TS · **healthcare/regulated data**. You hit all the nice-to-haves through this build.

---

## 1. One-sentence pitch (memorize)
> "Direct Supply sits where senior-care **procurement** meets a **regulated** environment, so I built **Sentinel** — a multi-agent copilot that equips a new care wing end-to-end: it sources equipment against contract pricing *and* validates every item against CMS / Life-Safety rules with citations. It's built on your exact stack — a **C# catalog service**, a **Python LangGraph agent core**, a **TypeScript MCP tool server + React console**, on **Postgres**, using **Anthropic and OpenAI**, containerized with **Docker**, provisioned with **Terraform on AWS** — and it ships with the eval harness and cost monitoring you'd need to actually *operate* it."

That sentence alone signals you read the JD, researched the company, and can architect a real system.

---

## 2. Concept — "Sentinel": Agentic Procurement & Compliance Copilot
**Demo scenario:**
> Facility operator: *"Opening a 30-bed memory-care wing in 60 days. Equip resident rooms, nursing station, and common areas within $480K, compliant with CMS Life-Safety + NC assisted-living rules, using our GPO contract pricing where available."*

Sentinel decomposes it, sources equipment, checks every item against **real regulation with citations**, keeps it in budget, and produces an **auditable plan** for human approval. Fuses Direct Supply's three product lines: **DSSI** (sourcing/contracts), **TELS** (compliance), **Attainia** (capital-equipment planning).

This is the **CredAgent architecture, re-skinned** (multi-agent + RAG-over-policy + decision + audit) — so it's credible *and* fast for you to build, and you can say "I've shipped this exact pattern in production for credit underwriting."

---

## 3. Polyglot service architecture (THE core — every stack element, with *why*)

```
 ┌───────────────────────────────────────────────────────────────────────┐
 │  TypeScript — React/Vite Operator Console                              │
 │  (procurement plan · live agent trace · compliance report ·           │
 │   audit trail · COST/LATENCY monitoring dashboard · HITL approve)      │
 └───────────────┬───────────────────────────────────────────────────────┘
                 │ REST/WebSocket
                 ▼
 ┌───────────────────────────────────────────────────────────────────────┐
 │  Python — Agent Orchestration Service (FastAPI + LangGraph)           │
 │  Planner → Sourcing → Compliance → Budget/Opt → Audit  (+ HITL)       │
 │  Models: Anthropic Claude (Opus reason / Haiku route) + OpenAI        │
 │          (embeddings + structured-extraction cross-check)             │
 └─────┬───────────────────────────────────────┬─────────────────────────┘
       │ MCP (tools)                            │ HTTP (system of record)
       ▼                                        ▼
 ┌──────────────────────────────┐   ┌──────────────────────────────────────┐
 │ TypeScript — MCP Tool Server │   │ C# — Catalog & Contract Service      │
 │ "agent-legible" tool layer:  │   │ (ASP.NET Core + EF Core)             │
 │  reg_search, validate_item,  │   │  catalog_search, get_contract_price, │
 │  validate_layout, cost_calc  │   │  check_stock, place_order            │
 │  (typed schemas, MCP std)    │   │  = the "existing established product" │
 └───────────────┬──────────────┘   └───────────────┬──────────────────────┘
                 │                                   │
                 └───────────────┬───────────────────┘
                                 ▼
        ┌──────────────────────────────────────────────────────┐
        │ PostgreSQL  — catalog · contracts · audit log ·        │
        │  eval results · pgvector store (CMS/NFPA regs)         │
        └──────────────────────────────────────────────────────┘

   Docker (every service) · Terraform → AWS (ECS Fargate ×3, RDS, S3, ECR, CloudWatch)
```

### Why each piece is where it is (this is your architecture-defense in the interview)
- **C# / ASP.NET Core — Catalog & Contract Service.** This is the **enterprise system-of-record** (mirrors DSSI, almost certainly a .NET shop). It owns the catalog, GPO contract pricing, stock, and order placement via EF Core → Postgres. **Putting the AI *in front of* a C# service is the literal "integrate AI into an existing, established product" requirement.** Don't bury C# in a corner — make it the system the agent must work *through*.
- **Python — Agent Orchestration Service.** FastAPI + LangGraph stateful graph. This is where your CredAgent expertise lives. Calls the C# service (HTTP) and the MCP server (tools).
- **TypeScript — two surfaces:**
  - **MCP Tool Server** — exposes compliance/cost tools over **Model Context Protocol** with typed schemas. This *is* the "code bases legible to agents / drive tooling" requirement, in their language, using Anthropic's own standard. High-signal.
  - **React/Vite Operator Console** — the forward-deployed, customer-facing surface (plan, live trace, monitoring).
- **PostgreSQL** — single store: catalog/contracts (written by C#), audit + eval (written by Python), `pgvector` regulation embeddings (RAG).
- **Anthropic + OpenAI** — **both**, deliberately: Claude **Opus** for compliance reasoning, Claude **Haiku** for cheap routing/extraction, **OpenAI** `text-embedding-3` for the RAG index *and* a structured-extraction cross-check (a second model verifying the first = a real reliability technique). Demonstrates frontier-ecosystem fluency + cost-aware routing.
- **Docker** — every service has a Dockerfile; `docker-compose.yml` runs the whole system locally.
- **Terraform** — `infra/` module provisions **all** AWS: ECR repos, 3 ECS Fargate services, RDS Postgres, S3 (regulation corpus + artifacts), IAM, CloudWatch. Real IaC, not click-ops.
- **AWS** — the deploy target. CloudWatch doubles as the monitoring backbone.

---

## 4. The agent graph (Python / LangGraph)
Stateful graph, shared state object (spec → cart → compliance findings → budget ledger → audit), HITL interrupt before "order":
1. **Planner** — decompose request → structured procurement spec (room types, qty, categories, constraints).
2. **Sourcing** — tools (via C# service): `catalog_search`, `get_contract_price`, `check_stock`, `find_substitution`.
3. **Compliance** — tools (via MCP server): `reg_search` (RAG over Appendix PP + NFPA 101), `validate_item`, `validate_layout` → citations + violation flags, **citation-or-abstain**.
4. **Budget/Optimization** — constraint solver tool (greedy/LP); keep within budget, propose trade-offs.
5. **Audit** — immutable decision record → Postgres (why each item / which rule / which contract / cost).
6. **HITL checkpoint** — operator approves/edits/rejects → C# `place_order`.

---

## 5. The "operate" layer — your differentiator (maps to the nice-to-have verbatim)
The JD nice-to-have: *"operating AI systems in production, with attention to **evaluation, cost, and performance** tradeoffs."* Build exactly that:
1. **Eval harness** (Python) — ~15–20 golden procurement scenarios with known outcomes. Metrics:
   - **Compliance recall** — % of planted violations caught (the metric that matters in regulation — your FraudPulse recall instinct).
   - **Citation-grounding rate** — % of compliance claims backed by a real retrieved reg.
   - **Budget adherence** + **plan completeness**.
   - Reproducible report (FraudPulse rigor).
2. **Citation-or-abstain guardrail** — Compliance Agent cannot assert a rule without grounded reg text; a hallucination gate blocks ungrounded claims.
3. **Cost + performance monitoring** — token cost per run, latency per agent node, tool-call success rate, **per-request cost guardrail**, model-routing report (Haiku vs Opus vs OpenAI spend). Surfaced in the React dashboard **and** CloudWatch.
4. **Schema-validated tool I/O** — Pydantic (Python) + Zod (TS MCP) + C# DTOs → typed end-to-end.

> The line that wins the room: *"I don't just build agents — I make them safe and economical to operate. That's the eval harness, the grounding gate, and the cost/latency monitoring — which is the 'operate in production' part of your JD."*

---

## 6. Real data (your style — keep it credible)
- **CMS State Operations Manual, Appendix PP** (LTC surveyor guidance) — real regulatory text → Compliance RAG corpus.
- **NFPA 101 Life-Safety Code** public references → fire/egress/safety rules.
- **CMS Care Compare / Provider datasets** (data.cms.gov) — real facilities + deficiency categories → ground facility profiles + planted-violation scenarios.
- **Catalog** — representative ~300-SKU senior-care equipment set (real taxonomies: beds, mobility, fall-prevention, nurse-call, furnishings) seeded into the **C# service**; synthesized GPO contract pricing.
- Cache downloads to **D:** (C: is tight). Be upfront: "public CMS data + representative catalog; with your real DSSI catalog/contracts this gets far richer."

---

## 7. Stack-coverage matrix (your "I used everything" checklist)

| JD stack item | Where it lives in Sentinel | Depth |
|---|---|---|
| **Python** | Agent orchestration (FastAPI + LangGraph), eval harness | Core |
| **C#** | Catalog & Contract Service (ASP.NET Core + EF Core) = system-of-record | Core service |
| **TypeScript** | MCP tool server **and** React/Vite console | 2 surfaces |
| **PostgreSQL** | catalog, contracts, audit, eval, pgvector RAG | Core |
| **Anthropic** | Claude Opus (compliance reasoning) + Haiku (routing) | Core |
| **OpenAI** | `text-embedding-3` RAG + structured-extraction cross-check | Yes |
| **Docker** | every service + `docker-compose` local | Yes |
| **Terraform** | `infra/` provisions all AWS | Yes |
| **AWS** | ECS Fargate ×3, RDS, S3, ECR, CloudWatch | Yes |
| *"legible to agents"* | MCP server + typed schemas + `AGENTS.md` | Bonus signal |
| *"existing products"* | AI wraps the C# system-of-record | Bonus signal |
| *"eval/cost/perf"* | eval harness + cost/latency dashboard + routing | Bonus signal |
| *healthcare/regulated* | CMS Appendix PP + NFPA RAG + audit trail | Bonus signal |

---

## 8. Repo structure
```
sentinel/
├─ services/
│  ├─ catalog-csharp/        # ASP.NET Core + EF Core  (C#)  → Postgres
│  ├─ agent-python/          # FastAPI + LangGraph      (Python)
│  └─ mcp-tools-ts/          # MCP server               (TypeScript)
├─ web/console-ts/           # React/Vite console       (TypeScript)
├─ eval/                     # golden scenarios + harness + reports (Python)
├─ data/                     # CMS Appendix PP, NFPA refs, catalog seed
├─ infra/                    # Terraform (ECS, RDS, S3, ECR, CloudWatch)
├─ docker-compose.yml
├─ AGENTS.md                 # "legible to agents" — tool + arch docs
└─ README.md
```

---

## 9. Build timeline (phased; each phase keeps the demo runnable)
| Phase | Time | Deliverable (stack touched) |
|---|---|---|
| 0 — Scaffold | 1 day | `docker-compose` up: **C#** catalog API + **Postgres** + seed catalog; **Python** FastAPI hello; **TS** console shell |
| 1 — Agent core | 2 days | **Python/LangGraph** Planner→Sourcing→Compliance→Budget→Audit calling the **C#** service; one scenario end-to-end; **Anthropic** wired |
| 2 — MCP + RAG | 1.5 days | **TS MCP server** (compliance tools) + pgvector RAG over Appendix PP with **OpenAI** embeddings; citation-or-abstain gate |
| 3 — Operate layer | 1.5 days | **eval harness** (compliance recall, grounding rate) + **cost/latency monitoring** + model routing ← the differentiator |
| 4 — Console + deploy | 2 days | **React/TS** console (plan, live trace, monitoring, HITL) + **Terraform** → **AWS** (RDS + ECS services) |

**Minimum demoable cut (if the interview is soon):** Phases 0–2 running on `docker-compose` locally + a hand-run eval report screenshot. That still *truthfully* uses Python + C# + TypeScript + Postgres + Anthropic + OpenAI + Docker. Add Terraform/AWS as the "and here's how it deploys" slide if you can't finish Phase 4. **Never cut the live compliance-violation catch** — that's the moment that wins.

---

## 10. Demo script (3-min and 10-min versions)
1. Type the new-wing request in the **TS console**.
2. Watch the **LangGraph trace** stream live (nodes light up; show which model each used + token cost).
3. Show the plan: itemized cart (from the **C# service**) + per-item **compliance citations** (from the **MCP/RAG** layer) + budget breakdown.
4. **Plant a violation live** (non-egress-compliant bed / over-budget item) → Compliance Agent catches it **with a citation**; hallucination gate blocks an ungrounded claim. *(The wow — rehearse it.)*
5. Show **audit trail** (Postgres), **eval report** (compliance recall, grounding rate, cost/run), **monitoring dashboard** (per-agent latency/cost).
6. Operator approves → **C#** `place_order`. Done.

---

## 11. Interview framing
- Open with §1 pitch → "Want me to run it?"
- **Architecture defense:** be ready to justify *why C# is the system-of-record, why an MCP server, why two model vendors, why Terraform.* (All answered in §3.)
- **Scale whiteboard:** "How does this serve 10,000 facilities?" → multi-tenant Postgres, ECS autoscaling, regulation-corpus versioning, eval-gated deploys.
- **Honesty:** prototype on public CMS data + representative catalog; the edge is the *pattern*, the *full-stack execution*, and the *operate* story.
- **Reuse credibility:** "Same multi-agent + RAG-over-policy + audit architecture I shipped in CredAgent for credit underwriting."
- **Close on their words:** "You asked for someone who can build, ship, *and operate* applied AI on Python/C#/TypeScript across Anthropic and OpenAI, deployed with Terraform on AWS. This is me showing you I already do all of it."

---

## 12. Interview-day checklist
- [ ] Live demo deployed (AWS) **and** a local `docker-compose` backup (don't trust conference wifi).
- [ ] 3-min and 10-min paths rehearsed; planted-violation catch smooth.
- [ ] Architecture diagram (§3) as one slide; stack-coverage matrix (§7) as one slide.
- [ ] Eval report + monitoring dashboard screenshots as fallback.
- [ ] Repo public, clean `README` + `AGENTS.md`; linked from ethanjgithub.github.io.
- [ ] Be ready to live-edit one tool to show the codebase is "legible to agents."

---

## 12b. Build it for $0 — free-resource map
The whole system runs on free tiers. Use Anthropic + OpenAI for the **demo** run (a full run costs pennies, inside new-account credits); a **provider abstraction** falls back to free models for dev/eval so you never burn credits while iterating.

| Stack element | Free resource | Notes |
|---|---|---|
| PostgreSQL + pgvector | **Neon** free | serverless Postgres, pgvector built in (same as VisionLog) |
| C# / Python / MCP services | **Render** / **Fly.io** / **HF Spaces** free | any Docker container; or local `docker-compose` |
| React console | **Vercel** free | (same as FraudPulse / VisionLog) |
| Anthropic Claude | new-account **$5 credit** | a demo run = pennies; Haiku routing keeps it tiny |
| OpenAI | free credit + cheap embeddings | `text-embedding-3-small` ≈ $0.02 / 1M tokens |
| Free model fallback (dev/eval) | **Groq** / **Gemini free** / **Ollama** (local) | provider abstraction preserves paid credits |
| Embeddings (free option) | **local BGE/GTE** (sentence-transformers) | CPU, $0; OpenAI as the "prod" path |
| Observability / tracing | **Langfuse** (self-host or Cloud free) | agent cost / latency / trace |
| Container registry | **ghcr.io** free | public images |
| CI/CD | **GitHub Actions** free | build · eval-gate · deploy |
| IaC | **Terraform** free → **LocalStack** or **AWS Free Tier** | `terraform plan` always free; apply to LocalStack ($0) or 12-mo free-tier RDS/EC2 |
| Repo + portfolio | **GitHub** + ethanjgithub.github.io | $0 |

**Honest interview line:** *"I built it on free tiers — Neon, Render, Vercel, Langfuse — with a provider abstraction so dev and eval run on free models (Groq/Ollama) and only the demo hits Claude/OpenAI. That's the cost-discipline your JD asks for, applied to my own build."* Cache datasets (CMS Appendix PP, NFPA refs, Care Compare) to **D:** (C: is tight).

---

## 13. Lighter alternative (only if the full build isn't feasible)
**"Survey-Readiness Agent"** — single domain (TELS-aligned): ingest a facility's maintenance/inspection logs + CMS deficiency history, RAG over Appendix PP, output a survey-readiness report with prioritized work orders + citations. Still polyglot-able (C# log service + Python agent + TS console) but half the surface area. Use only if time-boxed.
