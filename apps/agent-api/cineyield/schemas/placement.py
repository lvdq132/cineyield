from enum import Enum

from pydantic import BaseModel, Field


class PlacementComplexity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RightsStatus(str, Enum):
    CLEAR = "clear"
    REVIEW = "review"
    RESTRICTED = "restricted"


class PlacementOpportunity(BaseModel):
    id: str
    scene_id: str
    asset_id: str
    category: str
    object_label: str
    timecode_start: str | None = None
    timecode_end: str | None = None
    screen_time_seconds: int
    naturalness_score: float = Field(ge=0.0, le=100.0)
    brand_safety_score: float = Field(ge=0.0, le=100.0)
    complexity: PlacementComplexity
    rights_status: RightsStatus
    estimated_value_usd: float | None = None
    is_primary: bool = False


class TerritoryRights(BaseModel):
    territory: str
    status: RightsStatus


class BrandCampaign(BaseModel):
    id: str
    brand: str
    campaign_name: str
    product_line: str
    budget_min_usd: float
    budget_max_usd: float
    target_categories: list[str] = Field(default_factory=list)
    excluded_contexts: list[str] = Field(default_factory=list)
    territories: list[str] = Field(default_factory=list)
    visibility_seconds_min: int = 0
    visibility_seconds_max: int = 60
    is_active: bool = True
