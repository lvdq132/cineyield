"""Market Agent — campaign discovery via official mcp-clickhouse.

Real integration path:
  MarketAgent → mcp-clickhouse (stdio MCP server) → ClickHouse
  → campaign rows → deterministic scoring → CampaignMatch objects → AgentEvent

This MUST use the real mcp-clickhouse MCP server.
DO NOT replace with local JSON data and claim MCP was used.
"""
from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from ..config import get_settings
from ..schemas.events import AgentEvent, AgentEventKind
from ..schemas.matching import CampaignMatch, ScoreBreakdown
from .base import AgentContext, BaseAgent
from .mcp_market import query_campaigns_via_mcp
from .scoring import ScoredCampaign, score_campaigns

logger = logging.getLogger(__name__)


class MarketAgent(BaseAgent):
    """
    Queries campaign inventory from ClickHouse via the official mcp-clickhouse MCP server,
    then applies deterministic Python scoring to produce ranked CampaignMatch objects.
    """

    name = "market_agent"

    @property
    def is_configured(self) -> bool:
        return get_settings().clickhouse_configured

    async def run(self, ctx: AgentContext) -> dict[str, Any]:
        if not self.is_configured:
            raise RuntimeError(
                "MarketAgent requires CLICKHOUSE_HOST and credentials. "
                "Set them in .env before invoking."
            )

        opportunity = ctx.extra.get("opportunity")
        scene = ctx.extra.get("scene")
        if opportunity is None or scene is None:
            raise ValueError("MarketAgent requires 'opportunity' and 'scene' in ctx.extra")

        t_start = time.monotonic()

        logger.info(
            "MarketAgent: querying campaigns via mcp-clickhouse for opportunity %s",
            opportunity.get("id"),
        )

        # ── Real MCP call ──────────────────────────────────────────────────────
        mcp_result = await query_campaigns_via_mcp()
        # ──────────────────────────────────────────────────────────────────────

        raw_campaigns = mcp_result["rows"]
        mcp_latency_ms = mcp_result["latency_ms"]

        logger.info(
            "mcp-clickhouse returned %d campaign rows in %dms",
            len(raw_campaigns),
            mcp_latency_ms,
        )

        # ── Deterministic scoring ──────────────────────────────────────────────
        scored = score_campaigns(
            raw_campaigns,
            opportunity_category=opportunity.get("category", ""),
            opportunity_territories=opportunity.get("territories", ["US", "CA", "GB"]),
            screen_time_seconds=int(opportunity.get("screen_time_seconds") or 0),
            estimated_value_usd=opportunity.get("estimated_value_usd"),
            brand_safety_score=float(scene.get("brand_safety_score") or 0.0),
            scene_mood=scene.get("mood", ""),
            scene_narrative_weight=scene.get("narrative_weight", ""),
        )
        # ──────────────────────────────────────────────────────────────────────

        matches = [_to_campaign_match(s, opportunity.get("id", "")) for s in scored]
        total_latency_ms = int((time.monotonic() - t_start) * 1000)

        unblocked = [m for m in matches if not m.is_blocked]
        blocked = [m for m in matches if m.is_blocked]

        summary = (
            f"{len(raw_campaigns)} campaigns scanned · "
            f"{len(unblocked)} ranked · "
            f"{len(blocked)} blocked · "
            f"{mcp_latency_ms}ms"
        )

        agent_event = AgentEvent(
            event_id=str(uuid.uuid4()),
            agent_name=self.name,
            kind=AgentEventKind.COMPLETED,
            asset_id=ctx.asset_id,
            scene_id=ctx.scene_id,
            opportunity_id=ctx.opportunity_id,
            tool_name="mcp-clickhouse",
            summary=summary,
            latency_ms=total_latency_ms,
            occurred_at=_utcnow(),
        )

        return {
            "matches": matches,
            "raw_campaigns": raw_campaigns,
            "total_scanned": len(raw_campaigns),
            "ranked_count": len(unblocked),
            "blocked_count": len(blocked),
            "mcp_latency_ms": mcp_latency_ms,
            "agent_event": agent_event,
            "summary": summary,
        }


def _to_campaign_match(s: ScoredCampaign, opportunity_id: str) -> CampaignMatch:
    return CampaignMatch(
        campaign_id=s.campaign_id,
        opportunity_id=opportunity_id,
        brand=s.brand,
        campaign_name=s.campaign_name,
        product_line=s.product_line,
        score=s.composite,
        score_breakdown=ScoreBreakdown(
            context_fit=s.context_fit,
            category_fit=s.category_fit,
            visibility=s.visibility_score,
            brand_safety=s.brand_safety,
            territory=s.territory_score,
            budget_and_terms=s.budget_score,
        ),
        is_blocked=s.is_blocked,
        blocked_reason=s.blocked_reason,
        estimated_fee_usd=None,
        budget_min_usd=s.budget_min_usd,
        budget_max_usd=s.budget_max_usd,
        territories=s.territories,
    )


def _utcnow() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).isoformat()


def matches_to_event_dicts(matches: list[CampaignMatch]) -> list[dict[str, Any]]:
    """Shape CampaignMatch results for repository.write_match_events.

    Shared by every caller that persists a MarketAgent.run() result
    (routers/v1/opportunities.py, agents/pipeline.py) so the field mapping
    lives in exactly one place.
    """
    return [
        {
            "opportunity_id": m.opportunity_id,
            "campaign_id": m.campaign_id,
            "brand": m.brand,
            "composite_score": m.score,
            "context_fit": m.score_breakdown.context_fit,
            "category_fit": m.score_breakdown.category_fit,
            "visibility_score": m.score_breakdown.visibility,
            "brand_safety": m.score_breakdown.brand_safety,
            "territory_score": m.score_breakdown.territory,
            "budget_score": m.score_breakdown.budget_and_terms,
            "is_blocked": m.is_blocked,
            "blocked_reason": m.blocked_reason,
        }
        for m in matches
    ]
