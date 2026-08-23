# CineYield — Handoff for the Video Professional

This document is for the person producing the 3-minute submission video. It describes
**what CineYield is, the exact reliable demo sequence, what each screen proves, what to
say, and — importantly — what NOT to claim.** It does not include the video itself; the
final cinematic video is your deliverable.

> Engineering has intentionally **not** produced the video, generated voiceover, or
> generated HORIZONS footage. Everything below is factual and verified so your narration
> stays truthful.

---

## 1. What CineYield is (30-second version)

CineYield turns finished scenes into contextual product-placement opportunities. A
producer uploads a clip; a multi-agent AI pipeline (Google ADK orchestrating Gemini +
ClickHouse) understands the scene, finds matching brand campaigns, checks rights, guards
creative integrity, and drafts a deal — leaving the human producer as the final approval
authority. Approved placements and analytics persist in ClickHouse in real time.

**The problem it solves**: studios monetize placement *before* shooting, blindly.
CineYield finds monetizable placement opportunities *after* production, without
compromising story or brand safety — and keeps a human in the loop.

**Partner track**: ClickHouse (via the official `mcp-clickhouse` MCP server), plus
Google ADK + Gemini + Cloud Run.

---

## 2. Verified URLs

| Surface | URL |
|---------|-----|
| App (start here) | https://cineyield-web-pg7lg7ldma-uc.a.run.app |
| Backend health | https://cineyield-api-pg7lg7ldma-uc.a.run.app/health |
| API docs (nice B-roll) | https://cineyield-api-pg7lg7ldma-uc.a.run.app/docs |
| Agent trace (nice B-roll) | https://cineyield-api-pg7lg7ldma-uc.a.run.app/api/v1/agents/events?limit=6 |
| Analytics JSON (B-roll) | https://cineyield-api-pg7lg7ldma-uc.a.run.app/api/v1/analytics/summary |

---

## 3. Before you record (5 minutes)

Ask the engineering owner to run these, or run them if you have the repo checked out:

```bash
# 1. Confirm every integration is live (should print "12 passed / 0 failed")
bash scripts/smoke-contest.sh https://cineyield-api-pg7lg7ldma-uc.a.run.app

# 2. Reset demo state so the analytics/deal screens start clean
bash scripts/demo-reset.sh https://cineyield-api-pg7lg7ldma-uc.a.run.app
```

Then open the app and click through **once** as a warm-up (this also warms Cloud Run so
the recorded take is fast). The engineering test clip is at
`apps/agent-api/tests/fixtures/test_video.mp4`.

---

## 4. Exact demo sequence (matches the 3-minute budget)

The detailed click path with on-screen callouts lives in
[`DEMO_RUNBOOK.md`](DEMO_RUNBOOK.md). Summary and what each screen proves:

| # | Screen | What to show | What it proves | Approx |
|---|--------|--------------|----------------|--------|
| 1 | **Library** (`/library`) | Scene catalog with mood/category tags | The product indexes a library into a commercial-opportunity layer | 0:00–0:15 |
| 2 | **Analyze a Cut** | Click "Analyze a Cut" → pick `test_video.mp4` → "Analyzing cut…" overlay | The real ADK pipeline runs (Gemini + mcp-clickhouse). It takes tens of seconds *because the calls are real* | 0:15–1:00 |
| 3 | **Scene Intelligence** (`/scene/{id}`) | Scene name, mood, brand-safety score, opportunities | Gemini produced structured scene understanding from the video | 1:00–1:20 |
| 4 | **Marketplace** | Status bar: `market-agent · mcp-clickhouse · 27 scanned · N ranked`; score ring | ClickHouse inventory queried live through the official MCP server; ranking is deterministic | 1:20–1:40 |
| 5 | **Deal** | Proposal: campaign, estimated fee, `PRODUCER_REVIEW` | An agent composed a complete, structured deal for a human to review | 1:40–1:55 |
| 6 | **Approve + reload** | Click Approve → APPROVED badge → **reload page** → badge persists | Human-in-the-loop; approval is a ClickHouse mutation, not UI state | 1:55–2:15 |
| 7 | **Analytics** (`/analytics`) | Approved deals + revenue total | Every approval lands in ClickHouse and drives real analytics | 2:15–2:30 |
| 8 | **Agent trace** (optional, technical judges) | `/api/v1/agents/events?limit=6` JSON | Full audit trail: each agent, its tool, its latency | 2:30–2:45 |

---

## 5. Technologies to name on screen / in narration

Say these explicitly — they are the judged claims and they are all true:

- **Google ADK** — `LlmAgent` + `Runner` orchestrate five agents; every job reports
  `adk_used: true`.
- **Gemini 2.5 Flash (Vertex AI)** — scene video understanding and creative reasoning.
- **ClickHouse Cloud** — campaign inventory, proposals, analytics, and the agent audit
  trail.
- **Official `mcp-clickhouse` (MCP)** — the Market Agent's live database tool (stdio MCP
  server). *This is the partner-track proof — make sure the "mcp-clickhouse" label in the
  Marketplace status bar is legible on screen.*
- **Google Cloud Run** — hosts both services, fully serverless.
- **Deterministic scoring** — Python rules rank campaigns; the LLM does not invent the
  numbers.

---

## 6. Known loading / timing behavior (so nothing looks broken)

- **Upload → scene navigation takes tens of seconds** (Gemini video understanding + ADK
  orchestration + live ClickHouse). This is expected and is a *feature* to narrate ("real
  calls, not animations"), not a bug. Allow up to ~3–5 minutes on a cold instance; a
  warm-up run beforehand keeps the recorded take short.
- **First page load** may be slightly slow if the frontend is cold — do a warm-up load.
- **mcp-clickhouse** first query can be a few seconds (subprocess spawn + round-trip to
  ClickHouse Cloud). Subsequent queries are faster.

If the upload overlay disappears without navigating, the run may have failed — reset and
retry (see recovery in `DEMO_RUNBOOK.md`). Prefer showing a clean warmed-up take.

---

## 7. Claims to AVOID (do not say these — they are false or unverified)

- ❌ Do **not** say the shows, characters, or "HORIZONS" footage are real productions —
  they are **fictional demo content**, and the judged clip is an **engineering test
  video**.
- ❌ Do **not** present the revenue/market figures as audited or actual financial results
  — they are **illustrative**.
- ❌ Do **not** claim CineYield has real brand partnerships, signed deals, or paying
  studio customers — it does not.
- ❌ Do **not** claim real-time streaming-scale ingestion, or that it processes full
  episodes today — the demo analyzes a short clip.
- ❌ Do **not** claim the rights engine consults external/legal databases — rights
  clearance is a deterministic in-app rules engine (accurate to say "deterministic,
  auditable rules"; inaccurate to say "checks live legal databases").
- ❌ Do **not** invent latency/accuracy numbers. If you want a number, use what's on
  screen or in the agent trace.

Truthful framing to prefer: *"a working agentic prototype, live on Google Cloud, with
real Gemini, real ClickHouse via the official MCP server, and a human approving every
deal."*

---

## 8. Demo reset / rehearsal command

```bash
bash scripts/demo-reset.sh https://cineyield-api-pg7lg7ldma-uc.a.run.app
```

Deletes proposals and revenue events **only** for the canonical demo opportunity. It does
not touch brand campaigns, scenes, or the agent-event history.

---

## 9. Recovery during recording

- Pipeline > 60s: normal on cold start; wait. If it fails, reset + retry.
- Marketplace shows no match: run demo reset, re-upload; `opp_horizons_rooftop_001` always
  matches the 27 seeded campaigns.
- Backend errors: check `gcloud run services logs read cineyield-api --region=us-central1`
  (ask the engineering owner).

The single most reliable recording strategy: **reset → one warm-up pass → record the
second pass.**
