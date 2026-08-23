from pydantic import BaseModel, Field, field_validator


class DetectedObject(BaseModel):
    label: str
    category: str
    confidence: float = Field(ge=0.0, le=100.0)
    is_primary: bool = False
    timecode_start: str | None = None
    timecode_end: str | None = None


class DetectionBox(BaseModel):
    label: str
    confidence: float = Field(ge=0.0, le=100.0)
    x: float = Field(ge=0.0, le=100.0)
    y: float = Field(ge=0.0, le=100.0)
    width: float = Field(ge=0.0, le=100.0)
    height: float = Field(ge=0.0, le=100.0)
    is_primary: bool = False


class SceneAnalysis(BaseModel):
    scene_id: str
    asset_id: str
    episode: str | None = None
    name: str
    summary: str = ""
    brand_safety_score: float = Field(ge=0.0, le=100.0, default=0.0)
    narrative_weight: str = ""
    mood: str = ""
    duration_seconds: int = 0
    detected_objects: list[DetectedObject] = Field(default_factory=list)
    detection_boxes: list[DetectionBox] = Field(default_factory=list)
    gemini_model_used: str | None = None
    analyzed_at: str | None = None

    @field_validator("brand_safety_score")
    @classmethod
    def clamp_score(cls, v: float) -> float:
        return max(0.0, min(100.0, v))
