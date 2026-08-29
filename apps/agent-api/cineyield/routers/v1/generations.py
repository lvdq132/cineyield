"""Producer-controlled Nano Banana and Veo branded-media workflow."""
from __future__ import annotations

import uuid
from typing import Literal

from fastapi import APIRouter, Header, HTTPException, Response
from pydantic import BaseModel, Field

from ...config import get_settings
from ...db import repository
from ...services.generative_media import (
    CREATIVE_GUARDRAILS,
    build_placement_instructions,
    generate_branded_frame,
    poll_replacement_video,
    start_replacement_video,
)
from .deals import _resolve_deal_id

router = APIRouter(prefix="/generations", tags=["generations"])


class GenerateImageRequest(BaseModel):
    placement_instructions: str = Field(default="", max_length=1200)


class GenerationDecisionRequest(BaseModel):
    decision: Literal["approve", "reject"]
    note: str = Field(default="", max_length=1000)


def _require_context(proposal_id: str) -> tuple[str, dict]:
    if not get_settings().clickhouse_configured:
        raise HTTPException(503, detail="ClickHouse not configured")
    resolved = _resolve_deal_id(proposal_id)
    context = repository.get_generation_context(resolved)
    if not context:
        raise HTTPException(404, detail=f"Proposal {resolved!r} has no generation context")
    if not context.get("media") or not context["media"].get("frame_uri"):
        raise HTTPException(
            409,
            detail=(
                "This proposal is not attached to an uploaded source frame. "
                "Upload and analyze the cut before generating branded media."
            ),
        )
    return resolved, context


def _public_job(job: dict | None) -> dict | None:
    if not job:
        return None
    job_id = str(job["id"])
    result = dict(job)
    result["media_url"] = (
        f"/api/v1/generations/jobs/{job_id}/media"
        if job.get("status") == "COMPLETED" and job.get("output_uri")
        else None
    )
    result.pop("source_video_uri", None)
    result.pop("source_frame_uri", None)
    result.pop("output_uri", None)
    result.pop("operation_name", None)
    return result


def _refresh_video_job(job: dict) -> dict:
    if job.get("kind") != "VIDEO" or job.get("status") != "PROCESSING":
        return job
    operation_name = str(job.get("operation_name") or "")
    if not operation_name:
        return job
    status, output_uri, error = poll_replacement_video(operation_name)
    if status == "PROCESSING":
        return job
    updated = {
        **job,
        "status": status,
        "output_uri": output_uri or "",
        "error": error or "",
    }
    repository.write_generation_job(updated)
    repository.write_agent_event(
        agent_name="veo_generation",
        kind="completed" if status == "COMPLETED" else "failed",
        summary=(
            f"Veo replacement clip {job['id']} completed"
            if status == "COMPLETED"
            else f"Veo replacement clip {job['id']} failed: {error}"
        ),
        asset_id=None,
        scene_id=job.get("scene_id"),
        opportunity_id=job.get("opportunity_id"),
        campaign_id=job.get("campaign_id"),
        tool_name=get_settings().veo_model,
        success=status == "COMPLETED",
    )
    return repository.get_generation_job(str(job["id"])) or updated


@router.get("/proposals/{proposal_id}")
async def get_generation_workflow(proposal_id: str) -> dict:
    resolved, context = _require_context(proposal_id)
    jobs = repository.list_generation_jobs(resolved)
    refreshed: list[dict] = []
    for job in jobs:
        refreshed.append(_refresh_video_job(job))
    latest_image = next((job for job in refreshed if job.get("kind") == "IMAGE"), None)
    approved_image = next(
        (
            job for job in refreshed
            if job.get("kind") == "IMAGE"
            and job.get("status") == "COMPLETED"
            and job.get("decision") == "APPROVED"
        ),
        None,
    )
    latest_video = next((job for job in refreshed if job.get("kind") == "VIDEO"), None)
    deal_approved = str(context.get("workflow_state")) == "APPROVED"
    scene_id = str(context["scene_id"])
    return {
        "proposal_id": resolved,
        "deal_approved": deal_approved,
        "scene_id": scene_id,
        "sponsor": context.get("brand_name"),
        "product": context.get("product_line"),
        "original_frame_url": f"/api/v1/scenes/{scene_id}/media/frame",
        "original_video_url": f"/api/v1/scenes/{scene_id}/media/segment",
        "creative_guardrails": CREATIVE_GUARDRAILS,
        "latest_image": _public_job(latest_image),
        "approved_image": _public_job(approved_image),
        "latest_video": _public_job(latest_video),
        "video_unlocked": bool(deal_approved and approved_image),
    }


@router.post("/proposals/{proposal_id}/image", status_code=201)
async def create_branded_frame(proposal_id: str, body: GenerateImageRequest) -> dict:
    resolved, context = _require_context(proposal_id)
    if str(context.get("workflow_state")) != "APPROVED":
        raise HTTPException(409, detail="Approve the commercial proposal before generating media")
    prior_images = [
        job for job in repository.list_generation_jobs(resolved)
        if job.get("kind") == "IMAGE"
    ]
    generation_number = len(prior_images) + 1
    generation_id = f"img_{uuid.uuid4().hex[:16]}"
    instructions = build_placement_instructions(context, body.placement_instructions)
    base_job = {
        "id": generation_id,
        "proposal_id": resolved,
        "scene_id": context["scene_id"],
        "opportunity_id": context["opportunity_id"],
        "campaign_id": context["campaign_id"],
        "kind": "IMAGE",
        "status": "PROCESSING",
        "decision": "PENDING",
        "model": get_settings().nano_banana_model,
        "placement_instructions": instructions,
        "creative_guardrails": CREATIVE_GUARDRAILS,
        "source_video_uri": context["media"].get("segment_video_uri", ""),
        "source_frame_uri": context["media"].get("frame_uri", ""),
        "generation_number": generation_number,
    }
    repository.write_generation_job(base_job)
    try:
        output_uri, prompt = generate_branded_frame(
            context,
            placement_instructions=instructions,
            generation_id=generation_id,
            generation_number=generation_number,
        )
        repository.write_generation_job({
            **base_job,
            "status": "COMPLETED",
            "output_uri": output_uri,
            "prompt": prompt,
        })
        repository.write_agent_event(
            agent_name="nano_banana_generation",
            kind="completed",
            summary=f"Branded reference frame {generation_id} generated for {context['brand_name']}",
            scene_id=context["scene_id"],
            opportunity_id=context["opportunity_id"],
            campaign_id=context["campaign_id"],
            tool_name=get_settings().nano_banana_model,
            success=True,
        )
    except Exception as exc:
        repository.write_generation_job({
            **base_job,
            "status": "FAILED",
            "error": str(exc),
        })
        raise HTTPException(502, detail=f"Nano Banana generation failed: {exc}") from exc
    return _public_job(repository.get_generation_job(generation_id)) or {}


@router.post("/jobs/{job_id}/decision")
async def decide_generation(job_id: str, body: GenerationDecisionRequest) -> dict:
    job = repository.get_generation_job(job_id)
    if not job:
        raise HTTPException(404, detail=f"Generation {job_id!r} not found")
    if job.get("status") != "COMPLETED":
        raise HTTPException(409, detail="Only a completed generation can be approved or rejected")
    decision = "APPROVED" if body.decision == "approve" else "REJECTED"
    repository.write_generation_job({**job, "decision": decision})
    repository.write_agent_event(
        agent_name="producer",
        kind=f"generation_{body.decision}",
        summary=f"{job['kind']} generation {job_id} {decision.lower()}. Note: {body.note}",
        scene_id=job.get("scene_id"),
        opportunity_id=job.get("opportunity_id"),
        campaign_id=job.get("campaign_id"),
        success=body.decision == "approve",
    )
    return _public_job(repository.get_generation_job(job_id)) or {}


@router.post("/proposals/{proposal_id}/video", status_code=202)
async def create_replacement_video(proposal_id: str) -> dict:
    resolved, context = _require_context(proposal_id)
    if str(context.get("workflow_state")) != "APPROVED":
        raise HTTPException(409, detail="Approve the commercial proposal first")
    approved_image = repository.get_latest_generation(
        resolved, kind="IMAGE", decision="APPROVED"
    )
    if not approved_image or approved_image.get("status") != "COMPLETED":
        raise HTTPException(409, detail="Approve a branded reference frame first")
    prior_videos = [
        job for job in repository.list_generation_jobs(resolved)
        if job.get("kind") == "VIDEO"
    ]
    generation_id = f"vid_{uuid.uuid4().hex[:16]}"
    base_job = {
        "id": generation_id,
        "proposal_id": resolved,
        "scene_id": context["scene_id"],
        "opportunity_id": context["opportunity_id"],
        "campaign_id": context["campaign_id"],
        "kind": "VIDEO",
        "status": "PROCESSING",
        "decision": "PENDING",
        "model": get_settings().veo_model,
        "placement_instructions": approved_image.get("placement_instructions", ""),
        "creative_guardrails": CREATIVE_GUARDRAILS,
        "source_video_uri": context["media"].get("segment_video_uri", ""),
        "source_frame_uri": approved_image.get("output_uri", ""),
        "generation_number": len(prior_videos) + 1,
    }
    repository.write_generation_job(base_job)
    try:
        operation_name, prompt = start_replacement_video(
            context,
            approved_frame_uri=str(approved_image["output_uri"]),
            placement_instructions=str(approved_image.get("placement_instructions") or ""),
            generation_id=generation_id,
        )
        repository.write_generation_job({
            **base_job,
            "prompt": prompt,
            "operation_name": operation_name,
        })
        repository.write_agent_event(
            agent_name="veo_generation",
            kind="started",
            summary=f"Veo replacement clip {generation_id} started from approved frame {approved_image['id']}",
            scene_id=context["scene_id"],
            opportunity_id=context["opportunity_id"],
            campaign_id=context["campaign_id"],
            tool_name=get_settings().veo_model,
            success=True,
        )
    except Exception as exc:
        repository.write_generation_job({**base_job, "status": "FAILED", "error": str(exc)})
        raise HTTPException(502, detail=f"Veo generation failed to start: {exc}") from exc
    return _public_job(repository.get_generation_job(generation_id)) or {}


@router.get("/jobs/{job_id}")
async def get_generation_job(job_id: str) -> dict:
    job = repository.get_generation_job(job_id)
    if not job:
        raise HTTPException(404, detail=f"Generation {job_id!r} not found")
    job = _refresh_video_job(job)
    return _public_job(job) or {}


@router.get("/jobs/{job_id}/media")
async def get_generation_media(
    job_id: str,
    range_header: str | None = Header(default=None, alias="Range"),
) -> Response:
    job = repository.get_generation_job(job_id)
    if not job or job.get("status") != "COMPLETED" or not job.get("output_uri"):
        raise HTTPException(404, detail="Generation media is not available")
    from ...gcs import download_media_bytes, get_media_metadata

    uri = str(job["output_uri"])
    metadata = get_media_metadata(uri)
    total = int(metadata["size"])
    content_type = str(metadata.get("content_type") or (
        "image/png" if job.get("kind") == "IMAGE" else "video/mp4"
    ))
    headers = {"Accept-Ranges": "bytes", "Cache-Control": "private, max-age=300"}
    if not range_header or not range_header.startswith("bytes="):
        data = download_media_bytes(uri)
        headers["Content-Length"] = str(len(data))
        return Response(content=data, media_type=content_type, headers=headers)
    try:
        raw_start, raw_end = range_header[6:].split("-", 1)
        start = int(raw_start) if raw_start else 0
        end = int(raw_end) if raw_end else min(total - 1, start + 2_000_000)
        end = min(end, total - 1)
        if start < 0 or start >= total or end < start:
            raise ValueError
    except ValueError as exc:
        raise HTTPException(416, detail="Invalid byte range") from exc
    data = download_media_bytes(uri, start=start, end=end)
    headers.update({
        "Content-Range": f"bytes {start}-{end}/{total}",
        "Content-Length": str(len(data)),
    })
    return Response(status_code=206, content=data, media_type=content_type, headers=headers)
