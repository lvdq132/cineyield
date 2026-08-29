"""Scene intelligence and private scene-media routes."""
from fastapi import APIRouter, Header, HTTPException, Response

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
    if scene.get("media"):
        scene["media"] = {
            **scene["media"],
            "frame_url": f"/api/v1/scenes/{scene_id}/media/frame",
            "segment_url": f"/api/v1/scenes/{scene_id}/media/segment",
            "source_url": f"/api/v1/scenes/{scene_id}/media/source",
        }
    return scene


@router.get("/{scene_id}/opportunities")
async def get_scene_opportunities(scene_id: str) -> dict:
    settings = get_settings()
    if not settings.clickhouse_configured:
        raise HTTPException(503, detail="ClickHouse not configured")
    items = repository.get_scene_opportunities(scene_id)
    return {"scene_id": scene_id, "items": items, "total": len(items)}


@router.get("/{scene_id}/media/{media_kind}")
async def get_scene_media(
    scene_id: str,
    media_kind: str,
    range_header: str | None = Header(default=None, alias="Range"),
) -> Response:
    """Stream the private original frame/segment without making GCS public."""
    media = repository.get_scene_media(scene_id)
    if not media:
        raise HTTPException(404, detail="No source media is stored for this scene")
    keys = {
        "frame": ("frame_uri", "image/jpeg"),
        "segment": ("segment_video_uri", "video/mp4"),
        "source": ("source_video_uri", media.get("source_mime_type") or "video/mp4"),
    }
    if media_kind not in keys:
        raise HTTPException(404, detail="Media kind must be frame, segment, or source")
    uri_key, default_type = keys[media_kind]
    gcs_uri = str(media.get(uri_key) or "")
    if not gcs_uri:
        raise HTTPException(404, detail=f"No {media_kind} media is stored for this scene")

    from ...gcs import download_media_bytes, get_media_metadata

    metadata = get_media_metadata(gcs_uri)
    total = int(metadata["size"])
    content_type = str(metadata.get("content_type") or default_type)
    headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "private, max-age=300",
    }
    if not range_header or not range_header.startswith("bytes="):
        data = download_media_bytes(gcs_uri)
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

    data = download_media_bytes(gcs_uri, start=start, end=end)
    headers.update({
        "Content-Range": f"bytes {start}-{end}/{total}",
        "Content-Length": str(len(data)),
    })
    return Response(status_code=206, content=data, media_type=content_type, headers=headers)
