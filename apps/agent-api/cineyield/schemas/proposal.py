from pydantic import BaseModel

from .decisions import GuardrailCheck


class ProposalTerm(BaseModel):
    label: str
    value: str
    is_highlighted: bool = False


class Proposal(BaseModel):
    id: str
    opportunity_id: str
    campaign_id: str
    brand_name: str
    campaign_name: str
    brand_brief: str
    scene_title: str
    scene_episode: str
    scene_description: str
    placement_fee_usd: float
    terms: list[ProposalTerm]
    guardrails: list[GuardrailCheck]
    composed_by: str = "deal_agent"
    composed_at: str | None = None
