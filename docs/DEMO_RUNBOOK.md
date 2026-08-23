# CineYield Demo Runbook

**Product that exists**: An agentic pipeline that analyses a video scene, matches brands via ClickHouse + MCP, checks rights, guards creative integrity with Gemini, and creates a persistent deal — all in ~35 seconds.

**Starting URL**: `https://cineyield-web-pg7lg7ldma-uc.a.run.app`

---

## Pre-demo checklist (5 minutes before)

```bash
# Confirm production backend is healthy
bash scripts/e2e-prod-smoke.sh https://cineyield-api-pg7lg7ldma-uc.a.run.app

# Reset demo state so no approved deal is shown at start
bash scripts/demo-reset.sh https://cineyield-api-pg7lg7ldma-uc.a.run.app
```

Confirm:
- [ ] Analytics shows 0 approved deals (or reset confirmed)
- [ ] Library page loads
- [ ] Marketplace page loads with TOP MATCH visible
- [ ] Engineering test video at hand: `apps/agent-api/tests/fixtures/test_video.mp4`

---

## Click path (exact steps)

### Step 1 — Library (5 seconds)

1. Navigate to `https://cineyield-web-pg7lg7ldma-uc.a.run.app/library`
2. **Show**: Scene catalog — multiple clips with mood/category metadata
3. Say: *"CineYield indexes every scene in your library. Here's the commercial opportunity layer."*

### Step 2 — Analyze a Cut (35 seconds — the ADK moment)

1. Click **Analyze a Cut** button (top-right of library)
2. In the file picker, select `apps/agent-api/tests/fixtures/test_video.mp4`
3. **Show**: "Analyzing cut…" overlay — progress bar advances as the pipeline runs
4. Say: *"This is a real Google ADK pipeline. SceneAgent calls Gemini for video understanding, MarketAgent queries brand campaigns via the official mcp-clickhouse MCP server, then RightsAgent and Creative Guardian check the match is safe to close."*
5. Wait ~35 seconds for navigation to `/scene/{id}`

**What judges should notice**: The pipeline takes 30–40 seconds because it's making real Gemini and ClickHouse calls, not fake animations.

### Step 3 — Scene Intelligence (10 seconds)

1. On the Scene page: note scene name, mood, brand safety score, placement opportunities
2. Click the **opportunity card** to see ranked campaigns
3. Say: *"Gemini read the video and returned structured scene intelligence — mood, narrative weight, brand safety. That's the input to the MarketAgent."*

### Step 4 — Marketplace (10 seconds)

1. Navigate to `/marketplace` (or click Marketplace in sidebar)
2. **Show**: Status bar — "market-agent • mcp-clickhouse • 27 scanned • 1 ranked"
3. **Show**: Score ring with the top campaign
4. Say: *"The MarketAgent used the official ClickHouse MCP server via stdio transport to pull 27 live brand campaigns. Scoring is deterministic Python — no hallucination in the ranking."*

**ClickHouse MCP moment for judges**: The "mcp-clickhouse" label in the status bar shows the real MCP integration. Agent latency (~1 300 ms) is in the agent trace.

### Step 5 — Deal (10 seconds)

1. Click **Open Deal** on the top match
2. **Show**: Proposal — campaign name, estimated fee, workflow state `PRODUCER_REVIEW`
3. Say: *"DealAgent composed a complete proposal with structured terms. It's in ClickHouse, ready for producer sign-off."*

### Step 6 — Approve Placement (15 seconds — the persistence moment)

1. Click **Approve Placement**
2. Wait ~2 seconds
3. **Show**: APPROVED badge
4. **Reload the page** (Command+R / F5)
5. **Show**: APPROVED badge persists
6. Say: *"Approval is a `workflow_state` mutation in ClickHouse — not front-end state. It survives a full refresh."*

### Step 7 — Analytics (5 seconds)

1. Navigate to `/analytics`
2. **Show**: Approved deals count, total revenue in USD
3. Say: *"All analytics come straight from ClickHouse aggregation queries — every approval lands here in real time."*

### Step 8 — Agent Trace (optional, for technical judges)

1. Open: `https://cineyield-api-pg7lg7ldma-uc.a.run.app/api/v1/agents/events?limit=6`
2. **Show**: JSON with agent names, tool names, real latencies
3. Say: *"Every agent records its execution to ClickHouse — tool used, latency, summary. This is the full audit trail."*

---

## Expected outputs

| Step | Expected |
|------|----------|
| Library | Scenes with genre/mood tags |
| Upload | `analyzing cut` overlay, then navigation to `/scene/{id}` |
| Pipeline job | `status: completed`, `adk_used: true`, `pipeline_version: adk_llmagent_v1` |
| Marketplace | Status bar: `market-agent • mcp-clickhouse • 27 scanned` |
| Deal | `workflow_state: PRODUCER_REVIEW`, campaign name, fee |
| Approve | `workflow_state: APPROVED`, persists on reload |
| Analytics | `approved_deals ≥ 1`, `approved_revenue_usd > 0` |
| Agent trace | 6 events: scene_agent, market_agent, rights_agent, creative_guardian, deal_agent, producer |

---

## Recovery procedures

### Pipeline taking more than 60 seconds

Gemini Vertex AI cold-start can add 10–20s on first call. Wait up to 90s. If still pending, check:

```bash
# Backend logs
gcloud run services logs read cineyield-api \
  --project=project-01cc020f-432a-4192-bc0 \
  --region=us-central1 --limit=50
```

### "Analyzing cut" overlay disappears without navigation

The job may have failed. Check:

```bash
curl https://cineyield-api-pg7lg7ldma-uc.a.run.app/api/v1/ingest/status/JOB_ID_FROM_URL
```

### ClickHouse slow or timing out

mcp-clickhouse connects to ClickHouse Cloud (external). On slow networks the first call may take 3–5s. Subsequent calls are faster. The demo is unaffected by a single slow query.

### Marketplace shows no match

Run demo reset then reupload. The canonical opportunity `opp_horizons_rooftop_001` always has matches against the 27 seeded campaigns.

---

## Reset command

```bash
# Production reset (before each demo rehearsal)
bash scripts/demo-reset.sh https://cineyield-api-pg7lg7ldma-uc.a.run.app

# Or via API directly
curl -X POST https://cineyield-api-pg7lg7ldma-uc.a.run.app/api/v1/demo/reset \
  -H "Content-Type: application/json" \
  -d '{"opportunity_id": "opp_horizons_rooftop_001"}'
```

---

## Timings for 3-minute demo

| Segment | Time |
|---------|------|
| Library intro | 0:00–0:15 |
| Analyze a Cut (upload + wait) | 0:15–1:00 |
| Scene Intelligence | 1:00–1:20 |
| Marketplace + MCP callout | 1:20–1:40 |
| Deal detail | 1:40–1:55 |
| Approve + reload | 1:55–2:15 |
| Analytics | 2:15–2:30 |
| Agent trace (optional) | 2:30–2:45 |
| Wrap / summary | 2:45–3:00 |

---

*Voiceover script: to be written after production E2E confirmed.*
