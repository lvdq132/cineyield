"""Rights Agent — deterministic territory rights clearance.

All decisions are DETERMINISTIC — no LLM calls. Clearance is decided by the
hard-coded rules below (restricted categories + per-campaign territory
allow-lists). This keeps objective legal/rights constraints out of the LLM's
hands entirely, which is the point: rights is exactly the kind of decision that
must be reproducible and auditable, not generated.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from ..schemas.decisions import DecisionOutcome, RightsDecision, TerritoryDecision
from .base import AgentContext, BaseAgent

logger = logging.getLogger(__name__)

# Categories that are never cleared, in any territory.
_ALWAYS_RESTRICTED_CATEGORIES = {
    "tobacco", "gambling", "weapons", "adult content",
}


class RightsAgent(BaseAgent):
    name = "rights_agent"

    @property
    def is_configured(self) -> bool:
        return True  # deterministic — always runnable

    async def run(self, ctx: AgentContext) -> dict[str, Any]:
        opportunity = ctx.extra.get("opportunity", {})
        campaign = ctx.extra.get("campaign", {})

        result = check_rights(opportunity, campaign)
        return result.model_dump()


def check_rights(
    opportunity: dict[str, Any],
    campaign: dict[str, Any],
) -> RightsDecision:
    """Apply deterministic rights clearance rules."""
    opp_id = opportunity.get("id", "unknown")
    camp_id = campaign.get("id", "unknown")
    opp_territories: list[str] = opportunity.get("territories", campaign.get("territories", ["US"]))
    camp_territories: list[str] = campaign.get("territories", [])
    opp_category: str = opportunity.get("category", "").lower()

    territory_decisions: list[TerritoryDecision] = []
    cleared = 0

    # Determine which territories to evaluate
    eval_territories = [t for t in opp_territories if not camp_territories or t in camp_territories]
    if not eval_territories:
        eval_territories = opp_territories or ["US"]

    for territory in eval_territories:
        outcome, reason = _evaluate_territory(territory, opp_category, campaign)
        territory_decisions.append(TerritoryDecision(
            territory=territory, outcome=outcome, reason=reason,
        ))
        if outcome == DecisionOutcome.PASS:
            cleared += 1

    overall = _overall_outcome(territory_decisions)

    return RightsDecision(
        opportunity_id=opp_id,
        campaign_id=camp_id,
        overall_outcome=overall,
        territories=territory_decisions,
        cleared_territory_count=cleared,
        total_territory_count=len(territory_decisions),
        agent_version="rights_agent_v1_deterministic",
        decided_at=datetime.now(timezone.utc).isoformat(),
    )


def _evaluate_territory(
    territory: str,
    category: str,
    campaign: dict[str, Any],
) -> tuple[DecisionOutcome, str]:
    """Return (outcome, reason) for a single territory."""
    # Hard block: restricted category
    for restricted in _ALWAYS_RESTRICTED_CATEGORIES:
        if restricted in category:
            return DecisionOutcome.REJECT, f"Category '{category}' is restricted in all territories"

    # Territory must be in campaign's allowed territories (if specified)
    camp_territories: list[str] = campaign.get("territories", [])
    if camp_territories and territory not in camp_territories:
        return DecisionOutcome.REVIEW, f"Territory {territory} not explicitly cleared in campaign"

    return DecisionOutcome.PASS, "Cleared"


def _overall_outcome(decisions: list[TerritoryDecision]) -> DecisionOutcome:
    if any(d.outcome == DecisionOutcome.REJECT for d in decisions):
        return DecisionOutcome.REJECT
    if any(d.outcome == DecisionOutcome.REVIEW for d in decisions):
        return DecisionOutcome.REVIEW
    return DecisionOutcome.PASS
