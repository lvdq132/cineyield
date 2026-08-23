#!/usr/bin/env bash
# CineYield production smoke test — verifies all integrations are live after deploy.
#
# Usage:
#   bash scripts/e2e-prod-smoke.sh https://cineyield-api-xxx.run.app
#   bash scripts/e2e-prod-smoke.sh   # reads BACKEND_URL env var or prompts

set -euo pipefail

BACKEND_URL="${1:-${BACKEND_URL:-}}"
if [ -z "$BACKEND_URL" ]; then
  echo "Usage: $0 <backend-url>"
  echo "  e.g. $0 https://cineyield-api-xxxx-uc.a.run.app"
  exit 1
fi

PASS=0
FAIL=0

check() {
  local name="$1"
  local url="$2"
  local expect="$3"
  local result
  result=$(curl -sf --max-time 30 "$url" 2>/dev/null || echo 'CURL_FAILED')
  if echo "$result" | grep -q "$expect"; then
    echo "  ✓ $name"
    PASS=$((PASS+1))
  else
    echo "  ✗ $name — expected '$expect' in: ${result:0:200}"
    FAIL=$((FAIL+1))
  fi
}

echo ""
echo "CineYield production smoke test"
echo "Backend: $BACKEND_URL"
echo "────────────────────────────────"

check "health"              "${BACKEND_URL}/health"                             '"ok"'
check "ready"               "${BACKEND_URL}/ready"                              '"api"'
check "pipeline/status"     "${BACKEND_URL}/api/v1/pipeline/status"             '"gemini"'
check "analytics/summary"   "${BACKEND_URL}/api/v1/analytics/summary"          '"total_campaigns"'
check "agents/events"       "${BACKEND_URL}/api/v1/agents/events?limit=1"       '"events"'
check "content"             "${BACKEND_URL}/api/v1/content"                     '"scenes"'

echo "────────────────────────────────"
echo "  PASSED: $PASS  FAILED: $FAIL"

if [ "$FAIL" -gt 0 ]; then
  echo ""
  echo "Some checks failed. Check Cloud Run logs:"
  echo "  gcloud run services logs read cineyield-api --project=project-01cc020f-432a-4192-bc0 --region=us-central1"
  exit 1
fi

echo ""
echo "All smoke checks passed."
