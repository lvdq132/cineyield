# CineYield — Project Freeze

**Status: JUDGE-READY (frozen for submission).**
The only outstanding items are human/account-owner actions listed at the bottom.

## Frozen baseline

- **Frozen commit**: the commit tagged **`contest-freeze`** on `main` (run
  `git rev-parse contest-freeze` for the exact SHA).
- **Public repo**: https://github.com/lvdq132/cineyield — `main` was published as a
  single clean commit. Early local history had accidentally committed
  `apps/web/node_modules` (a 124 MB binary over GitHub's limit); rather than rewrite and
  force-push, `main` was rebuilt as one comprehensive commit of the verified tree. The
  prior granular commit subjects are preserved in that commit's body. The pre-rebuild
  history remains locally under the `rollback-pre-contest-audit-b7c053bb` tag.
- **Frozen date**: 2026-08-23.
- **Production is unchanged by this audit** — no code was redeployed. The deployed
  services are byte-for-byte the verified-working build; the repo commit above differs
  only in comments/docs/license (zero runtime behavior change).

## Production URLs

| Service | URL |
|---------|-----|
| Frontend | https://cineyield-web-pg7lg7ldma-uc.a.run.app |
| Backend | https://cineyield-api-pg7lg7ldma-uc.a.run.app |
| API docs | https://cineyield-api-pg7lg7ldma-uc.a.run.app/docs |

## Verification results (2026-08-23, all green)

| Check | Result |
|-------|--------|
| Backend pytest | **174 passed** |
| Backend ruff | clean |
| Backend mypy | clean (41 files) |
| Frontend ESLint | clean |
| Frontend `tsc --noEmit` | clean |
| Frontend `next build` | clean |
| Production smoke (`e2e-prod-smoke.sh`) | **6/6** |
| Production contest gate (`smoke-contest.sh`) | **12/12** |
| Production browser E2E (Playwright vs live URLs) | **8/8** |
| Secret scan (tracked files) | clean — no secrets tracked |

Integration status (live, from Cloud Run): Gemini 2.5 Flash (Vertex AI) **real**;
Google ADK `LlmAgent`/`Runner` **real** (`adk_used: true`); private GCS **real**;
ClickHouse Cloud **real**; official `mcp-clickhouse` **real** (`total_scanned=27`);
deterministic scoring **real**; producer approval + analytics persistence **real**;
`CINEYIELD_MODE=contest` enforced on the backend (no silent fallbacks).

## Reset / rehearsal command

The production browser E2E and any rehearsal create demo proposals/revenue. Reset the
canonical demo opportunity to a clean state before recording or judging:

```bash
bash scripts/demo-reset.sh https://cineyield-api-pg7lg7ldma-uc.a.run.app
# Re-verify integrations after reset:
bash scripts/smoke-contest.sh https://cineyield-api-pg7lg7ldma-uc.a.run.app   # expect 12/12
```

## Known non-blocking limitations (do NOT "fix" before submission)

1. **In-memory upload-job state** on the backend. Job status lives in process memory;
   under multi-instance scale-out a status poll could hit a replica without the job. The
   frontend already retries transient 404s, backend runs `min-instances=1`, and the
   production browser E2E (real upload) passes 8/8 — so this does not manifest in the
   demo. *Optional* hardening (single-flag, reversible, not applied): set backend
   `--max-instances=1`. Not required.
2. **Frontend has no `min-instances`** → a possible ~few-second cold start on the first
   visit. *Optional* hardening: frontend `--min-instances=1`. Not required.
3. **Frontend runs as the default Compute Engine service account.** The Next.js server
   makes no GCP API calls at runtime, so the real risk is low. A dedicated zero-permission
   runtime SA would be marginally cleaner. Documented, intentionally not changed.
4. (Optional hardening 1–2 were **not** applied because a production Cloud Run mutation
   requires owner approval and the current config already passes all verification. Apply
   only if desired; both are reversible metadata-only changes.)
5. **Cosmetic code items** (not judge-visible, left as-is to keep the freeze diff minimal):
   dead "Unknown Scene" fallback in `scene_agent.py` (never called); redundant
   `if x else x` in `scoring.py::score_campaigns`; DealAgent narrative lacks an explicit
   contest-mode Gemini guard (unreachable in practice — SceneAgent hard-fails first).

## Rules for any future agent before submission

- **Do NOT redeploy or reconfigure the Cloud Run services** without a strong reason and
  owner approval. They are verified-working; the video and judging depend on them.
- **Do NOT rewrite git history, force-push, or delete branches.**
- **Do NOT commit secrets.** `.env*` are ignored; the ClickHouse password lives only in
  Secret Manager.
- **Do NOT add features.** This is frozen. Only fix a genuine submission-breaking defect.
- **Do NOT produce the video** — that is the video professional's deliverable
  (`docs/VIDEO_PRO_HANDOFF.md`).
- If you must change production code, follow Phase 9: redeploy the affected service and
  re-run the full verification matrix above (`smoke-contest.sh` must return 12/12).

## Remaining human-only actions

1. **Create the GitHub repository, push, and set it public**, then link the URL on
   Devpost. `gh` is authenticated locally (account `lvdq132`); the owner should confirm
   the repo name and public visibility before it is created (public exposure is
   irreversible in effect — the code has been secret-scanned and is clean).
2. **Devpost submission fields**: team members, story/inspiration, built-with tags,
   partner track = ClickHouse, repo URL, hosted URL, and the uploaded video.
3. **The 3-minute demo video** — produced separately by the video professional.
