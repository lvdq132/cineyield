# CineYield — Devpost Submission Checklist

Status legend: `[x]` done · `[ ]` requires a human action (noted).

## Project identity

- [x] **Public hosted URL** — https://cineyield-web-pg7lg7ldma-uc.a.run.app *(live, verified)*
- [ ] **Repository URL** — repo must be created and pushed to GitHub, then set **public**
      (`gh` is authenticated locally; the owner should confirm repo name + public
      visibility — see `docs/PROJECT_FREEZE.md`).
- [ ] **3-minute demo video** — **owned by the video professional**, not engineering.
      Factual handoff prepared: `docs/VIDEO_PRO_HANDOFF.md`.
- [x] **Project title** — CineYield
- [x] **Tagline** — "Agentic product-placement OS for entertainment"
- [x] **Open-source license** — `LICENSE` (MIT) added at repo root; `apps/web/package.json`
      declares `"license": "MIT"`.

## Partner tracks

- [x] **ClickHouse** — official `mcp-clickhouse` (stdio MCP server) used live in the
      production pipeline
  - Tool: `run_query` against `cineyield.brand_campaigns` (27 rows)
  - Per-agent latency recorded in `cineyield.agent_events`
  - Analytics endpoint reads directly from ClickHouse
- [x] **Google ADK** — `google-adk` `LlmAgent` + `Runner(auto_create_session=True)`
  - `adk_used: true` present in every pipeline job response
  - `pipeline_version: adk_llmagent_v1` recorded in ClickHouse

## Real integration proof points (verified 2026-08-29)

- [x] `GET {backend}/api/v1/pipeline/status` → `gemini: true, clickhouse: true`
- [x] `GET {backend}/api/v1/agents/events?limit=5` → real ClickHouse rows with latency
- [x] `GET {backend}/api/v1/analytics/summary` → 3 approved deals, 27 campaigns, 12 scenes
- [x] Upload engineering MP4 → job completes with `adk_used: true`,
      `pipeline_version: adk_llmagent_v1` *(prod browser E2E, 8/8)*
- [x] Approve deal → `workflow_state: APPROVED` persists across page refresh *(prod E2E)*
- [x] Real upload → isolated MP4 segment + exact extracted frame persisted in GCS
- [x] Scene page → exact extracted frame, real detections, placement zones and scores
- [x] Nano Banana 2 → real approved branded frame with Original / Proposal comparison
- [x] Veo 3.1 → real asynchronous branded replacement job with approval controls
- [x] Contest gate `bash scripts/smoke-contest.sh <backend>` → **12 passed / 0 failed**

## Verification results (2026-08-23)

- [x] Backend pytest — **186 passed**, including credentialed MCP reachability
- [x] Backend `ruff` — clean · `mypy` — clean (41 files)
- [x] Frontend ESLint — clean · `tsc --noEmit` — clean · `next build` — clean
- [x] Production smoke (`e2e-prod-smoke.sh`) — **6/6**
- [x] Production contest gate (`smoke-contest.sh`) — **12/12**
- [x] Production browser E2E (Playwright vs live URLs) — **8/8**
- [x] No secrets tracked in git (`.env*` ignored; ClickHouse password in Secret Manager)

## Screenshots to capture (for Devpost gallery — human/video-pro task)

- [ ] Library page (catalog of scenes)
- [ ] Upload flow — "Analyzing cut" overlay with progress
- [ ] Scene Intelligence — scene name, mood, brand safety score, opportunities
- [ ] Scene Intelligence — exact source frame, detected props, placement zones
- [ ] Marketplace — MarketAgent status bar showing "mcp-clickhouse" + score ring
- [ ] Deal detail — proposal with campaign, fee, PRODUCER_REVIEW state
- [ ] Approved deal — APPROVED badge persistent after refresh
- [ ] Nano Banana — Original / Proposal comparison with approved reference
- [ ] Veo — playable Original / Branded replacement comparison
- [ ] Analytics — approved revenue total
- [ ] Backend `/docs` OpenAPI

## Technical details for Devpost

- **Built with**: Python 3.12, FastAPI, Google ADK, Gemini 2.5 Flash, Nano Banana 2
  (`gemini-3.1-flash-image`), Veo 3.1 (`veo-3.1-generate-001`) on Vertex AI,
  Next.js 15, React 19, ClickHouse Cloud, official mcp-clickhouse MCP server, Google
  Cloud Run.
- **Open-source libraries**: google-adk, google-genai, mcp, mcp-clickhouse,
  clickhouse-connect, fastapi, uvicorn, next.js, tailwindcss.
- **License**: MIT (`LICENSE` at repo root).

## Devpost fields still requiring human input

- [ ] Team members listed
- [ ] Story / inspiration written (1–3 paragraphs)
- [ ] Built-with tags: Google ADK, Gemini, ClickHouse, MCP, Cloud Run
- [ ] Demo video uploaded (video professional)
- [ ] GitHub repo created, pushed, and set **public**; URL linked on Devpost
- [ ] Public URL re-verified working at submission time
- [ ] Partner track selected: **ClickHouse**

## Secrets verified NOT in repo

- [x] `apps/agent-api/.env` — in `.gitignore` (untracked)
- [x] `apps/web/.env.local` — in `.gitignore` (untracked)
- [x] ClickHouse password — in Google Secret Manager, not in any committed file
- [x] No ADC credential files in the Docker image (Cloud Run service-account identity)
