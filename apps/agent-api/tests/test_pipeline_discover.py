"""Tests for cineyield.agents.pipeline.discover_campaigns_tool.

Covers two review findings:

FIX 1 (P0): discover_campaigns_tool is the other real call site for
MarketAgent.run() (besides routers/v1/opportunities.py) and must also
persist to cineyield.match_events, or a pipeline-run demo would still show
total_matches == 0 even after the opportunities.py fix.

FIX 4 (P1), "pipeline.py:196 only opportunities[0] is ever scored": a scene
can yield several detected placement opportunities, and a bad first
detection (blocked category, no budget fit, etc.) used to sink the whole
run even when a later opportunity in the same scene would have matched.
discover_campaigns_tool now tries each candidate in order and stops at the
first unblocked match.
"""
from unittest.mock import MagicMock

from cineyield.agents import pipeline
from cineyield.schemas.matching import CampaignMatch, ScoreBreakdown


def _match(campaign_id: str, opportunity_id: str, is_blocked: bool = False) -> CampaignMatch:
    return CampaignMatch(
        campaign_id=campaign_id,
        opportunity_id=opportunity_id,
        brand="Aurelius Systems",
        campaign_name="Focus Without Limits",
        product_line="Aurelius One Wireless Headphones",
        score=88.5,
        score_breakdown=ScoreBreakdown(
            context_fit=90.0, category_fit=100.0, visibility=80.0,
            brand_safety=96.0, territory=100.0, budget_and_terms=100.0,
        ),
        is_blocked=is_blocked,
        blocked_reason="Category mismatch" if is_blocked else None,
        territories=["US", "CA", "GB"],
    )


def _not_configured_settings():
    settings = MagicMock()
    settings.clickhouse_configured = False
    return settings


def _configured_settings():
    settings = MagicMock()
    settings.clickhouse_configured = True
    return settings


def test_discover_campaigns_tool_persists_match_events(monkeypatch):
    """FIX 1: pipeline's discover_campaigns_tool must also call
    repository.write_match_events for the matches it actually used."""
    import cineyield.agents.market_agent as market_agent_module
    import cineyield.config as config_module
    import cineyield.db.repository as repository_module

    fake_matches = [_match("camp_a", "opp_only"), _match("camp_b", "opp_only", is_blocked=True)]

    class _FakeMarketAgent:
        async def run(self, ctx):
            return {
                "matches": fake_matches,
                "total_scanned": 27,
                "ranked_count": 1,
                "blocked_count": 1,
                "mcp_latency_ms": 5,
                "summary": "fake",
            }

    monkeypatch.setattr(market_agent_module, "MarketAgent", _FakeMarketAgent)
    monkeypatch.setattr(config_module, "get_settings", _configured_settings)

    written = {}

    def _fake_write_match_events(matches):
        written["matches"] = matches

    monkeypatch.setattr(repository_module, "write_match_events", _fake_write_match_events)
    monkeypatch.setattr(repository_module, "write_agent_event", lambda **kw: "evt_1")

    pipeline._init_state()
    st = pipeline._state()
    st["scene"] = {"scene_id": "sc_1"}
    st["asset_id"] = "asset_1"
    st["opportunities"] = [{"id": "opp_only", "category": "Consumer audio"}]

    pipeline.discover_campaigns_tool()

    assert "matches" in written, "discover_campaigns_tool did not call repository.write_match_events"
    campaign_ids = {d["campaign_id"] for d in written["matches"]}
    assert campaign_ids == {"camp_a", "camp_b"}


def test_discover_campaigns_tool_skips_persist_when_not_configured(monkeypatch):
    import cineyield.agents.market_agent as market_agent_module
    import cineyield.config as config_module
    import cineyield.db.repository as repository_module

    class _FakeMarketAgent:
        async def run(self, ctx):
            return {
                "matches": [_match("camp_a", "opp_only")],
                "total_scanned": 27, "ranked_count": 1, "blocked_count": 0,
                "mcp_latency_ms": 5, "summary": "fake",
            }

    monkeypatch.setattr(market_agent_module, "MarketAgent", _FakeMarketAgent)
    monkeypatch.setattr(config_module, "get_settings", _not_configured_settings)

    write_calls = []
    monkeypatch.setattr(repository_module, "write_match_events", lambda m: write_calls.append(m))

    pipeline._init_state()
    st = pipeline._state()
    st["scene"] = {"scene_id": "sc_1"}
    st["asset_id"] = "asset_1"
    st["opportunities"] = [{"id": "opp_only", "category": "Consumer audio"}]

    pipeline.discover_campaigns_tool()

    assert write_calls == []


def test_discover_campaigns_tool_tries_second_opportunity_when_first_is_fully_blocked(monkeypatch):
    """FIX 4: opportunities[0] blocked everywhere must not sink a scene
    where opportunities[1] has a real match."""
    import cineyield.agents.market_agent as market_agent_module
    import cineyield.config as config_module

    monkeypatch.setattr(config_module, "get_settings", _not_configured_settings)

    calls = []

    class _FakeMarketAgent:
        async def run(self, ctx):
            opp_id = ctx.extra["opportunity"]["id"]
            calls.append(opp_id)
            if opp_id == "opp_bad":
                return {
                    "matches": [_match("camp_a", "opp_bad", is_blocked=True)],
                    "total_scanned": 27, "ranked_count": 0, "blocked_count": 27,
                    "mcp_latency_ms": 5, "summary": "blocked",
                }
            return {
                "matches": [_match("camp_a", "opp_good")],
                "total_scanned": 27, "ranked_count": 1, "blocked_count": 26,
                "mcp_latency_ms": 5, "summary": "matched",
            }

    monkeypatch.setattr(market_agent_module, "MarketAgent", _FakeMarketAgent)

    pipeline._init_state()
    st = pipeline._state()
    st["scene"] = {"scene_id": "sc_1"}
    st["asset_id"] = "asset_1"
    st["opportunities"] = [
        {"id": "opp_bad", "category": "Other"},
        {"id": "opp_good", "category": "Consumer audio"},
    ]

    result = pipeline.discover_campaigns_tool()

    assert calls == ["opp_bad", "opp_good"], "must try opp_bad first, then fall through to opp_good"
    assert result["ranked_count"] == 1
    assert pipeline._state()["opportunity"]["id"] == "opp_good"


def test_discover_campaigns_tool_stops_at_first_opportunity_that_matches(monkeypatch):
    """No wasted MCP calls when opportunities[0] already matches."""
    import cineyield.agents.market_agent as market_agent_module
    import cineyield.config as config_module

    monkeypatch.setattr(config_module, "get_settings", _not_configured_settings)

    calls = []

    class _FakeMarketAgent:
        async def run(self, ctx):
            calls.append(ctx.extra["opportunity"]["id"])
            return {
                "matches": [_match("camp_a", "opp_first")],
                "total_scanned": 27, "ranked_count": 1, "blocked_count": 26,
                "mcp_latency_ms": 5, "summary": "matched",
            }

    monkeypatch.setattr(market_agent_module, "MarketAgent", _FakeMarketAgent)

    pipeline._init_state()
    st = pipeline._state()
    st["scene"] = {"scene_id": "sc_1"}
    st["asset_id"] = "asset_1"
    st["opportunities"] = [
        {"id": "opp_first", "category": "Consumer audio"},
        {"id": "opp_second", "category": "Consumer audio"},
    ]

    pipeline.discover_campaigns_tool()

    assert calls == ["opp_first"]


def test_discover_campaigns_tool_reports_first_candidate_when_all_blocked(monkeypatch):
    """Total dead end (nothing unblocked anywhere) must still report the
    first candidate's result, not silently discard every attempt."""
    import cineyield.agents.market_agent as market_agent_module
    import cineyield.config as config_module

    monkeypatch.setattr(config_module, "get_settings", _not_configured_settings)

    class _FakeMarketAgent:
        async def run(self, ctx):
            opp_id = ctx.extra["opportunity"]["id"]
            return {
                "matches": [_match("camp_a", opp_id, is_blocked=True)],
                "total_scanned": 27, "ranked_count": 0, "blocked_count": 27,
                "mcp_latency_ms": 5, "summary": "blocked",
            }

    monkeypatch.setattr(market_agent_module, "MarketAgent", _FakeMarketAgent)

    pipeline._init_state()
    st = pipeline._state()
    st["scene"] = {"scene_id": "sc_1"}
    st["asset_id"] = "asset_1"
    st["opportunities"] = [
        {"id": "opp_a", "category": "Other"},
        {"id": "opp_b", "category": "Other"},
    ]

    result = pipeline.discover_campaigns_tool()

    assert result["ranked_count"] == 0
    assert pipeline._state()["opportunity"]["id"] == "opp_a"
