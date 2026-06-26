# Kickoff prompt for the Sentinel build chat
**Paste everything below the line into a new Claude Code chat opened in this folder (`sentinel-direct-supply/`).** `CLAUDE.md`, `HANDOFF.md`, `BUILD-PLAN.md`, and `ARCHITECTURE-DIAGRAMS.md` are already here for reference.

---

You are helping me, **Ethan Jones**, build a portfolio/interview demo called **Sentinel** to present in my upcoming **Direct Supply — AI Engineer** interview (Durham, NC). This is my first interview from my job search, so the demo needs to be excellent. Read `CLAUDE.md`, `HANDOFF.md`, `BUILD-PLAN.md`, and `ARCHITECTURE-DIAGRAMS.md` in this folder first — they contain the full spec, 8 Mermaid diagrams, and the $0 free-resource plan. Then start building.

## Who I am
AI/ML Software Engineer, ~1.5 yrs at Credence, B.S. Computer Science (Georgia Southern), based in Atlanta GA. I have three live portfolio apps on real data: **CredAgent** (5-agent LangGraph loan underwriter, SHAP, fair-lending), **FraudPulse** (XGBoost + IsolationForest, PR-AUC 0.88), **VisionLog** (browser YOLO26 + LangGraph text-to-SQL). Sentinel is deliberately the CredAgent architecture re-skinned onto Direct Supply's domain.

## What we're building
**Sentinel** — an agentic **Procurement & Compliance Copilot for senior care**. A facility manager asks to equip a new care wing within budget and compliant with CMS/Life-Safety rules; a LangGraph multi-agent graph (Planner → Sourcing → Compliance → Budget → Audit, with human-in-the-loop approval) sources equipment via a C# system-of-record service, validates each item against real CMS regulation **with citations** (citation-or-abstain + a hallucination gate), keeps it in budget, and emits an auditable plan — wrapped in an eval harness + cost/latency monitoring. Full spec in `BUILD-PLAN.md`.

## Hard constraints (do not drift from these)
- **Use every technology in Direct Supply's stack:** Python, C#, TypeScript, PostgreSQL · Anthropic + OpenAI · Docker, Terraform, AWS. (Where each lives: `BUILD-PLAN.md §3` + coverage matrix §7.)
- **$0 budget — free tiers only:** Neon (Postgres+pgvector), Render/Fly/HF Spaces (services), Vercel (console), Langfuse (tracing), Ollama/Groq/Gemini-free (dev/eval models), Terraform→LocalStack or AWS Free Tier, GitHub Actions. Anthropic/OpenAI only for the actual demo run. (`BUILD-PLAN.md §12b`.)
- **Real data** (I prefer real over synthetic): CMS State Operations Manual Appendix PP, NFPA 101 refs, CMS Care Compare. **Cache all downloads to the D: drive** (C: is tight).
- **Never fabricate compliance citations** — ground every claim in retrieved regulation text or abstain.
- Honest framing: it's a prototype on public data + a representative catalog.

## Start here
1. Confirm my interview date/format with me, then decide full build vs. the "minimum demoable cut" (`BUILD-PLAN.md §9`).
2. Begin **Phase 0**: scaffold `docker-compose` with the C# catalog service + Neon Postgres + a seed catalog, a Python FastAPI skeleton, and the TS console shell; download CMS Appendix PP + NFPA refs to D:.

---
## ORIGINAL JOB POSTING (verbatim — Direct Supply, REQ-2026-2440)

**AI Engineer** · Durham, NC · Full time · Posted 15 days ago · Req ID REQ-2026-2440
URL: https://directsupply.wd501.myworkdayjobs.com/direct-supply-careers/job/Durham-NC/AI-Engineer_REQ-2026-2440

**About the Role**
Direct Supply is building AI systems that change how care is delivered to millions of seniors and support the people who care for them. We're hiring engineers to design, ship, and operate those systems in production.
This role spans the full product lifecycle: discovery, experimentation, application delivery, and deployment. You'll work directly with customers and product teams, own technical calls, and see your product used at scale.
We expect technical rigor, architecture discipline, strong product judgment, and a track record of shipping. In return, you get autonomy and real customer impact.

**What You'll Do**
- Design, build, and operate systems in customer-facing production environments
- Translate ambiguous business and customer problems into prototypes & technical specs
- Track AI capabilities and apply them where they create clear leverage
- Own the full application lifecycle: product discovery, experimentation, evaluation, deployment, and monitoring
- Own system design, tradeoffs, and long-term scaling and maintainability
- Build code bases that are legible to agents and other developers; drive the organization forward on tooling
- Partner with product managers to enhance their product vision, including with AI-native solutions

**What We're Looking For**
- Strong applied AI and software engineering fundamentals
- Builders who can span tech, product, and design thinking with high autonomy
- Bias for shipping, iterating, and following customer feedback over polish
- High ownership & agency — measured by outcomes, not deliverables
- Curiosity to improve systems, products, and your own craft

**What We Work In** (you don't need every one of these, but this is the stack you'll be productive in)
- Python, C#, TypeScript, PostgreSQL
- Frontier model ecosystems & agent frameworks (e.g., Anthropic, OpenAI)
- Docker, Terraform, and AWS

**Minimum Qualifications**
- 2+ years in software engineering or applied AI
- Experience working with AI development tools in full-stack applications
- Experience designing AI-based solutions to real workflows
- Working knowledge of cloud and frontier AI platforms

**Nice to Have**
- Degree in Computer Science, Engineering, Data Science, or a related field
- Experience operating AI systems in production, with attention to evaluation, cost, and performance tradeoffs
- Background in high-ambiguity environments with proximity to customers (e.g., early-stage startups, forward-deployed engineering, internal product teams)
- Experience in large-scale Python, C#, and TypeScript codebases
- Experience integrating AI solutions into existing, established products
- Experience working with healthcare, regulated, or sensitive data

**About Direct Supply**
100% employee-owned; for 35+ years has delivered solution-driven platforms, products, and services for Senior Living and Healthcare. Product lines relevant to the demo: **DSSI** (procurement/spend network), **TELS** (facilities + regulatory compliance), **Attainia** (capital-equipment planning). Job performed on-site in Durham, NC.
