-- CineYield: Dedicated read-only MCP runtime user
-- Run as admin after 00_init_schema.sql + 01_seed.sql.
-- This user is ONLY for the runtime Market Agent (mcp-clickhouse).
-- Do NOT use the admin/default user for MCP at contest time.
--
-- Usage:
--   Replace {MCP_PASSWORD} with a generated secret before running.
--   Then set CLICKHOUSE_USER=cineyield_mcp and CLICKHOUSE_PASSWORD={MCP_PASSWORD}
--   in the runtime .env for mcp-clickhouse.
--
-- Generate a password: openssl rand -hex 32

-- Create dedicated MCP runtime user
CREATE USER IF NOT EXISTS cineyield_mcp
    IDENTIFIED WITH sha256_password BY '{MCP_PASSWORD}';

-- Market Agent reads: campaign inventory, opportunities, scene data, rights rules
GRANT SELECT ON cineyield.brand_campaigns       TO cineyield_mcp;
GRANT SELECT ON cineyield.placement_opportunities TO cineyield_mcp;
GRANT SELECT ON cineyield.scenes                TO cineyield_mcp;
GRANT SELECT ON cineyield.detected_objects      TO cineyield_mcp;
GRANT SELECT ON cineyield.rights_rules          TO cineyield_mcp;
GRANT SELECT ON cineyield.match_events          TO cineyield_mcp;
GRANT SELECT ON cineyield.content_assets        TO cineyield_mcp;

-- Market Agent writes: match events + agent events (observability)
GRANT INSERT ON cineyield.match_events          TO cineyield_mcp;
GRANT INSERT ON cineyield.agent_events          TO cineyield_mcp;

-- Explicitly NO: CREATE, ALTER, DROP, TRUNCATE, system tables, other databases
-- Explicitly NO: revenue_events, proposals (written by admin pipeline only)

-- Verify grants (run after applying):
-- SHOW GRANTS FOR cineyield_mcp;
