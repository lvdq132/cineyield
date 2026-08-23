"""Tests for GET /api/v1/opportunities/{id}/matches.

FIX 1 (P0 review): this endpoint runs MarketAgent.run() over all seeded
campaigns but, before this fix, never persisted the result --
cineyield.match_events had zero callers, so /analytics/summary's
total_matches was structurally always 0 no matter how many real matches
this endpoint found. This locks in that the endpoint now persists via
repository.write_match_events, and that repeated calls stay safe (the
dedup guarantee itself lives in the analytics/repository query tests).
"""
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from cineyield.schemas.matching import CampaignMatch, ScoreBreakdown
from main import app

client = TestClient(app)


def _mock_settings(configured: bool) -> MagicMock:
    settings = MagicMock()
    settings.clickhouse_configured = configured
    return settings


def _fake_opp_client() -> MagicMock:
    fake = MagicMock()
    result = MagicMock()
    result.column_names = ["id", "category", "screen_time_seconds", "brand_safety_score", "estimated_value_usd"]
    result.result_rows = [("opp_1", "Consumer audio", 26, 96.0, 185000.0)]
    fake.query.return_value = result
    return fake


def _fake_match(campaign_id: str, is_blocked: bool = False) -> CampaignMatch:
    return CampaignMatch(
        campaign_id=campaign_id,
        opportunity_id="opp_1",
        brand="Aurelius Systems",
        campaign_name="Focus Without Limits",
        product_line="Aurelius One Wireless Headphones",
        score=88.5,
        score_breakdown=ScoreBreakdown(
            context_fit=90.0, category_fit=100.0, visibility=80.0,
            brand_safety=96.0, territory=100.0, budget_and_terms=100.0,
        ),
        is_blocked=is_blocked,
        blocked_reason=None,
        territories=["US", "CA", "GB"],
    )


def test_matches_endpoint_persists_match_events():
    fake_matches = [_fake_match("camp_a"), _fake_match("camp_b", is_blocked=True)]

    with patch(
        "cineyield.routers.v1.opportunities.get_settings", return_value=_mock_settings(True)
    ), patch(
        "cineyield.routers.v1.opportunities.get_clickhouse_client", return_value=_fake_opp_client()
    ), patch(
        "cineyield.routers.v1.opportunities.MarketAgent"
    ) as MockAgent, patch(
        "cineyield.db.repository.write_match_events"
    ) as mock_write:
        MockAgent.return_value.run = AsyncMock(return_value={
            "matches": fake_matches,
            "total_scanned": 27,
            "ranked_count": 1,
            "mcp_latency_ms": 42,
        })

        resp = client.get("/api/v1/opportunities/opp_1/matches")

    assert resp.status_code == 200
    mock_write.assert_called_once()
    written = mock_write.call_args[0][0]
    assert len(written) == 2
    assert {d["campaign_id"] for d in written} == {"camp_a", "camp_b"}
    assert any(not d["is_blocked"] for d in written)
    assert any(d["is_blocked"] for d in written)


def test_matches_endpoint_does_not_persist_when_no_matches():
    with patch(
        "cineyield.routers.v1.opportunities.get_settings", return_value=_mock_settings(True)
    ), patch(
        "cineyield.routers.v1.opportunities.get_clickhouse_client", return_value=_fake_opp_client()
    ), patch(
        "cineyield.routers.v1.opportunities.MarketAgent"
    ) as MockAgent, patch(
        "cineyield.db.repository.write_match_events"
    ) as mock_write:
        MockAgent.return_value.run = AsyncMock(return_value={
            "matches": [], "total_scanned": 27, "ranked_count": 0, "mcp_latency_ms": 10,
        })

        resp = client.get("/api/v1/opportunities/opp_1/matches")

    assert resp.status_code == 200
    mock_write.assert_not_called()


def test_matches_endpoint_persist_failure_does_not_break_response():
    """A ClickHouse write failure must not turn a successful scan into a 500."""
    with patch(
        "cineyield.routers.v1.opportunities.get_settings", return_value=_mock_settings(True)
    ), patch(
        "cineyield.routers.v1.opportunities.get_clickhouse_client", return_value=_fake_opp_client()
    ), patch(
        "cineyield.routers.v1.opportunities.MarketAgent"
    ) as MockAgent, patch(
        "cineyield.db.repository.write_match_events", side_effect=RuntimeError("ClickHouse down")
    ):
        MockAgent.return_value.run = AsyncMock(return_value={
            "matches": [_fake_match("camp_a")], "total_scanned": 27, "ranked_count": 1, "mcp_latency_ms": 10,
        })

        resp = client.get("/api/v1/opportunities/opp_1/matches")

    assert resp.status_code == 200
    assert resp.json()["ranked_count"] == 1


# ─────────────────────────────────────────────────────────────────────────────
# POST /api/v1/opportunities/{id}/propose
#
# TASK 1 (P0 audit fix): this endpoint used to query cineyield.brand_campaigns
# directly via client.query() and never imported MarketAgent/mcp_market at
# all, so the "Open Deal" button's deal-creation step never touched the
# official mcp-clickhouse integration. These tests lock in that /propose now
# gets its campaign data exclusively from MarketAgent.run() (the same MCP
# path GET .../matches uses), and fails clearly instead of silently falling
# back to a direct query when the requested campaign isn't among the
# MCP-scored candidates.
# ─────────────────────────────────────────────────────────────────────────────

def _fake_propose_client() -> MagicMock:
    """.query.side_effect has exactly 2 results (opp, scene) -- a 3rd call
    (e.g. a direct SELECT ... FROM brand_campaigns, as the pre-fix endpoint
    used to make) raises StopIteration and fails the test with a 500."""
    fake = MagicMock()
    opp_result = MagicMock()
    opp_result.column_names = [
        "id", "scene_id", "asset_id", "category", "object_label",
        "timecode_start", "timecode_end", "screen_time_seconds",
        "naturalness_score", "brand_safety_score", "complexity",
        "rights_status", "estimated_value_usd", "is_primary",
    ]
    opp_result.result_rows = [(
        "opp_1", "scene_1", "asset_1", "Consumer audio", "Headphones",
        "00:00:05", "00:00:30", 26,
        90.0, 96.0, "Medium",
        "cleared", 185000.0, True,
    )]
    scene_result = MagicMock()
    scene_result.column_names = ["id", "name", "summary", "mood", "narrative_weight", "brand_safety_score"]
    scene_result.result_rows = [("scene_1", "Rooftop Scene", "A quiet moment.", "Reflective", "High", 96.0)]
    fake.query.side_effect = [opp_result, scene_result]
    return fake


def _fake_raw_campaign(campaign_id: str) -> dict:
    return {
        "id": campaign_id,
        "brand": "Aurelius Systems",
        "campaign_name": "Focus Without Limits",
        "product_line": "Aurelius One Wireless Headphones",
        "budget_min_usd": 150_000.0,
        "budget_max_usd": 250_000.0,
        "target_categories": ["Consumer audio"],
        "excluded_contexts": [],
        "territories": ["US", "CA", "GB"],
        "visibility_seconds_min": 5,
        "visibility_seconds_max": 40,
    }


def _mock_market_agent_run(matches, raw_campaigns, mcp_latency_ms=42):
    return AsyncMock(return_value={
        "matches": matches,
        "raw_campaigns": raw_campaigns,
        "total_scanned": len(raw_campaigns),
        "ranked_count": sum(1 for m in matches if not m.is_blocked),
        "blocked_count": sum(1 for m in matches if m.is_blocked),
        "mcp_latency_ms": mcp_latency_ms,
    })


def test_propose_gets_campaign_via_market_agent_not_direct_query():
    fake_match = _fake_match("camp_a")
    raw_campaigns = [_fake_raw_campaign("camp_a")]

    with patch(
        "cineyield.routers.v1.opportunities.get_settings", return_value=_mock_settings(True)
    ), patch(
        "cineyield.routers.v1.opportunities.get_clickhouse_client", return_value=_fake_propose_client()
    ), patch(
        "cineyield.routers.v1.opportunities.MarketAgent"
    ) as MockAgent, patch(
        "cineyield.agents.creative_guardian.CreativeGuardian"
    ) as MockGuardian, patch(
        "cineyield.agents.deal_agent.DealAgent"
    ) as MockDeal, patch(
        "cineyield.db.repository.upsert_proposal"
    ) as mock_upsert, patch(
        "cineyield.db.repository.write_agent_event"
    ) as mock_event:
        MockAgent.return_value.run = _mock_market_agent_run([fake_match], raw_campaigns)
        MockGuardian.return_value.run = AsyncMock(return_value={"guardrails": [{"name": "Test", "detail": "ok"}]})
        MockDeal.return_value.run = AsyncMock(return_value={
            "id": "prop_123",
            "placement_fee_usd": 12345.0,
            "brand_brief": "A great fit.",
            "terms": [{"label": "Fee", "value": "$12,345"}],
        })

        resp = client.post("/api/v1/opportunities/opp_1/propose", json={"campaign_id": "camp_a"})

    assert resp.status_code == 200, resp.text
    body = resp.json()

    # MarketAgent (the MCP path) was actually invoked, once, with this opportunity.
    MockAgent.return_value.run.assert_called_once()
    ctx = MockAgent.return_value.run.call_args[0][0]
    assert ctx.opportunity_id == "opp_1"
    assert ctx.extra["opportunity"]["id"] == "opp_1"

    # Response is backward-compatible with ProposeResponse (api-client.ts) ...
    for key in [
        "proposal_id", "brand_name", "campaign_name", "placement_fee_usd",
        "brand_brief", "scene_title", "scene_description", "composite_score",
        "terms", "guardrails",
    ]:
        assert key in body, f"missing {key!r} in propose response"

    assert body["proposal_id"] == "prop_123"
    assert body["brand_name"] == "Aurelius Systems"
    assert body["campaign_name"] == "Focus Without Limits"
    assert body["placement_fee_usd"] == 12345.0
    # ... and composite_score now reflects the real MCP-scored match instead
    # of the old dead "composite" key that always fell back to 70.0.
    assert body["composite_score"] == fake_match.score == 88.5
    # Additive evidence field proving this call went through mcp-clickhouse.
    assert body["mcp_latency_ms"] == 42

    mock_upsert.assert_called_once()
    mock_event.assert_called_once()


def test_propose_404_when_campaign_not_among_mcp_candidates():
    """The requested campaign_id must come back from mcp-clickhouse's scored
    candidates — /propose must fail clearly rather than silently querying
    ClickHouse directly for a campaign MCP didn't return."""
    fake_match = _fake_match("camp_a")
    raw_campaigns = [_fake_raw_campaign("camp_a")]

    with patch(
        "cineyield.routers.v1.opportunities.get_settings", return_value=_mock_settings(True)
    ), patch(
        "cineyield.routers.v1.opportunities.get_clickhouse_client", return_value=_fake_propose_client()
    ), patch(
        "cineyield.routers.v1.opportunities.MarketAgent"
    ) as MockAgent:
        MockAgent.return_value.run = _mock_market_agent_run([fake_match], raw_campaigns)

        resp = client.post("/api/v1/opportunities/opp_1/propose", json={"campaign_id": "camp_zzz_missing"})

    assert resp.status_code == 404
    assert "mcp-clickhouse-scored candidates" in resp.json()["detail"]


def test_propose_returns_503_when_clickhouse_not_configured():
    with patch(
        "cineyield.routers.v1.opportunities.get_settings", return_value=_mock_settings(False)
    ):
        resp = client.post("/api/v1/opportunities/opp_1/propose", json={"campaign_id": "camp_a"})
    assert resp.status_code == 503


@pytest.mark.asyncio
async def test_propose_returns_502_not_500_when_mcp_is_unreachable():
    """An mcp-clickhouse failure on the "Open Deal" click must not be a bare 500.

    /propose deliberately requires the MCP path, so when that path fails the
    honest answer is an upstream-dependency error with a readable message --
    never a stack trace, and never a silent fall back to a direct ClickHouse
    query, which would make the partner integration unfalsifiable.
    """
    from fastapi import HTTPException

    from cineyield.routers.v1 import opportunities as opps

    class _DeadMarketAgent:
        def __init__(self, *a, **kw):
            pass

        async def run(self, _ctx):
            raise RuntimeError("mcp-clickhouse executable not found")

    with patch(
        "cineyield.routers.v1.opportunities.get_settings", return_value=_mock_settings(True)
    ), patch(
        "cineyield.routers.v1.opportunities.get_clickhouse_client", return_value=_fake_opp_client()
    ), patch(
        "cineyield.routers.v1.opportunities.MarketAgent", _DeadMarketAgent
    ):
        with pytest.raises(HTTPException) as exc:
            await opps.create_proposal("opp_x", opps.ProposeRequest(campaign_id="camp_x"))

    assert exc.value.status_code == 502
    detail = str(exc.value.detail).lower()
    assert "mcp-clickhouse" in detail
    assert "no proposal was created" in detail
