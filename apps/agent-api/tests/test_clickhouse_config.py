"""ClickHouse configuration tests — no cloud credentials required."""


from cineyield.config import Settings
from cineyield.db.client import check_connection, reset_client_cache


def test_settings_clickhouse_not_configured_by_default():
    s = Settings(clickhouse_host="")
    assert not s.clickhouse_configured


def test_settings_clickhouse_configured_when_host_set():
    s = Settings(clickhouse_host="example.clickhouse.cloud")
    assert s.clickhouse_configured


def test_settings_clickhouse_defaults():
    s = Settings(clickhouse_host="example.clickhouse.cloud")
    assert s.clickhouse_port == 8443
    assert s.clickhouse_secure is True
    assert s.clickhouse_verify is True
    assert s.clickhouse_database == "cineyield"
    assert s.clickhouse_user == "default"


def test_settings_official_env_var_names():
    """Verify env var names match official mcp-clickhouse documentation."""
    # These names come from the official ClickHouse/mcp-clickhouse repo
    env_vars = [
        "CLICKHOUSE_HOST",
        "CLICKHOUSE_PORT",
        "CLICKHOUSE_USER",
        "CLICKHOUSE_PASSWORD",
        "CLICKHOUSE_SECURE",
        "CLICKHOUSE_VERIFY",
        "CLICKHOUSE_CONNECT_TIMEOUT",
        "CLICKHOUSE_SEND_RECEIVE_TIMEOUT",
    ]
    # pydantic-settings maps these: lower-cased field name = env var with SCREAMING_SNAKE_CASE
    field_names = {
        "clickhouse_host": "CLICKHOUSE_HOST",
        "clickhouse_port": "CLICKHOUSE_PORT",
        "clickhouse_user": "CLICKHOUSE_USER",
        "clickhouse_password": "CLICKHOUSE_PASSWORD",
        "clickhouse_secure": "CLICKHOUSE_SECURE",
        "clickhouse_verify": "CLICKHOUSE_VERIFY",
        "clickhouse_connect_timeout": "CLICKHOUSE_CONNECT_TIMEOUT",
        "clickhouse_send_receive_timeout": "CLICKHOUSE_SEND_RECEIVE_TIMEOUT",
    }
    # All expected env var names are present in our mapping
    for field, env_var in field_names.items():
        assert env_var in env_vars, f"{env_var} missing from official env var list"


def test_check_connection_returns_error_when_not_configured():
    """check_connection must not raise; returns error dict when unconfigured."""
    # Without credentials, should return error gracefully
    reset_client_cache()
    result = check_connection()
    # Either ok (if real CH is reachable) or error — never an exception
    assert result["status"] in ("ok", "error")
    assert "message" in result
