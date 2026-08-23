"""Deal and approval routes."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from ...config import get_settings

router = APIRouter(prefix="/deals", tags=["deals"])


class ApprovalRequest(BaseModel):
    approved: bool
    approver: str
    note: str = ""


@router.get("/{deal_id}")
async def get_deal(deal_id: str) -> dict:
    settings = get_settings()
    if not settings.clickhouse_configured:
        raise HTTPException(503, detail="ClickHouse not configured")
    from ...db import repository
    proposal = repository.get_proposal(deal_id)
    if not proposal:
        raise HTTPException(404, detail=f"Deal {deal_id!r} not found")
    return proposal


@router.post("/{deal_id}/approve")
async def approve_deal(deal_id: str, body: ApprovalRequest) -> dict:
    settings = get_settings()
    if not settings.clickhouse_configured:
        raise HTTPException(503, detail="ClickHouse not configured")

    from ...db import repository
    from ...db.client import get_clickhouse_client

    client = get_clickhouse_client()
    # asset_id comes from the opportunity, not the proposal -- proposals do not
    # carry it. It used to be written as "" on every revenue event, which made
    # revenue impossible to attribute to a title and meant any analytics query
    # scoped by content asset silently reported zero revenue.
    #
    # `proposals` is a plain MergeTree and upsert_proposal() INSERTs rather
    # than replaces, so a re-composed proposal (same id, e.g. DealAgent
    # recomputing a fee) leaves two rows behind. GROUP BY p.id alone (no
    # placement_fee_usd, opportunity_id or campaign_id in the group key) plus
    # argMax(..., composed_at) picks every column from the single latest row,
    # so the fee this endpoint records always matches the fee
    # repository.get_proposal (ORDER BY composed_at DESC LIMIT 1) shows on
    # the deal page -- rather than an arbitrary row picked by an unordered
    # LIMIT 1 over a GROUP BY that (previously) split on the very fee it was
    # trying to disambiguate.
    result = client.query(
        "SELECT p.id AS id, "
        "       argMax(p.opportunity_id, p.composed_at) AS opportunity_id, "
        "       argMax(p.campaign_id, p.composed_at) AS campaign_id, "
        "       argMax(p.placement_fee_usd, p.composed_at) AS placement_fee_usd, "
        "       any(o.asset_id) AS asset_id "
        "FROM cineyield.proposals AS p "
        "LEFT JOIN cineyield.placement_opportunities AS o "
        "       ON o.id = p.opportunity_id "
        "WHERE p.id = {deal_id:String} "
        "GROUP BY p.id "
        "LIMIT 1",
        parameters={"deal_id": deal_id},
    )
    if not result.result_rows:
        raise HTTPException(404, detail=f"Deal {deal_id!r} not found")

    row = dict(zip(result.column_names, result.result_rows[0]))

    if body.approved:
        # Idempotent: a second approve on an already-APPROVED deal must not
        # write a second revenue event (that would double-count approved
        # revenue in /analytics/summary). workflow_state on the proposal is
        # the canonical source of truth (repository.get_proposal), so check
        # that rather than revenue_events directly.
        existing = repository.get_proposal(deal_id)
        if existing and existing.get("is_approved"):
            prior_event = repository.get_revenue_event_for_proposal(deal_id)
            return {
                "deal_id": deal_id,
                "approved": True,
                "approver": body.approver,
                "revenue_event_id": prior_event.get("event_id") if prior_event else None,
                "status": "APPROVED",
                "workflow_state": "APPROVED",
                "already_approved": True,
            }

        # 1. Authoritative state change: workflow_state = APPROVED on the proposal
        repository.approve_proposal(deal_id)

        # 2. Revenue event — audit consequence, NOT the source of truth
        rev_id = repository.write_revenue_event(
            proposal_id=deal_id,
            opportunity_id=row["opportunity_id"],
            campaign_id=row["campaign_id"],
            asset_id=row.get("asset_id") or "",
            amount_usd=float(row["placement_fee_usd"]),
            revenue_type="placement_fee",
        )

        # 3. Audit agent event
        repository.write_agent_event(
            agent_name="producer",
            kind="approved",
            summary=f"Deal {deal_id} approved by {body.approver}. Note: {body.note}",
            opportunity_id=row["opportunity_id"],
            campaign_id=row["campaign_id"],
            asset_id=row.get("asset_id") or "",
            success=True,
        )
        return {
            "deal_id": deal_id,
            "approved": True,
            "approver": body.approver,
            "revenue_event_id": rev_id,
            "status": "APPROVED",
            "workflow_state": "APPROVED",
        }
    else:
        repository.write_agent_event(
            agent_name="producer",
            kind="rejected",
            summary=f"Deal {deal_id} rejected by {body.approver}. Note: {body.note}",
            opportunity_id=row["opportunity_id"],
            campaign_id=row["campaign_id"],
            asset_id=row.get("asset_id") or "",
            success=False,
        )
        return {
            "deal_id": deal_id,
            "approved": False,
            "approver": body.approver,
            "status": "rejected",
        }
