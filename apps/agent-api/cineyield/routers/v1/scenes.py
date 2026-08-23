"""Scene intelligence routes."""
from fastapi import APIRouter, HTTPException

from ...config import get_settings
from ...db import repository

router = APIRouter(prefix="/scenes", tags=["scenes"])


@router.get("/{scene_id}")
async def get_scene(scene_id: str) -> dict:
    settings = get_settings()
    if not settings.clickhouse_configured:
        raise HTTPException(503, detail="ClickHouse not configured")
    scene = repository.get_scene(scene_id)
    if scene is None:
        raise HTTPException(404, detail=f"Scene {scene_id!r} not found")
    return scene


@router.get("/{scene_id}/opportunities")
async def get_scene_opportunities(scene_id: str) -> dict:
    settings = get_settings()
    if not settings.clickhouse_configured:
        raise HTTPException(503, detail="ClickHouse not configured")
    items = repository.get_scene_opportunities(scene_id)
    return {"scene_id": scene_id, "items": items, "total": len(items)}
