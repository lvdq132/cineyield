"""Deal and producer-decision routes."""
from typing import Literal

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from ...config import get_settings

router = APIRouter(prefix="/deals", tags=["deals"])


class ApprovalRequest(BaseModel):
    approved: bool
    approver: str
    note: str = ""


class DecisionRequest(BaseModel):
    action: Literal["approve", "reject", "counter", "request_changes"]
    approver: str
    note: str = ""


CANONICAL_DEAL_ALIASES = {
    "aurelius-systems": ("opp_horizons_rooftop_001", "camp_aurelius_001"),
}


@router.get("")
async def list_deals(limit: int = Query(100, ge=1, le=500)) -> dict:
    settings = get_settings()
    if not settings.clickhouse_configured:
        raise HTTPException(503, detail="ClickHouse not configured")
    from ...db import repository

    items = repository.list_proposals(limit=limit)
    return {"items": items, "total": len(items)}


def _resolve_deal_id(deal_id: str) -> str:
    """Resolve stable demo URLs to the latest real persisted proposal."""
    alias = CANONICAL_DEAL_ALIASES.get(deal_id)
    if not alias:
        return deal_id

    from ...db import repository

    resolved = repository.get_latest_proposal_id(
        opportunity_id=alias[0], campaign_id=alias[1]
    )
    if not resolved:
        raise HTTPException(
            404,
            detail=(
                "No persisted proposal exists for the canonical Aurelius "
                "placement. Open the proposal from Marketplace first."
            ),
        )
    return resolved


@router.get("/{deal_id}")
async def get_deal(deal_id: str) -> dict:
    settings = get_settings()
    if not settings.clickhouse_configured:
        raise HTTPException(503, detail="ClickHouse not configured")
    from ...db import repository
    resolved_id = _resolve_deal_id(deal_id)
    proposal = repository.get_proposal(resolved_id)
    if not proposal:
        raise HTTPException(404, detail=f"Deal {resolved_id!r} not found")
    if resolved_id != deal_id:
        proposal["canonical_alias"] = deal_id
    return proposal


@router.post("/{deal_id}/approve")
async def approve_deal(deal_id: str, body: ApprovalRequest) -> dict:
    settings = get_settings()
    if not settings.clickhouse_configured:
        raise HTTPException(503, detail="ClickHouse not configured")

    from ...db import repository
    from ...db.client import get_clickhouse_client

    deal_id = _resolve_deal_id(deal_id)

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


@router.post("/{deal_id}/decision")
async def decide_deal(deal_id: str, body: DecisionRequest) -> dict:
    """Persist every producer control shown in the deal room.

    Approval keeps the established revenue-event behavior.  The remaining
    actions update the proposal's canonical workflow state and write an audit
    event, so they are real, refresh-safe controls rather than decorative UI.
    """
    if body.action == "approve":
        return await approve_deal(
            deal_id,
            ApprovalRequest(approved=True, approver=body.approver, note=body.note),
        )

    settings = get_settings()
    if not settings.clickhouse_configured:
        raise HTTPException(503, detail="ClickHouse not configured")

    from ...db import repository

    resolved_id = _resolve_deal_id(deal_id)
    proposal = repository.get_proposal(resolved_id)
    if not proposal:
        raise HTTPException(404, detail=f"Deal {resolved_id!r} not found")

    if body.action in {"counter", "request_changes"} and not body.note.strip():
        raise HTTPException(422, detail="Add a note before sending this decision")

    state_by_action = {
        "reject": "REJECTED",
        "counter": "COUNTERED",
        "request_changes": "CHANGES_REQUESTED",
    }
    state = state_by_action[body.action]
    repository.set_proposal_workflow_state(resolved_id, state)
    repository.write_agent_event(
        agent_name="producer",
        kind=body.action,
        summary=(
            f"Deal {resolved_id} {body.action.replace('_', ' ')} by "
            f"{body.approver}. Note: {body.note}"
        ),
        opportunity_id=proposal.get("opportunity_id") or "",
        campaign_id=proposal.get("campaign_id") or "",
        success=body.action != "reject",
    )
    return {
        "deal_id": resolved_id,
        "approved": False,
        "approver": body.approver,
        "status": state,
        "workflow_state": state,
        "action": body.action,
    }
