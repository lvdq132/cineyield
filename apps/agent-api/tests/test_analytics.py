"""Tests for GET /api/v1/analytics/summary.

Regression guard for two live-data bugs found via direct ClickHouse
inspection:

1. scenes / placement_opportunities picked up rows left behind by test
   ingest runs whose asset_id has no matching content_assets row
   ("orphans"), inflating the headline counts shown to a judge.
2. scenes / placement_opportunities are plain MergeTree tables (no
   ReplacingMergeTree/dedup engine), so a retried pipeline write can
   leave two rows with the same id — count() must not double-count.

These tests assert the aggregate queries are (a) scoped to known
content_assets and (b) deduplicated via count(DISTINCT ...), and that
the endpoint assembles the response from those scoped/deduped values.
"""
from unittest.mock import MagicMock, patch

from fastapi.testclient import TestClient

from main import app

client = TestClient(app)


def _mock_settings(configured: bool) -> MagicMock:
    settings = MagicMock()
    settings.clickhouse_configured = configured
    return settings


def _fake_client(rows_by_marker: dict[str, list[tuple]]) -> MagicMock:
    """A ClickHouse client stub whose .query() dispatches on a unique
    substring marker in the SQL text, so call order in analytics.py can
    change without breaking these tests."""
    fake = MagicMock()
    captured_sql: list[str] = []

    def fake_query(sql, *args, **kwargs):
        captured_sql.append(sql)
        for marker, rows in rows_by_marker.items():
            if marker in sql:
                result = MagicMock()
                result.result_rows = rows
                return result
        raise AssertionError(f"Unexpected query, no marker matched:\n{sql}")

    fake.query.side_effect = fake_query
    fake.captured_sql = captured_sql
    return fake


def test_analytics_summary_returns_503_when_clickhouse_not_configured():
    with patch(
        "cineyield.routers.v1.analytics.get_settings",
        return_value=_mock_settings(False),
    ):
        resp = client.get("/api/v1/analytics/summary")
    assert resp.status_code == 503


def test_analytics_scenes_query_scoped_to_known_assets_and_deduped():
    """The scenes aggregate must dedupe via DISTINCT and exclude scenes
    whose asset_id has no matching content_assets row."""
    fake = _fake_client({
        "FROM cineyield.revenue_events": [(0, 0.0)],
        "FROM cineyield.placement_opportunities": [(0,)],
        "FROM cineyield.brand_campaigns": [(0,)],
        "FROM cineyield.scenes": [(1,)],
        "FROM cineyield.match_events": [(0,)],
    })
    with patch(
        "cineyield.routers.v1.analytics.get_settings",
        return_value=_mock_settings(True),
    ), patch("cineyield.db.client.get_clickhouse_client", return_value=fake):
        resp = client.get("/api/v1/analytics/summary")

    assert resp.status_code == 200
    scenes_sql = next(s for s in fake.captured_sql if "FROM cineyield.scenes" in s)
    assert "DISTINCT" in scenes_sql
    assert "cineyield.content_assets" in scenes_sql


def test_analytics_opportunities_query_scoped_to_known_assets_and_deduped():
    """The opportunities aggregate must dedupe via DISTINCT and exclude
    opportunities whose asset_id has no matching content_assets row."""
    fake = _fake_client({
        "FROM cineyield.revenue_events": [(0, 0.0)],
        "FROM cineyield.placement_opportunities": [(0,)],
        "FROM cineyield.brand_campaigns": [(0,)],
        "FROM cineyield.scenes": [(0,)],
        "FROM cineyield.match_events": [(0,)],
    })
    with patch(
        "cineyield.routers.v1.analytics.get_settings",
        return_value=_mock_settings(True),
    ), patch("cineyield.db.client.get_clickhouse_client", return_value=fake):
        resp = client.get("/api/v1/analytics/summary")

    assert resp.status_code == 200
    opps_sql = next(s for s in fake.captured_sql if "FROM cineyield.placement_opportunities" in s)
    assert "DISTINCT" in opps_sql
    assert "cineyield.content_assets" in opps_sql


def test_analytics_matches_query_scoped_to_known_assets():
    """Qualified-match count must join through to content_assets so
    matches on orphaned test-fixture opportunities are excluded, and must
    dedupe by (opportunity_id, campaign_id) rather than event_id.

    event_id is a fresh uuid4() minted on every write_match_events() call
    (repository.py), so count(DISTINCT event_id) never collapses repeated
    writes for the same opportunity+campaign pair -- re-scanning the same
    opportunity (GET /opportunities/{id}/matches) would otherwise inflate
    this count on every call.
    """
    fake = _fake_client({
        "FROM cineyield.revenue_events": [(0, 0.0)],
        "FROM cineyield.placement_opportunities": [(0,)],
        "FROM cineyield.brand_campaigns": [(0,)],
        "FROM cineyield.scenes": [(0,)],
        "FROM cineyield.match_events": [(0,)],
    })
    with patch(
        "cineyield.routers.v1.analytics.get_settings",
        return_value=_mock_settings(True),
    ), patch("cineyield.db.client.get_clickhouse_client", return_value=fake):
        resp = client.get("/api/v1/analytics/summary")

    assert resp.status_code == 200
    matches_sql = next(s for s in fake.captured_sql if "FROM cineyield.match_events" in s)
    assert "GROUP BY me.opportunity_id, me.campaign_id" in matches_sql
    assert "argMax(me.is_blocked, me.occurred_at)" in matches_sql
    assert "cineyield.content_assets" in matches_sql
    assert "cineyield.placement_opportunities" in matches_sql


def test_analytics_revenue_query_deduped():
    """Approved-deal count/revenue must be deduplicated by proposal_id, not
    by a bare `SELECT DISTINCT event_id, amount_usd`.

    Regression: event_id is a fresh uuid4() minted on every
    write_revenue_event() call, so two rows from approving the same deal
    twice can never share an event_id -- `DISTINCT event_id, amount_usd`
    collapses nothing, ever, and previously let a double-approval double
    every headline revenue number. Deduping by proposal_id (the real
    identity of "one approved deal") via argMax(amount_usd, occurred_at)
    actually guarantees the one-row-per-approval invariant, and
    deals.approve_deal is now idempotent so a repeat approval doesn't even
    write a second row in the first place -- this is defense in depth for
    rows written before that guard existed.

    NOTE: unlike scenes/opportunities/matches, this query is deliberately
    NOT scoped to `asset_id IN (SELECT id FROM content_assets)`: legacy
    revenue rows written before deals.py joined through to the real
    asset_id may still carry asset_id="", so an asset_id scope here would
    zero out real approved deals rather than exclude test-fixture
    pollution.
    """
    fake = _fake_client({
        "FROM cineyield.revenue_events": [(0, 0.0)],
        "FROM cineyield.placement_opportunities": [(0,)],
        "FROM cineyield.brand_campaigns": [(0,)],
        "FROM cineyield.scenes": [(0,)],
        "FROM cineyield.match_events": [(0,)],
    })
    with patch(
        "cineyield.routers.v1.analytics.get_settings",
        return_value=_mock_settings(True),
    ), patch("cineyield.db.client.get_clickhouse_client", return_value=fake):
        resp = client.get("/api/v1/analytics/summary")

    assert resp.status_code == 200
    revenue_sql = next(s for s in fake.captured_sql if "cineyield.revenue_events" in s)
    assert "GROUP BY proposal_id" in revenue_sql
    assert "argMax(amount_usd, occurred_at)" in revenue_sql
    assert "SELECT DISTINCT event_id, amount_usd" not in revenue_sql


def test_analytics_summary_end_to_end_assembles_scoped_values():
    """Full endpoint contract: response fields reflect the scoped/deduped
    counts returned by ClickHouse, regardless of query call order."""
    fake = _fake_client({
        "FROM cineyield.revenue_events": [(2, 259000.0)],
        "FROM cineyield.placement_opportunities": [(16,)],
        "FROM cineyield.brand_campaigns": [(27,)],
        "FROM cineyield.scenes": [(12,)],
        "FROM cineyield.match_events": [(9,)],
    })
    with patch(
        "cineyield.routers.v1.analytics.get_settings",
        return_value=_mock_settings(True),
    ), patch("cineyield.db.client.get_clickhouse_client", return_value=fake):
        resp = client.get("/api/v1/analytics/summary")

    assert resp.status_code == 200
    body = resp.json()
    assert body["approved_deals"] == 2
    assert body["approved_revenue_usd"] == 259000.0
    assert body["total_opportunities"] == 16
    assert body["total_campaigns"] == 27
    assert body["total_scenes"] == 12
    assert body["total_matches"] == 9


def test_get_comparable_deals_scoped_to_known_content_assets():
    """repository.get_comparable_deals must also exclude orphaned
    test-fixture opportunities and dedupe match_events -- both deal_count
    and median_score, computed over the SAME deduped (opportunity_id,
    campaign_id) rows so a re-scanned opportunity isn't counted once but
    weighted multiple times in the median."""
    from cineyield.db.repository import get_comparable_deals

    with patch("cineyield.db.repository.get_clickhouse_client") as mock_client:
        mock_query = MagicMock()
        result = MagicMock()
        result.result_rows = [(3, 88.5)]
        mock_query.return_value = result
        mock_client.return_value.query = mock_query

        deals = get_comparable_deals("Consumer Audio")

        assert deals == {"deal_count": 3, "median_score": 88.5}
        call_args, call_kwargs = mock_query.call_args
        sql = call_args[0]
        assert "GROUP BY me.opportunity_id, me.campaign_id" in sql
        assert "argMax(me.composite_score, me.occurred_at)" in sql
        assert "argMax(me.is_blocked, me.occurred_at)" in sql
        assert "cineyield.content_assets" in sql
        assert call_kwargs.get("parameters") == {"category": "Consumer Audio"}
