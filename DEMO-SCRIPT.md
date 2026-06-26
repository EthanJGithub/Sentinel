# Sentinel — Demo Runbook (interview)

Two paths rehearsed: a **3-minute** version and a **10-minute** version. Never cut the
live violation-catch — that's the moment that wins the room.

## Before you walk in
- [ ] `docker compose up --build` works on your laptop (the offline backup — don't trust wifi).
- [ ] `.env` has `ANTHROPIC_API_KEY` + `OPENAI_API_KEY` and `PROVIDER_MODE=demo` for the real run.
- [ ] Console open at `http://localhost:5173`; eval report open at `eval/reports/latest.md`.
- [ ] One-slide architecture diagram (`ARCHITECTURE-DIAGRAMS.md §1`) + stack-coverage matrix (`README` table).
- [ ] Repo public, linked from your portfolio.

## Opening line (memorize)
> "Direct Supply sits where senior-care **procurement** meets a **regulated** environment, so
> I built Sentinel on your exact stack — a C# catalog service, a Python LangGraph agent core,
> a TypeScript MCP tool server and React console, on Postgres, using Anthropic and OpenAI,
> containerized with Docker and provisioned with Terraform on AWS — and it ships with the eval
> harness and cost monitoring you'd need to actually *operate* it. Want me to run it?"

## 3-minute path
1. **Type the request** (or pick the "30-bed memory-care wing" scenario). Hit *Generate*.
2. **Narrate the trace** as nodes light up: Planner (Haiku) → Sourcing (C# catalog) →
   Compliance (Opus + MCP reg_search) → Budget → Audit. Point at the per-node cost/latency
   in the right rail: *"every node is metered — that's the operate story."*
3. **The catch.** Set *Plant violation → TRAP-NC-001* and re-run. The Compliance Agent flags
   the bedside-only call station **VIOLATION** with a citation to **42 CFR §483.90(g)**, and the
   plan holds it back from the order. *"It cites the regulation, and where it can't ground a
   claim it abstains — it never makes up a citation."*
4. **Approve.** Violating line is excluded; order places through the C# service.

## 10-minute path (adds)
- **Architecture defense** — why C# is the system-of-record (integrate AI into an existing
  product), why an MCP server (legible to agents, Anthropic's own standard), why two model
  vendors (Opus reasoning + OpenAI grounding cross-check = a real reliability technique),
  why Terraform (real IaC, not click-ops).
- **The hallucination gate** — show an ABSTAIN finding (`gate_blocked`): the model proposed a
  verdict the retrieved reg didn't support, so the gate downgraded it to human review.
- **The eval harness** — `python eval/harness.py`. Walk the table: compliance recall 100%,
  citation accuracy 100%, **zero false-violations**, grounding ≥ 95%, budget adherence 100%.
  *"This is the deploy gate — a drop in recall blocks the rollout in CI."*
- **Cost discipline** — Haiku-vs-Opus-vs-OpenAI routing report + per-request cost ceiling.
  *"Dev and eval run on free/heuristic models; only the demo hits Claude/OpenAI."*
- **Scale whiteboard** — 10k facilities → multi-tenant Postgres, ECS autoscaling, S3
  regulation-corpus versioning, eval-gated deploys.

## If something breaks
- WS down → the console auto-falls back to REST, then to an embedded sample (flagged "offline
  sample"). The demo still tells the full story.
- Models down / no keys → `PROVIDER_MODE=dev` runs the whole thing on the heuristic path; the
  violation is still caught (rules are deterministic) and the eval still passes.

## Honesty framing (say it plainly)
> "It's a prototype on public CMS data plus a representative catalog. The edge is the
> architecture, the full-stack execution, and the operate layer. Point it at your real DSSI
> catalog and the licensed NFPA text and it gets far richer — same pattern I shipped in
> production for credit underwriting."

## Lines that land
- *"I don't just build agents — I make them safe and economical to operate."*
- *"Citation-or-abstain: in a regulated domain, 'I don't know, here's why' beats a confident guess."*
- *"You asked for build, ship, **and operate** across Python/C#/TypeScript, Anthropic and OpenAI,
  on Terraform + AWS. This is me showing you I already do all of it."*
