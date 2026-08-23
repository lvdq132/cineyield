"""Video ingest routes — upload, status, scene results.

In contest mode (CINEYIELD_MODE=contest) every step is mandatory:
Gemini, GCS, ClickHouse, and ADK orchestration must all succeed.
No fixture or fallback substitution is permitted.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from pydantic import BaseModel

from ...config import get_settings

router = APIRouter(prefix="/ingest", tags=["ingest"])

# In-memory job store (replaced with ClickHouse in production)
_jobs: dict[str, dict] = {}

SUPPORTED_MIME_TYPES = {
    "video/mp4", "video/quicktime", "video/avi",
    "video/webm", "video/x-matroska",
}
MAX_FILE_SIZE_MB = 500


class IngestJobResponse(BaseModel):
    job_id: str
    asset_id: str
    status: str
    filename: str
    size_bytes: int
    submitted_at: str
    message: str = ""


class JobStatusResponse(BaseModel):
    job_id: str
    asset_id: str
    status: str
    submitted_at: str
    completed_at: str | None = None
    error: str | None = None
    scene_analysis: dict | None = None


@router.post("/upload", response_model=IngestJobResponse, status_code=202)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: Annotated[UploadFile, File(description="Video file for scene analysis")],
) -> IngestJobResponse:
    """Upload a video clip for full ADK pipeline analysis.

    Returns a job_id for polling. The full pipeline runs asynchronously:
    SceneAgent (Gemini) → MarketAgent (mcp-clickhouse) →
    RightsAgent → CreativeGuardian → DealAgent.

    In CINEYIELD_MODE=contest all integrations are mandatory.
    """
    settings = get_settings()

    content_type = file.content_type or ""
    if content_type not in SUPPORTED_MIME_TYPES:
        raise HTTPException(
            status_code=415,
            detail=(
                f"Unsupported media type '{content_type}'. "
                f"Supported: {', '.join(sorted(SUPPORTED_MIME_TYPES))}"
            ),
        )

    data = await file.read()
    size_bytes = len(data)
    size_mb = size_bytes / (1024 * 1024)

    if size_mb > MAX_FILE_SIZE_MB:
        raise HTTPException(
            status_code=413,
            detail=f"File too large ({size_mb:.1f} MB). Maximum is {MAX_FILE_SIZE_MB} MB.",
        )

    job_id = f"job_{uuid.uuid4().hex[:16]}"
    asset_id = f"asset_{uuid.uuid4().hex[:12]}"
    now = datetime.now(timezone.utc).isoformat()

    _jobs[job_id] = {
        "job_id": job_id,
        "asset_id": asset_id,
        "status": "queued",
        "filename": file.filename or "upload.mp4",
        "size_bytes": size_bytes,
        "submitted_at": now,
        "completed_at": None,
        "error": None,
        "scene_analysis": None,
    }

    if settings.gemini_configured:
        background_tasks.add_task(_run_pipeline_job, job_id, data, content_type, asset_id)
        status = "queued"
        message = "Full ADK pipeline queued. Poll /status/{job_id} for results."
    elif settings.is_contest_mode:
        raise HTTPException(
            503,
            detail=(
                "CINEYIELD_MODE=contest requires Gemini. "
                "Set GOOGLE_API_KEY or GOOGLE_CLOUD_PROJECT + ADC."
            ),
        )
    else:
        _jobs[job_id]["status"] = "pending_credentials"
        status = "pending_credentials"
        message = (
            "Gemini is not configured. Set GOOGLE_API_KEY or "
            "GOOGLE_CLOUD_PROJECT + GEMINI_MODEL in .env to enable analysis."
        )

    return IngestJobResponse(
        job_id=job_id,
        asset_id=asset_id,
        status=status,
        filename=file.filename or "upload.mp4",
        size_bytes=size_bytes,
        submitted_at=now,
        message=message,
    )


@router.get("/status/{job_id}", response_model=JobStatusResponse)
async def get_job_status(job_id: str) -> JobStatusResponse:
    """Poll the status of a video analysis job."""
    job = _jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    return JobStatusResponse(
        job_id=job["job_id"],
        asset_id=job["asset_id"],
        status=job["status"],
        submitted_at=job["submitted_at"],
        completed_at=job.get("completed_at"),
        error=job.get("error"),
        scene_analysis=job.get("scene_analysis"),
    )


@router.get("/formats")
async def list_supported_formats() -> dict:
    """Return supported video formats and upload limits."""
    return {
        "supported_mime_types": sorted(SUPPORTED_MIME_TYPES),
        "max_file_size_mb": MAX_FILE_SIZE_MB,
        "note": "Files >100 MB are uploaded to Gemini File API automatically.",
    }


async def _run_pipeline_job(job_id: str, data: bytes, mime: str, asset_id: str) -> None:
    """Background task: run the full ADK pipeline on uploaded video bytes.

    Runs: SceneAgent → MarketAgent → RightsAgent → CreativeGuardian → DealAgent
    All results are persisted to ClickHouse within each pipeline tool.
    In contest mode, any failure propagates as a job failure (no fallback).
    """
    import tempfile
    from pathlib import Path

    _jobs[job_id]["status"] = "analyzing"
    ext = mime.split("/")[-1].replace("quicktime", "mov")
    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False) as tmp:
            tmp.write(data)
            tmp_path = tmp.name

        from ...agents.pipeline import run_pipeline

        result = await run_pipeline(
            video_input={
                "video_path": tmp_path,
                "asset_id": asset_id,
            },
        )

        scene = result.get("scene") or {}
        opportunities = result.get("opportunities") or []
        proposal = result.get("proposal") or {}

        # surface scene_id and primary opportunity_id for frontend navigation
        scene_id = scene.get("scene_id") or asset_id
        primary_opp = next(
            (o for o in opportunities if o.get("is_primary")),
            opportunities[0] if opportunities else {},
        )

        _jobs[job_id]["status"] = "completed"
        _jobs[job_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
        _jobs[job_id]["scene_analysis"] = {
            # Top-level fields the frontend reads
            "scene_id": scene_id,
            "asset_id": asset_id,
            # Full pipeline result for completeness
            "scene": scene,
            "opportunities": opportunities,
            "primary_opportunity_id": primary_opp.get("id"),
            "market_result": result.get("market_result"),
            "rights_decision": result.get("rights_decision"),
            "creative_decision": result.get("creative_decision"),
            "proposal_id": proposal.get("id"),
            "pipeline_version": result.get("pipeline_version"),
            "adk_used": result.get("adk_used", False),
            "total_latency_ms": result.get("total_latency_ms"),
        }

    except Exception as exc:
        _jobs[job_id]["status"] = "failed"
        _jobs[job_id]["completed_at"] = datetime.now(timezone.utc).isoformat()
        _jobs[job_id]["error"] = str(exc)
        import logging
        logging.getLogger(__name__).error("Pipeline job %s failed: %s", job_id, exc)
    finally:
        if tmp_path:
            Path(tmp_path).unlink(missing_ok=True)
