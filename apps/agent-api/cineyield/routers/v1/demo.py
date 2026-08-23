"""Demo reset — clears proposal/revenue state for one opportunity.

Safe: no DROP or TRUNCATE. Only deletes rows for the specified opportunity_id
so judges can run the canonical flow repeatedly from a clean slate.
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from ...db.client import get_clickhouse_client

router = APIRouter(prefix="/demo", tags=["demo"])

CANONICAL_OPP = "opp_horizons_rooftop_001"


class ResetRequest(BaseModel):
    opportunity_id: str = CANONICAL_OPP


class ResetResponse(BaseModel):
    opportunity_id: str
    proposals_deleted: int
    revenue_events_deleted: int
    message: str


@router.post("/reset", response_model=ResetResponse)
async def demo_reset(body: ResetRequest) -> ResetResponse:
    """Delete proposals and revenue events for one opportunity.

    Allows the canonical judged flow to be rehearsed from a clean state.
    Does not affect other opportunities, scenes, campaigns, or agent events.
    """
    opp_id = body.opportunity_id
    client = get_clickhouse_client()

    # Count before deletion so we can report
    prop_count = client.query(
        "SELECT count() FROM cineyield.proposals WHERE opportunity_id = {oid:String}",
        parameters={"oid": opp_id},
    ).result_rows[0][0]

    rev_count = client.query(
        "SELECT count() FROM cineyield.revenue_events WHERE opportunity_id = {oid:String}",
        parameters={"oid": opp_id},
    ).result_rows[0][0]

    # ClickHouse Cloud SharedMergeTree: ALTER TABLE DELETE is the row-deletion mechanism
    client.command(
        "ALTER TABLE cineyield.proposals DELETE WHERE opportunity_id = {oid:String}",
        parameters={"oid": opp_id},
    )
    client.command(
        "ALTER TABLE cineyield.revenue_events DELETE WHERE opportunity_id = {oid:String}",
        parameters={"oid": opp_id},
    )

    return ResetResponse(
        opportunity_id=opp_id,
        proposals_deleted=int(prop_count),
        revenue_events_deleted=int(rev_count),
        message=(
            f"Reset complete. Deleted {prop_count} proposal(s) and "
            f"{rev_count} revenue event(s) for opportunity {opp_id}."
        ),
    )
