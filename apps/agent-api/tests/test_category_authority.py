"""The analyzed opportunity category is authoritative, not the orchestrator's guess.

The ADK orchestrator is an LLM: it chooses `discover_campaigns_tool`'s arguments
by function-calling. In a real pipeline run it passed the detected object label
("Smartphone") rather than the taxonomy category ("Mobile devices"). Scoring
hard-blocks on category mismatch, so that override silently blocked all 27
campaigns and the pipeline produced a scene and then no deal at all.

These tests pin both halves of the fix: scoring must not treat a blank category
as a wildcard, and the tool must not let the model overwrite a real category.
"""
from cineyield.agents.scoring import score_campaigns

CAMPAIGNS = [
    {
        "id": "camp_a",
        "target_categories": ["Mobile devices"],
        "excluded_contexts": [],
        "territories": ["US", "CA", "GB"],
        "visibility_seconds_min": 1,
        "visibility_seconds_max": 60,
        "budget_min_usd": 10_000.0,
        "budget_max_usd": 100_000.0,
    },
    {
        "id": "camp_b",
        "target_categories": ["Beauty"],
        "excluded_contexts": [],
        "territories": ["US"],
        "visibility_seconds_min": 1,
        "visibility_seconds_max": 60,
        "budget_min_usd": 10_000.0,
        "budget_max_usd": 100_000.0,
    },
]

COMMON = dict(
    opportunity_territories=["US", "CA", "GB"],
    screen_time_seconds=5,
    estimated_value_usd=6_800.0,
    brand_safety_score=95.0,
    scene_mood="Tense",
    scene_narrative_weight="Low",
)


def _unblocked(category: str) -> list[str]:
    scored = score_campaigns(CAMPAIGNS, opportunity_category=category, **COMMON)
    return [s.campaign_id for s in scored if not s.is_blocked]


def test_correct_category_matches_only_the_right_campaign():
    assert _unblocked("Mobile devices") == ["camp_a"]


def test_category_match_is_case_insensitive():
    assert _unblocked("mobile DEVICES") == ["camp_a"]


def test_object_label_instead_of_category_blocks_everything():
    """This is the observed failure: the LLM passed the object label."""
    assert _unblocked("Smartphone") == []


def test_blank_category_is_not_a_wildcard():
    """Regression: substring matching made "" match every campaign.

    A blank category previously scored 100.0 against all campaigns, presenting
    every one of them as a deterministically validated match. It must fail
    closed instead -- no category is no evidence of fit, not universal fit.
    """
    assert _unblocked("") == []
    assert _unblocked("   ") == []


def test_blank_target_category_does_not_match_everything():
    campaigns = [{**CAMPAIGNS[0], "id": "camp_blank", "target_categories": ["", "  "]}]
    scored = score_campaigns(campaigns, opportunity_category="Mobile devices", **COMMON)
    assert [s.campaign_id for s in scored if not s.is_blocked] == []


def test_tool_does_not_let_the_model_overwrite_a_real_category(monkeypatch):
    """discover_campaigns_tool must treat the analyzed category as authoritative.

    Behavioural, not a source-text pin (that broke on any reformat while
    proving nothing about actual behaviour, and would keep passing even if
    an inverted guard silently let the model's argument win). This drives
    the tool end to end with a fake MarketAgent and asserts the category the
    agent actually received.
    """
    from unittest.mock import MagicMock

    import cineyield.agents.market_agent as market_agent_module
    import cineyield.config as config_module
    from cineyield.agents import pipeline

    captured: dict = {}

    class _FakeMarketAgent:
        async def run(self, ctx):
            captured["category"] = ctx.extra["opportunity"].get("category")
            return {
                "matches": [],
                "total_scanned": 27,
                "ranked_count": 0,
                "blocked_count": 27,
                "mcp_latency_ms": 1,
                "summary": "fake",
            }

    monkeypatch.setattr(market_agent_module, "MarketAgent", _FakeMarketAgent)

    # discover_campaigns_tool does its own local `from ..config import
    # get_settings` write-path check; force it False so this test can't
    # reach the real ClickHouse configured via .env.
    not_configured = MagicMock()
    not_configured.clickhouse_configured = False
    monkeypatch.setattr(config_module, "get_settings", lambda: not_configured)

    pipeline._init_state()
    st = pipeline._state()
    st["scene"] = {"scene_id": "sc_test"}
    st["asset_id"] = "asset_test"
    st["opportunities"] = [{"id": "opp_test", "category": "Consumer audio"}]

    pipeline.discover_campaigns_tool(category="Smartphone")

    assert captured["category"] == "Consumer audio", (
        "discover_campaigns_tool must only fall back to the model-supplied "
        "category when scene analysis produced none"
    )


# ─── Blank mood must not behave as a wildcard ────────────────────────────────
#
# Matching is substring based and "" is a substring of every string, so a blank
# scene mood used to match every excluded_context and hard-block the campaign.
# GET /matches passed no mood at all, so it reported 1 of 27 campaigns unblocked
# while /propose, which passes the real scene, reported 7 -- and the two
# disagreed about which campaign was even the best match.
#
# Note the deliberate asymmetry with category: a blank CATEGORY fails closed
# (no evidence of fit, so do not match), while a blank MOOD fails open (no
# evidence of a conflict, so do not block). Both refuse to treat "" as a
# wildcard; they just differ on which direction is the safe one.

_EXCLUDING = [
    {
        "id": "camp_excl",
        "target_categories": ["Mobile devices"],
        "excluded_contexts": ["violence", "tragedy"],
        "territories": ["US", "CA", "GB"],
        "visibility_seconds_min": 1,
        "visibility_seconds_max": 60,
        "budget_min_usd": 10_000.0,
        "budget_max_usd": 100_000.0,
    },
]


def _score(mood: str, narrative_weight: str = ""):
    return score_campaigns(
        _EXCLUDING,
        opportunity_category="Mobile devices",
        opportunity_territories=["US", "CA", "GB"],
        screen_time_seconds=5,
        estimated_value_usd=6_800.0,
        brand_safety_score=95.0,
        scene_mood=mood,
        scene_narrative_weight=narrative_weight,
    )


def test_blank_mood_does_not_block_every_excluded_context():
    scored = _score("")
    assert [s.campaign_id for s in scored if not s.is_blocked] == ["camp_excl"]


def test_whitespace_mood_is_treated_as_blank():
    assert [s.campaign_id for s in _score("   ") if not s.is_blocked] == ["camp_excl"]


def test_a_real_conflicting_mood_still_blocks():
    scored = _score("Violence")
    assert [s.campaign_id for s in scored if not s.is_blocked] == []
    assert "adjacency conflict" in (scored[0].blocked_reason or "")


def test_a_real_non_conflicting_mood_does_not_block():
    assert [s.campaign_id for s in _score("Dusk") if not s.is_blocked] == ["camp_excl"]


def test_blank_excluded_context_entry_is_not_a_wildcard():
    campaigns = [{**_EXCLUDING[0], "excluded_contexts": ["", "  "]}]
    scored = score_campaigns(
        campaigns,
        opportunity_category="Mobile devices",
        opportunity_territories=["US", "CA", "GB"],
        screen_time_seconds=5,
        estimated_value_usd=6_800.0,
        brand_safety_score=95.0,
        scene_mood="Dusk",
        scene_narrative_weight="High",
    )
    assert [s.campaign_id for s in scored if not s.is_blocked] == ["camp_excl"]
