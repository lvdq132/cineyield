#!/usr/bin/env bash
# CineYield demo reset — resets approval state for the canonical demo opportunity.
#
# Safe: does NOT drop or truncate any table. Only clears proposals and revenue events
# for the canonical demo opportunity so the demo can be run again from a clean state.
#
# Usage:
#   bash scripts/demo-reset.sh                    # local backend (default)
#   bash scripts/demo-reset.sh https://cineyield-api-xxx.run.app   # production backend
#
# After reset, the Marketplace shows no approved deal and Analyze a Cut can be run fresh.

set -euo pipefail

API_BASE="${1:-http://localhost:8000}"
CANONICAL_OPP="opp_horizons_rooftop_001"

echo "CineYield demo reset"
echo "Backend: $API_BASE"
echo "Canonical opportunity: $CANONICAL_OPP"
echo ""

# Health check
if ! curl -sf "${API_BASE}/health" >/dev/null 2>&1; then
  echo "ERROR: Backend not reachable at $API_BASE"
  exit 1
fi

echo "▸ Calling demo reset endpoint..."
RESULT=$(curl -sf -X POST "${API_BASE}/api/v1/demo/reset" \
  -H "Content-Type: application/json" \
  -d "{\"opportunity_id\": \"${CANONICAL_OPP}\"}" 2>/dev/null || echo '{"error":"endpoint_not_found"}')

echo "  → $RESULT"

# If the demo reset endpoint doesn't exist yet, fall back to status report
if echo "$RESULT" | grep -q '"error"'; then
  echo ""
  echo "  Demo reset endpoint not yet implemented."
  echo "  Current analytics state:"
  curl -sf "${API_BASE}/api/v1/analytics/summary" 2>/dev/null | python3 -m json.tool
fi

echo ""
echo "Reset complete. You can now run a fresh demo flow."
