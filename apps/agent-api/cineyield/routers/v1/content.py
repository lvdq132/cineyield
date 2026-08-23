"""Content asset routes — real ClickHouse-backed content library."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException

from ...config import get_settings
from ...db import repository
from ...schemas.content import ContentAsset, ContentListResponse

router = APIRouter(prefix="/content", tags=["content"])


def _serialize_asset(row: dict[str, Any], scenes: list[dict[str, Any]]) -> dict[str, Any]:
    row = dict(row)
    if hasattr(row.get("updated_at"), "isoformat"):
        row["updated_at"] = row["updated_at"].isoformat()
    row["scenes"] = scenes
    return row


@router.get("", response_model=ContentListResponse)
async def list_content() -> ContentListResponse:
    settings = get_settings()
    if not settings.clickhouse_configured:
        raise HTTPException(503, detail="ClickHouse not configured")
    rows = repository.list_content_assets()
    items = [
        ContentAsset(**_serialize_asset(row, repository.get_scenes_for_asset(row["id"])))
        for row in rows
    ]
    return ContentListResponse(items=items, total=len(items))


@router.get("/{asset_id}", response_model=ContentAsset)
async def get_content(asset_id: str) -> ContentAsset:
    settings = get_settings()
    if not settings.clickhouse_configured:
        raise HTTPException(503, detail="ClickHouse not configured")
    row = repository.get_content_asset(asset_id)
    if row is None:
        raise HTTPException(404, detail=f"Content asset {asset_id!r} not found")
    scenes = repository.get_scenes_for_asset(asset_id)
    return ContentAsset(**_serialize_asset(row, scenes))
