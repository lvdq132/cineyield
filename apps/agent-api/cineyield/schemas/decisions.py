from enum import Enum

from pydantic import BaseModel


class DecisionOutcome(str, Enum):
    PASS = "pass"
    REVIEW = "review"
    REJECT = "reject"


class TerritoryDecision(BaseModel):
    territory: str
    outcome: DecisionOutcome
    reason: str = ""


class RightsDecision(BaseModel):
    opportunity_id: str
    campaign_id: str
    overall_outcome: DecisionOutcome
    territories: list[TerritoryDecision]
    cleared_territory_count: int = 0
    total_territory_count: int = 0
    agent_version: str = ""
    decided_at: str | None = None


class GuardrailCheck(BaseModel):
    name: str
    outcome: DecisionOutcome
    detail: str = ""


class CreativeDecision(BaseModel):
    opportunity_id: str
    campaign_id: str
    overall_outcome: DecisionOutcome
    guardrails: list[GuardrailCheck]
    narrative_impact: str = ""
    gemini_reasoning: str = ""
    agent_version: str = ""
    decided_at: str | None = None
