# CineYield — Judge Technical Proof

Concise, verifiable evidence that CineYield's core claims are real, not decorative.
Every item below is checkable by a judge against the live deployment. No credentials
are included in this document.

- **Frontend**: https://cineyield-web-pg7lg7ldma-uc.a.run.app
- **Backend**: https://cineyield-api-pg7lg7ldma-uc.a.run.app
- **API docs (OpenAPI)**: https://cineyield-api-pg7lg7ldma-uc.a.run.app/docs

Last verified: **2026-08-23** (see "Live verification snapshot" below).

---

## 1. One command a judge can run

The contest gate exercises Gemini, ClickHouse, and mcp-clickhouse **through the app's
own integrations** (never a direct side-channel query), and fails non-zero with a
specific reason if any is faked or unreachable:

```bash
bash scripts/smoke-contest.sh https://cineyield-api-pg7lg7ldma-uc.a.run.app
```

Latest result against production: **12 passed / 0 failed / 0 warnings** — including a
live mcp-clickhouse query (`total_scanned=27`) and a real Gemini narrative call with
**no template fallback permitted** (contest mode), and a confirmed new
`cineyield.agent_events` row written during the run.

---

## 2. Google ADK — real runtime use

- Orchestrator is a genuine `google.adk.agents.LlmAgent` driven by
  `google.adk.runners.Runner(auto_create_session=True)`.
  Source: [`apps/agent-api/cineyield/agents/pipeline.py`](../apps/agent-api/cineyield/agents/pipeline.py) (`_build_adk_agent`, `run_pipeline`).
- Gemini (the model) selects and sequences five tools — `analyze_scene`,
  `discover_campaigns`, `check_rights`, `check_creative`, `compose_proposal` — each of
  which calls a canonical Python agent that does the real work.
- Every pipeline job response carries `adk_used: true` and
  `pipeline_version: adk_llmagent_v1`. `adk_used` is set **only after** the ADK runner
  actually completes; it is never hard-coded.
- **Contest mode has no fallback**: if the ADK runner raises, the pipeline re-raises
  (`ADK pipeline failed in contest mode — no fallback permitted`). The direct-execution
  fallback exists only for local development and is unreachable when
  `CINEYIELD_MODE=contest`.

Verify:
```bash
# adk_used:true + pipeline_version present in a completed job's scene_analysis
curl -s https://cineyield-api-pg7lg7ldma-uc.a.run.app/api/v1/ingest/status/<job_id>
```

## 3. Gemini (Vertex AI) — real runtime use

- Model: **gemini-2.5-flash** via Vertex AI (`GOOGLE_GENAI_USE_VERTEXAI=1`,
  Application Default Credentials — no API key baked into the image).
- Used in two materially different places:
  - **SceneAgent** — multimodal video understanding (`google.genai` `generate_content`
    with the uploaded clip). Source: [`scene_agent.py`](../apps/agent-api/cineyield/agents/scene_agent.py).
  - **CreativeGuardian** and **DealAgent narrative** — semantic/creative reasoning.
    Source: [`creative_guardian.py`](../apps/agent-api/cineyield/agents/creative_guardian.py),
    [`deal_agent.py`](../apps/agent-api/cineyield/agents/deal_agent.py).
- In contest mode a Gemini failure re-raises rather than substituting canned text
  (CreativeGuardian lines re-raise; the contest gate asserts a real Gemini brand brief
  of non-trivial length).

## 4. ClickHouse Cloud — real, and necessary

- Live cluster on ClickHouse Cloud (SharedMergeTree), schema in
  [`infra/clickhouse/`](../infra/clickhouse/).
- ClickHouse is **load-bearing**, not decorative — it stores and serves:
  - `brand_campaigns` (27 rows) — the inventory the Market Agent scores against.
  - `scenes`, `opportunities` — persisted scene intelligence.
  - `proposals` (incl. `workflow_state`) — the human-approval state machine.
  - `agent_events` — the full agent audit trail with per-agent latency.
  - `revenue_events` — the numbers the analytics screen aggregates.
- Analytics endpoint reads straight from ClickHouse aggregates, no fixtures.

Verify:
```bash
curl -s https://cineyield-api-pg7lg7ldma-uc.a.run.app/api/v1/analytics/summary
curl -s "https://cineyield-api-pg7lg7ldma-uc.a.run.app/api/v1/agents/events?limit=6"
```

## 5. Official `mcp-clickhouse` — real, at runtime, from Cloud Run

- The Market Agent's **only** path to campaign inventory is the official
  `mcp-clickhouse` MCP server, spawned as a subprocess over **stdio** and invoked via
  the MCP `ClientSession` (`call_tool("run_query", ...)`).
  Source: [`mcp_market.py`](../apps/agent-api/cineyield/agents/mcp_market.py),
  [`market_agent.py`](../apps/agent-api/cineyield/agents/market_agent.py).
- There is **no direct-query fallback** on the judged path. `POST .../propose`
  deliberately returns an honest **502** if mcp-clickhouse fails, rather than silently
  querying ClickHouse another way — the code comment states this is to keep the partner
  integration falsifiable. Source: [`opportunities.py`](../apps/agent-api/cineyield/routers/v1/opportunities.py).
- The contest gate proves this end-to-end: the matches endpoint reports
  `mcp_latency_ms` and `total_scanned=27`, measured from Cloud Run.

## 6. Deterministic scoring separated from LLM reasoning

- Campaign ranking is **pure Python** (`agents/scoring.py`) — weighted composite over
  category fit, context fit, visibility, brand safety, territory, and budget, with
  documented hard-block rules. No LLM influences the ranking numbers.
- Rights clearance (`agents/rights_agent.py`) is fully deterministic and reproducible —
  by design, so a legal/rights decision is auditable, not generated.
- Gemini is used only where semantic judgement is appropriate (scene understanding,
  creative adjacency, narrative prose) — never for objective constraints.

## 7. Human-in-the-loop approval + auditability

- A proposal is created in `PRODUCER_REVIEW`. Approval is a real ClickHouse
  `ALTER TABLE ... UPDATE workflow_state` mutation via `POST .../approve`
  (idempotent; double-approval cannot double-count revenue).
  Source: [`routers/v1/deals.py`](../apps/agent-api/cineyield/routers/v1/deals.py).
- Approval **persists across a full page reload** — it is server/database state, not
  front-end state.
- Every agent writes an `agent_events` row (agent name, tool name, latency, summary),
  giving a complete execution trace queryable at `/api/v1/agents/events`.

## 8. Tests

- Backend: **174 passed** (`cd apps/agent-api && pytest`).
- Frontend: ESLint clean, `tsc --noEmit` clean, `next build` clean.
- Production browser E2E (Playwright against the deployed URLs): the canonical judged
  flow — library → real upload → ADK pipeline → scene → matches → deal → approve →
  analytics.
- CI (`.github/workflows/ci.yml`) runs lint/type/test with **no** cloud credentials —
  it intentionally cannot verify the live integrations; the contest gate above is what
  does that.

---

## Live verification snapshot (2026-08-23)

| Check | Result |
|-------|--------|
| Backend `/health` | `ok` |
| Backend `/ready` | api/gemini/gcs/clickhouse all ok |
| `CINEYIELD_MODE` (Cloud Run env) | `contest` |
| Contest gate (`smoke-contest.sh`, prod) | **12 passed / 0 failed** |
| Production smoke (`e2e-prod-smoke.sh`) | **6 passed / 0 failed** |
| Backend pytest | **174 passed** |
| mcp-clickhouse live query | `total_scanned=27`, 7 ranked |
| `agent_events` write during propose | row count `39 → 40` |
| Analytics (real ClickHouse) | 27 campaigns · 12 scenes · 16 opportunities · 3 approved deals · $240,700 revenue |

---

## What is REAL vs FICTIONAL (no overclaiming)

- **Real**: all integrations above, deterministic scoring, approval persistence,
  analytics, agent trace, Cloud Run deployment.
- **Fictional demo data**: show/character names and scene library content are invented;
  the judged upload uses an engineering test clip, not licensed footage.
- **Illustrative**: revenue/market figures are representative, not audited financials.
