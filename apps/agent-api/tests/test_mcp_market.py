"""MCP market tool tests.

Unit tests: no cloud credentials required.
Integration tests: require real ClickHouse + mcp-clickhouse (marked with @pytest.mark.integration).
Contest smoke test: fails intentionally if contest mode is on but MCP is unreachable.
"""

import pytest

from cineyield.agents.mcp_market import _mcp_clickhouse_executable, _parse_mcp_result
from cineyield.config import get_settings

# ─── Unit: MCP result parser ─────────────────────────────────────────────────

def test_parse_mcp_result_json_array():
    raw = '[{"id":"camp_001","brand":"Aurelius","campaign_name":"Focus"}]'
    result = _parse_mcp_result(raw)
    assert len(result) == 1
    assert result[0]["brand"] == "Aurelius"


def test_parse_mcp_result_empty():
    assert _parse_mcp_result("") == []
    assert _parse_mcp_result("   ") == []


def test_parse_mcp_result_single_json_object():
    raw = '{"id":"camp_001","brand":"Aurelius"}'
    result = _parse_mcp_result(raw)
    assert len(result) == 1


def test_parse_mcp_result_ndjson():
    raw = '{"id":"camp_001","brand":"Aurelius"}\n{"id":"camp_002","brand":"Aurora"}'
    result = _parse_mcp_result(raw)
    assert len(result) == 2


# ─── Unit: executable location ───────────────────────────────────────────────

def test_mcp_clickhouse_executable_found():
    """mcp-clickhouse must be installed in the current venv."""
    exe = _mcp_clickhouse_executable()
    assert exe
    assert "mcp-clickhouse" in exe


# ─── Unit: MCP configuration ─────────────────────────────────────────────────

def test_mcp_env_vars_use_official_names():
    """The env dict passed to mcp-clickhouse subprocess must use official variable names."""
    from cineyield.agents.mcp_market import _mcp_clickhouse_env
    env = _mcp_clickhouse_env()
    required_keys = [
        "CLICKHOUSE_HOST",
        "CLICKHOUSE_PORT",
        "CLICKHOUSE_USER",
        "CLICKHOUSE_PASSWORD",
        "CLICKHOUSE_SECURE",
        "CLICKHOUSE_VERIFY",
    ]
    for key in required_keys:
        assert key in env, f"Official env var {key!r} missing from mcp env"


# ─── Integration tests (require real ClickHouse + mcp-clickhouse) ────────────

@pytest.mark.integration
async def test_query_campaigns_via_mcp_real():
    """
    INTEGRATION: Requires CLICKHOUSE_HOST configured in .env.
    Verifies that a real mcp-clickhouse query returns campaign rows.
    """
    from cineyield.agents.mcp_market import query_campaigns_via_mcp

    if not get_settings().clickhouse_configured:
        pytest.skip("CLICKHOUSE_HOST not configured — skipping integration test")

    result = await query_campaigns_via_mcp()
    assert result["row_count"] > 0
    assert result["latency_ms"] > 0
    assert result["tool"] == "mcp-clickhouse"

    rows = result["rows"]
    first = rows[0]
    assert "brand" in first
    assert "campaign_name" in first


# ─── Contest smoke test ───────────────────────────────────────────────────────

@pytest.mark.contest
async def test_contest_mcp_reachable():
    """
    CONTEST SMOKE TEST: This test intentionally FAILS if mcp-clickhouse
    cannot reach ClickHouse. A silent fallback to fake data is not acceptable.

    Run with: pytest -m contest tests/test_mcp_market.py
    Expected result in contest mode: PASS (real connection) or FAIL (not connected).
    Never: PASS via fake data.
    """
    from cineyield.agents.mcp_market import query_campaigns_via_mcp

    assert get_settings().clickhouse_configured, (
        "CONTEST FAILURE: CLICKHOUSE_HOST is not configured. "
        "Set credentials in .env before running the contest smoke test."
    )

    result = await query_campaigns_via_mcp()

    assert result["row_count"] >= 27, (
        f"CONTEST FAILURE: Expected at least 27 seeded campaigns, got {result['row_count']}. "
        "Run: make db-seed to load seed data."
    )

    brands = {r.get("brand") for r in result["rows"]}
    assert "Aurelius Systems" in brands, (
        "CONTEST FAILURE: Canonical demo campaign 'Aurelius Systems' not found in ClickHouse. "
        "Run: make db-seed"
    )
