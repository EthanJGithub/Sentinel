# Sentinel — Architecture Diagrams (Direct Supply demo)
Companion to `direct-supply-demo-plan.md`. Eight in-depth Mermaid diagrams. All render on GitHub.

---

## 1. System container diagram (polyglot stack + free hosts)
Every JD technology, and where it runs for free.

```mermaid
flowchart LR
  user(["Facility Operator"])

  subgraph FE["Frontend — TypeScript (Vercel, free)"]
    console["React / Vite Operator Console<br/>plan · live trace · monitoring · HITL approve"]
  end

  subgraph PY["Orchestration — Python (Render free)"]
    agent["FastAPI + LangGraph<br/>Planner → Sourcing → Compliance → Budget → Audit"]
  end

  subgraph TS["Agent-legible tooling — TypeScript (Render free)"]
    mcp["MCP Tool Server<br/>reg_search · validate_item · validate_layout · cost_calc"]
  end

  subgraph CS["System of record — C# (Render free, Docker)"]
    catalog["ASP.NET Core + EF Core<br/>catalog · contracts · stock · place_order"]
  end

  subgraph AI["Frontier models"]
    anth["Anthropic Claude<br/>Opus reason / Haiku route"]
    oai["OpenAI<br/>embeddings + cross-check"]
  end

  db[("PostgreSQL + pgvector — Neon free<br/>catalog · contracts · audit · eval · reg_chunks")]
  lf["Langfuse — Cloud free<br/>trace · token cost · latency"]

  user --> console
  console -->|"REST / WebSocket"| agent
  agent -->|"MCP"| mcp
  agent -->|"HTTP"| catalog
  agent --> anth
  agent --> oai
  mcp --> db
  catalog --> db
  agent --> db
  agent -.->|"telemetry"| lf
```

---

## 2. Agent orchestration — LangGraph state machine
Stateful graph with re-source loops and a human-in-the-loop interrupt.

```mermaid
stateDiagram-v2
  [*] --> Planner
  Planner --> Sourcing: structured procurement spec
  Sourcing --> Compliance: candidate cart
  Compliance --> Sourcing: violations → re-source
  Compliance --> Budget: validated + citations
  Budget --> Sourcing: over budget → swap items
  Budget --> Audit: in-budget plan
  Audit --> HITL: immutable decision record
  HITL --> PlaceOrder: operator approves
  HITL --> Planner: operator edits / rejects
  PlaceOrder --> [*]

  note right of Compliance
    citation-or-abstain gate:
    no grounded reg text → abstain + flag for human
  end note
  note right of Budget
    constraint solver tool
    (greedy / LP) keeps cart ≤ budget
  end note
```

---

## 3. End-to-end request sequence (incl. live violation catch)
The exact flow you narrate in the demo.

```mermaid
sequenceDiagram
  actor Op as Operator
  participant UI as Console (TS)
  participant AG as Agent (Python/LangGraph)
  participant CS as Catalog Svc (C#)
  participant MCP as MCP Tools (TS)
  participant DB as Postgres + pgvector
  participant LLM as Claude / OpenAI
  participant LF as Langfuse

  Op->>UI: "Equip 30-bed wing, $480K, compliant"
  UI->>AG: POST /plan
  AG->>LLM: Planner decompose (Haiku)
  LLM-->>AG: procurement spec
  AG->>CS: catalog_search + get_contract_price
  CS->>DB: query catalog + contracts
  DB-->>CS: SKUs + GPO pricing
  CS-->>AG: candidate cart
  AG->>MCP: validate_item + reg_search
  MCP->>DB: vector search (Appendix PP, NFPA 101)
  DB-->>MCP: reg chunks
  MCP->>LLM: compliance reasoning (Opus)
  LLM-->>MCP: findings + citations
  MCP-->>AG: validated + violation flags
  alt violation found (planted in demo)
    AG->>CS: find_substitution
    CS-->>AG: compliant alternative
  end
  AG->>DB: write audit record
  AG-->>UI: stream plan + citations + running cost
  AG-->>LF: trace + token cost + per-node latency
  Op->>UI: approve
  UI->>AG: POST /approve
  AG->>CS: place_order
  CS-->>AG: order confirmation
```

---

## 4. Data model (PostgreSQL ERD)
One Postgres instance; C# writes catalog/contracts, Python writes audit/eval, pgvector holds regs.

```mermaid
erDiagram
  FACILITY ||--o{ PROCUREMENT_PLAN : requests
  PROCUREMENT_PLAN ||--|{ PLAN_LINE : contains
  PRODUCT ||--o{ PLAN_LINE : "selected as"
  PRODUCT ||--o{ CONTRACT_PRICE : "priced by"
  CONTRACT ||--o{ CONTRACT_PRICE : defines
  PLAN_LINE ||--o{ COMPLIANCE_FINDING : "validated by"
  REG_CHUNK ||--o{ COMPLIANCE_FINDING : "cited in"
  PROCUREMENT_PLAN ||--|{ AUDIT_RECORD : logs
  EVAL_SCENARIO ||--o{ EVAL_RESULT : produces

  FACILITY {
    uuid id PK
    string name
    string state
    string care_type
  }
  PRODUCT {
    uuid id PK
    string sku
    string category
    numeric list_price
  }
  CONTRACT {
    uuid id PK
    string gpo_name
  }
  CONTRACT_PRICE {
    uuid id PK
    uuid product_id FK
    uuid contract_id FK
    numeric price
  }
  PROCUREMENT_PLAN {
    uuid id PK
    uuid facility_id FK
    numeric budget
    string status
  }
  PLAN_LINE {
    uuid id PK
    uuid plan_id FK
    uuid product_id FK
    int qty
    numeric line_cost
  }
  REG_CHUNK {
    uuid id PK
    string source
    string citation
    text content
    vector embedding
  }
  COMPLIANCE_FINDING {
    uuid id PK
    uuid plan_line_id FK
    uuid reg_chunk_id FK
    string verdict
    text rationale
  }
  AUDIT_RECORD {
    uuid id PK
    uuid plan_id FK
    string agent
    jsonb decision
    timestamptz ts
  }
  EVAL_SCENARIO {
    uuid id PK
    string name
    jsonb expected
  }
  EVAL_RESULT {
    uuid id PK
    uuid scenario_id FK
    numeric compliance_recall
    numeric grounding_rate
    numeric cost_usd
  }
```

---

## 5. Compliance: citation-or-abstain (the trust mechanism)
Why the agent can be trusted in a regulated domain.

```mermaid
flowchart TD
  start(["Item to validate"]) --> embed["Embed item + room context"]
  embed --> search["pgvector search<br/>Appendix PP + NFPA 101"]
  search --> hit{"Relevant reg<br/>retrieved?"}
  hit -->|no| abstain["ABSTAIN<br/>flag for human review"]
  hit -->|yes| reason["Claude Opus:<br/>does item satisfy the reg?"]
  reason --> grounded{"Claim quotes<br/>retrieved text?"}
  grounded -->|no| gate["HALLUCINATION GATE<br/>reject ungrounded claim"]
  gate --> abstain
  grounded -->|yes| verdict{"Compliant?"}
  verdict -->|yes| pass["PASS + citation"]
  verdict -->|no| fail["VIOLATION + citation<br/>→ re-source loop"]
```

---

## 6. Free deployment topology ($0 end-to-end)
Local dev and a live demo, both at no cost.

```mermaid
flowchart TB
  subgraph dev["Local dev — $0"]
    dc["docker-compose:<br/>C# + Python + MCP + Postgres + Ollama"]
  end

  subgraph live["Live demo — free tiers"]
    vercel["Vercel<br/>React console"]
    render["Render / Fly.io / HF Spaces<br/>C# · Python · MCP (Docker)"]
    neon["Neon<br/>Postgres + pgvector"]
    lf["Langfuse Cloud free<br/>tracing"]
  end

  subgraph iac["IaC — $0"]
    tf["Terraform"]
    target["LocalStack (free)<br/>or AWS Free Tier (12-mo)"]
  end

  gha["GitHub Actions (free)<br/>build · eval-gate · deploy"]
  ghcr["ghcr.io (free)<br/>container registry"]

  gha --> ghcr
  ghcr --> render
  gha --> vercel
  vercel --> render
  render --> neon
  render -.-> lf
  gha --> tf
  tf --> target
```

---

## 7. Model routing & cost control (Anthropic + OpenAI + free fallback)
Provider-agnostic, cost-aware — maps directly to the JD's "cost/performance tradeoffs."

```mermaid
flowchart LR
  task(["Agent task"]) --> router{"Task type?"}
  router -->|"routing / extraction"| haiku["Claude Haiku — cheap"]
  router -->|"compliance reasoning"| opus["Claude Opus — high quality"]
  router -->|"embeddings"| emb["OpenAI text-embedding-3<br/>or local BGE (free)"]
  router -->|"cross-check"| oai["OpenAI — structured verify"]

  haiku --> meter["Cost meter<br/>per-request budget guard"]
  opus --> meter
  emb --> meter
  oai --> meter
  meter --> lf["Langfuse: cost · latency · trace"]

  subgraph freedev["DEV / EVAL mode — $0"]
    groq["Groq free"]
    gemini["Gemini free tier"]
    ollama["Ollama (local)"]
  end
  router -.->|"PROVIDER=dev"| freedev
```

---

## 8. Eval-gated CI/CD (the "operate" proof)
Regressions in compliance recall block the deploy.

```mermaid
flowchart LR
  golden["~20 golden scenarios<br/>with planted violations"] --> harness["Eval harness (Python)"]
  harness --> m1["compliance recall"]
  harness --> m2["citation-grounding rate"]
  harness --> m3["budget adherence"]
  harness --> m4["cost / latency"]
  m1 --> gate{"Thresholds met?"}
  m2 --> gate
  m3 --> gate
  m4 --> gate
  gate -->|yes| deploy["GitHub Actions →<br/>deploy Render + Vercel"]
  gate -->|no| block["Block merge<br/>regression caught"]
```
```
```
