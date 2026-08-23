from fastapi import APIRouter
from pydantic import BaseModel

from ..config import get_settings
from ..db.client import check_connection

router = APIRouter(tags=["health"])


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


class ReadinessResponse(BaseModel):
    status: str
    checks: dict[str, str]


@router.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    return HealthResponse(status="ok", service="cineyield-agent-api", version="0.1.0")


@router.get("/ready", response_model=ReadinessResponse)
async def ready() -> ReadinessResponse:
    settings = get_settings()
    checks: dict[str, str] = {"api": "ok"}

    checks["gemini"] = "configured" if settings.gemini_configured else "not_configured"
    checks["gcs"] = "configured" if settings.gcs_configured else "not_configured"

    if settings.clickhouse_configured:
        result = check_connection()
        checks["clickhouse"] = result["status"]
    else:
        checks["clickhouse"] = "not_configured"

    # "ok" = API is alive. "degraded" = a configured service is erroring.
    # Unconfigured optional services (gemini, gcs, clickhouse) don't degrade readiness.
    overall = "ok" if all(v != "error" for v in checks.values()) else "degraded"
    return ReadinessResponse(status=overall, checks=checks)
