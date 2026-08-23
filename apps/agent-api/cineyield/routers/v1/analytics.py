"""Analytics summary routes — real ClickHouse data."""
from fastapi import APIRouter, HTTPException

from ...config import get_settings

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary")
async def get_analytics_summary() -> dict:
    """Return key analytics metrics from persisted ClickHouse data."""
    settings = get_settings()
    if not settings.clickhouse_configured:
        raise HTTPException(503, detail="ClickHouse not configured")

    from ...db.client import get_clickhouse_client
    client = get_clickhouse_client()

    # NOTE: scenes / placement_opportunities are plain MergeTree tables fed by an
    # ingest pipeline that has been re-run against test fixtures. Those runs left
    # orphaned rows behind whose asset_id has no matching cineyield.content_assets
    # row. Every aggregate below is scoped to known content assets so orphaned
    # test-fixture rows never inflate the headline numbers, and uses
    # count(DISTINCT id) so a row re-inserted by a retried pipeline run (plain
    # MergeTree does not deduplicate on INSERT) cannot double-count either.
    # This keeps /analytics/summary stable across repeated calls and background
    # merges.
    #
    # revenue_events and match_events are NOT deduplicated by count(DISTINCT
    # event_id): every write mints a fresh uuid4() event_id
    # (repository.write_revenue_event / write_match_events), so two rows for
    # the same approval or the same (opportunity, campaign) re-scan can never
    # share an event_id -- DISTINCT event_id collapses nothing there, ever.
    # Both are instead deduped by their real identity (proposal_id for
    # revenue, (opportunity_id, campaign_id) for matches) via GROUP BY +
    # argMax(..., occurred_at), so a second POST /deals/{id}/approve or a
    # repeated GET /opportunities/{id}/matches cannot inflate these numbers.
    #
    # revenue_events is NOT scoped by asset_id here: legacy rows written
    # before deals.py started joining through to the opportunity's real
    # asset_id may still carry asset_id="", and an asset_id IN
    # (content_assets) filter would silently zero those out rather than
    # exclude test-fixture pollution.

    # Approved deals + revenue — deduped by proposal_id (one row per
    # approval), taking each proposal's latest revenue event so a repeat
    # approval (see deals.approve_deal's idempotency guard) cannot double it.
    rev = client.query(
        "SELECT count() AS approved_deals, sum(amount_usd) AS approved_revenue_usd "
        "FROM ("
        "  SELECT proposal_id, argMax(amount_usd, occurred_at) AS amount_usd "
        "  FROM cineyield.revenue_events "
        "  WHERE revenue_type = 'placement_fee' "
        "  GROUP BY proposal_id"
        ")"
    )
    rev_row = rev.result_rows[0] if rev.result_rows else (0, 0.0)
    approved_deals = int(rev_row[0])
    approved_revenue = float(rev_row[1] or 0.0)

    # Total opportunities in DB — scoped to known content assets, deduplicated
    opps = client.query(
        "SELECT count(DISTINCT id) FROM cineyield.placement_opportunities "
        "WHERE asset_id IN (SELECT id FROM cineyield.content_assets)"
    )
    total_opps = int(opps.result_rows[0][0]) if opps.result_rows else 0

    # Total campaigns
    camps = client.query(
        "SELECT count(DISTINCT id) FROM cineyield.brand_campaigns WHERE is_active = true"
    )
    total_campaigns = int(camps.result_rows[0][0]) if camps.result_rows else 0

    # Total scenes analyzed — scoped to known content assets, deduplicated
    scenes = client.query(
        "SELECT count(DISTINCT id) FROM cineyield.scenes "
        "WHERE asset_id IN (SELECT id FROM cineyield.content_assets)"
    )
    total_scenes = int(scenes.result_rows[0][0]) if scenes.result_rows else 0

    # Qualified matches (non-blocked match events) — scoped to known content
    # assets, deduped to one row per (opportunity_id, campaign_id) pair via
    # argMax(..., occurred_at) so re-scanning the same opportunity (e.g. a
    # judge reloading /opportunities/{id}/matches) cannot multiply the count.
    matches = client.query(
        "SELECT count() FROM ("
        "  SELECT me.opportunity_id AS opportunity_id, me.campaign_id AS campaign_id, "
        "         argMax(me.is_blocked, me.occurred_at) AS is_blocked "
        "  FROM cineyield.match_events me "
        "  INNER JOIN cineyield.placement_opportunities po ON me.opportunity_id = po.id "
        "  WHERE po.asset_id IN (SELECT id FROM cineyield.content_assets) "
        "  GROUP BY me.opportunity_id, me.campaign_id"
        ") WHERE NOT is_blocked"
    )
    total_matches = int(matches.result_rows[0][0]) if matches.result_rows else 0

    return {
        "approved_deals": approved_deals,
        "approved_revenue_usd": approved_revenue,
        "total_opportunities": total_opps,
        "total_campaigns": total_campaigns,
        "total_scenes": total_scenes,
        "total_matches": total_matches,
    }
