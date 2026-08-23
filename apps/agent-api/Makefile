.PHONY: install dev test test-unit test-integration test-contest lint format typecheck clean \
        db-init db-seed db-health mcp-health clickhouse-verify

VENV := .venv
PYTHON := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
PYTEST := $(VENV)/bin/pytest
RUFF := $(VENV)/bin/ruff
MYPY := $(VENV)/bin/mypy
UVICORN := $(VENV)/bin/uvicorn

INFRA := ../../infra/clickhouse

install:
	python3 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements-dev.txt

dev:
	$(UVICORN) main:app --reload --host 0.0.0.0 --port 8000

# Unit tests only (no cloud credentials required)
test-unit:
	$(PYTEST) tests/ -v -m "not integration and not contest"

# All tests including integration (requires CLICKHOUSE_HOST in .env)
test-integration:
	$(PYTEST) tests/ -v -m integration

# Contest smoke test — FAILS intentionally if MCP is not reachable
test-contest:
	$(PYTEST) tests/test_mcp_market.py -v -m contest

# Default test target: unit tests only
test: test-unit

lint:
	$(RUFF) check cineyield/ tests/ main.py

format:
	$(RUFF) format cineyield/ tests/ main.py

typecheck:
	$(MYPY) cineyield/ main.py

clean:
	rm -rf $(VENV) __pycache__ .pytest_cache .mypy_cache .ruff_cache

# ─── ClickHouse ───────────────────────────────────────────────

# Initialize schema (requires CLICKHOUSE_HOST in .env)
db-init:
	$(PYTHON) -c "from cineyield.db.repository import apply_sql_file; \
		apply_sql_file('$(INFRA)/00_init_schema.sql'); \
		print('Schema initialized')"

# Seed demo data
db-seed:
	$(PYTHON) -c "from cineyield.db.repository import apply_sql_file; \
		apply_sql_file('$(INFRA)/01_seed.sql'); \
		print('Seed data loaded')"

# Health check — verifies real connection
db-health:
	$(PYTHON) -c "from cineyield.db.client import check_connection; \
		import json; result = check_connection(); \
		print(json.dumps(result, indent=2)); \
		exit(0 if result['status'] == 'ok' else 1)"

# MCP health — verifies mcp-clickhouse can query ClickHouse
mcp-health:
	$(PYTHON) -c "import asyncio; \
		from cineyield.agents.mcp_market import query_campaigns_via_mcp; \
		result = asyncio.run(query_campaigns_via_mcp()); \
		print(f'mcp-clickhouse: {result[\"row_count\"]} rows in {result[\"latency_ms\"]}ms')"

# Full end-to-end verification (run after filling in .env credentials)
# Validates: env vars → connectivity → schema → seed counts → MCP query → scoring → Aurelius top match
clickhouse-verify:
	$(PYTHON) scripts/clickhouse_verify.py
