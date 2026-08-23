"""CineYield Agent API — FastAPI application entry point."""
import logging
import os

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from cineyield.config import get_settings
from cineyield.middleware.correlation import CorrelationIDMiddleware
from cineyield.routers.health import router as health_router
from cineyield.routers.v1 import router as v1_router

settings = get_settings()

# Propagate Vertex AI settings to os.environ so ADK/google-genai can read them.
# pydantic-settings loads .env into Settings but external SDKs read os.environ directly.
if settings.google_cloud_project:
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", settings.google_cloud_project)
if settings.google_cloud_region:
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", settings.google_cloud_region)
    os.environ.setdefault("GOOGLE_CLOUD_REGION", settings.google_cloud_region)
os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "1")

logging.basicConfig(level=getattr(logging, settings.log_level, logging.INFO))
logger = logging.getLogger("cineyield")

app = FastAPI(
    title="CineYield Agent API",
    description="Agentic product-placement operating system for entertainment.",
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(CorrelationIDMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(v1_router)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", None)
    logger.exception("Unhandled error", extra={"correlation_id": correlation_id})
    return JSONResponse(
        status_code=500,
        content={
            "error": "internal_server_error",
            "message": str(exc) if settings.environment == "development" else "An unexpected error occurred.",
            "correlation_id": correlation_id,
        },
    )
