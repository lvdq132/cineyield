"""Full pipeline route — VIDEO → GCS → Gemini → ClickHouse → proposal."""
from __future__ import annotations

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...config import get_settings

router = APIRouter(prefix="/pipeline", tags=["pipeline"])


class PipelineRequest(BaseModel):
    gcs_uri: str = ""
    video_path: str = ""
    asset_id: str = ""


@router.post("/run")
async def run_pipeline(body: PipelineRequest) -> dict:
    """Run the full CineYield agentic pipeline for a video asset.

    Executes: SceneAgent (Gemini) → MarketAgent (mcp-clickhouse) →
    RightsAgent → CreativeGuardian → DealAgent → Proposal
    """
    settings = get_settings()
    if not settings.gemini_configured:
        raise HTTPException(
            503,
            detail=(
                "Gemini is not configured. Set GOOGLE_API_KEY or GOOGLE_CLOUD_PROJECT in .env. "
                "Then run: gcloud auth application-default login"
            ),
        )
    if not body.gcs_uri and not body.video_path:
        raise HTTPException(400, detail="Provide gcs_uri or video_path")

    from ...agents.pipeline import run_pipeline as _run

    result = await _run(
        video_input={
            "gcs_uri": body.gcs_uri,
            "video_path": body.video_path,
            "asset_id": body.asset_id,
        },
    )
    return result


@router.get("/status")
async def pipeline_status() -> dict:
    """Report which pipeline components are configured and ready."""
    settings = get_settings()
    return {
        "gemini": settings.gemini_configured,
        "gcs": settings.gcs_configured,
        "clickhouse": settings.clickhouse_configured,
        "model": settings.gemini_model,
        "project": bool(settings.google_cloud_project),
        "ready": settings.gemini_configured and settings.clickhouse_configured,
        "mode": settings.cineyield_mode,
    }
