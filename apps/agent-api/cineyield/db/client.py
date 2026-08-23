"""ClickHouse connection client using clickhouse-connect."""
from __future__ import annotations

import logging
from functools import lru_cache
from typing import Any

import clickhouse_connect
from clickhouse_connect.driver.client import Client

from ..config import get_settings

logger = logging.getLogger(__name__)


def _build_client(database: str | None = None) -> Client:
    settings = get_settings()
    if not settings.clickhouse_configured:
        raise RuntimeError(
            "ClickHouse is not configured. "
            "Set CLICKHOUSE_HOST in .env before connecting."
        )
    return clickhouse_connect.get_client(
        host=settings.clickhouse_host,
        port=settings.clickhouse_port,
        username=settings.clickhouse_user,
        password=settings.clickhouse_password,
        database=database if database is not None else settings.clickhouse_database,
        secure=settings.clickhouse_secure,
        verify=settings.clickhouse_verify,
        connect_timeout=settings.clickhouse_connect_timeout,
        send_receive_timeout=settings.clickhouse_send_receive_timeout,
    )


def get_bootstrap_client() -> Client:
    """Connect to the 'default' system database — used for CREATE DATABASE."""
    return _build_client(database="default")


@lru_cache(maxsize=1)
def get_clickhouse_client() -> Client:
    return _build_client()


def reset_client_cache() -> None:
    """Clear the cached client — used in tests."""
    get_clickhouse_client.cache_clear()


def check_connection() -> dict[str, Any]:
    """Verify ClickHouse connectivity. Returns status dict without raising."""
    try:
        client = get_clickhouse_client()
        result = client.query("SELECT 1 AS ok")
        row = result.first_row
        if row and row[0] == 1:
            return {"status": "ok", "message": "Connected"}
        return {"status": "error", "message": "Unexpected query result"}
    except Exception as exc:
        logger.warning("ClickHouse health check failed: %s", exc)
        return {"status": "error", "message": str(exc)}
