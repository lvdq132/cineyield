from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Service
    environment: str = "development"
    log_level: str = "INFO"
    api_version: str = "v1"

    # CORS — comma-separated origins
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:3000"

    # Google Cloud
    google_cloud_project: str = ""
    google_cloud_region: str = "us-central1"

    # Gemini
    gemini_model: str = "gemini-2.0-flash"
    google_api_key: str = ""

    # Generative media. Nano Banana 2 is global-only on Vertex AI; Veo 3.1
    # runs in us-central1. Keeping these separate from GEMINI_MODEL lets the
    # analysis model evolve without silently changing an approved media flow.
    nano_banana_model: str = "gemini-3.1-flash-image"
    nano_banana_region: str = "global"
    veo_model: str = "veo-3.1-generate-001"
    veo_region: str = "us-central1"

    # Google Cloud Storage
    gcs_bucket_name: str = ""

    # ClickHouse — official mcp-clickhouse variable names
    # See: https://github.com/ClickHouse/mcp-clickhouse
    clickhouse_host: str = ""
    clickhouse_port: int = 8443
    clickhouse_database: str = "cineyield"
    clickhouse_user: str = "default"
    clickhouse_password: str = ""
    clickhouse_secure: bool = True
    clickhouse_verify: bool = True
    clickhouse_connect_timeout: int = 30
    clickhouse_send_receive_timeout: int = 30

    # mcp-clickhouse auth (for HTTP/SSE transport; stdio needs no auth)
    # Set CLICKHOUSE_MCP_AUTH_DISABLED=true for local development only
    clickhouse_mcp_auth_disabled: bool = False
    clickhouse_mcp_auth_token: str = ""

    # Runtime mode: "development" (fixtures allowed) | "contest" (all real, no fallbacks)
    # Set CINEYIELD_MODE=contest to enable strict contest enforcement.
    cineyield_mode: str = "development"

    # Legacy alias — kept for backwards compatibility with test code.
    # Do not set both; prefer CINEYIELD_MODE=contest.
    contest_mode: bool = False

    @property
    def is_contest_mode(self) -> bool:
        """True when running in contest/judged mode. All integrations mandatory."""
        return self.cineyield_mode.lower() == "contest" or self.contest_mode

    @property
    def allowed_origins(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def gemini_configured(self) -> bool:
        return bool(self.google_api_key or self.google_cloud_project)

    @property
    def clickhouse_configured(self) -> bool:
        return bool(self.clickhouse_host)

    @property
    def gcs_configured(self) -> bool:
        return bool(self.gcs_bucket_name)


@lru_cache
def get_settings() -> Settings:
    return Settings()
