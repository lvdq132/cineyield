#!/usr/bin/env bash
# CineYield contest gate — the ONE command that proves the judged demo path
# actually exercises every mandatory real integration, above all the
# ClickHouse partner-track requirement: mcp-clickhouse.
#
# scripts/e2e-prod-smoke.sh checks liveness of already-working endpoints
# (health/ready/pipeline-status/analytics/agents-events/content). None of
# those calls the only endpoint that invokes query_campaigns_via_mcp, so
# that script cannot detect a broken or missing MCP integration. This
# script is that missing gate. It FAILS NON-ZERO, with a specific message,
# unless ALL of the following are true:
#
#   1. mandatory env/config present (Gemini, ClickHouse, GCS)              [GET /ready, /pipeline/status]
#   2. ClickHouse reachable                                                [GET /ready -> checks.clickhouse == "ok"]
#   3. mcp-clickhouse reachable THROUGH THE APP'S OWN INTEGRATION          [GET /api/v1/opportunities/{id}/matches
#      (never a direct DB query — must go through query_campaigns_via_mcp)  -> MarketAgent -> query_campaigns_via_mcp]
#   4. Gemini reachable                                                    [POST /api/v1/opportunities/{id}/propose
#                                                                            -> DealAgent's Gemini narrative call]
#   5. the canonical demo asset/scene/opportunity exists                   [GET /api/v1/content/{asset},
#                                                                            /api/v1/scenes/{scene}, /api/v1/opportunities/{opp}]
#   6. a real agent run produces genuinely persisted agent_events          [GET /api/v1/agents/events before/after
#                                                                            the propose call above]
#
# Usage:
#   bash scripts/smoke-contest.sh                          # http://localhost:8000
#   bash scripts/smoke-contest.sh http://localhost:8014     # local, custom port
#   bash scripts/smoke-contest.sh https://cineyield-api-xxx.run.app   # deployed
#
# Requires: curl, python3 (stdlib only — no extra deps). Works identically
# against a local `make dev`-style server and a deployed Cloud Run URL; it
# only ever talks HTTP to $BASE_URL, never touches ClickHouse/GCS/Gemini
# credentials directly.
#
# Check 4's guarantee is strongest when the server under test runs with
# CINEYIELD_MODE=contest (the production Cloud Run backend always does —
# see README "Contest mode"): in that mode a Gemini failure surfaces as an
# HTTP 500 instead of silently falling back to templated prose, so a 200
# here is proof Gemini actually answered. Outside contest mode the same
# check still runs, but a passing result is downgraded to a WARN because a
# template fallback could be masking an unreachable Gemini.

set -euo pipefail

BASE_URL="${1:-${BASE_URL:-http://localhost:8000}}"
BASE_URL="${BASE_URL%/}"
CANONICAL_ASSET="horizons"
CANONICAL_SCENE="rooftop-reflection"
CANONICAL_OPP="opp_horizons_rooftop_001"
CANONICAL_CAMPAIGN="camp_aurelius_001"

PASS=0
FAIL=0
WARNINGS=0
declare -a FAILURES=()

ok()   { echo "  ✓ $1"; PASS=$((PASS+1)); }
bad()  { echo "  ✗ $1"; FAIL=$((FAIL+1)); FAILURES+=("$1"); }
warn() { echo "  ! $1"; WARNINGS=$((WARNINGS+1)); }

# jget <json> <dotted.path> [default] -- tiny stdlib-only JSON field getter.
# Missing keys / parse errors resolve to [default] (empty string if omitted).
jget() {
  python3 -c '
import json, sys
default = sys.argv[3] if len(sys.argv) > 3 else ""
try:
    d = json.loads(sys.argv[1])
    for p in sys.argv[2].split("."):
        d = d[int(p)] if p.isdigit() else d[p]
    print("" if d is None else d)
except Exception:
    print(default)
' "$1" "$2" "${3:-}"
}

# http_call METHOD PATH [JSON_BODY] -- prints "<body>\n<status_code>"
http_call() {
  local method="$1" path="$2" data="${3:-}"
  if [ -n "$data" ]; then
    curl -s --max-time 30 -X "$method" "${BASE_URL}${path}" \
      -H "Content-Type: application/json" -d "$data" -w '\n%{http_code}' 2>/dev/null \
      || printf '\n000'
  else
    curl -s --max-time 30 -X "$method" "${BASE_URL}${path}" -w '\n%{http_code}' 2>/dev/null \
      || printf '\n000'
  fi
}

http_status() { echo "$1" | tail -n1; }
http_body()   { echo "$1" | sed '$d'; }

echo ""
echo "CineYield contest gate"
echo "Backend: $BASE_URL"
echo "────────────────────────────────"

# ── Prerequisite: backend reachable at all ─────────────────────────────────
RESP=$(http_call GET /health)
if [ "$(http_status "$RESP")" != "200" ]; then
  echo "  ✗ GET /health unreachable (status $(http_status "$RESP")) — backend not running at $BASE_URL"
  exit 1
fi

# ── 1+2: mandatory config present + ClickHouse reachable ───────────────────
echo ""
echo "▸ 1-2. Config + ClickHouse reachability (GET /ready)"
RESP=$(http_call GET /ready)
READY_STATUS=$(http_status "$RESP")
READY_BODY=$(http_body "$RESP")
if [ "$READY_STATUS" != "200" ]; then
  bad "GET /ready returned HTTP $READY_STATUS"
else
  GEMINI=$(jget "$READY_BODY" checks.gemini)
  GCS=$(jget "$READY_BODY" checks.gcs)
  CH=$(jget "$READY_BODY" checks.clickhouse)

  [ "$GEMINI" = "configured" ] && ok "Gemini configured" || bad "Gemini not configured (checks.gemini=$GEMINI) — set GOOGLE_API_KEY or GOOGLE_CLOUD_PROJECT"
  [ "$GCS" = "configured" ]    && ok "GCS configured"    || bad "GCS not configured (checks.gcs=$GCS) — set GCS_BUCKET_NAME"
  [ "$CH" = "ok" ]             && ok "ClickHouse reachable (checks.clickhouse=ok)" || bad "ClickHouse not reachable (checks.clickhouse=$CH) — set CLICKHOUSE_HOST/USER/PASSWORD"
fi

PIPELINE_RESP=$(http_call GET /api/v1/pipeline/status)
PIPELINE_BODY=$(http_body "$PIPELINE_RESP")
MODE=$(jget "$PIPELINE_BODY" mode "development")
if [ "$MODE" = "contest" ]; then
  ok "Server running in CINEYIELD_MODE=contest (integration failures cannot silently fall back)"
else
  warn "Server not in contest mode (mode=$MODE) — a Gemini/creative fallback could mask a broken integration; check 4 below is weaker as a result"
fi

# ── 5: canonical demo asset/scene/opportunity exist ─────────────────────────
echo ""
echo "▸ 5. Canonical demo content exists"
RESP=$(http_call GET "/api/v1/content/${CANONICAL_ASSET}")
[ "$(http_status "$RESP")" = "200" ] && ok "content asset '${CANONICAL_ASSET}' exists" || bad "content asset '${CANONICAL_ASSET}' missing (HTTP $(http_status "$RESP"))"

RESP=$(http_call GET "/api/v1/scenes/${CANONICAL_SCENE}")
[ "$(http_status "$RESP")" = "200" ] && ok "scene '${CANONICAL_SCENE}' exists" || bad "scene '${CANONICAL_SCENE}' missing (HTTP $(http_status "$RESP"))"

RESP=$(http_call GET "/api/v1/opportunities/${CANONICAL_OPP}")
OPP_STATUS=$(http_status "$RESP")
[ "$OPP_STATUS" = "200" ] && ok "opportunity '${CANONICAL_OPP}' exists" || bad "opportunity '${CANONICAL_OPP}' missing (HTTP $OPP_STATUS)"

# ── 3: mcp-clickhouse reachable through the app's own integration ──────────
echo ""
echo "▸ 3. mcp-clickhouse reachable via the app's own integration (GET .../matches)"
RESP=$(http_call GET "/api/v1/opportunities/${CANONICAL_OPP}/matches")
MATCHES_STATUS=$(http_status "$RESP")
MATCHES_BODY=$(http_body "$RESP")
if [ "$MATCHES_STATUS" != "200" ]; then
  bad "GET .../matches returned HTTP $MATCHES_STATUS — mcp-clickhouse is unreachable or broken. Body: $(echo "$MATCHES_BODY" | cut -c1-300)"
else
  MCP_LAT=$(jget "$MATCHES_BODY" mcp_latency_ms)
  TOTAL_SCANNED=$(jget "$MATCHES_BODY" total_scanned 0)
  if [ -z "$MCP_LAT" ]; then
    bad "GET .../matches returned HTTP 200 but mcp_latency_ms is null/missing — MarketAgent did not actually call mcp-clickhouse"
  elif ! [ "$TOTAL_SCANNED" -ge 1 ] 2>/dev/null; then
    bad "GET .../matches returned total_scanned=$TOTAL_SCANNED — expected real campaign rows from mcp-clickhouse"
  else
    ok "mcp-clickhouse reachable (mcp_latency_ms=${MCP_LAT}ms, total_scanned=${TOTAL_SCANNED})"
    # A scan that returns 27 campaigns and ranks none of them is not a working
    # market lookup -- it is the marketplace showing every candidate blocked.
    # This check exists because that really happened: /matches passed no scene
    # mood, and since matching is substring based, "" matched every
    # excluded_context and hard-blocked 6 of 27 campaigns, so the marketplace
    # advertised the wrong top match while /propose disagreed with it.
    RANKED=$(jget "$MATCHES_BODY" ranked_count 0)
    if [ "$RANKED" -ge 1 ] 2>/dev/null; then
      ok "market lookup ranked $RANKED campaign(s) — not every candidate blocked"
    else
      bad "GET .../matches scanned $TOTAL_SCANNED campaigns but ranked_count=$RANKED — every candidate is blocked, so the marketplace has no usable match"
    fi
  fi
fi

# ── 4 + 6: Gemini reachable + real agent run persists agent_events ─────────
# One POST /propose call proves both: DealAgent calls Gemini for the brand
# brief/narrative (check 4), and on success writes exactly one new
# cineyield.agent_events row (check 6). It also re-invokes the MCP path
# (Task 1 fix), so a MCP failure here would additionally re-confirm check 3.
echo ""
echo "▸ 4+6. Gemini reachable + agent_events persisted (POST .../propose)"

EVENTS_BEFORE=$(http_call GET "/api/v1/agents/events?opportunity_id=${CANONICAL_OPP}&limit=500")
COUNT_BEFORE=$(jget "$(http_body "$EVENTS_BEFORE")" count 0)
TOP_ID_BEFORE=$(jget "$(http_body "$EVENTS_BEFORE")" events.0.event_id "")

if [ "$OPP_STATUS" != "200" ]; then
  bad "skipped propose call — canonical opportunity missing (see check 5)"
else
  PROPOSE_RESP=$(http_call POST "/api/v1/opportunities/${CANONICAL_OPP}/propose" "{\"campaign_id\": \"${CANONICAL_CAMPAIGN}\"}")
  PROPOSE_STATUS=$(http_status "$PROPOSE_RESP")
  PROPOSE_BODY=$(http_body "$PROPOSE_RESP")

  if [ "$PROPOSE_STATUS" != "200" ]; then
    bad "POST .../propose returned HTTP $PROPOSE_STATUS. Body: $(echo "$PROPOSE_BODY" | cut -c1-400)"
  else
    BRIEF=$(jget "$PROPOSE_BODY" brand_brief)
    PROPOSE_MCP_LAT=$(jget "$PROPOSE_BODY" mcp_latency_ms)
    if [ -z "$BRIEF" ]; then
      bad "POST .../propose succeeded but brand_brief is empty — DealAgent narrative step did not run"
    elif [ "$MODE" = "contest" ]; then
      ok "Gemini reachable (contest mode: no template fallback permitted; brand_brief=${#BRIEF} chars)"
    else
      warn "propose succeeded with a non-empty brand_brief (${#BRIEF} chars), but server is not in contest mode so a template fallback cannot be ruled out as proof of Gemini reachability"
    fi
    if [ -n "$PROPOSE_MCP_LAT" ]; then
      ok "propose also went through mcp-clickhouse (mcp_latency_ms=${PROPOSE_MCP_LAT}ms) — Task 1 fix confirmed live"
    else
      bad "POST .../propose succeeded but returned no mcp_latency_ms — it may be bypassing mcp-clickhouse again"
    fi

    EVENTS_AFTER=$(http_call GET "/api/v1/agents/events?opportunity_id=${CANONICAL_OPP}&limit=500")
    COUNT_AFTER=$(jget "$(http_body "$EVENTS_AFTER")" count 0)
    TOP_ID_AFTER=$(jget "$(http_body "$EVENTS_AFTER")" events.0.event_id "")

    if [ "$COUNT_AFTER" -gt "$COUNT_BEFORE" ] 2>/dev/null; then
      ok "agent_events row count increased ($COUNT_BEFORE -> $COUNT_AFTER) for ${CANONICAL_OPP}"
    elif [ -n "$TOP_ID_AFTER" ] && [ "$TOP_ID_AFTER" != "$TOP_ID_BEFORE" ]; then
      ok "a fresh agent_events row appeared (event_id ${TOP_ID_AFTER} != previous ${TOP_ID_BEFORE:-<none>})"
    else
      bad "no new cineyield.agent_events row detected after propose (count stayed at $COUNT_BEFORE, top event_id unchanged) — persistence may be silently failing"
    fi
  fi
fi

# ── Summary ──────────────────────────────────────────────────────────────
echo ""
echo "────────────────────────────────"
echo "  PASSED: $PASS   FAILED: $FAIL   WARNINGS: $WARNINGS"

if [ "$FAIL" -gt 0 ]; then
  echo ""
  echo "Contest gate FAILED:"
  for f in "${FAILURES[@]}"; do
    echo "  - $f"
  done
  exit 1
fi

echo ""
if [ "$WARNINGS" -gt 0 ]; then
  # Do not restate a clean bill of health when a check was downgraded. The
  # warning above exists precisely because something could not be proven, and
  # a summary line that ignores it is the overclaim this gate is meant to stop.
  echo "Contest gate PASSED with $WARNINGS warning(s). mcp-clickhouse and ClickHouse are"
  echo "confirmed live through the app's own integrations. Re-run against a server started"
  echo "with CINEYIELD_MODE=contest to also prove Gemini, since only contest mode rules out"
  echo "a template fallback."
else
  echo "Contest gate PASSED. mcp-clickhouse, ClickHouse, and Gemini are all live through the app's own integrations."
fi
