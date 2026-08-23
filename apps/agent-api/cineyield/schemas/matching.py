from pydantic import BaseModel, Field


class ScoreBreakdown(BaseModel):
    context_fit: float = Field(ge=0.0, le=100.0)
    category_fit: float = Field(ge=0.0, le=100.0)
    visibility: float = Field(ge=0.0, le=100.0)
    brand_safety: float = Field(ge=0.0, le=100.0)
    territory: float = Field(ge=0.0, le=100.0)
    budget_and_terms: float = Field(ge=0.0, le=100.0)

    @property
    def composite(self) -> float:
        """Deterministic weighted composite score."""
        weights = {
            "context_fit": 0.25,
            "category_fit": 0.25,
            "visibility": 0.15,
            "brand_safety": 0.20,
            "territory": 0.10,
            "budget_and_terms": 0.05,
        }
        return sum(
            getattr(self, k) * w for k, w in weights.items()
        )


class CampaignMatch(BaseModel):
    campaign_id: str
    opportunity_id: str
    brand: str
    campaign_name: str
    product_line: str
    score: float = Field(ge=0.0, le=100.0)
    score_breakdown: ScoreBreakdown
    is_blocked: bool = False
    blocked_reason: str | None = None
    estimated_fee_usd: float | None = None
    budget_min_usd: float | None = None
    budget_max_usd: float | None = None
    territories: list[str] = Field(default_factory=list)
