"""ClickHouse MCP integration boundary for the Market Agent.

Uses the official mcp-clickhouse server via stdio transport.
This is the REAL integration path — never replaced with local fake data.

The MCP server is spawned as a subprocess using the installed mcp-clickhouse binary.
Campaign data flows: MarketAgent → mcp-clickhouse → ClickHouse → raw rows → deterministic scoring.
"""
from __future__ import annotations

import logging
import os
import shutil
import sys
import time
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from ..config import get_settings

logger = logging.getLogger(__name__)

# MCP tool name exposed by mcp-clickhouse
_RUN_QUERY_TOOL = "run_query"

# SQL query: find active campaigns compatible with a Consumer Audio headphones opportunity.
# Parameterized via Python f-string after validation — no user input reaches this query.
_CAMPAIGN_QUERY = """
SELECT
    id,
    brand,
    campaign_name,
    product_line,
    budget_min_usd,
    budget_max_usd,
    target_categories,
    excluded_contexts,
    territories,
    visibility_seconds_min,
    visibility_seconds_max
FROM cineyield.brand_campaigns
WHERE is_active = true
ORDER BY budget_max_usd DESC
LIMIT 100
"""


def _mcp_clickhouse_env() -> dict[str, str]:
    """Build env for the mcp-clickhouse subprocess from current settings."""
    s = get_settings()
    env = {
        **os.environ,
        "CLICKHOUSE_HOST": s.clickhouse_host,
        "CLICKHOUSE_PORT": str(s.clickhouse_port),
        "CLICKHOUSE_USER": s.clickhouse_user,
        "CLICKHOUSE_PASSWORD": s.clickhouse_password,
        "CLICKHOUSE_SECURE": "true" if s.clickhouse_secure else "false",
        "CLICKHOUSE_VERIFY": "true" if s.clickhouse_verify else "false",
        "CLICKHOUSE_CONNECT_TIMEOUT": str(s.clickhouse_connect_timeout),
        "CLICKHOUSE_SEND_RECEIVE_TIMEOUT": str(s.clickhouse_send_receive_timeout),
    }
    if s.clickhouse_mcp_auth_disabled:
        env["CLICKHOUSE_MCP_AUTH_DISABLED"] = "true"
    elif s.clickhouse_mcp_auth_token:
        env["CLICKHOUSE_MCP_AUTH_TOKEN"] = s.clickhouse_mcp_auth_token
    return env


def _mcp_clickhouse_executable() -> str:
    """Locate the mcp-clickhouse binary in the current venv or PATH."""
    # Check venv first
    venv_bin = os.path.join(sys.prefix, "bin", "mcp-clickhouse")
    if os.path.isfile(venv_bin):
        return venv_bin
    # Fall back to PATH
    found = shutil.which("mcp-clickhouse")
    if found:
        return found
    raise RuntimeError(
        "mcp-clickhouse executable not found. "
        "Run: pip install mcp-clickhouse"
    )


async def query_campaigns_via_mcp(sql: str = _CAMPAIGN_QUERY) -> dict[str, Any]:
    """
    Execute a SQL query against ClickHouse via the official mcp-clickhouse MCP server.

    Returns:
        {
            "rows": list[dict],      # parsed campaign rows
            "row_count": int,
            "latency_ms": int,
            "tool": "mcp-clickhouse",
            "tool_name": "run_query",
        }

    Raises RuntimeError if ClickHouse or mcp-clickhouse is not reachable.
    """
    settings = get_settings()
    if not settings.clickhouse_configured:
        raise RuntimeError(
            "ClickHouse not configured. "
            "Set CLICKHOUSE_HOST (and credentials) in .env."
        )

    executable = _mcp_clickhouse_executable()
    env = _mcp_clickhouse_env()

    server_params = StdioServerParameters(
        command=executable,
        args=[],
        env=env,
    )

    t_start = time.monotonic()

    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()

            result = await session.call_tool(
                _RUN_QUERY_TOOL,
                arguments={"query": sql},
            )

    latency_ms = int((time.monotonic() - t_start) * 1000)

    # Parse result content — mcp-clickhouse returns JSON-encoded table text
    raw_text = ""
    for block in result.content:
        if hasattr(block, "text"):
            raw_text += block.text

    rows = _parse_mcp_result(raw_text)
    logger.info(
        "mcp-clickhouse query completed: %d rows in %dms",
        len(rows),
        latency_ms,
    )

    return {
        "rows": rows,
        "row_count": len(rows),
        "latency_ms": latency_ms,
        "tool": "mcp-clickhouse",
        "tool_name": _RUN_QUERY_TOOL,
    }


def _parse_mcp_result(raw: str) -> list[dict[str, Any]]:
    """Parse the tabular/JSON output returned by mcp-clickhouse run_query.

    mcp-clickhouse returns columnar JSON:
        {"columns": ["col1", "col2", ...], "rows": [[v1, v2, ...], ...]}

    Fallback paths handle older NDJSON and plain JSON array formats.
    """
    import json

    raw = raw.strip()
    if not raw:
        return []

    try:
        parsed = json.loads(raw)
        # Canonical mcp-clickhouse format: columnar {columns, rows}
        if isinstance(parsed, dict) and "columns" in parsed and "rows" in parsed:
            columns = parsed["columns"]
            return [dict(zip(columns, row)) for row in parsed["rows"]]
        # Plain JSON array of objects
        if isinstance(parsed, list):
            return parsed
        # Single JSON object
        return [parsed]
    except json.JSONDecodeError:
        pass

    # Fall back: newline-delimited JSON objects
    rows = []
    for line in raw.splitlines():
        line = line.strip()
        if line:
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError:
                logger.debug("Skipping unparseable MCP result line: %r", line)
    return rows
