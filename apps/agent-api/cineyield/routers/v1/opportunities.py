"""Placement opportunity routes."""
import logging

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...agents.base import AgentContext
from ...agents.market_agent import MarketAgent
from ...config import get_settings
from ...db.client import get_clickhouse_client

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/opportunities", tags=["opportunities"])


class ProposeRequest(BaseModel):
    campaign_id: str


def _scene_for_scoring(opp: dict) -> dict:
    """The scene fields `score_campaigns` actually reads, fetched by scene id.

    Falls back to the opportunity's own brand-safety score if the scene row is
    missing, but never invents a mood: an absent mood must mean "no adjacency
    evidence", never "conflicts with everything".
    """
    from ...db import repository

    scene = None
    scene_id = opp.get("scene_id")
    if scene_id:
        try:
            scene = repository.get_scene(scene_id)
        except Exception:  # noqa: BLE001 - scoring must not die on a scene read
            scene = None
    if not scene:
        return {"brand_safety_score": opp.get("brand_safety_score", 70.0)}
    return {
        "brand_safety_score": scene.get("brand_safety_score", opp.get("brand_safety_score", 70.0)),
        "mood": scene.get("mood", ""),
        "narrative_weight": scene.get("narrative_weight", ""),
    }


@router.get("/{opportunity_id}")
async def get_opportunity(opportunity_id: str) -> dict:
    settings = get_settings()
    if not settings.clickhouse_configured:
        raise HTTPException(503, detail="ClickHouse not configured")
    client = get_clickhouse_client()
    result = client.query(
        "SELECT id, scene_id, asset_id, category, object_label, "
        "timecode_start, timecode_end, screen_time_seconds, "
        "naturalness_score, brand_safety_score, complexity, "
        "rights_status, estimated_value_usd, is_primary "
        "FROM cineyield.placement_opportunities WHERE id = {opp_id:String} LIMIT 1",
        parameters={"opp_id": opportunity_id},
    )
    rows = result.result_rows
    if not rows:
        raise HTTPException(404, detail=f"Opportunity {opportunity_id!r} not found")
    return dict(zip(result.column_names, rows[0]))


@router.get("/{opportunity_id}/matches")
async def get_opportunity_matches(opportunity_id: str) -> dict:
    settings = get_settings()
    if not settings.clickhouse_configured:
        raise HTTPException(503, detail="ClickHouse not configured")

    client = get_clickhouse_client()
    result = client.query(
        # scene_id is required: scoring reads the scene's mood and
        # narrative_weight, and without them this endpoint scores differently
        # from /propose for the same campaign.
        "SELECT id, scene_id, category, screen_time_seconds, brand_safety_score, "
        "estimated_value_usd "
        "FROM cineyield.placement_opportunities WHERE id = {opp_id:String} LIMIT 1",
        parameters={"opp_id": opportunity_id},
    )
    rows = result.result_rows
    if not rows:
        raise HTTPException(404, detail=f"Opportunity {opportunity_id!r} not found")
    opp = dict(zip(result.column_names, rows[0]))

    agent = MarketAgent()
    ctx = AgentContext(
        opportunity_id=opportunity_id,
        extra={
            "opportunity": {**opp, "territories": ["US", "CA", "GB"]},
            # Pass the REAL scene, not just its safety score. Scoring reads
            # mood and narrative_weight, and a missing mood used to make every
            # campaign with any excluded_contexts look like an adjacency
            # conflict -- so this endpoint reported 1 of 27 campaigns unblocked
            # while /propose, which passes the real scene, reported 7, and the
            # two disagreed about which campaign was even the best match.
            "scene": _scene_for_scoring(opp),
        },
    )
    market_result = await agent.run(ctx)
    all_matches = market_result.get("matches", [])
    serialized = [
        m.model_dump() if hasattr(m, "model_dump") else m
        for m in all_matches
    ]
    ranked_count = sum(1 for m in serialized if not m.get("is_blocked"))

    # Persist so /analytics/summary's total_matches reflects real scans
    # instead of a table nothing ever wrote to. Safe to call repeatedly: the
    # analytics query dedupes to the latest write per (opportunity_id,
    # campaign_id) pair, so re-scanning the same opportunity cannot inflate
    # the count.
    try:
        from ...agents.market_agent import matches_to_event_dicts
        from ...db import repository
        if all_matches:
            repository.write_match_events(matches_to_event_dicts(all_matches))
    except Exception as exc:
        logger.warning(
            "ClickHouse match_events write failed in get_opportunity_matches: %s", exc
        )

    return {
        "opportunity_id": opportunity_id,
        "total_scanned": market_result.get("total_scanned", len(serialized)),
        "ranked_count": ranked_count,
        "mcp_latency_ms": market_result.get("mcp_latency_ms"),
        "matches": serialized,
    }


@router.post("/{opportunity_id}/propose")
async def create_proposal(opportunity_id: str, body: ProposeRequest) -> dict:
    """Run the full proposal pipeline for one opportunity + campaign pair, persist and return."""
    settings = get_settings()
    if not settings.clickhouse_configured:
        raise HTTPException(503, detail="ClickHouse not configured")

    client = get_clickhouse_client()

    # Load opportunity
    opp_result = client.query(
        "SELECT id, scene_id, asset_id, category, object_label, timecode_start, timecode_end, "
        "screen_time_seconds, naturalness_score, brand_safety_score, complexity, "
        "rights_status, estimated_value_usd, is_primary "
        "FROM cineyield.placement_opportunities WHERE id = {opp_id:String} LIMIT 1",
        parameters={"opp_id": opportunity_id},
    )
    if not opp_result.result_rows:
        raise HTTPException(404, detail=f"Opportunity {opportunity_id!r} not found")
    opp = dict(zip(opp_result.column_names, opp_result.result_rows[0]))
    opp["territories"] = ["US", "CA", "GB"]

    # Load scene for context
    scene_dict: dict = {}
    scene_id = opp.get("scene_id", "")
    if scene_id:
        sc_result = client.query(
            "SELECT id, name, summary, mood, narrative_weight, brand_safety_score "
            "FROM cineyield.scenes WHERE id = {sid:String} LIMIT 1",
            parameters={"sid": scene_id},
        )
        if sc_result.result_rows:
            scene_dict = dict(zip(sc_result.column_names, sc_result.result_rows[0]))

    if not scene_dict:
        scene_dict = {
            "brand_safety_score": opp.get("brand_safety_score", 70.0),
            "narrative_weight": "Medium",
            "mood": "Neutral",
            "name": "Scene",
            "summary": "",
        }

    # Campaign data + deterministic score via the same MCP path GET .../matches
    # uses: MarketAgent → mcp-clickhouse (stdio) → ClickHouse → score_campaigns.
    # /propose must never read cineyield.brand_campaigns directly — the
    # requested campaign_id has to actually come back from mcp-clickhouse.
    market_agent = MarketAgent()
    try:
        market_result = await market_agent.run(AgentContext(
            opportunity_id=opportunity_id,
            extra={"opportunity": opp, "scene": scene_dict},
        ))
    except RuntimeError as exc:
        # MarketAgent raises RuntimeError when the mcp-clickhouse binary is
        # missing or its stdio session fails. This is the "Open Deal" click, so
        # a bare 500 with a stack trace is the worst possible thing to show.
        # 502 is the honest status: an upstream dependency this endpoint
        # deliberately requires did not answer. Deliberately NOT falling back to
        # a direct ClickHouse query -- routing this path through MCP is the
        # point, and a silent fallback would make the partner integration
        # unfalsifiable.
        logger.error("propose: mcp-clickhouse market lookup failed: %s", exc)
        raise HTTPException(
            502,
            detail=(
                "The campaign market lookup failed: mcp-clickhouse did not "
                "answer. No proposal was created."
            ),
        ) from exc
    mcp_latency_ms = market_result.get("mcp_latency_ms")
    raw_campaigns: list[dict] = market_result.get("raw_campaigns", [])
    campaign = next((c for c in raw_campaigns if c.get("id") == body.campaign_id), None)
    match = next(
        (m for m in market_result.get("matches", []) if m.campaign_id == body.campaign_id),
        None,
    )
    if campaign is None or match is None:
        raise HTTPException(
            404,
            detail=(
                f"Campaign {body.campaign_id!r} not found among the "
                f"{len(raw_campaigns)} mcp-clickhouse-scored candidates for "
                f"opportunity {opportunity_id!r}. It may be inactive or "
                f"outside the top {len(raw_campaigns)} campaigns by budget."
            ),
        )

    campaign_match_dict: dict = {
        "campaign_id": match.campaign_id,
        "brand": match.brand,
        "campaign_name": match.campaign_name,
        "product_line": match.product_line,
        "budget_min_usd": match.budget_min_usd,
        "budget_max_usd": match.budget_max_usd,
        "territories": match.territories,
        "context_fit": match.score_breakdown.context_fit,
        "category_fit": match.score_breakdown.category_fit,
        "visibility_score": match.score_breakdown.visibility,
        "brand_safety": match.score_breakdown.brand_safety,
        "territory_score": match.score_breakdown.territory,
        "budget_score": match.score_breakdown.budget_and_terms,
        # Key name matches what DealAgent._calculate_fee actually reads
        # (see tests/test_agents_deterministic.py::test_fee_calculation_basic).
        # NOTE: the dict this replaced was built from ScoredCampaign.to_dict(),
        # which only ever produced a "composite" key — so composite_score
        # here (and the fee it drives) was silently always defaulting to
        # 70.0 before this change. Fixed as part of rebuilding this dict.
        "composite_score": match.score,
        "is_blocked": match.is_blocked,
        "blocked_reason": match.blocked_reason,
        "campaign": campaign,
    }

    # RightsAgent (deterministic)
    from ...agents.rights_agent import check_rights
    rights_result = check_rights(opp, campaign)

    # CreativeGuardian
    from ...agents.creative_guardian import CreativeGuardian
    creative_result = await CreativeGuardian().run(AgentContext(extra={
        "scene": scene_dict,
        "opportunity": opp,
        "campaign": campaign,
    }))

    # DealAgent
    from ...agents.deal_agent import DealAgent
    proposal_dict = await DealAgent().run(AgentContext(extra={
        "scene": scene_dict,
        "opportunity": opp,
        "campaign_match": campaign_match_dict,
        "rights_decision": rights_result.model_dump(),
        "creative_decision": creative_result,
    }))

    # Persist
    from ...db import repository
    repository.upsert_proposal({
        **proposal_dict,
        "brand_name": campaign.get("brand", ""),
        "campaign_name": campaign.get("campaign_name", ""),
        "opportunity_id": opportunity_id,
        "campaign_id": body.campaign_id,
        "scene_title": scene_dict.get("name", "Scene"),
        "scene_description": scene_dict.get("summary", ""),
    })

    repository.write_agent_event(
        agent_name="deal_agent",
        kind="proposal_created",
        summary=f"Proposal {proposal_dict['id']} for {campaign.get('brand')} × {opportunity_id}",
        opportunity_id=opportunity_id,
        campaign_id=body.campaign_id,
        success=True,
    )

    return {
        "proposal_id": proposal_dict["id"],
        "brand_name": campaign.get("brand", ""),
        "campaign_name": campaign.get("campaign_name", ""),
        "placement_fee_usd": proposal_dict.get("placement_fee_usd", 0),
        "brand_brief": proposal_dict.get("brand_brief", ""),
        "scene_title": scene_dict.get("name", "Scene"),
        "scene_description": scene_dict.get("summary", ""),
        "composite_score": campaign_match_dict.get("composite_score", 70.0),
        "terms": proposal_dict.get("terms", []),
        "guardrails": creative_result.get("guardrails", []),
        # Additive field (not in ProposeResponse's typed fields, harmlessly
        # ignored by the frontend) — direct evidence that this call actually
        # went through mcp-clickhouse rather than a direct ClickHouse query.
        "mcp_latency_ms": mcp_latency_ms,
    }
