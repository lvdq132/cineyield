from enum import Enum

from pydantic import BaseModel, Field


class AgentEventKind(str, Enum):
    STARTED = "started"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class AgentEvent(BaseModel):
    event_id: str
    agent_name: str
    kind: AgentEventKind
    asset_id: str | None = None
    scene_id: str | None = None
    opportunity_id: str | None = None
    campaign_id: str | None = None
    tool_name: str | None = None
    summary: str = ""
    latency_ms: int | None = None
    occurred_at: str


class ApprovalEvent(BaseModel):
    event_id: str
    proposal_id: str
    opportunity_id: str
    campaign_id: str
    approved: bool
    approver: str
    approver_role: str = "producer"
    note: str = ""
    placement_fee_usd: float | None = None
    occurred_at: str


class RevenueEvent(BaseModel):
    event_id: str
    proposal_id: str
    opportunity_id: str
    campaign_id: str
    asset_id: str
    amount_usd: float = Field(ge=0.0)
    revenue_type: str = "placement_fee"
    territory: str | None = None
    occurred_at: str
