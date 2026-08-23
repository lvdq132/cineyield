"""Agent events routes — real ClickHouse audit trail."""
from fastapi import APIRouter, HTTPException

from ...config import get_settings

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("/events")
async def get_agent_events(
    limit: int = 50,
    opportunity_id: str | None = None,
) -> dict:
    """Return recent agent events from ClickHouse."""
    settings = get_settings()
    if not settings.clickhouse_configured:
        raise HTTPException(503, detail="ClickHouse not configured")

    from ...db.client import get_clickhouse_client
    client = get_clickhouse_client()

    if opportunity_id:
        result = client.query(
            "SELECT event_id, correlation_id, agent_name, kind, "
            "asset_id, scene_id, opportunity_id, campaign_id, "
            "tool_name, summary, latency_ms, success, occurred_at "
            "FROM cineyield.agent_events "
            "WHERE opportunity_id = {opp_id:String} "
            "ORDER BY occurred_at DESC LIMIT {limit:UInt32}",
            parameters={"opp_id": opportunity_id, "limit": limit},
        )
    else:
        result = client.query(
            "SELECT event_id, correlation_id, agent_name, kind, "
            "asset_id, scene_id, opportunity_id, campaign_id, "
            "tool_name, summary, latency_ms, success, occurred_at "
            "FROM cineyield.agent_events "
            "ORDER BY occurred_at DESC LIMIT {limit:UInt32}",
            parameters={"limit": limit},
        )

    events = []
    for row in result.result_rows:
        ev = dict(zip(result.column_names, row))
        # Serialize datetime to ISO string
        if hasattr(ev.get("occurred_at"), "isoformat"):
            ev["occurred_at"] = ev["occurred_at"].isoformat()
        events.append(ev)

    return {"events": events, "count": len(events)}
