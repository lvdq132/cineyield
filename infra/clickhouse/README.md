# CineYield ClickHouse Setup

## Quick start (ClickHouse Cloud)

1. Create a free ClickHouse Cloud instance at https://clickhouse.cloud
2. Copy credentials into `apps/agent-api/.env`:

```
CLICKHOUSE_HOST=your-instance.clickhouse.cloud
CLICKHOUSE_PORT=8443
CLICKHOUSE_USER=default
CLICKHOUSE_PASSWORD=your-password
CLICKHOUSE_SECURE=true
CLICKHOUSE_VERIFY=true
```

3. Initialize schema:

```bash
cd apps/agent-api
make db-init    # applies infra/clickhouse/00_init_schema.sql
make db-seed    # applies infra/clickhouse/01_seed.sql
make db-health  # verifies connection + table counts
```

## Environment variables (official mcp-clickhouse names)

| Variable | Description | Example |
|---|---|---|
| `CLICKHOUSE_HOST` | Host without protocol | `abc123.clickhouse.cloud` |
| `CLICKHOUSE_PORT` | HTTP port | `8443` (cloud) / `8123` (local) |
| `CLICKHOUSE_USER` | Username | `default` |
| `CLICKHOUSE_PASSWORD` | Password | your password |
| `CLICKHOUSE_SECURE` | Use TLS | `true` for cloud |
| `CLICKHOUSE_VERIFY` | Verify TLS cert | `true` for cloud |
| `CLICKHOUSE_CONNECT_TIMEOUT` | Seconds | `30` |
| `CLICKHOUSE_SEND_RECEIVE_TIMEOUT` | Seconds | `30` |

## Schema overview

| Table | Purpose |
|---|---|
| `content_assets` | Video/content catalog |
| `scenes` | Gemini scene intelligence output |
| `detected_objects` | Objects identified per scene |
| `placement_opportunities` | Commercial opportunities |
| `brand_campaigns` | Brand campaign inventory (Market Agent source) |
| `rights_rules` | Deterministic territory clearance rules |
| `match_events` | Campaign match results |
| `proposals` | Qualified proposals |
| `agent_events` | Sanitized agent execution log |
| `revenue_events` | Approval and revenue records |

## Local ClickHouse (Docker)

```bash
docker run -d --name cineyield-clickhouse \
  -p 8123:8123 -p 9000:9000 \
  -e CLICKHOUSE_DB=cineyield \
  clickhouse/clickhouse-server
```

Then set: `CLICKHOUSE_HOST=localhost`, `CLICKHOUSE_PORT=8123`, `CLICKHOUSE_SECURE=false`
