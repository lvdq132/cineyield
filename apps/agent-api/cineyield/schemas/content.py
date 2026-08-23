from enum import Enum

from pydantic import BaseModel, Field


class ContentFormat(str, Enum):
    TV_SERIES = "tv_series"
    FILM = "film"
    MICRODRAMA = "microdrama"
    YOUTUBE = "youtube"
    SOCIAL = "social"


class AnalysisStatus(str, Enum):
    QUEUED = "queued"
    ANALYZING = "analyzing"
    ANALYZED = "analyzed"
    FAILED = "failed"


class ContentAssetScene(BaseModel):
    """Lightweight scene summary embedded in a content asset response."""

    id: str
    asset_id: str
    episode: str | None = None
    name: str
    summary: str = ""
    brand_safety_score: float = 0.0
    narrative_weight: str = ""
    mood: str = ""
    duration_seconds: int = 0


class ContentAsset(BaseModel):
    id: str
    title: str
    subtitle: str
    format: ContentFormat
    status: AnalysisStatus = AnalysisStatus.QUEUED
    scene_count: int = 0
    opportunity_count: int = 0
    estimated_value_usd: float | None = None
    gcs_uri: str | None = None
    updated_at: str | None = None
    scenes: list[ContentAssetScene] = Field(default_factory=list)


class ContentListResponse(BaseModel):
    items: list[ContentAsset]
    total: int
