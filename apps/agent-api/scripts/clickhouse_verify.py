#!/usr/bin/env python3
"""
CineYield ClickHouse + MCP verification script.
Run after setting credentials in .env:

    cd apps/agent-api
    python scripts/clickhouse_verify.py

Steps:
  1  Required environment variables present
  2  Direct ClickHouse connectivity
  3  Schema tables exist
  4  Seed data counts
  5  Campaign inventory sanity
  6  mcp-clickhouse executable found
  7  mcp-clickhouse SQL query (real MCP call)
  8  MarketAgent canonical scoring
  9  Aurelius Systems is top unblocked candidate
 10  Sanitized AgentEvent created correctly
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

# Make sure we can import cineyield from this script location
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Load .env before cineyield imports so env vars are present
from dotenv import load_dotenv  # noqa: E402

load_dotenv(ROOT / ".env")

PASS = "\033[92m✓ PASS\033[0m"
FAIL = "\033[91m✗ FAIL\033[0m"
SKIP = "\033[93m  SKIP\033[0m"
WARN = "\033[93m! WARN\033[0m"

results: list[tuple[str, bool, str]] = []


def step(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    icon = PASS if ok else FAIL
    print(f"  {icon}  {name}" + (f"  [{detail}]" if detail else ""))


def section(title: str) -> None:
    print(f"\n── {title} {'─' * max(0, 60 - len(title))}")


# ─────────────────────────────────────────────────────────────
# Step 1: Environment variables
# ─────────────────────────────────────────────────────────────
section("1. Environment variables")

required = ["CLICKHOUSE_HOST", "CLICKHOUSE_USER", "CLICKHOUSE_PASSWORD"]
missing = [v for v in required if not os.environ.get(v)]
step("Required env vars present", not missing,
     f"missing: {missing}" if missing else "CLICKHOUSE_HOST, CLICKHOUSE_USER, CLICKHOUSE_PASSWORD")

if missing:
    print(f"\n{FAIL}  Cannot continue — set missing variables in .env")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────
# Step 2: Direct ClickHouse connectivity
# ─────────────────────────────────────────────────────────────
section("2. Direct ClickHouse connectivity")

from cineyield.db.client import (  # noqa: E402
    check_connection,
    get_clickhouse_client,
    reset_client_cache,
)

reset_client_cache()
conn = check_connection()
step("ClickHouse connection", conn["status"] == "ok",
     conn.get("message", ""))

if conn["status"] != "ok":
    print(f"\n{FAIL}  Cannot continue — ClickHouse not reachable")
    sys.exit(1)

client = get_clickhouse_client()

# ─────────────────────────────────────────────────────────────
# Step 3: Schema tables
# ─────────────────────────────────────────────────────────────
section("3. Schema tables")

expected_tables = [
    "content_assets", "scenes", "detected_objects",
    "placement_opportunities", "brand_campaigns", "rights_rules",
    "match_events", "proposals", "agent_events", "revenue_events",
]

try:
    result = client.query("SHOW TABLES IN cineyield")
    existing = {row[0] for row in result.result_rows}
    for table in expected_tables:
        step(f"Table: cineyield.{table}", table in existing)
except Exception as exc:
    step("Schema check", False, str(exc))

# ─────────────────────────────────────────────────────────────
# Step 4: Seed data counts
# ─────────────────────────────────────────────────────────────
section("4. Seed data counts")

checks = {
    "brand_campaigns": (27, "SELECT count() FROM cineyield.brand_campaigns WHERE is_active = true"),
    "content_assets": (6, "SELECT count() FROM cineyield.content_assets"),
    "scenes": (1, "SELECT count() FROM cineyield.scenes"),
    "placement_opportunities": (5, "SELECT count() FROM cineyield.placement_opportunities"),
    "rights_rules": (20, "SELECT count() FROM cineyield.rights_rules"),
}

for name, (expected_min, sql) in checks.items():
    try:
        count = client.query(sql).first_row[0]
        ok = count >= expected_min
        step(f"{name}: >= {expected_min} rows", ok, f"{count} found")
    except Exception as exc:
        step(f"{name} count", False, str(exc))

# ─────────────────────────────────────────────────────────────
# Step 5: Campaign inventory sanity
# ─────────────────────────────────────────────────────────────
section("5. Campaign inventory")

try:
    result = client.query(
        "SELECT brand, campaign_name FROM cineyield.brand_campaigns "
        "WHERE brand = 'Aurelius Systems' LIMIT 1"
    )
    found_aurelius = len(result.result_rows) > 0
    step("Canonical campaign 'Aurelius Systems' seeded", found_aurelius)

    result2 = client.query(
        "SELECT brand FROM cineyield.brand_campaigns "
        "WHERE has(excluded_contexts, 'reflective') OR has(excluded_contexts, 'dusk')"
    )
    has_blocked = len(result2.result_rows) > 0
    step("Blocked campaigns present (creative conflict candidates)", has_blocked,
         f"{len(result2.result_rows)} found")
except Exception as exc:
    step("Campaign inventory", False, str(exc))

# ─────────────────────────────────────────────────────────────
# Step 6: mcp-clickhouse executable
# ─────────────────────────────────────────────────────────────
section("6. mcp-clickhouse executable")

try:
    from cineyield.agents.mcp_market import _mcp_clickhouse_executable
    exe = _mcp_clickhouse_executable()
    step("mcp-clickhouse binary found", True, exe)
except Exception as exc:
    step("mcp-clickhouse binary found", False, str(exc))
    print(f"\n{FAIL}  Install with: pip install mcp-clickhouse")
    sys.exit(1)

# ─────────────────────────────────────────────────────────────
# Step 7: Real MCP query
# ─────────────────────────────────────────────────────────────
section("7. mcp-clickhouse real MCP query")

async def run_mcp_query():
    from cineyield.agents.mcp_market import query_campaigns_via_mcp
    return await query_campaigns_via_mcp()

try:
    t = time.monotonic()
    mcp_result = asyncio.run(run_mcp_query())
    elapsed = int((time.monotonic() - t) * 1000)
    row_count = mcp_result["row_count"]
    ok = row_count >= 27
    step("MCP query returned rows", ok, f"{row_count} rows in {elapsed}ms")
    step("Tool identified as mcp-clickhouse", mcp_result.get("tool") == "mcp-clickhouse")
except Exception as exc:
    step("MCP query", False, str(exc)[:120])
    mcp_result = None

# ─────────────────────────────────────────────────────────────
# Step 8: MarketAgent canonical scoring
# ─────────────────────────────────────────────────────────────
section("8. MarketAgent deterministic scoring")

if mcp_result and mcp_result.get("rows"):
    from cineyield.agents.scoring import score_campaigns

    ROOFTOP_SCENE = {"brand_safety_score": 96.0, "mood": "Dusk", "narrative_weight": "High"}
    ROOFTOP_OPP = {
        "category": "Consumer audio",
        "territories": ["US", "CA", "GB"],
        "screen_time_seconds": 26,
        "estimated_value_usd": 185000.0,
    }

    try:
        scored = score_campaigns(
            mcp_result["rows"],
            opportunity_category=ROOFTOP_OPP["category"],
            opportunity_territories=ROOFTOP_OPP["territories"],
            screen_time_seconds=ROOFTOP_OPP["screen_time_seconds"],
            estimated_value_usd=ROOFTOP_OPP["estimated_value_usd"],
            brand_safety_score=ROOFTOP_SCENE["brand_safety_score"],
            scene_mood=ROOFTOP_SCENE["mood"],
            scene_narrative_weight=ROOFTOP_SCENE["narrative_weight"],
        )
        unblocked = [s for s in scored if not s.is_blocked]
        blocked = [s for s in scored if s.is_blocked]

        step("Scoring produced ranked results", len(unblocked) > 0,
             f"{len(unblocked)} ranked, {len(blocked)} blocked")
        step("Results sorted by composite score",
             all(unblocked[i].composite >= unblocked[i+1].composite
                 for i in range(len(unblocked)-1)) if len(unblocked) > 1 else True)

        # Step 9: Aurelius is top candidate
        if unblocked:
            top = unblocked[0]
            is_aurelius = top.brand == "Aurelius Systems"
            step("Aurelius Systems is top unblocked candidate (data-driven)",
                 is_aurelius,
                 f"top={top.brand} score={top.composite:.1f}")
            if not is_aurelius:
                print(f"    Top 3 unblocked: {[s.brand for s in unblocked[:3]]}")
        else:
            step("Aurelius Systems top candidate", False, "No unblocked results")

        # Vortex/Stride should be blocked
        blocked_brands = {s.brand for s in blocked}
        step("Vortex Energy blocked (creative conflict)",
             "Vortex Energy" in blocked_brands)
        step("Stride Apparel blocked (category mismatch)",
             "Stride Apparel" in blocked_brands)

    except Exception as exc:
        step("Scoring", False, str(exc))
else:
    print(f"  {SKIP}  Scoring skipped — no MCP rows available")

# ─────────────────────────────────────────────────────────────
# Step 10: Sanitized AgentEvent
# ─────────────────────────────────────────────────────────────
section("10. Sanitized AgentEvent")

try:
    import uuid  # noqa: E402
    from datetime import datetime, timezone  # noqa: E402

    from cineyield.schemas.events import AgentEvent, AgentEventKind  # noqa: E402

    event = AgentEvent(
        event_id=str(uuid.uuid4()),
        agent_name="market_agent",
        kind=AgentEventKind.COMPLETED,
        tool_name="mcp-clickhouse",
        summary="27 campaigns scanned · 6 ranked · 2 blocked · 145ms",
        latency_ms=145,
        occurred_at=datetime.now(timezone.utc).isoformat(),
    )
    # Verify no secrets leak through the schema
    event_dict = event.model_dump()
    has_password = any("password" in str(v).lower() for v in event_dict.values())
    step("AgentEvent schema valid", True, f"kind={event.kind.value}")
    step("AgentEvent contains no password/secret fields", not has_password)
    step("AgentEvent tool_name is 'mcp-clickhouse'", event.tool_name == "mcp-clickhouse")

except Exception as exc:
    step("AgentEvent creation", False, str(exc))

# ─────────────────────────────────────────────────────────────
# Summary
# ─────────────────────────────────────────────────────────────
total = len(results)
passed = sum(1 for _, ok, _ in results if ok)
failed = total - passed

print(f"\n{'═'*60}")
print("  CineYield ClickHouse + MCP Verification")
print(f"  {passed}/{total} checks passed" + (f"  ({failed} FAILED)" if failed else ""))
print(f"{'═'*60}\n")

if failed:
    sys.exit(1)
